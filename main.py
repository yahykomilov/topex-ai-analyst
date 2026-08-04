import asyncio
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import amocrm
import db
import i18n
import pdf
import state
from i18n import t
from analyzer import (
    analyze_transcript,
    extract_metrics,
    report_excerpt,
    team_report,
    uz_tz,
)
from config import (
    AUDIO_DIR,
    EXTRA_OWNER_IDS,
    MANAGER_WHITELIST,
    MIN_CALL_DURATION,
    POLL_INTERVAL,
    TELEGRAM_BOT_TOKEN,
    TMP_DIR,
    amo_enabled,
)
from transcriber import transcribe
from preprocess import preprocess

from config import DATA_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(DATA_DIR / "bot.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("bot")

# fontTools при сборке PDF сыплет сотнями строк на каждый файл
logging.getLogger("fontTools").setLevel(logging.WARNING)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

TG_LIMIT = 4096
PAGE_SIZE = 8

# чаты, от которых ждём имя сотрудника для поиска (следующим сообщением)
pending_search: set[int] = set()


# ================== ВСПОМОГАТЕЛЬНОЕ ==================

def split_message(text: str) -> list[str]:
    chunks, current = [], ""
    for line in text.split("\n"):
        # супер-длинная строка без переносов: режем по лимиту, не теряя данные
        if len(line) > TG_LIMIT:
            if current:
                chunks.append(current)
                current = ""
            for i in range(0, len(line), TG_LIMIT):
                chunks.append(line[i:i + TG_LIMIT])
            continue
        if len(current) + len(line) + 1 > TG_LIMIT:
            if current:
                chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)
    return chunks


async def send_long(chat_id: int, text: str, reply_markup=None) -> None:
    chunks = split_message(text)
    for i, chunk in enumerate(chunks):
        await bot.send_message(
            chat_id, chunk, reply_markup=reply_markup if i == len(chunks) - 1 else None
        )


def is_owner_chat(chat_id: int) -> bool:
    return state.get_owner() == chat_id or chat_id in EXTRA_OWNER_IDS


def fmt_dt(ts: int) -> str:
    if not ts:
        return "—"
    return datetime.fromtimestamp(ts).strftime("%d.%m %H:%M")


def fmt_dur(seconds: int) -> str:
    m, s = divmod(int(seconds or 0), 60)
    mm, ss = t("dur_min"), t("dur_sec")
    return f"{m}{mm}{s:02d}{ss}" if m else f"{s}{ss}"


def manager_allowed(name: str) -> bool:
    """Только операторы из белого списка (плюс ручные загрузки)."""
    if not MANAGER_WHITELIST:
        return True
    if name.startswith("📤"):
        return True
    low = name.strip().lower()
    return any(w.lower() in low for w in MANAGER_WHITELIST)


def call_button(c) -> list[InlineKeyboardButton]:
    """Кнопка разобранного звонка."""
    emoji = db.VERDICT_EMOJI.get(c["verdict"], "❓")
    score = f"{c['score']}/10" if c["score"] is not None else "—"
    status = i18n.call_status_short(c["call_status"])
    label = (
        f"{emoji} {fmt_dt(c['created_at'])} • {fmt_dur(c['duration'])} • {score}"
        f"{f' • {status}' if status else ''} • {c['phone'] or t('no_phone')}"
    )
    return [InlineKeyboardButton(text=label[:60], callback_data=f"call:{c['id']}")]


def pending_button(c, manager_id: str) -> list[InlineKeyboardButton]:
    """Кнопка ещё не разобранного звонка из CRM."""
    status = i18n.call_status_short(c["call_status"])
    label = (
        f"⬜ {fmt_dt(c['created_at'])} • {fmt_dur(c['duration'])}"
        f"{f' • {status}' if status else ''} • {c['phone'] or t('no_phone')}"
    )
    return [
        InlineKeyboardButton(
            text=label[:60], callback_data=f"anlz:{c['note_id']}:{manager_id}"
        )
    ]


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_managers"), callback_data="mgrs")],
            [InlineKeyboardButton(text=t("btn_daily"), callback_data="daily")],
            [InlineKeyboardButton(text=t("btn_stats"), callback_data="stats")],
            [InlineKeyboardButton(text=t("btn_language"), callback_data="lang")],
        ]
    )


def back_kb(callback_data: str = "mgrs", text: str | None = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text or t("btn_back"), callback_data=callback_data)]
        ]
    )


# ================== КОМАНДЫ ==================

