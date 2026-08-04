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
# Приоритет: OpenAI (основная) > Groq (бесплатный fallback) > Groq-8B (запасной)
# Claude не в цепочке: клиент ещё не оплатил, ANTHROPIC_API_KEY пустой → путь не активен.
# ---------------------------------------------------------------------------
GROQ_FALLBACK_MODEL = "llama-3.1-8b-instant"  # последний запасной на исчерпание лимита

# цепочка (имя, клиент, модель) — перебираем по порядку при лимите/ошибке
_LLM_CHAIN: list[tuple[str, AsyncOpenAI, str]] = []
if OPENAI_API_KEY:
    _LLM_CHAIN.append(("OpenAI", AsyncOpenAI(api_key=OPENAI_API_KEY), ANALYSIS_MODEL))
if GROQ_API_KEY:
    _groq_client = AsyncOpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)
    _LLM_CHAIN.append(("Groq", _groq_client, GROQ_ANALYSIS_MODEL))
    _LLM_CHAIN.append(("Groq fallback", _groq_client, GROQ_FALLBACK_MODEL))

if not _LLM_CHAIN:
    raise RuntimeError(
        "Нет ключа для анализа: задайте OPENAI_API_KEY или GROQ_API_KEY в .env"
    )

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
    user_message = (
        f"СТАТИСТИКА (посчитано точно):\n{facts}\n\n"
        f"ВЫЖИМКИ ИЗ АУДИТОВ ЗВОНКОВ ЗА ДЕНЬ:\n{call_summaries}"
    )
    if ANTHROPIC_API_KEY:
        report = await _analyze_claude(user_message, TEAM_PROMPT)
    else:
        report = await _analyze_openai(user_message, TEAM_PROMPT)
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


def extract_errors(report: str) -> list[dict[str, str]]:
    """
    Вытаскивает из отчёта блок ошибок/советов как структурированный список.

    Работает с русским и узбекским форматом:
      RU:  "🔴 ЧТО ИСПРАВИТЬ" + "ГДЕ: ..." + "👉 Как надо: ..."
      UZ:  "TUZATILADIGAN JOYLARI" / "TAVSIYALAR" + "QAYERDA: ..."

    Каждый элемент: {'error': ..., 'where': ..., 'fix': ...}
    where — «где именно ошибка»: дословная цитата реплики менеджера
    (или '—', если модель не указала).
    """
    if not report:
        return []

    # заголовки начала блока (первый найденный)
    start = -1
    for header in ("🔴 ЧТО ИСПРАВИТЬ", "TUZATILADIGAN JOYLARI", "TAVSIYALAR"):
        idx = report.find(header)
        if idx != -1 and (start == -1 or idx < start):
            start = idx
    if start == -1:
        return []

    # конец блока — следующий секционный заголовок
    block = report[start:]
    end = len(block)
    for marker in ("💡", "➖", "MASLAHAT:", "BALLOVCHI"):
        idx = block.find(marker, 3)  # 3 — пропускаем сам заголовок
        if idx != -1 and idx < end:
            end = idx
    block = block[:end]

    items: list[dict[str, str]] = []
    # разделяем блок на пункты: "1. ...", "2. ..."
    parts = re.split(r"\n\s*(?=\d+\.\s)", block)
    for part in parts:
        # отсекаем сам заголовок секции (в нём нет ни фикса, ни локации)
        if "👉" not in part and not re.search(r"(?:ГДЕ|QAYERDA)\s*[:：]", part):
            continue
        lines = [ln.strip() for ln in part.strip().splitlines() if ln.strip()]
        error, where, fix = "", "", ""
        for ln in lines:
            if ln.startswith("👉"):
                fix = ln.lstrip("👉").strip()
                fix = re.sub(r"^(?:Как надо|Как исправить)\s*[:：]\s*", "", fix)
            elif re.match(r"^QAYERDA\s*[:：]", ln, re.IGNORECASE):
                where = re.sub(r"^QAYERDA\s*[:：]\s*", "", ln, flags=re.IGNORECASE)
            elif re.match(r"^ГДЕ\s*[:：]", ln, re.IGNORECASE):
                where = re.sub(r"^ГДЕ\s*[:：]\s*", "", ln, flags=re.IGNORECASE)
            elif not error:
                error = re.sub(r"^\d+\.\s*", "", ln)
        if not error and not fix:
            continue
        items.append({"error": error, "where": where or "—", "fix": fix})
    return items


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
    Отправляет запрос по цепочке моделей: OpenAI (основная) → Groq → Groq fallback.
    При RateLimitError/ошибке — автоматически переключается на следующую модель.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    last_error: Exception | None = None
    for name, client, model in _LLM_CHAIN:
        try:
            log.info("Анализ через %s (%s)...", name, model)
            resp = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=max_tokens,
                timeout=180,
            )
            return resp.choices[0].message.content or ""
        except RateLimitError as e:
            last_error = e
            log.warning("Лимит модели %s (%s) исчерпан", name, model)
            continue
        except Exception as e:
            last_error = e
            log.error("Ошибка модели %s (%s): %s", name, model, e)
            continue

    # Если все модели упали — пробрасываем последнюю ошибку
    if last_error is not None:
        raise last_error
    raise RuntimeError("Пустая цепочка моделей для анализа")


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
