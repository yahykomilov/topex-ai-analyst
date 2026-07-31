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
import pdf
import state
from analyzer import (
    analyze_transcript,
    extract_metrics,
    extract_summary,
    report_excerpt,
    team_report,
    uz_document,
    uz_tz,
)
from config import (
    AMO_DEFAULT_HOST,
    AUDIO_DIR,
    MANAGER_WHITELIST,
    MIN_CALL_DURATION,
    POLL_INTERVAL,
    TELEGRAM_BOT_TOKEN,
    TMP_DIR,
)
from i18n import t, LANGS, LANG_NAMES
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

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

TG_LIMIT = 4096
PAGE_SIZE = 8


# ================== ВСПОМОГАТЕЛЬНОЕ ==================

def split_message(text: str) -> list[str]:
    chunks, current = [], ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > TG_LIMIT:
            if current:
                chunks.append(current)
            current = line[:TG_LIMIT]
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
    return state.get_owner() == chat_id


def fmt_dt(ts: int) -> str:
    if not ts:
        return "—"
    return datetime.fromtimestamp(ts).strftime("%d.%m %H:%M")


def fmt_dur(seconds: int) -> str:
    m, s = divmod(int(seconds or 0), 60)
    return f"{m}м{s:02d}с" if m else f"{s}с"


def manager_allowed(name: str) -> bool:
    """Только операторы из белого списка (плюс ручные загрузки)."""
    if not MANAGER_WHITELIST:
        return True
    if name.startswith("📤"):
        return True
    low = name.strip().lower()
    return any(w.lower() in low for w in MANAGER_WHITELIST)


def lang_row(lang: str | None = None) -> list[InlineKeyboardButton]:
    """Ряд кнопок выбора языка (по кнопке на каждый язык). Текущий помечаем точкой."""
    cur = lang or state.get_lang()
    return [
        InlineKeyboardButton(
            text=("• " if code == cur else "") + LANG_NAMES[code],
            callback_data=f"setlang:{code}",
        )
        for code in LANGS
    ]


def main_menu_kb(lang: str | None = None) -> InlineKeyboardMarkup:
    lang = lang or state.get_lang()
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_employees"), callback_data="mgrs")],
            [InlineKeyboardButton(text=t(lang, "btn_daily"), callback_data="daily")],
            [InlineKeyboardButton(text=t(lang, "btn_stats"), callback_data="stats")],
            lang_row(lang),
        ]
    )


def lang_kb(lang: str | None = None) -> InlineKeyboardMarkup:
    """Клавиатура только с выбором языка — вешаем на мастер подключения,
    чтобы язык можно было переключить в любой момент, ещё до появления меню."""
    lang = lang or state.get_lang()
    return InlineKeyboardMarkup(inline_keyboard=[lang_row(lang)])


def back_kb(callback_data: str = "mgrs", text: str = "⬅️ Назад") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=text, callback_data=callback_data)]]
    )


def menu_text(lang: str | None = None) -> str:
    return t(lang or state.get_lang(), "menu_title")


# ================== КОМАНДЫ ==================

@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    owner = state.get_owner()
    lang = state.get_lang()
    if owner is None:
        state.set_owner(message.chat.id)
        await message.answer(t(lang, "owner_assigned"))
    elif owner != message.chat.id:
        await message.answer(t(lang, "private_taken"))
        return
    # первый вход владельца: пока amoCRM не подключён — ведём через мастер ввода ключей
    if not amocrm.is_configured():
        await begin_amo_setup(message.chat.id)
        return
    await message.answer(menu_text(lang), reply_markup=main_menu_kb(lang))


@dp.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    if not is_owner_chat(message.chat.id):
        return
    await message.answer(menu_text(), reply_markup=main_menu_kb())


@dp.message(Command("status"))
async def cmd_status(message: Message) -> None:
    if not is_owner_chat(message.chat.id):
        return
    lang = state.get_lang()
    if amocrm.is_configured():
        try:
            name = await amocrm.check_connection()
            amo_line = t(lang, "status_amo_ok", name=name, sec=POLL_INTERVAL)
        except Exception as e:
            amo_line = t(lang, "status_amo_err", err=str(e))
    else:
        amo_line = t(lang, "status_amo_off")
    await message.answer(
        t(lang, "status_body", amo=amo_line, sec=MIN_CALL_DURATION, n=db.stats_for()["total"]),
        reply_markup=main_menu_kb(lang),
    )


