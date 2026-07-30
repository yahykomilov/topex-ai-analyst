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
)

log = logging.getLogger("analyzer")

# Приоритет анализатора: Claude (если есть ключ) > Groq (бесплатно) > OpenAI
if GROQ_API_KEY and not ANTHROPIC_API_KEY:
    _openai = AsyncOpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)
    _chat_model = GROQ_ANALYSIS_MODEL
else:
    _openai = AsyncOpenAI(api_key=OPENAI_API_KEY)
    _chat_model = ANALYSIS_MODEL


async def analyze_transcript(transcript: str, meta: str = "") -> str:
    user_message = build_user_message(transcript, meta)
    if ANTHROPIC_API_KEY:
        report = await _analyze_claude(user_message, SYSTEM_PROMPT)
    else:
        report = await _analyze_openai(user_message, SYSTEM_PROMPT)
    return _sanitize(report)


async def team_report(facts: str, call_summaries: str) -> str:
    """Общий отчёт отдела за день."""
    user_message = (
        f"СТАТИСТИКА (посчитано точно):\n{facts}\n\n"
        f"ВЫЖИМКИ ИЗ АУДИТОВ ЗВОНКОВ ЗА ДЕНЬ:\n{call_summaries}"
    )
    if ANTHROPIC_API_KEY:
        report = await _analyze_claude(user_message, TEAM_PROMPT)
    else:
        report = await _analyze_openai(user_message, TEAM_PROMPT)
    return _sanitize(report)


def _split_chunks(text: str, size: int = 2200) -> list[str]:
    """Режем текст на куски по предложениям, чтобы модель ничего не сократила."""
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
    """Полный дословный диалог на узбекском (по кускам) + ТЗ. Сейчас не используется."""
    chunks = _split_chunks(transcript)
    dialog_parts = []
    for i, chunk in enumerate(chunks, 1):
        note = f"(Bu suhbatning {i}-qismi, jami {len(chunks)} qism.)\n" if len(chunks) > 1 else ""
        user_message = f'{note}Transkript qismi:\n"""\n{chunk}\n"""'
        if ANTHROPIC_API_KEY:
            part = await _analyze_claude(user_message, UZ_DIALOG_PROMPT, max_tokens=6000)
        else:
            part = await _analyze_openai(user_message, UZ_DIALOG_PROMPT, max_tokens=6000)
        dialog_parts.append(_sanitize(part))
    dialog = "\n".join(dialog_parts)
    tz = await uz_tz(transcript)
    return (
        "SUHBAT MATNI (to'liq dialog):\n\n"
        + dialog
        + "\n\n------------------------------------\n\n"
        + tz
    )


def report_excerpt(report: str, max_len: int = 700) -> str:
    """Короткая выжимка из отчёта по звонку — для сводного отчёта за день."""
    parts = []
    m = re.search(r"Итог разговора:.*", report)
    if m:
        parts.append(m.group(0))
    m = re.search(r"ОЦЕНКА РАБОТЫ:.*", report)
    if m:
        parts.append(m.group(0))
    m = re.search(r"🔴[\s\S]*?(?=🟡|❌|➖|📝|$)", report)
    if m:
        parts.append("Критические ошибки: " + m.group(0).strip())
    m = re.search(r"💡[\s\S]*$", report)
    if m:
        parts.append(m.group(0).strip())
    excerpt = "\n".join(parts) if parts else report
    return excerpt[:max_len]


# запасная модель Groq на случай исчерпания дневного лимита основной
# (у каждой модели Groq свой отдельный лимит токенов в день)
GROQ_FALLBACK_MODEL = "llama-3.1-8b-instant"


async def _analyze_openai(
    user_message: str, system_prompt: str, max_tokens: int = 4000
) -> str:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    try:
        log.info("Анализ через %s...", _chat_model)
        resp = await _openai.chat.completions.create(
            model=_chat_model,
            messages=messages,
            temperature=0.3,
            max_tokens=max_tokens,
        )
    except RateLimitError:
        if not GROQ_API_KEY or _chat_model == GROQ_FALLBACK_MODEL:
            raise
        log.warning(
            "Лимит модели %s исчерпан — переключаюсь на запасную %s",
            _chat_model, GROQ_FALLBACK_MODEL,
        )
        resp = await _openai.chat.completions.create(
            model=GROQ_FALLBACK_MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=max_tokens,
        )
    return resp.choices[0].message.content or ""


async def _analyze_claude(
    user_message: str, system_prompt: str, max_tokens: int = 4000
) -> str:
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


def extract_metrics(report: str) -> tuple[int | None, str]:
    """Достаёт из отчёта оценку (0-10) и вердикт: ok / fail / doubt."""
    score = None
    m = re.search(r"ОЦЕНКА РАБОТЫ:\s*(\d{1,2})", report)
    if m:
        score = min(int(m.group(1)), 10)

    verdict = "doubt"
    m = re.search(r"Итог разговора:\s*(.+)", report)
    if m:
        outcome = m.group(1).lower()
        if "продал" in outcome or "договорил" in outcome:
            verdict = "ok"
        elif "слил" in outcome:
            verdict = "fail"
    if verdict == "doubt" and score is not None:
        if score >= 8:
            verdict = "ok"
        elif score <= 3:
            verdict = "fail"
    return score, verdict


def _sanitize(text: str) -> str:
    """Убирает Markdown-разметку, чтобы отчёт красиво выглядел в Telegram."""
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^```.*$", "", text, flags=re.MULTILINE)
    return text.strip()
