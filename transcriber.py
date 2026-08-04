"""
# Topex AI Analyst — Transcriber
#
# Why stoic #4 — Качество распознавания на узбекском
# Мульти-провайдер: Groq Whisper #1 → OpenAI Whisper → Gemini
# + автоопределение языка, предобработка аудио.
"""

import asyncio
import logging
import re
from pathlib import Path

from openai import AsyncOpenAI

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GROQ_API_KEY,
    GROQ_API_KEY_2,
    GROQ_BASE_URL,
    GROQ_WHISPER_MODEL,
    OPENAI_API_KEY,
    OPENAI_TRANSCRIBE_MODEL,
    WHISPER_LANGUAGE,
)

log = logging.getLogger("transcriber")

# Whisper принимает: mp3, mp4, mpeg, mpga, m4a, wav, webm, ogg/oga, flac
WHISPER_MAX_BYTES = 25 * 1024 * 1024

# Если транскрипт короче — считаем что Whisper не справился
MIN_TRANSCRIPT_LENGTH = 30

# ---------------------------------------------------------------------------
# Провайдеры
# ---------------------------------------------------------------------------

_PROVIDERS: list[dict] = []

# OpenAI — платный основной провайдер (если ключ задан).
# Качество лучше Groq-Whisper, особенно на узбекском; цена см. OPENAI_TRANSCRIBE_MODEL.
if OPENAI_API_KEY:
    _PROVIDERS.append({
        "name": "OpenAI Transcribe",
        "client": AsyncOpenAI(api_key=OPENAI_API_KEY),
        "model": OPENAI_TRANSCRIBE_MODEL,
    })

# Groq — бесплатный fallback (если OpenAI не задан или не справился)
if GROQ_API_KEY:
    _PROVIDERS.append({
        "name": "Groq Whisper #1",
        "client": AsyncOpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL),
        "model": GROQ_WHISPER_MODEL,
    })

if GROQ_API_KEY_2:
    _PROVIDERS.append({
        "name": "Groq Whisper #2",
        "client": AsyncOpenAI(api_key=GROQ_API_KEY_2, base_url=GROQ_BASE_URL),
        "model": GROQ_WHISPER_MODEL,
    })


async def transcribe(audio_path: Path) -> str:
    """
    Расшифровка аудио с мульти-провайдерным Fallback.

    Цепочка:
      1. OpenAI Transcribe (основной, платный — gpt-4o-mini-transcribe / gpt-4o-transcribe)
      2. Groq Whisper #1 (бесплатный fallback)
      3. Groq Whisper #2 (запасной ключ)
      4. Gemini Flash (если Groq не справился с узбекским)

    Если язык WHISPER_LANGUAGE=uz и результат подозрительно короткий —
    пробуем Gemini (у него лучше с multiligual).
    """
    size = audio_path.stat().st_size
    if size > WHISPER_MAX_BYTES and not GEMINI_API_KEY:
        raise ValueError(
            f"Файл {size // 1024 // 1024} МБ — больше лимита Whisper (25 МБ). "
            "Используйте GEMINI_API_KEY для больших файлов."
        )

    # Узбекский: Gemini слушает само аудио и различает говорящих по голосам —
    # даёт точнее и сразу с ролями (Operator/Mijoz), чего Whisper не умеет.
    # Поэтому для uz Gemini — ОСНОВНОЙ, а Whisper ниже остаётся страховкой.
    if WHISPER_LANGUAGE == "uz" and GEMINI_API_KEY:
        try:
            gemini_text = await _gemini_transcribe(audio_path)
            if _quality_check(gemini_text, min_len=10):
                log.info("Gemini (uz, основной): %d символов", len(gemini_text))
                return gemini_text
            log.info("Gemini (uz): качество низкое, пробую Whisper")
        except Exception as e:
            log.warning("Gemini (uz, основной): ошибка — %s, пробую Whisper", e)

    # Пробуем Whisper-провайдеры (Groq #1 → Groq #2 → OpenAI)
    whisper_text = ""
    for p in _PROVIDERS:
        try:
            whisper_text = await _whisper_transcribe(p["client"], p["model"], audio_path)
            log.info("%s: %d символов", p["name"], len(whisper_text))

            if _quality_check(whisper_text):
                log.info("%s: качество норм, берём", p["name"])
                return whisper_text
            else:
                log.info("%s: качество низкое, пробуем следующий", p["name"])
        except Exception as e:
            log.warning("%s: ошибка — %s", p["name"], e)
            continue

    # Если Whisper не дал нормального текста — пробуем Gemini
    if GEMINI_API_KEY and not _quality_check(whisper_text):
        try:
            gemini_text = await _gemini_transcribe(audio_path)
            log.info("Gemini: %d символов", len(gemini_text))
            if _quality_check(gemini_text, min_len=10):
                return gemini_text
        except Exception as e:
            log.warning("Gemini: ошибка — %s", e)

    # Если ничего не вышло — возвращаем лучшее из Whisper
    if whisper_text:
        return whisper_text

    raise RuntimeError("Все провайдеры расшифровки недоступны.")