# ================== ПОДКЛЮЧЕНИЕ AMOCRM (мастер ввода ключей) ==================

# порядок шагов мастера; на каждый шаг владелец шлёт одно сообщение.
# Адрес кабинета не спрашиваем — аккаунт один и тот же (AMO_DEFAULT_HOST).
AMO_STEPS = ["secret", "integration_id", "token"]


def setup_step_text(step: str, lang: str) -> str:
    """Текст текущего шага мастера на нужном языке (для шага 1 — с вступлением)."""
    intro = t(lang, "amo_intro") + "\n\n" if step == "secret" else ""
    return intro + t(lang, "amo_" + step)


@dp.message(Command("connect"))
async def cmd_connect(message: Message) -> None:
    if not is_owner_chat(message.chat.id):
        return
    await begin_amo_setup(message.chat.id)


@dp.message(Command("til", "language", "lang"))
async def cmd_lang(message: Message) -> None:
    """Показать выбор языка — работает в ЛЮБОЙ момент (и в мастере, и в меню)."""
    if not is_owner_chat(message.chat.id):
        return
    lang = state.get_lang()
    await message.answer(t(lang, "choose_lang"), reply_markup=lang_kb(lang))


async def begin_amo_setup(chat_id: int) -> None:
    state.set_setup({"step": "secret"})
    lang = state.get_lang()
    await bot.send_message(
        chat_id, setup_step_text("secret", lang), reply_markup=lang_kb(lang)
    )


async def handle_amo_setup(message: Message, setup: dict) -> None:
    """Ловит очередное значение мастера. Когда собраны все 4 — проверяет и сохраняет."""
    step = setup.get("step")
    if step not in AMO_STEPS:
        state.set_setup(None)
        return
    setup[step] = message.text.strip()
    lang = state.get_lang()

    idx = AMO_STEPS.index(step)
    if idx + 1 < len(AMO_STEPS):
        next_step = AMO_STEPS[idx + 1]
        setup["step"] = next_step
        state.set_setup(setup)
        await message.answer(setup_step_text(next_step, lang), reply_markup=lang_kb(lang))
        return

    # все значения введены — аккаунт фиксированный, проверяем подключение
    state.set_setup(None)
    host = AMO_DEFAULT_HOST
    token = setup.get("token", "")
    status = await message.answer(t(lang, "amo_checking", host=host))
    try:
        name = await amocrm.verify(host, token)
    except Exception as e:
        await status.edit_text(t(lang, "amo_fail", host=host, err=str(e)))
        return
    state.set_amo(host, token, setup.get("secret", ""), setup.get("integration_id", ""))
    amocrm.reset_cache()
    await status.edit_text(t(lang, "amo_connected", name=name))
    await message.answer(menu_text(lang), reply_markup=main_menu_kb(lang))


# ================== МЕНЮ / КНОПКИ ==================

@dp.callback_query(F.data == "menu")
async def cb_menu(cb: CallbackQuery) -> None:
    state.set_awaiting_search(False)
    await cb.message.edit_text(menu_text(), reply_markup=main_menu_kb())
    await cb.answer()


async def build_employee_entries() -> list[tuple[str, str, int]]:
    """Сотрудники = все пользователи AmoCRM + все, у кого есть звонки в базе.

    Отсортированы по числу разобранных звонков (убыв.). Используется и в списке
    сотрудников, и в поиске по имени.
    """
    db_rows = {str(r["manager_id"]): (r["manager_name"], r["cnt"]) for r in db.managers()}
    entries: list[tuple[str, str, int]] = []
    if amocrm.is_configured():
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