@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    owner = state.get_owner()
    if owner is None:
        state.set_owner(message.chat.id)
        await message.answer(t("owner_set"))
    elif owner != message.chat.id and message.chat.id not in EXTRA_OWNER_IDS:
        await message.answer(t("private_bot"))
        return
    await message.answer(t("menu_text"), reply_markup=main_menu_kb())


@dp.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    if not is_owner_chat(message.chat.id):
        return
    pending_search.discard(message.chat.id)
    await message.answer(t("menu_text"), reply_markup=main_menu_kb())


def language_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"setlang:{code}")]
            for code, label in i18n.LANGUAGES.items()
        ]
        + [[InlineKeyboardButton(text=t("btn_menu"), callback_data="menu")]]
    )


@dp.message(Command("language", "til"))
async def cmd_language(message: Message) -> None:
    if not is_owner_chat(message.chat.id):
        return
    await message.answer(t("lang_prompt"), reply_markup=language_kb())


@dp.callback_query(F.data == "lang")
async def cb_language(cb: CallbackQuery) -> None:
    await cb.message.edit_text(t("lang_prompt"), reply_markup=language_kb())
    await cb.answer()


@dp.callback_query(F.data.startswith("setlang:"))
async def cb_set_language(cb: CallbackQuery) -> None:
    lang = cb.data.split(":")[1]
    if lang not in i18n.LANGUAGES:
        await cb.answer()
        return
    i18n.set_lang(lang)
    await cb.answer(t("lang_changed"))
    await cb.message.edit_text(t("menu_text"), reply_markup=main_menu_kb())


@dp.message(Command("status"))
async def cmd_status(message: Message) -> None:
    if not is_owner_chat(message.chat.id):
        return
    if amo_enabled():
        try:
            name = await amocrm.check_connection()
            amo_line = t("status_amo_ok", name=name, interval=POLL_INTERVAL)
        except Exception as e:
            amo_line = t("status_amo_error", error=e)
    else:
        amo_line = t("status_amo_off")
    await message.answer(
        f"{t('status_title')}\n\n{amo_line}\n"
        f"{t('status_min_duration', seconds=MIN_CALL_DURATION)}\n"
        f"{t('status_db_calls', total=db.stats_for()['total'])}",
        reply_markup=main_menu_kb(),
    )


# ================== МЕНЮ / КНОПКИ ==================

@dp.callback_query(F.data == "menu")
async def cb_menu(cb: CallbackQuery) -> None:
    pending_search.discard(cb.message.chat.id)
    await cb.message.edit_text(t("menu_text"), reply_markup=main_menu_kb())
    await cb.answer()


async def collect_managers() -> list[tuple[str, str, int]]:
    """Сотрудники = все пользователи AmoCRM + все, у кого есть звонки в базе."""
    db_rows = {str(r["manager_id"]): (r["manager_name"], r["cnt"]) for r in db.managers()}
    entries: list[tuple[str, str, int]] = []
    if amo_enabled():
        try:
            users = await amocrm.get_users()
            for uid, name in users.items():
                _, cnt = db_rows.pop(str(uid), (name, 0))
                if manager_allowed(name):
                    entries.append((str(uid), name, cnt))
        except Exception as e:
            log.error("Не удалось получить сотрудников AmoCRM: %s", e)
    for mid, (name, cnt) in db_rows.items():
        if manager_allowed(name):
            entries.append((mid, name, cnt))
    entries.sort(key=lambda x: -x[2])
    return entries


