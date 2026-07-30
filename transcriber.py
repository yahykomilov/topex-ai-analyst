import logging
from pathlib import Path

from openai import AsyncOpenAI

from config import (
    GROQ_API_KEY,
    GROQ_BASE_URL,
    GROQ_WHISPER_MODEL,
    OPENAI_API_KEY,
    WHISPER_LANGUAGE,
)

log = logging.getLogger("transcriber")

# Если задан GROQ_API_KEY — расшифровка идёт через Groq (бесплатный тариф),
# иначе через OpenAI Whisper.
if GROQ_API_KEY:
    _client = AsyncOpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)
    _model = GROQ_WHISPER_MODEL
else:
    _client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    _model = "whisper-1"

# Whisper принимает: mp3, mp4, mpeg, mpga, m4a, wav, webm, ogg/oga, flac
WHISPER_MAX_BYTES = 25 * 1024 * 1024


async def transcribe(audio_path: Path) -> str:
    size = audio_path.stat().st_size
    if size > WHISPER_MAX_BYTES:
        raise ValueError(
            f"Файл {size // 1024 // 1024} МБ — больше лимита Whisper (25 МБ)."
        )
    log.info("Расшифровка %s (%d КБ) через %s...", audio_path.name, size // 1024, _model)
    with open(audio_path, "rb") as f:
        # если WHISPER_LANGUAGE задан (uz) — расшифровка строго на этом языке,
        # иначе Whisper определяет язык сам
        kwargs = {"model": _model, "file": f, "response_format": "text"}
        if WHISPER_LANGUAGE:
            kwargs["language"] = WHISPER_LANGUAGE
        result = await _client.audio.transcriptions.create(**kwargs)
    text = result if isinstance(result, str) else getattr(result, "text", str(result))
    return text.strip()
