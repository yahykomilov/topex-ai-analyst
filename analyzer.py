"""
# Topex AI Analyst — Analyzer
#
# Why stoic #3 — AI baholash sifati
# Детальный парсинг критериев, улучшенный скоринг, fallback-модели.
"""

import logging
import re

import httpx
from openai import AsyncOpenAI, RateLimitError

from config import (
    ANALYSIS_MODEL,
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
    GROQ_ANALYSIS_MODEL,
    GROQ_API_KEY,
    GROQ_BASE_URL,
    OPENAI_API_KEY,
)
from prompt import (
    SYSTEM_PROMPT,
    TEAM_PROMPT,
    UZ_DIALOG_PROMPT,
    UZ_TZ_PROMPT,
    build_user_message,
    CRITERIA_KEYS,
    MAX_CRITERIA_SCORE,
    CRITERIA_COUNT,
    MAX_TOTAL_SCORE,
)

log = logging.getLogger("analyzer")

# ---------------------------------------------------------------------------
# LLM Client init
# Приоритет: Claude > Groq (бесплатно) > OpenAI
# ---------------------------------------------------------------------------
if GROQ_API_KEY and not ANTHROPIC_API_KEY:
    _openai = AsyncOpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)
    _chat_model = GROQ_ANALYSIS_MODEL
else:
    _openai = AsyncOpenAI(api_key=OPENAI_API_KEY)
    _chat_model = ANALYSIS_MODEL

# запасная модель Groq на случай исчерпания дневного лимита основной
GROQ_FALLBACK_MODEL = "llama-3.1-8b-instant"

# ---------------------------------------------------------------------------
# ОСНОВНЫЕ ФУНКЦИИ
# ---------------------------------------------------------------------------


async def analyze_transcript(transcript: str, meta: str = "") -> str:
    """Полный анализ звонка: возвращает отчёт по шаблону из SYSTEM_PROMPT."""
    user_message = build_user_message(transcript, meta)
    if ANTHROPIC_API_KEY:
        report = await _analyze_claude(user_message, SYSTEM_PROMPT)
    else:
        report = await _analyze_openai(user_message, SYSTEM_PROMPT)
    return _sanitize(report)


async def team_report(facts: str, call_summaries: str) -> str:
    """Общий отчёт отдела за день."""
    # Groq free-tier считает в TPM и вход, и запрошенный max_tokens — большой payload
    # ловит 413. Режем выжимки и ограничиваем ответ, чтобы отчёт всегда собирался.
    if len(call_summaries) > 6000:
        call_summaries = call_summaries[:6000] + "\n…(часть выжимок обрезана под лимит модели)"
    user_message = (
        f"СТАТИСТИКА (посчитано точно):\n{facts}\n\n"
        f"ВЫЖИМКИ ИЗ АУДИТОВ ЗВОНКОВ ЗА ДЕНЬ:\n{call_summaries}"
    )
    if ANTHROPIC_API_KEY:
        report = await _analyze_claude(user_message, TEAM_PROMPT, max_tokens=2000)
    else:
        report = await _analyze_openai(user_message, TEAM_PROMPT, max_tokens=2000)
    return _sanitize(report)


async def uz_tz(transcript: str) -> str:
    """Короткое ТЗ для сотрудника на узбекском (что улучшить)."""
    tz_source = (
        transcript
        if len(transcript) <= 9000
        else transcript[:6500] + "\n...\n" + transcript[-2000:]
    )
    tz_message = f'Suhbat transkripti:\n"""\n{tz_source}\n"""'
    if ANTHROPIC_API_KEY:
        tz = await _analyze_claude(tz_message, UZ_TZ_PROMPT, max_tokens=1500)
    else:
        tz = await _analyze_openai(tz_message, UZ_TZ_PROMPT, max_tokens=1500)
    return _sanitize(tz)


async def uz_document(transcript: str) -> str:
    """Полный дословный диалог на узбекском (по кускам) + ТЗ."""
    chunks = _split_chunks(transcript)
    dialog_parts = []
    for i, chunk in enumerate(chunks, 1):
        note = (
            f"(Bu suhbatning {i}-qismi, jami {len(chunks)} qism.)\n"
            if len(chunks) > 1
            else ""
        )
        user_message = f'{note}Transkript qismi:\n"""\n{chunk}\n"""'
        if ANTHROPIC_API_KEY:
            part = await _analyze_claude(
                user_message, UZ_DIALOG_PROMPT, max_tokens=6000
            )
        else:
            part = await _analyze_openai(
                user_message, UZ_DIALOG_PROMPT, max_tokens=6000
            )
        dialog_parts.append(_sanitize(part))
    dialog = "\n".join(dialog_parts)
    tz = await uz_tz(transcript)
    return (
        "SUHBAT MATNI (to'liq dialog):\n\n"
        + dialog
        + "\n\n------------------------------------\n\n"
        + tz
    )