# ---------------------------------------------------------------------------
# INTERNAL: Whisper
# ---------------------------------------------------------------------------


async def _whisper_transcribe(
    client: AsyncOpenAI, model: str, audio_path: Path
) -> str:
    """Один запрос к Whisper (OpenAI-совместимый API)."""
    with open(audio_path, "rb") as f:
        kwargs = {"model": model, "file": f, "response_format": "text"}
        if WHISPER_LANGUAGE:
            kwargs["language"] = WHISPER_LANGUAGE
        result = await client.audio.transcriptions.create(**kwargs)
    text = result if isinstance(result, str) else getattr(result, "text", str(result))
    return text.strip()


# ---------------------------------------------------------------------------
# INTERNAL: Gemini
# ---------------------------------------------------------------------------


async def _gemini_transcribe(audio_path: Path) -> str:
    """Расшифровка через Google Gemini (хорош для узбекского)."""
    try:
        from google import genai

        gemini_client = genai.Client(api_key=GEMINI_API_KEY)

        # Загружаем файл в Gemini (синхронно, но быстро)
        file = await asyncio.to_thread(gemini_client.files.upload, file=audio_path)

        # Ждём обработки (polling с таймаутом ~30 сек — иначе риск зависнуть навсегда)
        for _ in range(30):
            meta = await asyncio.to_thread(gemini_client.files.get, name=file.name)
            if meta.state.name == "ACTIVE":
                break
            if meta.state.name == "FAILED":
                raise RuntimeError(f"Gemini file processing failed: {meta}")
            await asyncio.sleep(1)
        else:
            raise RuntimeError("Gemini: файл не обработан за 30 сек (таймаут)")

        prompt = (
            "This is a phone call between a sales operator and a client, "
            "in Uzbek or Russian. Transcribe it word for word in the original "
            "spoken language. There are TWO speakers — tell them apart BY VOICE "
            "and label EVERY line as 'Operator:' or 'Mijoz:' (use exactly these "
            "labels). Keep the labels consistent through the whole call. "
            "Output ONLY the labeled dialog, no explanations, no commentary."
        )
        response = await asyncio.to_thread(
            gemini_client.models.generate_content,
            model=GEMINI_MODEL,
            contents=[prompt, file],
        )

        # Чистим
        text = response.text.strip() if response.text else ""
        return text

    except ImportError:
        log.warning("google-genai не установлен — Gemini недоступен")
        return ""
    except Exception as e:
        log.warning("Gemini transcription error: %s", e)
        return ""


# ---------------------------------------------------------------------------
# QUALITY CHECK
# ---------------------------------------------------------------------------


def _quality_check(text: str, min_len: int = MIN_TRANSCRIPT_LENGTH) -> bool:
    """
    Проверяет качество транскрипции.

    Плохое качество если:
    - Слишком короткий текст (< min_len символов)
    - Текст состоит в основном из мусора (не букв)
    """
    if len(text) < min_len:
        return False

    # Считаем долю буквенных символов (кириллица + латиница)
    letters = len(re.findall(r"[a-zA-Zа-яА-ЯўғқҳцёЎҒҚҲ]", text))
    total = len(text)
    ratio = letters / total if total > 0 else 0

    # Если букв меньше 50% — похоже на мусор
    if ratio < 0.5:
        log.debug("Низкое качество: букв %d/%d = %.0f%%", letters, total, ratio * 100)
        return False

    return True