def managers_kb(entries: list[tuple[str, str, int]], with_search: bool) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text=f"👨‍💼 {name} ({cnt})", callback_data=f"mgr:{mid}:0")]
        for mid, name, cnt in entries
    ]
    if with_search:
        kb.append([InlineKeyboardButton(text=t("btn_search"), callback_data="mgrfind")])
    kb.append([InlineKeyboardButton(text=t("btn_menu"), callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


@dp.callback_query(F.data == "mgrs")
async def cb_managers(cb: CallbackQuery) -> None:
    pending_search.discard(cb.message.chat.id)
    entries = await collect_managers()

    if not entries:
        await cb.message.edit_text(
            t("managers_empty"), reply_markup=back_kb("menu", t("btn_menu"))
        )
        await cb.answer()
        return

    await cb.message.edit_text(
        t("managers_title"),
        reply_markup=managers_kb(entries, with_search=True),
    )
    await cb.answer()


@dp.callback_query(F.data == "mgrfind")
async def cb_manager_search(cb: CallbackQuery) -> None:
    pending_search.add(cb.message.chat.id)
    await cb.message.edit_text(
        t("search_prompt"), reply_markup=back_kb("mgrs", t("btn_to_managers"))
    )
    await cb.answer()


async def show_search_results(chat_id: int, query: str) -> None:
    needle = query.strip().casefold()
    found = [e for e in await collect_managers() if needle in e[1].casefold()]
    if not found:
        await bot.send_message(
            chat_id,
            t("search_none", query=query),
            reply_markup=back_kb("mgrs", t("btn_to_managers")),
        )
        return
    await bot.send_message(
        chat_id,
        t("search_results", query=query, count=len(found)),
        reply_markup=managers_kb(found, with_search=True),
    )


@dp.callback_query(F.data.startswith("mgr:"))
async def cb_manager(cb: CallbackQuery) -> None:
    _, manager_id, page_s = cb.data.split(":")
    page = int(page_s)
    total = db.count_for(manager_id)
    calls = db.calls_for(manager_id, offset=page * PAGE_SIZE, limit=PAGE_SIZE)

    name = t("manager_unknown")
    if calls:
        name = db.get_call(calls[0]["id"])["manager_name"]
    elif amo_enabled() and manager_id.isdigit():
        try:
            users = await amocrm.get_users()
            name = users.get(int(manager_id), name)
        except Exception:
            pass

    # неразобранные звонки этого сотрудника из CRM (можно разобрать по нажатию)
    pending = []
    if page == 0 and amo_enabled() and manager_id.isdigit():
        try:
            crm_calls = await amocrm.fetch_recent_calls()
            pending = [
                c
                for c in crm_calls
                if c.get("created_by") == int(manager_id)
                and c["duration"] >= MIN_CALL_DURATION
                and c["link"]
                and not db.has_note(c["note_id"])
            ][:10]
        except Exception as e:
            log.error("Ошибка получения звонков CRM: %s", e)

    if total:
        stats = db.stats_for(manager_id)
        header = f"👨‍💼 {name}\n\n{i18n.format_stats(stats)}\n\n"
    else:
        header = f"👨‍💼 {name}\n\n{t('manager_no_calls')}\n\n"
    header += t("manager_pick_call") if calls or pending else t("manager_no_crm_calls")

    kb = [call_button(c) for c in calls]
    kb += [pending_button(c, manager_id) for c in pending]

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"mgr:{manager_id}:{page - 1}"))
    if (page + 1) * PAGE_SIZE < total:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"mgr:{manager_id}:{page + 1}"))
    if nav:
        kb.append(nav)
    kb.append(
        [InlineKeyboardButton(text=t("btn_pick_date"), callback_data=f"dates:{manager_id}")]
    )
    kb.append([InlineKeyboardButton(text=t("btn_to_managers"), callback_data="mgrs")])

    await cb.message.edit_text(header, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await cb.answer()


def _day_bounds(day_key: str) -> tuple[int, int]:
    d = datetime.strptime(day_key, "%Y%m%d")
    start = int(d.timestamp())
    return start, start + 86400


@dp.callback_query(F.data.startswith("dates:"))
async def cb_dates(cb: CallbackQuery) -> None:
    manager_id = cb.data.split(":")[1]
    date_counts: dict[str, int] = dict(db.dates_for(manager_id))

    # добавляем даты неразобранных звонков из CRM
    if amo_enabled() and manager_id.isdigit():
        try:
            crm_calls = await amocrm.fetch_recent_calls()
            for c in crm_calls:
                if (
                    c.get("created_by") == int(manager_id)
                    and c["duration"] >= MIN_CALL_DURATION
                    and c["link"]
                    and not db.has_note(c["note_id"])
                    and c["created_at"]
                ):
                    key = datetime.fromtimestamp(c["created_at"]).strftime("%Y%m%d")
                    date_counts[key] = date_counts.get(key, 0) + 1
        except Exception as e:
            log.error("Ошибка получения звонков CRM: %s", e)

    if not date_counts:
        await cb.answer(t("dates_empty"))
        return

    weekdays = i18n.raw("weekdays")
    kb = []
    for key in sorted(date_counts, reverse=True)[:14]:
        d = datetime.strptime(key, "%Y%m%d")
        label = t(
            "day_calls_label",
            date=d.strftime("%d.%m.%Y"),
            weekday=weekdays[d.weekday()],
            count=date_counts[key],
        )
        kb.append([InlineKeyboardButton(text=label, callback_data=f"mgrd:{manager_id}:{key}")])
    kb.append(
        [InlineKeyboardButton(text=t("btn_to_manager"), callback_data=f"mgr:{manager_id}:0")]
    )

    await cb.message.edit_text(
        t("dates_title"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
    )
    await cb.answer()


@dp.callback_query(F.data.startswith("mgrd:"))
async def cb_manager_day(cb: CallbackQuery) -> None:
    _, manager_id, day_key = cb.data.split(":")
    start_ts, end_ts = _day_bounds(day_key)
    day_label = datetime.strptime(day_key, "%Y%m%d").strftime("%d.%m.%Y")

    calls = db.calls_for_day(manager_id, start_ts, end_ts)

    pending = []
    if amo_enabled() and manager_id.isdigit():
        try:
            crm_calls = await amocrm.fetch_recent_calls()
            pending = [
                c
                for c in crm_calls
                if c.get("created_by") == int(manager_id)
                and c["duration"] >= MIN_CALL_DURATION
                and c["link"]
                and not db.has_note(c["note_id"])
                and c["created_at"]
                and start_ts <= c["created_at"] < end_ts
            ]
        except Exception as e:
            log.error("Ошибка получения звонков CRM: %s", e)

    name = t("manager_unknown")
    if calls:
        row = db.get_call(calls[0]["id"])
        name = row["manager_name"]
    elif amo_enabled() and manager_id.isdigit():
        try:
            users = await amocrm.get_users()
            name = users.get(int(manager_id), name)
        except Exception:
            pass

    if not calls and not pending:
        await cb.answer(t("day_empty", day=day_label))
        return

    kb = [call_button(c) for c in calls]
    kb += [pending_button(c, manager_id) for c in pending[:20]]
    kb.append(
        [InlineKeyboardButton(text=t("btn_other_date"), callback_data=f"dates:{manager_id}")]
    )
    kb.append(
        [InlineKeyboardButton(text=t("btn_to_manager"), callback_data=f"mgr:{manager_id}:0")]
    )

    await cb.message.edit_text(
        t("day_title", name=name, day=day_label, count=len(calls) + len(pending)),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
    )
    await cb.answer()


@dp.callback_query(F.data.startswith("anlz:"))
async def cb_analyze(cb: CallbackQuery) -> None:
    _, note_id_s, manager_id = cb.data.split(":")
    note_id = int(note_id_s)
    await cb.answer(t("analyzing"))

    existing = db.find_by_note(note_id)
    if existing:
        await send_call_package(cb.message.chat.id, existing["id"])
        return

    msg = await bot.send_message(
        cb.message.chat.id, t("analyzing_long")
    )
    try:
        crm_calls = await amocrm.fetch_recent_calls()
        call = next((c for c in crm_calls if c["note_id"] == note_id), None)
        if call is None:
            await msg.edit_text(t("call_not_in_crm"))
            return
        state.mark_processed(note_id)
        row_id = await process_amo_call(call)
        if row_id is None:
            await msg.edit_text(t("call_not_analyzed"))
            return
        await msg.delete()
        await send_call_package(cb.message.chat.id, row_id)
    except Exception as e:
        log.exception("Ошибка разбора звонка %s", note_id)
        await msg.edit_text(t("error", error=e))


PDF_SEPARATOR = "\n\n" + "-" * 60 + "\n\n"


def build_call_pdf(call, uz_doc: str | None) -> Path:
    """PDF со всем разбором: диалог по ролям, оценка, советы AI и ТЗ на узбекском."""
    score = f"{call['score']}/10" if call["score"] is not None else "—"
    status_label = i18n.call_status_label(call["call_status"])
    meta_lines = [
        t("pdf_manager", name=call["manager_name"]),
        t(
            "pdf_date",
            date=fmt_dt(call["created_at"]),
            direction=i18n.direction(call["direction"]),
            duration=fmt_dur(call["duration"]),
        ),
        t("pdf_score", score=score) + (f" • {status_label}" if status_label else ""),
    ]
    if call["phone"]:
        meta_lines.append(t("pdf_phone", phone=call["phone"]))
    if call["card_url"]:
        meta_lines.append(t("pdf_card", url=call["card_url"]))

    sections = [call["report"] or t("report_missing")]
    if uz_doc:
        sections.append(f"{t('pdf_uz_section')}\n\n{uz_doc}")

    # имя файла — только из id: manager_name приходит из CRM, в путь его не пускаем
    dest = TMP_DIR / f"call_{call['id']}.pdf"
    return pdf.make_call_pdf(
        dest,
        t("pdf_title"),
        meta_lines,
        PDF_SEPARATOR.join(sections),
    )


async def send_call_pdf(chat_id: int, call, uz_doc: str | None) -> None:
    path = None
    try:
        path = await asyncio.to_thread(build_call_pdf, call, uz_doc)
        await bot.send_document(chat_id, FSInputFile(path))
    except Exception as e:
        log.exception("Не удалось собрать PDF для звонка %s", call["id"])
        await bot.send_message(chat_id, t("pdf_failed", error=e))
    finally:
        if path:
            Path(path).unlink(missing_ok=True)


async def send_call_package(chat_id: int, call_id: int) -> None:
    """Аудио + PDF (диалог на узбекском + ТЗ) + кнопки."""
    c = db.get_call(call_id)
    if not c:
        await bot.send_message(chat_id, t("call_not_found"))
        return

    emoji = db.VERDICT_EMOJI.get(c["verdict"], "❓")
    score = f"{c['score']}/10" if c["score"] is not None else "—"
    status_label = i18n.call_status_label(c["call_status"])
    status_str = f" • {status_label}" if status_label else ""
    caption_lines = [
        f"{emoji} {c['manager_name']} • {score}",
        f"📅 {fmt_dt(c['created_at'])} • {i18n.direction(c['direction'])} • {fmt_dur(c['duration'])}{status_str}",
    ]
    if c["phone"]:
        caption_lines.append(f"📱 {c['phone']}")
    if c["card_url"]:
        caption_lines.append(f"🔗 {c['card_url']}")
    caption = "\n".join(caption_lines)

    # 1. Аудио
    audio_sent = False
    audio_path = Path(c["audio_path"]) if c["audio_path"] else None
    if audio_path and audio_path.exists():
        await bot.send_audio(chat_id, FSInputFile(audio_path), caption=caption[:1024])
        audio_sent = True
    elif c["rec_link"]:
        try:
            fresh = await amocrm.download_recording(
                {"link": c["rec_link"], "note_id": c["note_id"] or c["id"]}, AUDIO_DIR
            )
            await bot.send_audio(chat_id, FSInputFile(fresh), caption=caption[:1024])
            audio_sent = True
        except Exception as e:
            log.error("Не удалось скачать запись повторно: %s", e)
    if not audio_sent:
        await bot.send_message(chat_id, caption + "\n" + t("audio_unavailable"))

    # 2. Разбор с диалогом — прямо в Telegram (не только в PDF)
    report_text = c["report"] or t("report_missing")
    await send_long(chat_id, f"{t('report_title')}\n\n{report_text}")

    # 3. Короткое ТЗ на узбекском (генерируем один раз, потом берём из базы)
    uz = c["uz_doc"]
    if not uz and c["transcript"]:
        try:
            uz = await uz_tz(c["transcript"])
            db.set_uz_doc(call_id, uz)
        except Exception as e:
            log.exception("Ошибка генерации ТЗ")
            uz = None

    # 4. PDF со всем разбором
    await send_call_pdf(chat_id, c, uz)

    kb = back_kb(f"mgr:{c['manager_id']}:0", t("btn_to_calls"))
    if uz:
        await send_long(chat_id, uz, reply_markup=kb)
    else:
        await bot.send_message(chat_id, t("tz_unavailable"), reply_markup=kb)


@dp.callback_query(F.data.startswith("call:"))
async def cb_call(cb: CallbackQuery) -> None:
    call_id = int(cb.data.split(":")[1])
    await cb.answer()
    await send_call_package(cb.message.chat.id, call_id)


@dp.callback_query(F.data.startswith("txt:"))
async def cb_transcript(cb: CallbackQuery) -> None:
    call_id = int(cb.data.split(":")[1])
    c = db.get_call(call_id)
    if not c:
        await cb.answer(t("call_not_found"))
        return
    await cb.answer()
    text = c["transcript"] or t("transcript_missing")
    await send_long(
        cb.message.chat.id,
        f"{t('transcript_title')}\n\n{text}",
        reply_markup=back_kb(f"mgr:{c['manager_id']}:0", t("btn_to_calls")),
    )


@dp.callback_query(F.data.startswith("rep:"))
async def cb_report(cb: CallbackQuery) -> None:
    call_id = int(cb.data.split(":")[1])
    c = db.get_call(call_id)
    if not c:
        await cb.answer(t("call_not_found"))
        return
    await cb.answer()
    await send_long(
        cb.message.chat.id,
        c["report"] or t("report_missing"),
        reply_markup=back_kb(f"mgr:{c['manager_id']}:0", t("btn_to_calls")),
    )


@dp.callback_query(F.data == "stats")
async def cb_stats(cb: CallbackQuery) -> None:
    total_stats = db.stats_for()
    lines = [t("stats_title"), i18n.format_stats(total_stats)]
    rows = [r for r in db.managers() if manager_allowed(r["manager_name"])]
    if rows:
        lines.append(t("stats_by_manager"))
        for r in rows:
            s = db.stats_for(r["manager_id"])
            avg = (
                t("stats_manager_avg", avg=s["avg_score"])
                if s["avg_score"] is not None
                else ""
            )
            lines.append(
                t(
                    "stats_manager_line",
                    name=r["manager_name"],
                    total=s["total"],
                    answered=s.get("answered", 0),
                    noanswer=s["counts"].get("noanswer", 0),
                    ok=s["percent"]["ok"],
                    fail=s["percent"]["fail"],
                    doubt=s["percent"]["doubt"],
                    avg=avg,
                )
            )
    await cb.message.edit_text("\n".join(lines), reply_markup=back_kb("menu", t("btn_menu")))
    await cb.answer()


# ================== ОТЧЁТ ЗА ДЕНЬ ==================

DAILY_REPORT_HOUR = 20  # автоотчёт каждый день в 20:00


async def build_daily_report() -> str | None:
    now = datetime.now()
    day_start = int(datetime(now.year, now.month, now.day).timestamp())
    calls = [
        c
        for c in db.calls_between(day_start, day_start + 86400)
        if manager_allowed(c["manager_name"])
    ]
    if not calls:
        return None

    phones = {c["phone"] for c in calls if c["phone"]}
    no_phone = sum(1 for c in calls if not c["phone"])
    clients = len(phones) + no_phone
    verdicts = {"ok": 0, "fail": 0, "doubt": 0, "noanswer": 0}
    scores = []
    per_mgr: dict[str, dict] = {}
    for c in calls:
        verdicts[c["verdict"]] = verdicts.get(c["verdict"], 0) + 1
        if c["score"] is not None:
            scores.append(c["score"])
        m = per_mgr.setdefault(
            c["manager_name"],
            {"n": 0, "ok": 0, "fail": 0, "doubt": 0, "noanswer": 0, "scores": []},
        )
        m["n"] += 1
        m[c["verdict"]] += 1
        if c["score"] is not None:
            m["scores"].append(c["score"])

    avg = round(sum(scores) / len(scores), 1) if scores else "—"
    facts = [
        f"Дата: {now.strftime('%d.%m.%Y')}",
        f"Клиентов обслужено (уникальных): {clients}",
        f"Звонков разобрано: {len(calls)}",
        f"Отвечено (был разговор): {verdicts['ok'] + verdicts['fail'] + verdicts['doubt']} — "
        f"✅ успешных {verdicts['ok']}, ❌ неуспешных {verdicts['fail']}, ❓ под вопросом {verdicts['doubt']}",
        f"📵 Недозвон / не взяли трубку: {verdicts['noanswer']}",
        f"Средний балл отдела: {avg}/10",
        "",
        "По сотрудникам:",
    ]
    for name, m in sorted(per_mgr.items(), key=lambda x: -x[1]["n"]):
        m_avg = round(sum(m["scores"]) / len(m["scores"]), 1) if m["scores"] else "—"
        facts.append(
            f"- {name}: {m['n']} зв., ср. балл {m_avg}/10, "
            f"✅{m['ok']} ❌{m['fail']} ❓{m['doubt']} 📵{m['noanswer']}"
        )

    summaries = []
    total_len = 0
    MAX_SUMMARY_CHARS = 8000
    for c in calls[:25]:
        s = (
            f"— {c['manager_name']} • {fmt_dt(c['created_at'])} • {c['phone'] or 'без номера'}:\n"
            f"{report_excerpt(c['report'] or '')}"
        )
        if total_len + len(s) > MAX_SUMMARY_CHARS:
            break
        summaries.append(s)
        total_len += len(s)
    shown = len(summaries)
    if len(calls) > shown:
        summaries.append(f"(и ещё {len(calls) - shown} звонков — в выжимку не вошли)")

    return await team_report("\n".join(facts), "\n\n".join(summaries))


@dp.callback_query(F.data == "daily")
async def cb_daily(cb: CallbackQuery) -> None:
    await cb.answer(t("daily_preparing"))
    msg = await bot.send_message(cb.message.chat.id, t("daily_building"))
    try:
        report = await build_daily_report()
        if report is None:
            await msg.edit_text(t("daily_empty"))
            return
        await msg.delete()
        await send_long(
            cb.message.chat.id, report, reply_markup=back_kb("menu", t("btn_menu_plain"))
        )
    except Exception as e:
        log.exception("Ошибка отчёта за день")
        await msg.edit_text(t("daily_error", error=e))


async def daily_report_loop() -> None:
    while True:
        await asyncio.sleep(300)
        try:
            owner = state.get_owner()
            if owner is None:
                continue
            now = datetime.now()
            today = now.strftime("%Y-%m-%d")
            if now.hour >= DAILY_REPORT_HOUR and state.get_last_daily() != today:
                report = await build_daily_report()
                state.set_last_daily(today)
                if report:
                    await bot.send_message(owner, t("daily_auto"))
                    await send_long(owner, report)
        except Exception as e:
            log.error("Ошибка автоотчёта: %s", e)


# ================== РУЧНАЯ ЗАГРУЗКА ==================

@dp.message(F.voice | F.audio | F.document)
async def handle_file(message: Message) -> None:
    if not is_owner_chat(message.chat.id):
        await message.answer(t("private_hint"))
        return

    doc = message.document
    if doc and (doc.file_name or "").lower().endswith(".txt"):
        path = TMP_DIR / f"tg_{doc.file_id}.txt"
        await bot.download(doc, destination=path)
        transcript = path.read_text(encoding="utf-8", errors="ignore")
        path.unlink(missing_ok=True)
        status = await message.answer(t("manual_auditing"))
        try:
            await run_manual_analysis(message, transcript)
            await status.delete()
        except Exception as e:
            log.exception("Ошибка анализа txt")
            await status.edit_text(t("error", error=e))
        return

    media = message.voice or message.audio or doc
    if doc and not (doc.mime_type or "").startswith("audio"):
        await message.answer(t("manual_send_audio"))
        return

    if media.file_size and media.file_size > 20 * 1024 * 1024:
        await message.answer(t("manual_too_big"))
        return

    ext = ".ogg" if message.voice else ".mp3"
    fname = (doc and doc.file_name) or (message.audio and message.audio.file_name) or ""
    if "." in fname:
        ext = "." + fname.rsplit(".", 1)[-1]

    path = AUDIO_DIR / f"manual_{media.file_unique_id}{ext}"
    status = await message.answer(t("manual_got_audio"))
    try:
        await bot.download(media, destination=path)
        path = preprocess(path)
        transcript = await transcribe(path)
        if len(transcript) < 30:
            await status.edit_text(t("manual_no_speech"))
            path.unlink(missing_ok=True)
            return
        await status.edit_text(t("manual_transcribed"))
        duration = (message.voice and message.voice.duration) or (
            message.audio and message.audio.duration
        ) or 0
        await run_manual_analysis(message, transcript, duration=duration, audio_path=path)
        await status.delete()
    except Exception as e:
        log.exception("Ошибка обработки файла")
        await status.edit_text(t("error", error=e))


@dp.message(F.text)
async def handle_text(message: Message) -> None:
    if not is_owner_chat(message.chat.id):
        await message.answer(t("private_hint"))
        return
    text = message.text.strip()

    # ждём имя сотрудника после кнопки «Поиск по имени»
    if message.chat.id in pending_search:
        pending_search.discard(message.chat.id)
        await show_search_results(message.chat.id, text)
        return

    if len(text) < 100:
        await message.answer(t("manual_text_short"))
        return
    status = await message.answer(t("manual_auditing"))
    try:
        await run_manual_analysis(message, text)
        await status.delete()
    except Exception as e:
        log.exception("Ошибка анализа текста")
        await status.edit_text(t("error", error=e))


async def run_manual_analysis(
    message: Message, transcript: str, duration: int = 0, audio_path: Path | None = None
) -> None:
    report = await analyze_transcript(transcript)
    score, verdict = extract_metrics(report)
    row_id = db.save_call(
        source="manual",
        note_id=None,
        manager_id="manual",
        manager_name="📤 Ручные загрузки",
        phone="",
        direction="",
        duration=duration,
        created_at=int(message.date.timestamp()) if message.date else int(time.time()),
        transcript=transcript,
        report=report,
        score=score,
        verdict=verdict,
        card_url="",
        rec_link="",
        audio_path=str(audio_path) if audio_path else "",
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_audio_tz"), callback_data=f"call:{row_id}")],
            [InlineKeyboardButton(text=t("btn_menu_plain"), callback_data="menu")],
        ]
    )
    await send_long(message.chat.id, report, reply_markup=kb)


# ================== АВТОРЕЖИМ: ОПРОС AMOCRM ==================

async def process_amo_call(call: dict) -> int | None:
    """Скачивает, расшифровывает и разбирает звонок. Тихо: ничего не шлёт в чат.

    Возвращает id записи в базе или None, если разобрать не удалось.
    """
    users = {}
    try:
        users = await amocrm.get_users()
    except Exception as e:
        log.error("Не удалось получить сотрудников AmoCRM: %s", e)
    manager_name = users.get(call.get("created_by"), "Неизвестный сотрудник")
    manager_id = str(call.get("created_by") or "unknown")

    direction = "Входящий" if call["note_type"] == "call_in" else "Исходящий"
    meta = (
        f"Менеджер (из CRM): {manager_name}\n"
        f"Тип: {direction} звонок\n"
        f"Телефон клиента: {call['phone']}\n"
        f"Длительность: {call['duration']} сек"
    )
    card_url = amocrm.entity_url(call)

    call_status = call.get("call_status")

    # Недозвон / пропущенный — не анализируем, просто фиксируем
    if call_status in (5, 6, 7):
        row_id = db.save_call(
            source="amo",
            note_id=call["note_id"],
            manager_id=manager_id,
            manager_name=manager_name,
            phone=call["phone"],
            direction=direction,
            duration=call["duration"],
            created_at=call["created_at"] or int(time.time()),
            transcript="",
            report="",
            score=None,  # недозвон/пропущенный — разговора не было, не тянем средний балл вниз
            verdict="noanswer",  # отдельная категория: клиент не взял трубку (НЕ «неуспешный» разговор)
            call_status=call_status,
            card_url=card_url,
            rec_link="",
            audio_path="",
        )
        log.info("Звонок %s: недозвон/пропущен (status=%s), сохранён", call["note_id"], call_status)
        return row_id

    try:
        audio_path = await amocrm.download_recording(call, AUDIO_DIR)
        audio_path = preprocess(audio_path)
        transcript = await transcribe(audio_path)
        if len(transcript) < 30:
            log.info("Звонок %s: почти нет речи, пропускаю", call["note_id"])
            return None
        report = await analyze_transcript(transcript, meta)
        score, verdict = extract_metrics(report)
        row_id = db.save_call(
            source="amo",
            note_id=call["note_id"],
            manager_id=manager_id,
            manager_name=manager_name,
            phone=call["phone"],
            direction=direction,
            duration=call["duration"],
            created_at=call["created_at"] or int(time.time()),
            transcript=transcript,
            report=report,
            score=score,
            verdict=verdict,
            call_status=call_status,
            card_url=card_url,
            rec_link=call["link"],
            audio_path=str(audio_path),
        )
        log.info("Звонок %s разобран: %s, %s/10", call["note_id"], manager_name, score)
        return row_id
    except Exception:
        log.exception("Ошибка обработки звонка %s", call["note_id"])
        return None


async def amo_poller() -> None:
    if not amo_enabled():
        log.info("AmoCRM не настроен — работаю в ручном режиме (файлы/текст в боте).")
        return
    try:
        name = await amocrm.check_connection()
        log.info("AmoCRM подключён: %s", name)
    except Exception as e:
        log.error("AmoCRM: ошибка подключения — %s", e)
        owner = state.get_owner()
        if owner:
            await bot.send_message(owner, t("status_amo_error", error=e))
        return

    if not state.amo_initialized():
        try:
            for call in await amocrm.fetch_recent_calls():
                state.mark_processed(call["note_id"])
            state.set_amo_initialized()
            log.info("Первый запуск: старые звонки пропущены, слежу только за новыми.")
        except Exception as e:
            log.error("Ошибка инициализации AmoCRM: %s", e)

    owner_warned = False
    while True:
        # пока никто не нажал /start — звонки не трогаем, чтобы отчёты не пропали
        if state.get_owner() is None:
            if not owner_warned:
                log.info("Жду, пока владелец нажмёт /start в боте — звонки пока не обрабатываю.")
                owner_warned = True
            await asyncio.sleep(10)
            continue
        try:
            calls = await amocrm.fetch_recent_calls()
            users = {}
            try:
                users = await amocrm.get_users()
            except Exception as e:
                log.error("Не удалось получить сотрудников: %s", e)
            for call in calls:
                if state.is_processed(call["note_id"]):
                    continue
                state.mark_processed(call["note_id"])
                if call["duration"] < MIN_CALL_DURATION:
                    log.info(
                        "Звонок %s пропущен: %d сек (недозвон/короткий)",
                        call["note_id"], call["duration"],
                    )
                    continue
                mgr_name = users.get(call.get("created_by"), "")
                if users and not manager_allowed(mgr_name or "?"):
                    log.info(
                        "Звонок %s пропущен: сотрудник %s не в списке анализа",
                        call["note_id"], mgr_name or call.get("created_by"),
                    )
                    continue
                log.info("Новый звонок %s (%d сек) — обрабатываю", call["note_id"], call["duration"])
                await process_amo_call(call)
        except Exception as e:
            log.error("Ошибка опроса AmoCRM: %s", e)
        await asyncio.sleep(POLL_INTERVAL)


async def main() -> None:
    log.info("Бот запускается...")
    asyncio.create_task(amo_poller())
    asyncio.create_task(daily_report_loop())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