# ---------------------------------------------------------------------------
# ПАРСИНГ ОТЧЁТА: критерии, общая оценка, вердикт
# ---------------------------------------------------------------------------


def extract_criteria_scores(report: str) -> dict[str, int | None]:
    """
    Парсит детальные оценки по 5 критериям из отчёта LLM.
    Ищет паттерны вида:
      - "Приветствие и начало: 2/2"
      - "1. Salomlashish: 1/2"
      - "2. Выявление потребностей: 1/2"

    Возвращает словарь {ключ_критерия: балл_или_None}.
    """
    scores: dict[str, int | None] = {
        "greeting": None,
        "needs": None,
        "objections": None,
        "politeness": None,
        "closing": None,
    }

    # Паттерн: строка с русским или узбекским названием критерия, цифрой и /2
    pattern = re.compile(
        r"(?:^\d\.\s*)?"
        r"(?P<name>"
        r"Приветствие[^:]*|Salomlashish[^:]*|"
        r"Выявление потребностей[^:]*|Ehtiyojni aniqlash[^:]*|"
        r"Работа с возражениями[^:]*|E'tirozlarga javob[^:]*|"
        r"Вежливость[^:]*|Mulozot[^:]*|"
        r"Завершение[^:]*|Yakunlash[^:]*"
        r")"
        r"[:\s]*"
        r"(?P<score>\d+)"
        r"\s*/\s*2",
        re.MULTILINE | re.IGNORECASE,
    )

    for match in pattern.finditer(report):
        name_raw = match.group("name").strip().lower()
        score_val = int(match.group("score"))
        score_val = min(max(score_val, 0), MAX_CRITERIA_SCORE)

        # Маппинг русского/узбекского названия на ключ
        for ru_name, key in CRITERIA_KEYS.items():
            if ru_name.lower() in name_raw or name_raw.startswith(ru_name.lower()):
                scores[key] = score_val
                break

    return scores


def extract_total_score(report: str) -> int | None:
    """
    Парсит общую оценку из отчёта.
    Поддерживает оба формата:
    - Старый: "ОЦЕНКА РАБОТЫ: 7"
    - Новый:  "ОБЩАЯ ОЦЕНКА: 7/10"
    - Узбек:  "UMUMIY BAHO: 7/10"
    """
    pattern = re.compile(
        r"(?:ОБЩАЯ ОЦЕНКА|ОЦЕНКА РАБОТЫ|UMUMIY BAHO)\s*[:\s]*(\d{1,2})"
    )
    m = pattern.search(report)
    if m:
        return min(int(m.group(1)), MAX_TOTAL_SCORE)
    return None


def extract_verdict(report: str, total_score: int | None = None) -> str:
    """
    Определяет вердикт звонка: ok / fail / doubt.
    Использует:
    1. Поле "Итог разговора:" (продал/договорил/слил)
    2. Если не найдено — по общей оценке
    """
    m = re.search(r"Итог разговора:\s*(.+)", report)
    if m:
        outcome = m.group(1).lower()
        # ok keywords
        if any(kw in outcome for kw in ("продал", "договорил", "купил", "заказал")):
            return "ok"
        # fail keywords
        if any(kw in outcome for kw in ("слил", "отказ", "не купил", "не заказал")):
            return "fail"

    # Fallback: по оценке
    if total_score is not None:
        if total_score >= 7:
            return "ok"
        if total_score <= 3:
            return "fail"

    return "doubt"


def extract_metrics(report: str) -> tuple[int | None, str]:
    """
    Основная функция: возвращает (score, verdict) для сохранения в БД.
    Использует новые детальные парсеры, но обратно совместима со старым форматом.
    """
    # Пробуем новый формат (ОБЩАЯ ОЦЕНКА)
    score = extract_total_score(report)

    # Fallback: старый формат (ОЦЕНКА РАБОТЫ)
    if score is None:
        m = re.search(r"ОЦЕНКА РАБОТЫ:\s*(\d{1,2})", report)
        if m:
            score = min(int(m.group(1)), MAX_TOTAL_SCORE)

    verdict = extract_verdict(report, score)
    return score, verdict