def employees_kb(
    entries: list[tuple[str, str, int]], lang: str, with_search: bool = True
) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text=f"👨‍💼 {name} ({cnt})", callback_data=f"mgr:{mid}:0")]
        for mid, name, cnt in entries
    ]
    if with_search:
        kb.append([InlineKeyboardButton(text=t(lang, "btn_search"), callback_data="find")])
    kb.append([InlineKeyboardButton(text=t(lang, "btn_back_menu"), callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


@dp.callback_query(F.data == "mgrs")
async def cb_managers(cb: CallbackQuery) -> None:
    state.set_awaiting_search(False)
    lang = state.get_lang()
    entries = await build_employee_entries()
    if not entries:
        await cb.message.edit_text(
            t(lang, "employees_empty"),
            reply_markup=back_kb("menu", t(lang, "btn_back_menu")),
        )
        await cb.answer()
        return
    await cb.message.edit_text(
        t(lang, "employees_title"),
        reply_markup=employees_kb(entries, lang),
    )
    await cb.answer()


# ================== ЯЗЫК + ПОИСК СОТРУДНИКА ==================

def _next_lang(cur: str) -> str:
    return LANGS[(LANGS.index(cur) + 1) % len(LANGS)] if cur in LANGS else "ru"


async def _rerender_after_lang(cb: CallbackQuery, code: str) -> None:
    """Перерисовать текущее сообщение (мастер или меню) на новом языке."""
    setup = state.get_setup()
    if setup:
        await cb.message.edit_text(
            setup_step_text(setup.get("step", "secret"), code), reply_markup=lang_kb(code)
        )
    else:
        await cb.message.edit_text(menu_text(code), reply_markup=main_menu_kb(code))


@dp.callback_query(F.data.startswith("setlang:"))
async def cb_setlang(cb: CallbackQuery) -> None:
    code = cb.data.split(":")[1]
    if code not in LANGS:
        code = "ru"
    state.set_lang(code)
    await cb.answer(t(code, "lang_switched"))
    await _rerender_after_lang(cb, code)


@dp.callback_query(F.data == "lang")
async def cb_lang(cb: CallbackQuery) -> None:
    # запасной обработчик для старых кнопок-тумблеров: циклим язык по кругу
    code = _next_lang(state.get_lang())
    state.set_lang(code)
    await cb.answer(t(code, "lang_switched"))
    await _rerender_after_lang(cb, code)


@dp.callback_query(F.data == "find")
async def cb_find(cb: CallbackQuery) -> None:
    lang = state.get_lang()
    state.set_awaiting_search(True)
    await cb.answer()
    await cb.message.answer(
        t(lang, "search_prompt"),
        reply_markup=back_kb("mgrs", t(lang, "btn_back_employees")),
    )


async def run_employee_search(chat_id: int, query: str) -> None:
    """Ищет сотрудников по подстроке имени и показывает совпадения кнопками."""
    lang = state.get_lang()
    q = query.strip().lower()
    entries = await build_employee_entries()
    matched = [e for e in entries if q in e[1].lower()]
    if not matched:
        await bot.send_message(
            chat_id,
            t(lang, "search_none") + query,
            reply_markup=back_kb("mgrs", t(lang, "btn_back_employees")),
        )
        return
    await bot.send_message(
        chat_id,
        t(lang, "search_title", q=query),
        reply_markup=employees_kb(matched, lang, with_search=False),
    )


@dp.callback_query(F.data.startswith("mgr:"))
async def cb_manager(cb: CallbackQuery) -> None:
    _, manager_id, page_s = cb.data.split(":")
    page = int(page_s)
    lang = state.get_lang()
    total = db.count_for(manager_id)
    calls = db.calls_for(manager_id, offset=page * PAGE_SIZE, limit=PAGE_SIZE)

    name = t(lang, "mgr_default_name")
    if calls:
        name = db.get_call(calls[0]["id"])["manager_name"]
    elif amocrm.is_configured() and manager_id.isdigit():
        try:
            users = await amocrm.get_users()
            name = users.get(int(manager_id), name)
        except Exception:
            pass

    # неразобранные звонки этого сотрудника из CRM (можно разобрать по нажатию)
    pending = []
    if page == 0 and amocrm.is_configured() and manager_id.isdigit():
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
        header = f"👨‍💼 {name}\n\n{db.format_stats(stats, lang)}\n\n"
    else:
        header = f"👨‍💼 {name}\n\n{t(lang, 'mgr_no_calls')}\n\n"
    if calls or pending:
        header += t(lang, "calls_pick_hint")
    else:
        header += t(lang, "calls_none_crm")

    kb = []
    for c in calls:
        emoji = db.VERDICT_EMOJI.get(c["verdict"], "❓")
        score = f"{c['score']}/10" if c["score"] is not None else "—"
        status_tag = db.status_short(c["call_status"], lang)
        status_str = f" • {status_tag}" if status_tag else ""
        label = f"{emoji} {fmt_dt(c['created_at'])} • {fmt_dur(c['duration'])} • {score}{status_str} • {c['phone'] or t(lang, 'no_number')}"
        kb.append([InlineKeyboardButton(text=label[:60], callback_data=f"call:{c['id']}")])
    for c in pending:
        status_tag = db.status_short(c["call_status"], lang)
        status_str = f" • {status_tag}" if status_tag else ""
        label = f"⬜ {fmt_dt(c['created_at'])} • {fmt_dur(c['duration'])}{status_str} • {c['phone'] or t(lang, 'no_number')}"
        kb.append(
            [InlineKeyboardButton(text=label[:60], callback_data=f"anlz:{c['note_id']}:{manager_id}")]
        )

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"mgr:{manager_id}:{page - 1}"))
    if (page + 1) * PAGE_SIZE < total:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"mgr:{manager_id}:{page + 1}"))
    if nav:
        kb.append(nav)
    kb.append([InlineKeyboardButton(text=t(lang, "btn_pick_date"), callback_data=f"dates:{manager_id}")])
    kb.append([InlineKeyboardButton(text=t(lang, "btn_back_employees"), callback_data="mgrs")])

    await cb.message.edit_text(header, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await cb.answer()


WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def _day_bounds(day_key: str) -> tuple[int, int]:
    d = datetime.strptime(day_key, "%Y%m%d")
    start = int(d.timestamp())
    return start, start + 86400


@dp.callback_query(F.data.startswith("dates:"))
async def cb_dates(cb: CallbackQuery) -> None:
    manager_id = cb.data.split(":")[1]
    lang = state.get_lang()
    date_counts: dict[str, int] = dict(db.dates_for(manager_id))

    # добавляем даты неразобранных звонков из CRM
    if amocrm.is_configured() and manager_id.isdigit():
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
        await cb.answer(t(lang, "no_calls_yet"))
        return

    kb = []
    for key in sorted(date_counts, reverse=True)[:14]:
        d = datetime.strptime(key, "%Y%m%d")
        label = f"📅 {d.strftime('%d.%m.%Y')} ({t(lang, f'wd_{d.weekday()}')}) • {date_counts[key]} {t(lang, 'calls_short')}"
        kb.append([InlineKeyboardButton(text=label, callback_data=f"mgrd:{manager_id}:{key}")])
    kb.append([InlineKeyboardButton(text=t(lang, "btn_to_employee"), callback_data=f"mgr:{manager_id}:0")])

    await cb.message.edit_text(
        t(lang, "dates_pick"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
    )
    await cb.answer()


@dp.callback_query(F.data.startswith("mgrd:"))
async def cb_manager_day(cb: CallbackQuery) -> None:
    _, manager_id, day_key = cb.data.split(":")
    lang = state.get_lang()
    start_ts, end_ts = _day_bounds(day_key)
    day_label = datetime.strptime(day_key, "%Y%m%d").strftime("%d.%m.%Y")

    calls = db.calls_for_day(manager_id, start_ts, end_ts)

    pending = []
    if amocrm.is_configured() and manager_id.isdigit():
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

    name = t(lang, "mgr_default_name")
    if calls:
        row = db.get_call(calls[0]["id"])
        name = row["manager_name"]
    elif amocrm.is_configured() and manager_id.isdigit():
        try:
            users = await amocrm.get_users()
            name = users.get(int(manager_id), name)
        except Exception:
            pass

    if not calls and not pending:
        await cb.answer(t(lang, "no_calls_day", day=day_label))
        return

    kb = []
    for c in calls:
        emoji = db.VERDICT_EMOJI.get(c["verdict"], "❓")
        score = f"{c['score']}/10" if c["score"] is not None else "—"
        status_tag = db.status_short(c["call_status"], lang)
        status_str = f" • {status_tag}" if status_tag else ""
        label = f"{emoji} {fmt_dt(c['created_at'])} • {fmt_dur(c['duration'])} • {score}{status_str} • {c['phone'] or t(lang, 'no_number')}"
        kb.append([InlineKeyboardButton(text=label[:60], callback_data=f"call:{c['id']}")])
    for c in pending[:20]:
        status_tag = db.status_short(c["call_status"], lang)
        status_str = f" • {status_tag}" if status_tag else ""
        label = f"⬜ {fmt_dt(c['created_at'])} • {fmt_dur(c['duration'])}{status_str} • {c['phone'] or t(lang, 'no_number')}"
        kb.append(
            [InlineKeyboardButton(text=label[:60], callback_data=f"anlz:{c['note_id']}:{manager_id}")]
        )
    kb.append([InlineKeyboardButton(text=t(lang, "btn_other_date"), callback_data=f"dates:{manager_id}")])
    kb.append([InlineKeyboardButton(text=t(lang, "btn_to_employee"), callback_data=f"mgr:{manager_id}:0")])

    await cb.message.edit_text(
        t(lang, "day_calls_header", name=name, day=day_label, n=len(calls) + len(pending)),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
    )
    await cb.answer()


@dp.callback_query(F.data.startswith("anlz:"))
async def cb_analyze(cb: CallbackQuery) -> None:
    _, note_id_s, manager_id = cb.data.split(":")
    note_id = int(note_id_s)
    lang = state.get_lang()
    await cb.answer(t(lang, "analyzing_short"))

    existing = db.find_by_note(note_id)
    if existing:
        await send_call_package(cb.message.chat.id, existing["id"])
        return

    msg = await bot.send_message(cb.message.chat.id, t(lang, "downloading"))
    try:
        crm_calls = await amocrm.fetch_recent_calls()
        call = next((c for c in crm_calls if c["note_id"] == note_id), None)
        if call is None:
            await msg.edit_text(t(lang, "call_not_found_crm"))
            return
        state.mark_processed(note_id)
        row_id = await process_amo_call(call)
        if row_id is None:
            await msg.edit_text(t(lang, "analyze_failed"))
            return
        await msg.delete()
        await send_call_package(cb.message.chat.id, row_id)
    except Exception as e:
        log.exception("Ошибка разбора звонка %s", note_id)
        await msg.edit_text(t(lang, "error_generic", err=str(e)))


async def _build_pdf(c, lang: str, body: str) -> Path | None:
    """Собирает PDF по звонку. При любой ошибке (нет шрифта и т.п.) — None, звонок
    всё равно откроется текстом. Возвращает путь к готовому файлу."""
    if not body.strip():
        return None
    title = t(lang, "pdf_title", name=c["manager_name"])
    score = f"{c['score']}/10" if c["score"] is not None else "—"
    status_lbl = db.status_label(c["call_status"], lang)
    meta_lines = [
        f"{fmt_dt(c['created_at'])} • {c['direction'] or '—'} • {fmt_dur(c['duration'])}",
        f"{t(lang, 'pdf_score')}: {score}" + (f" • {status_lbl}" if status_lbl else ""),
    ]
    if c["phone"]:
        meta_lines.append(f"Tel: {c['phone']}")
    dest = TMP_DIR / f"call_{c['id']}.pdf"
    try:
        return await asyncio.to_thread(pdf.make_call_pdf, dest, title, meta_lines, body)
    except Exception:
        log.exception("Не удалось собрать PDF для звонка %s", c["id"])
        return None


async def send_call_package(chat_id: int, call_id: int) -> None:
    """Аудио + PDF (полный разбор на выбранном языке) + текст-выжимка + кнопки."""
    c = db.get_call(call_id)
    lang = state.get_lang()
    if not c:
        await bot.send_message(chat_id, t(lang, "call_not_found"))
        return

    emoji = db.VERDICT_EMOJI.get(c["verdict"], "❓")
    score = f"{c['score']}/10" if c["score"] is not None else "—"
    status_lbl = db.status_label(c["call_status"], lang)
    status_str = f" • {status_lbl}" if status_lbl else ""
    caption_lines = [
        f"{emoji} {c['manager_name']} • {score}",
        f"📅 {fmt_dt(c['created_at'])} • {c['direction'] or '—'} • {fmt_dur(c['duration'])}{status_str}",
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
        await bot.send_message(chat_id, caption + "\n" + t(lang, "audio_unavailable"))

    # 2. Готовим содержимое разбора на выбранном языке.
    #    uz: полный дословный диалог + ТЗ (uz_document, кэш в doc_full) и короткое ТЗ в чат.
    #    ru: готовый аудит (report) — он уже на русском, лишних вызовов LLM нет.
    inline_text = ""
    pdf_body = ""
    if lang == "uz":
        pdf_body = c["doc_full"] or ""
        if not pdf_body and c["transcript"]:
            try:
                pdf_body = await uz_document(c["transcript"])
                db.set_doc_full(call_id, pdf_body)
            except Exception:
                log.exception("Ошибка генерации uz-документа")
        uz = c["uz_doc"]
        if not uz and c["transcript"]:
            try:
                uz = await uz_tz(c["transcript"])
                db.set_uz_doc(call_id, uz)
            except Exception:
                log.exception("Ошибка генерации ТЗ")
        inline_text = uz or ""
        if not pdf_body:
            pdf_body = inline_text or c["report"] or c["transcript"] or ""
    else:  # ru (и en, пока сам AI-разбор не переведён)
        pdf_body = c["report"] or c["transcript"] or ""
        # в чат — только короткий вывод + совет; полный разбор с диалогом уходит в PDF
        inline_text = extract_summary(c["report"]) if c["report"] else ""

    # 3. PDF-документ (если есть из чего собрать; ошибка сборки не ломает звонок)
    pdf_path = await _build_pdf(c, lang, pdf_body)
    if pdf_path:
        try:
            await bot.send_document(
                chat_id,
                FSInputFile(pdf_path, filename=f"call_{c['id']}.pdf"),
                caption=t(lang, "pdf_caption"),
            )
        except Exception:
            log.exception("Не удалось отправить PDF звонка %s", c["id"])
        finally:
            pdf_path.unlink(missing_ok=True)

    # 4. Текст-выжимка в чат + кнопка назад
    kb = back_kb(f"mgr:{c['manager_id']}:0", t(lang, "btn_back_calls"))
    if inline_text:
        await send_long(chat_id, inline_text, reply_markup=kb)
    else:
        await bot.send_message(chat_id, t(lang, "doc_unavailable"), reply_markup=kb)


@dp.callback_query(F.data.startswith("call:"))
async def cb_call(cb: CallbackQuery) -> None:
    call_id = int(cb.data.split(":")[1])
    await cb.answer()
    await send_call_package(cb.message.chat.id, call_id)


@dp.callback_query(F.data.startswith("txt:"))
async def cb_transcript(cb: CallbackQuery) -> None:
    call_id = int(cb.data.split(":")[1])
    lang = state.get_lang()
    c = db.get_call(call_id)
    if not c:
        await cb.answer(t(lang, "call_not_found"))
        return
    await cb.answer()
    text = c["transcript"] or t(lang, "transcript_empty")
    await send_long(
        cb.message.chat.id,
        t(lang, "transcript_title", text=text),
        reply_markup=back_kb(f"mgr:{c['manager_id']}:0", t(lang, "btn_back_calls")),
    )


@dp.callback_query(F.data.startswith("rep:"))
async def cb_report(cb: CallbackQuery) -> None:
    call_id = int(cb.data.split(":")[1])
    lang = state.get_lang()
    c = db.get_call(call_id)
    if not c:
        await cb.answer(t(lang, "call_not_found"))
        return
    await cb.answer()
    await send_long(
        cb.message.chat.id,
        c["report"] or t(lang, "report_empty"),
        reply_markup=back_kb(f"mgr:{c['manager_id']}:0", t(lang, "btn_back_calls")),
    )


@dp.callback_query(F.data == "stats")
async def cb_stats(cb: CallbackQuery) -> None:
    lang = state.get_lang()
    total_stats = db.stats_for()
    lines = [t(lang, "stats_dept_title"), db.format_stats(total_stats, lang)]
    rows = [r for r in db.managers() if manager_allowed(r["manager_name"])]
    if rows:
        lines.append(t(lang, "stats_by_employee"))
        for r in rows:
            s = db.stats_for(r["manager_id"])
            avg = t(lang, "avg_score_suffix", x=s["avg_score"]) if s["avg_score"] is not None else ""
            lines.append(
                f"• {r['manager_name']}: {s['total']} {t(lang, 'calls_short')}, "
                f"✅{s['percent']['ok']}% ❌{s['percent']['fail']}% ❓{s['percent']['doubt']}%{avg}"
            )
    await cb.message.edit_text("\n".join(lines), reply_markup=back_kb("menu", t(lang, "btn_back_menu")))
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
    verdicts = {"ok": 0, "fail": 0, "doubt": 0}
    scores = []
    per_mgr: dict[str, dict] = {}
    for c in calls:
        verdicts[c["verdict"]] = verdicts.get(c["verdict"], 0) + 1
        if c["score"] is not None:
            scores.append(c["score"])
        m = per_mgr.setdefault(
            c["manager_name"], {"n": 0, "ok": 0, "fail": 0, "doubt": 0, "scores": []}
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
        f"Успешных: {verdicts['ok']}, неуспешных: {verdicts['fail']}, под вопросом: {verdicts['doubt']}",
        f"Средний балл отдела: {avg}/10",
        "",
        "По сотрудникам:",
    ]
    for name, m in sorted(per_mgr.items(), key=lambda x: -x[1]["n"]):
        m_avg = round(sum(m["scores"]) / len(m["scores"]), 1) if m["scores"] else "—"
        facts.append(
            f"- {name}: {m['n']} зв., ср. балл {m_avg}/10, "
            f"успешных {m['ok']}, неуспешных {m['fail']}, под вопросом {m['doubt']}"
        )

    summaries = []
    for c in calls[:15]:
        summaries.append(
            f"— {c['manager_name']} • {fmt_dt(c['created_at'])} • {c['phone'] or 'без номера'}:\n"
            f"{report_excerpt(c['report'] or '', max_len=300)}"
        )
    if len(calls) > 15:
        summaries.append(f"(и ещё {len(calls) - 15} звонков — в выжимку не вошли)")

    return await team_report("\n".join(facts), "\n\n".join(summaries))


@dp.callback_query(F.data == "daily")
async def cb_daily(cb: CallbackQuery) -> None:
    lang = state.get_lang()
    await cb.answer(t(lang, "preparing_report"))
    msg = await bot.send_message(cb.message.chat.id, t(lang, "daily_building"))
    try:
        report = await build_daily_report()
        if report is None:
            await msg.edit_text(t(lang, "daily_empty"))
            return
        await msg.delete()
        await send_long(cb.message.chat.id, report, reply_markup=back_kb("menu", t(lang, "btn_menu")))
    except Exception as e:
        log.exception("Ошибка отчёта за день")
        await msg.edit_text(t(lang, "daily_error", err=str(e)))


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
                    await bot.send_message(owner, t(state.get_lang(), "daily_auto_header"))
                    await send_long(owner, report)
        except Exception as e:
            log.error("Ошибка автоотчёта: %s", e)


# ================== РУЧНАЯ ЗАГРУЗКА ==================

@dp.message(F.voice | F.audio | F.document)
async def handle_file(message: Message) -> None:
    lang = state.get_lang()
    if not is_owner_chat(message.chat.id):
        await message.answer(t(lang, "private_bot"))
        return

    doc = message.document
    if doc and (doc.file_name or "").lower().endswith(".txt"):
        path = TMP_DIR / f"tg_{doc.file_id}.txt"
        await bot.download(doc, destination=path)
        transcript = path.read_text(encoding="utf-8", errors="ignore")
        path.unlink(missing_ok=True)
        status = await message.answer(t(lang, "auditing"))
        try:
            await run_manual_analysis(message, transcript)
            await status.delete()
        except Exception as e:
            log.exception("Ошибка анализа txt")
            await status.edit_text(t(lang, "error_generic", err=str(e)))
        return

    media = message.voice or message.audio or doc
    if doc and not (doc.mime_type or "").startswith("audio"):
        await message.answer(t(lang, "send_audio_hint"))
        return

    if media.file_size and media.file_size > 20 * 1024 * 1024:
        await message.answer(t(lang, "file_too_big"))
        return

    ext = ".ogg" if message.voice else ".mp3"
    fname = (doc and doc.file_name) or (message.audio and message.audio.file_name) or ""
    if "." in fname:
        ext = "." + fname.rsplit(".", 1)[-1]

    path = AUDIO_DIR / f"manual_{media.file_unique_id}{ext}"
    status = await message.answer(t(lang, "got_recording"))
    try:
        await bot.download(media, destination=path)
        path = preprocess(path)
        transcript = await transcribe(path)
        if len(transcript) < 30:
            await status.edit_text(t(lang, "no_speech"))
            path.unlink(missing_ok=True)
            return
        await status.edit_text(t(lang, "transcribed_auditing"))
        duration = (message.voice and message.voice.duration) or (
            message.audio and message.audio.duration
        ) or 0
        await run_manual_analysis(message, transcript, duration=duration, audio_path=path)
        await status.delete()
    except Exception as e:
        log.exception("Ошибка обработки файла")
        await status.edit_text(t(lang, "error_generic", err=str(e)))


@dp.message(F.text)
async def handle_text(message: Message) -> None:
    lang = state.get_lang()
    if not is_owner_chat(message.chat.id):
        await message.answer(t(lang, "private_bot"))
        return
    # мастер подключения amoCRM: очередной текст — это значение шага (ключ/айди/токен/адрес)
    setup = state.get_setup()
    if setup:
        await handle_amo_setup(message, setup)
        return
    text = message.text.strip()
    # режим поиска сотрудника: следующий текст трактуем как имя, а не как расшифровку
    if state.is_awaiting_search():
        state.set_awaiting_search(False)
        await run_employee_search(message.chat.id, text)
        return
    if len(text) < 100:
        await message.answer(t(lang, "send_call_hint"))
        return
    status = await message.answer(t(lang, "auditing"))
    try:
        await run_manual_analysis(message, text)
        await status.delete()
    except Exception as e:
        log.exception("Ошибка анализа текста")
        await status.edit_text(t(lang, "error_generic", err=str(e)))


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
    lang = state.get_lang()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_audio_review"), callback_data=f"call:{row_id}")],
            [InlineKeyboardButton(text=t(lang, "btn_menu"), callback_data="menu")],
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
            score=None,  # недозвон/пропущенный — разговора не было, не портим средний балл нулём
            verdict="fail",
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
    waiting_logged = False
    while True:
        # ждём, пока владелец подключит amoCRM (введёт ключи) и станет владельцем
        if not amocrm.is_configured() or state.get_owner() is None:
            if not waiting_logged:
                log.info("Жду подключения amoCRM и владельца — звонки пока не трогаю.")
                waiting_logged = True
            await asyncio.sleep(5)
            continue
        waiting_logged = False

        # первый запуск на этом аккаунте: помечаем текущую историю обработанной,
        # чтобы не вывалить владельцу все старые звонки разом (и при смене аккаунта тоже)
        if not state.amo_initialized():
            try:
                name = await amocrm.check_connection()
                log.info("AmoCRM подключён: %s", name)
                for call in await amocrm.fetch_recent_calls():
                    state.mark_processed(call["note_id"])
                state.set_amo_initialized()
                log.info("Старые звонки пропущены, слежу только за новыми.")
            except Exception as e:
                log.error("AmoCRM: ошибка подключения/инициализации — %s", e)
                await asyncio.sleep(POLL_INTERVAL)
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