def report_excerpt(report: str, max_len: int = 700) -> str:
    """
    Короткая выжимка из отчёта по звонку — для сводного отчёта за день.
    Извлекает: итог, оценку, критические ошибки, главный совет.
    """
    parts = []

    # Итог разговора
    m = re.search(r"Итог разговора:.*", report)
    if m:
        parts.append(m.group(0))

    # Общая оценка (новый формат)
    m = re.search(r"ОБЩАЯ ОЦЕНКА:.*", report)
    if not m:
        # старый формат
        m = re.search(r"ОЦЕНКА РАБОТЫ:.*", report)
    if m:
        parts.append(m.group(0))

    # Оценки по критериям (новые) — берём только строку с баллами
    criteria_lines = re.findall(
        r"^\d\..*?(?:\d/2).*$", report, re.MULTILINE
    )
    if criteria_lines:
        parts.append("Критерии: " + "; ".join(c.strip() for c in criteria_lines[:5]))

    # Что исправить (🔴 секция)
    m = re.search(r"🔴[^➖]*(?=💡|➖|$)", report, re.DOTALL)
    if m:
        parts.append(m.group(0).strip())

    # Главный совет (💡 секция)
    m = re.search(r"💡[^➖]*(?=➖|📋|$)", report, re.DOTALL)
    if m:
        parts.append(m.group(0).strip())

    excerpt = "\n".join(parts) if parts else report
    return excerpt[:max_len]


def extract_summary(report: str) -> str:
    """Короткий вывод + совет для чата. Сам диалог и полный разбор идут в PDF,
    в Telegram — только итог звонка и главный совет оператору."""
    parts = []
    for pat in (r"⭐\s*ОБЩАЯ ОЦЕНКА:.*", r"⏱\s*Итог разговора:.*"):
        m = re.search(pat, report)
        if m:
            parts.append(m.group(0).strip())
    m = re.search(r"💡[^➖]*", report, re.DOTALL)  # секция «СОВЕТ …»
    if m:
        parts.append(m.group(0).strip())
    summary = "\n".join(parts).strip()
    return summary or report_excerpt(report, max_len=500)


# ---------------------------------------------------------------------------
# ВНУТРЕННИЕ ФУНКЦИИ
# ---------------------------------------------------------------------------


def _split_chunks(text: str, size: int = 2200) -> list[str]:
    """Режет текст на куски по предложениям."""
    sentences = re.split(r"(?<=[.!?…])\s+", text)
    chunks, current = [], ""
    for s in sentences:
        if current and len(current) + len(s) + 1 > size:
            chunks.append(current)
            current = s
        else:
            current = f"{current} {s}".strip()
    if current:
        chunks.append(current)
    return chunks or [text]


async def _analyze_openai(
    user_message: str, system_prompt: str, max_tokens: int = 4000
) -> str:
    """
    Отправляет запрос в OpenAI/Groq.
    При RateLimitError — автоматический fallback на запасную модель Groq.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    models_to_try = [_chat_model]
    if GROQ_API_KEY and _chat_model != GROQ_FALLBACK_MODEL:
        models_to_try.append(GROQ_FALLBACK_MODEL)

    last_error = None
    for model in models_to_try:
        try:
            log.info("Анализ через %s...", model)
            resp = await _openai.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=max_tokens,
                timeout=180,
            )
            return resp.choices[0].message.content or ""
        except RateLimitError as e:
            last_error = e
            log.warning("Лимит модели %s исчерпан", model)
            continue
        except Exception as e:
            last_error = e
            log.error("Ошибка модели %s: %s", model, e)
            continue

    # Если все модели упали — пробуем последнюю с повышением лимита
    raise last_error  # type: ignore[misc]


async def _analyze_claude(
    user_message: str, system_prompt: str, max_tokens: int = 4000
) -> str:
    """Отправляет запрос в Anthropic Claude."""
    log.info("Анализ через Claude (%s)...", CLAUDE_MODEL)
    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": CLAUDE_MODEL,
                "max_tokens": max_tokens,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_message}],
            },
        )
        r.raise_for_status()
        data = r.json()
    return "".join(b.get("text", "") for b in data.get("content", []))


def _sanitize(text: str) -> str:
    """Убирает Markdown-разметку для Telegram."""
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^```.*$", "", text, flags=re.MULTILINE)
    return text.strip()
