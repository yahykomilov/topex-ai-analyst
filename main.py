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
import auth
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

# чаты в процессе входа: {chat_id: {"stage": "login"|"password", "login": str}}
pending_login: dict[int, dict] = {}


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


# ================== РОЛИ: КТО СМОТРИТ И ЧТО ЕМУ ВИДНО ==================

# Владелец бота (первый /start и EXTRA_OWNER_IDS) работает без логина — как «владелец».
OWNER_VIEW = {
    "login": "owner",
    "full_name": "",
    "role": auth.OWNER,
    "branch_id": None,
    "operator_amo_id": None,
}


def viewer(chat_id: int):
    """Кто смотрит: вошедший по /login пользователь или владелец чата. None — посторонний."""
    user = auth.current_user(chat_id)
    if user is not None:
        return user
    if is_owner_chat(chat_id):
        return OWNER_VIEW
    return None


def role_of(user) -> str:
    return user["role"] if user else ""


def role_label(user) -> str:
    return t(f"role_{role_of(user)}") if user else ""


def view_name(user) -> str:
    if not user:
        return ""
    return user["full_name"] or user["login"]


def scope_of(user) -> list | None:
    """Какие manager_id видит смотрящий: None = все, список = только эти, [] = никого."""
    return auth.visible_manager_ids(user)


def is_boss(user) -> bool:
    """Директор или владелец — видит все филиалы."""
    return role_of(user) in (auth.DIRECTOR, auth.OWNER)


async def cb_viewer(cb: CallbackQuery):
    """Смотрящий для нажатой кнопки; None + подсказка, если не авторизован."""
    user = viewer(cb.message.chat.id)
    if user is None:
        await cb.answer(t("auth_not_logged_in"), show_alert=True)
    return user


async def denied(cb: CallbackQuery, user, manager_id) -> bool:
    """True + предупреждение, если смотрящему не положено видеть этого сотрудника."""
    if not auth.can_see_manager(user, manager_id):
        await cb.answer(t("auth_no_access"), show_alert=True)
        return True
    return False


def own_manager_id(user) -> str | None:
    """amoCRM-id самого оператора (для экрана «мои звонки»)."""
    if role_of(user) != auth.OPERATOR:
        return None
    return user["operator_amo_id"] or None


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


def main_menu_kb(user=None) -> InlineKeyboardMarkup:
    """Меню под роль смотрящего: оператор / РОП / директор (владелец)."""
    role = role_of(user)
    if role == auth.OPERATOR:
        rows = [
            [InlineKeyboardButton(text=t("btn_my_calls"), callback_data="mycalls")],
            [InlineKeyboardButton(text=t("btn_my_stats"), callback_data="stats")],
            [InlineKeyboardButton(text=t("btn_my_errors"), callback_data="errs:all")],
            [InlineKeyboardButton(text=t("btn_daily"), callback_data="daily")],
        ]
    elif role == auth.ROP:
        rows = [
            [InlineKeyboardButton(text=t("btn_branch_team"), callback_data="mgrs")],
            [InlineKeyboardButton(text=t("btn_branch_stats"), callback_data="stats")],
            [InlineKeyboardButton(text=t("btn_branch_errors"), callback_data="errs:all")],
            [InlineKeyboardButton(text=t("btn_daily"), callback_data="daily")],
        ]
    else:  # директор и владелец — весь отдел
        rows = [
            [InlineKeyboardButton(text=t("btn_managers"), callback_data="mgrs")],
            [InlineKeyboardButton(text=t("btn_branches"), callback_data="stats")],
            [InlineKeyboardButton(text=t("btn_daily"), callback_data="daily")],
            [InlineKeyboardButton(text=t("btn_stats"), callback_data="statsall")],
        ]
    rows.append([InlineKeyboardButton(text=t("btn_language"), callback_data="lang")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def menu_screen_text(user) -> str:
    """Текст главного меню под роль + строка «кто вошёл»."""
    role = role_of(user)
    if role == auth.OPERATOR:
        body = t("menu_text_operator")
    elif role == auth.ROP:
        body = t("menu_text_rop")
    else:
        body = t("menu_text")
    if user is None or user is OWNER_VIEW:
        return body
    branch = auth.branch_name(user["branch_id"]) if user["branch_id"] else ""
    head = t(
        "menu_role_line",
        name=view_name(user),
        role=role_label(user),
        branch=t("menu_branch_suffix", branch=branch) if branch else "",
    )
    return f"{head}\n\n{body}"


def back_kb(callback_data: str = "mgrs", text: str | None = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text or t("btn_back"), callback_data=callback_data)]
        ]
    )


# ================== КОМАНДЫ ==================

@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    if state.get_owner() is None:
        state.set_owner(message.chat.id)
        await message.answer(t("owner_set"))
    user = viewer(message.chat.id)
    if user is None:
        # не владелец и не вошёл — предлагаем логин (роли заводит владелец)
        await message.answer(f"{t('private_bot')}\n\n{t('auth_login_hint')}")
        return
    await message.answer(menu_screen_text(user), reply_markup=main_menu_kb(user))


@dp.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    user = viewer(message.chat.id)
    if user is None:
        await message.answer(t("auth_not_logged_in"))
        return
    pending_search.discard(message.chat.id)
    await message.answer(menu_screen_text(user), reply_markup=main_menu_kb(user))


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
    if viewer(message.chat.id) is None:
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
    user = viewer(cb.message.chat.id)
    await cb.answer(t("lang_changed"))
    await cb.message.edit_text(menu_screen_text(user), reply_markup=main_menu_kb(user))


@dp.message(Command("status"))
async def cmd_status(message: Message) -> None:
    if not is_boss(viewer(message.chat.id)):
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
        reply_markup=main_menu_kb(viewer(message.chat.id)),
    )


# ================== ВХОД / ВЫХОД ==================

async def do_login(message: Message, login_name: str, password: str) -> None:
    """Проверяет логин/пароль и сразу удаляет сообщение с паролем из чата."""
    chat_id = message.chat.id
    try:
        await message.delete()
    except Exception:  # нет прав на удаление — не критично
        pass

    account = auth.find_login(login_name)
    if account is not None and not account["active"]:
        pending_login.pop(chat_id, None)
        await bot.send_message(chat_id, t("auth_inactive"))
        return

    user = auth.login(chat_id, login_name, password)
    if user is None:
        await bot.send_message(chat_id, t("auth_failed"))
        return

    pending_login.pop(chat_id, None)
    pending_search.discard(chat_id)
    await bot.send_message(
        chat_id, t("auth_success", name=view_name(user), role=role_label(user))
    )
    if user["role"] == auth.OPERATOR and not user["operator_amo_id"]:
        await bot.send_message(chat_id, t("auth_operator_unbound"))
    elif user["role"] == auth.ROP and user["branch_id"] is None:
        await bot.send_message(chat_id, t("rop_no_branch"))
    await bot.send_message(
        chat_id, menu_screen_text(user), reply_markup=main_menu_kb(user)
    )


@dp.message(Command("login"))
async def cmd_login(message: Message) -> None:
    parts = (message.text or "").split()
    if len(parts) >= 3:  # /login логин пароль — одной строкой
        await do_login(message, parts[1], parts[2])
        return
    pending_login[message.chat.id] = {"stage": "login"}
    await message.answer(t("auth_login_prompt"))


@dp.message(Command("logout"))
async def cmd_logout(message: Message) -> None:
    pending_login.pop(message.chat.id, None)
    pending_search.discard(message.chat.id)
    auth.logout(message.chat.id)
    await message.answer(t("auth_logged_out"))


@dp.message(Command("whoami"))
async def cmd_whoami(message: Message) -> None:
    user = viewer(message.chat.id)
    if user is None:
        await message.answer(t("auth_not_logged_in"))
        return
    await message.answer(menu_screen_text(user), reply_markup=main_menu_kb(user))


# ================== НАСТРОЙКА РОЛЕЙ (ТОЛЬКО ВЛАДЕЛЕЦ) ==================

async def admin_ok(message: Message) -> bool:
    if is_owner_chat(message.chat.id):
        return True
    await message.answer(t("admin_only"))
    return False


@dp.message(Command("branch_add"))
async def cmd_branch_add(message: Message) -> None:
    if not await admin_ok(message):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer(t("admin_usage_branch_add"))
        return
    name = parts[1].strip()
    branch_id = auth.create_branch(name)
    await message.answer(t("admin_branch_added", name=name, id=branch_id))


@dp.message(Command("branches"))
async def cmd_branches(message: Message) -> None:
    if not await admin_ok(message):
        return
    rows = auth.list_branches()
    if not rows:
        await message.answer(t("admin_branches_empty"))
        return
    lines = [t("admin_branches")]
    for b in rows:
        lines.append(f"{b['id']} — {b['name']} — {len(auth.branch_operator_ids(b['id']))}")
    await send_long(message.chat.id, "\n".join(lines))


@dp.message(Command("user_add"))
async def cmd_user_add(message: Message) -> None:
    if not await admin_ok(message):
        return
    parts = (message.text or "").split(maxsplit=6)
    if len(parts) < 4:
        await send_long(message.chat.id, t("admin_usage_user_add"))
        return
    login_name, password, role = parts[1], parts[2], parts[3].lower()
    branch_arg = parts[4] if len(parts) > 4 else "-"
    amo_arg = parts[5] if len(parts) > 5 else "-"
    full_name = parts[6].strip() if len(parts) > 6 else ""

    if role not in auth.ROLES:
        await message.answer(t("admin_bad_role"))
        return
    if auth.find_login(login_name) is not None:
        await message.answer(t("admin_user_exists", login=login_name))
        return
    branch_id = None
    if branch_arg not in ("-", ""):
        if not branch_arg.isdigit() or not auth.branch_exists(int(branch_arg)):
            await message.answer(t("admin_bad_branch", id=branch_arg))
            return
        branch_id = int(branch_arg)
    amo_id = None if amo_arg in ("-", "") else amo_arg

    auth.create_user(
        login_name,
        password,
        role,
        full_name=full_name or login_name,
        branch_id=branch_id,
        operator_amo_id=amo_id,
    )
    extra = []
    if branch_id:
        extra.append(auth.branch_name(branch_id))
    if amo_id:
        extra.append(f"amo:{amo_id}")
    await message.answer(
        t(
            "admin_user_added",
            login=login_name,
            role=t(f"role_{role}"),
            extra=f"({', '.join(extra)})" if extra else "",
        )
    )


@dp.message(Command("users"))
async def cmd_users(message: Message) -> None:
    if not await admin_ok(message):
        return
    rows = auth.list_users()
    if not rows:
        await message.answer(t("admin_users_empty"))
        return
    lines = [t("admin_users")]
    for u in rows:
        branch = auth.branch_name(u["branch_id"]) or "—"
        role_name = t("role_" + u["role"])
        amo = u["operator_amo_id"] or "—"
        off = "" if u["active"] else t("admin_inactive_mark")
        lines.append(f"• {u['login']} — {role_name} — {branch} — {amo}{off}")
    await send_long(message.chat.id, "\n".join(lines))


@dp.message(Command("bind"))
async def cmd_bind(message: Message) -> None:
    if not await admin_ok(message):
        return
    parts = (message.text or "").split()
    if len(parts) < 3:
        await message.answer(t("admin_usage_bind"))
        return
    user = auth.find_login(parts[1])
    if user is None:
        await message.answer(t("admin_user_not_found", login=parts[1]))
        return
    auth.bind_operator(user["id"], parts[2])
    await message.answer(t("admin_bound", login=parts[1], amo_id=parts[2]))


@dp.message(Command("passwd"))
async def cmd_passwd(message: Message) -> None:
    if not await admin_ok(message):
        return
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(t("admin_usage_passwd"))
        return
    user = auth.find_login(parts[1])
    if user is None:
        await message.answer(t("admin_user_not_found", login=parts[1]))
        return
    auth.set_password(user["id"], parts[2].strip())
    try:
        await message.delete()  # пароль в чате не оставляем
    except Exception:
        pass
    await bot.send_message(message.chat.id, t("admin_passwd_ok", login=parts[1]))


@dp.message(Command("user_on", "user_off"))
async def cmd_user_access(message: Message) -> None:
    if not await admin_ok(message):
        return
    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.answer(t("admin_usage_access"))
        return
    user = auth.find_login(parts[1])
    if user is None:
        await message.answer(t("admin_user_not_found", login=parts[1]))
        return
    turn_on = parts[0].split("@")[0].endswith("user_on")
    auth.set_active(user["id"], turn_on)
    await message.answer(
        t("admin_access_on" if turn_on else "admin_access_off", login=parts[1])
    )


@dp.message(Command("amo_ids"))
async def cmd_amo_ids(message: Message) -> None:
    if not await admin_ok(message):
        return
    entries = await collect_managers()
    if not entries:
        await message.answer(t("admin_amo_ids_empty"))
        return
    lines = [t("admin_amo_ids")]
    lines += [f"• {mid} — {name} — {cnt}" for mid, name, cnt in entries]
    await send_long(message.chat.id, "\n".join(lines))


# ================== МЕНЮ / КНОПКИ ==================

@dp.callback_query(F.data == "menu")
async def cb_menu(cb: CallbackQuery) -> None:
    user = await cb_viewer(cb)
    if user is None:
        return
    pending_search.discard(cb.message.chat.id)
    await cb.message.edit_text(menu_screen_text(user), reply_markup=main_menu_kb(user))
    await cb.answer()


async def collect_managers(scope: list | None = None) -> list[tuple[str, str, int]]:
    """Сотрудники = все пользователи AmoCRM + все, у кого есть звонки в базе.

    scope=None — все (директор/владелец); список manager_id — только они (РОП/оператор).
    """
    allow = None if scope is None else {str(x) for x in scope}

    def visible(mid: str, name: str) -> bool:
        if allow is not None:
            return mid in allow  # привязка к филиалу важнее белого списка
        return manager_allowed(name)

    db_rows = {str(r["manager_id"]): (r["manager_name"], r["cnt"]) for r in db.managers()}
    entries: list[tuple[str, str, int]] = []
    if amo_enabled():
        try:
            users = await amocrm.get_users()
            for uid, name in users.items():
                _, cnt = db_rows.pop(str(uid), (name, 0))
                if visible(str(uid), name):
                    entries.append((str(uid), name, cnt))
        except Exception as e:
            log.error("Не удалось получить сотрудников AmoCRM: %s", e)
    for mid, (name, cnt) in db_rows.items():
        if visible(mid, name):
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
    user = await cb_viewer(cb)
    if user is None:
        return
    pending_search.discard(cb.message.chat.id)

    # оператор видит только себя — сразу открываем его собственные звонки
    if role_of(user) == auth.OPERATOR:
        await cb_my_calls(cb)
        return

    scope = scope_of(user)
    entries = await collect_managers(scope)

    if not entries:
        empty = t("managers_empty")
        if role_of(user) == auth.ROP:
            empty = (
                t("rop_no_branch") if user["branch_id"] is None
                else t("branch_no_operators")
            )
        await cb.message.edit_text(empty, reply_markup=back_kb("menu", t("btn_menu")))
        await cb.answer()
        return

    title = t("managers_title")
    if role_of(user) == auth.ROP and user["branch_id"] is not None:
        title = t("branch_title", name=auth.branch_name(user["branch_id"])) + title

    await cb.message.edit_text(
        title,
        # поиск по имени — только тем, кто видит больше одного сотрудника
        reply_markup=managers_kb(entries, with_search=len(entries) > 1),
    )
    await cb.answer()


@dp.callback_query(F.data == "mgrfind")
async def cb_manager_search(cb: CallbackQuery) -> None:
    if await cb_viewer(cb) is None:
        return
    pending_search.add(cb.message.chat.id)
    await cb.message.edit_text(
        t("search_prompt"), reply_markup=back_kb("mgrs", t("btn_to_managers"))
    )
    await cb.answer()


async def show_search_results(chat_id: int, query: str, scope: list | None = None) -> None:
    needle = query.strip().casefold()
    found = [e for e in await collect_managers(scope) if needle in e[1].casefold()]
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
    user = await cb_viewer(cb)
    if user is None:
        return
    _, manager_id, page_s = cb.data.split(":")
    if await denied(cb, user, manager_id):
        return
    await render_manager(cb, user, manager_id, int(page_s))


@dp.callback_query(F.data == "mycalls")
async def cb_my_calls(cb: CallbackQuery) -> None:
    """Экран оператора: только свои звонки."""
    user = await cb_viewer(cb)
    if user is None:
        return
    manager_id = own_manager_id(user)
    if manager_id is None:
        if role_of(user) == auth.OPERATOR:
            await cb.answer(t("auth_operator_unbound"), show_alert=True)
        else:
            await cb_managers(cb)
        return
    await render_manager(cb, user, manager_id, 0)


async def render_manager(cb: CallbackQuery, user, manager_id: str, page: int) -> None:
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

    # для руководителя показываем, из какого филиала оператор
    _, branch = auth.branch_of_manager(manager_id)
    title = f"👨‍💼 {name}"
    if branch and role_of(user) != auth.OPERATOR:
        title += f" • 🏢 {branch}"

    if total:
        stats = db.stats_for(manager_id)
        header = f"{title}\n\n{i18n.format_stats(stats)}\n\n"
    else:
        header = f"{title}\n\n{t('manager_no_calls')}\n\n"
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
    kb.append(
        [
            InlineKeyboardButton(
                text=t("btn_my_errors") if role_of(user) == auth.OPERATOR else t("btn_errors"),
                callback_data=f"errs:{manager_id}",
            )
        ]
    )
    if role_of(user) == auth.OPERATOR:
        kb.append([InlineKeyboardButton(text=t("btn_menu"), callback_data="menu")])
    else:
        kb.append([InlineKeyboardButton(text=t("btn_to_managers"), callback_data="mgrs")])

    await cb.message.edit_text(header, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await cb.answer()


def _day_bounds(day_key: str) -> tuple[int, int]:
    d = datetime.strptime(day_key, "%Y%m%d")
    start = int(d.timestamp())
    return start, start + 86400


@dp.callback_query(F.data.startswith("dates:"))
async def cb_dates(cb: CallbackQuery) -> None:
    user = await cb_viewer(cb)
    if user is None:
        return
    manager_id = cb.data.split(":")[1]
    if await denied(cb, user, manager_id):
        return
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
    user = await cb_viewer(cb)
    if user is None:
        return
    _, manager_id, day_key = cb.data.split(":")
    if await denied(cb, user, manager_id):
        return
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
    user = await cb_viewer(cb)
    if user is None:
        return
    _, note_id_s, manager_id = cb.data.split(":")
    if await denied(cb, user, manager_id):
        return
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
    user = await cb_viewer(cb)
    if user is None:
        return
    call_id = int(cb.data.split(":")[1])
    c = db.get_call(call_id)
    if not c:
        await cb.answer(t("call_not_found"))
        return
    if await denied(cb, user, c["manager_id"]):
        return
    await cb.answer()
    await send_call_package(cb.message.chat.id, call_id)


@dp.callback_query(F.data.startswith("txt:"))
async def cb_transcript(cb: CallbackQuery) -> None:
    user = await cb_viewer(cb)
    if user is None:
        return
    call_id = int(cb.data.split(":")[1])
    c = db.get_call(call_id)
    if not c:
        await cb.answer(t("call_not_found"))
        return
    if await denied(cb, user, c["manager_id"]):
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
    user = await cb_viewer(cb)
    if user is None:
        return
    call_id = int(cb.data.split(":")[1])
    c = db.get_call(call_id)
    if not c:
        await cb.answer(t("call_not_found"))
        return
    if await denied(cb, user, c["manager_id"]):
        return
    await cb.answer()
    await send_long(
        cb.message.chat.id,
        c["report"] or t("report_missing"),
        reply_markup=back_kb(f"mgr:{c['manager_id']}:0", t("btn_to_calls")),
    )


def manager_stats_line(name: str, stats: dict) -> str:
    avg = (
        t("stats_manager_avg", avg=stats["avg_score"])
        if stats["avg_score"] is not None
        else ""
    )
    return t(
        "stats_manager_line",
        name=name,
        total=stats["total"],
        answered=stats.get("answered", 0),
        noanswer=stats["counts"].get("noanswer", 0),
        ok=stats["percent"]["ok"],
        fail=stats["percent"]["fail"],
        doubt=stats["percent"]["doubt"],
        avg=avg,
    )


@dp.callback_query(F.data == "stats")
async def cb_stats(cb: CallbackQuery) -> None:
    """Статистика под роль: директор — филиалы, РОП — свой филиал, оператор — себя."""
    user = await cb_viewer(cb)
    if user is None:
        return
    if is_boss(user):
        await render_branches(cb, user)
    elif role_of(user) == auth.ROP:
        if user["branch_id"] is None:
            await cb.message.edit_text(
                t("rop_no_branch"), reply_markup=back_kb("menu", t("btn_menu"))
            )
            await cb.answer()
            return
        await render_branch(cb, user, user["branch_id"])
    else:
        await render_my_stats(cb, user)


@dp.callback_query(F.data == "statsall")
async def cb_stats_all(cb: CallbackQuery) -> None:
    """Итог по всему, что видит смотрящий (старый экран «Общая статистика»)."""
    user = await cb_viewer(cb)
    if user is None:
        return
    scope = scope_of(user)
    lines = [t("stats_title"), i18n.format_stats(db.stats_for_ids(scope))]
    rows = db.managers_scoped(scope)
    if scope is None:
        rows = [r for r in rows if manager_allowed(r["manager_name"])]
    if rows:
        lines.append(t("stats_by_manager"))
        for r in rows:
            lines.append(
                manager_stats_line(r["manager_name"], db.stats_for(r["manager_id"]))
            )
    back = "stats" if is_boss(user) else "menu"
    await cb.message.edit_text(
        "\n".join(lines),
        reply_markup=back_kb(back, t("btn_to_branches") if is_boss(user) else t("btn_menu")),
    )
    await cb.answer()


# ---------- экран директора: сводка по филиалам ----------

async def render_branches(cb: CallbackQuery, user) -> None:
    branches = auth.branches_with_operators()
    if not branches:
        await cb.message.edit_text(
            t("branches_empty"), reply_markup=back_kb("menu", t("btn_menu"))
        )
        await cb.answer()
        return

    lines = [t("branches_title")]
    ranked: list[tuple[float, str]] = []
    kb: list[list[InlineKeyboardButton]] = []
    for branch_id, name, ids in branches:
        s = db.stats_for_ids(ids)
        if s["total"]:
            avg = s["avg_score"]
            lines.append(
                t(
                    "branch_line",
                    name=name,
                    operators=len(ids),
                    total=s["total"],
                    answered=s["answered"],
                    noanswer=s["counts"]["noanswer"],
                    ok=s["percent"]["ok"],
                    fail=s["percent"]["fail"],
                    doubt=s["percent"]["doubt"],
                    avg=t("branch_avg_suffix", avg=avg) if avg is not None else "",
                )
            )
            if avg is not None:
                ranked.append((avg, name))
        else:
            lines.append(f"🏢 {name} — {len(ids)}\n{t('branch_no_calls')}")
        kb.append(
            [InlineKeyboardButton(text=f"🏢 {name}", callback_data=f"br:{branch_id}")]
        )

    # где лучше / где хуже
    if len(ranked) > 1:
        ranked.sort(key=lambda x: -x[0])
        lines.append("")
        lines.append(t("branch_best", name=ranked[0][1], avg=ranked[0][0]))
        lines.append(t("branch_worst", name=ranked[-1][1], avg=ranked[-1][0]))

    # операторы со звонками, но без филиала — их не видно ни одному РОПу
    assigned = auth.assigned_operator_ids()
    loose = [
        r
        for r in db.managers()
        if str(r["manager_id"]) not in assigned
        and r["manager_id"] != "manual"
        and manager_allowed(r["manager_name"])
    ]
    if loose:
        lines.append(t("branch_unassigned", count=len(loose)))

    kb.append([InlineKeyboardButton(text=t("btn_dept_total"), callback_data="statsall")])
    kb.append([InlineKeyboardButton(text=t("btn_menu"), callback_data="menu")])
    await cb.message.edit_text(
        "\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )
    await cb.answer()


@dp.callback_query(F.data.startswith("br:"))
async def cb_branch(cb: CallbackQuery) -> None:
    user = await cb_viewer(cb)
    if user is None:
        return
    branch_id = int(cb.data.split(":")[1])
    # директор/владелец — любой филиал, РОП — только свой
    if not is_boss(user) and user["branch_id"] != branch_id:
        await cb.answer(t("auth_no_access"), show_alert=True)
        return
    await render_branch(cb, user, branch_id)


# ---------- экран РОПа: операторы филиала ----------

async def render_branch(cb: CallbackQuery, user, branch_id: int) -> None:
    name = auth.branch_name(branch_id)
    if not name:
        await cb.answer(t("branch_not_found"), show_alert=True)
        return

    ids = auth.branch_operator_ids(branch_id)
    lines = [t("branch_title", name=name), i18n.format_stats(db.stats_for_ids(ids))]
    kb: list[list[InlineKeyboardButton]] = []

    if not ids:
        lines.append("")
        lines.append(t("branch_no_operators"))
    else:
        # имя оператора: из учётки, иначе как записано в звонках
        from_calls = {
            str(r["manager_id"]): r["manager_name"] for r in db.managers_scoped(ids)
        }
        ranked = []
        for op in auth.list_operators(branch_id):
            mid = op["operator_amo_id"]
            if not mid:
                continue
            s = db.stats_for(mid)
            op_name = op["full_name"] or from_calls.get(str(mid)) or str(mid)
            # без оценок — в конец рейтинга
            ranked.append((s["avg_score"] if s["avg_score"] is not None else -1, op_name, mid, s))
        ranked.sort(key=lambda x: -x[0])

        lines.append(t("stats_by_manager"))
        for place, (_, op_name, mid, s) in enumerate(ranked, 1):
            lines.append(f"{place}. " + manager_stats_line(op_name, s))
            kb.append(
                [
                    InlineKeyboardButton(
                        text=f"👨‍💼 {op_name} ({s['total']})", callback_data=f"mgr:{mid}:0"
                    )
                ]
            )
        lines.append(t("branch_pick_operator"))

    kb.append(
        [InlineKeyboardButton(text=t("btn_branch_errors"), callback_data=f"errs:b{branch_id}")]
    )
    if is_boss(user):
        kb.append([InlineKeyboardButton(text=t("btn_to_branches"), callback_data="stats")])
    kb.append([InlineKeyboardButton(text=t("btn_menu"), callback_data="menu")])

    await cb.message.edit_text(
        "\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )
    await cb.answer()


# ---------- экран оператора: своя статистика ----------

async def render_my_stats(cb: CallbackQuery, user) -> None:
    manager_id = own_manager_id(user)
    if manager_id is None:
        await cb.message.edit_text(
            t("auth_operator_unbound"), reply_markup=back_kb("menu", t("btn_menu"))
        )
        await cb.answer()
        return

    stats = db.stats_for(manager_id)
    lines = [t("my_stats_title", name=view_name(user))]
    lines.append(i18n.format_stats(stats) if stats["total"] else t("my_no_calls"))
    kb = [
        [InlineKeyboardButton(text=t("btn_my_calls"), callback_data="mycalls")],
        [InlineKeyboardButton(text=t("btn_my_errors"), callback_data="errs:all")],
        [InlineKeyboardButton(text=t("btn_menu"), callback_data="menu")],
    ]
    await cb.message.edit_text(
        "\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )
    await cb.answer()


# ---------- ошибки: где именно ошиблись ----------

@dp.callback_query(F.data.startswith("errs:"))
async def cb_errors(cb: CallbackQuery) -> None:
    """Звонки с ошибками (❌/❓): у себя, у оператора или по филиалу."""
    user = await cb_viewer(cb)
    if user is None:
        return
    target = cb.data.split(":", 1)[1]
    back_to, back_text = "menu", t("btn_menu")

    if target == "all":
        ids = scope_of(user)
        if role_of(user) == auth.ROP and user["branch_id"] is not None:
            back_to, back_text = "stats", t("btn_back")
    elif target.startswith("b") and target[1:].isdigit():
        branch_id = int(target[1:])
        if not is_boss(user) and user["branch_id"] != branch_id:
            await cb.answer(t("auth_no_access"), show_alert=True)
            return
        ids = auth.branch_operator_ids(branch_id)
        back_to, back_text = f"br:{branch_id}", t("btn_back")
    else:
        if await denied(cb, user, target):
            return
        ids = [target]
        back_to, back_text = f"mgr:{target}:0", t("btn_to_calls")

    rows = db.problem_calls(ids, limit=PAGE_SIZE * 2)
    if not rows:
        await cb.message.edit_text(
            t("errors_empty"), reply_markup=back_kb(back_to, back_text)
        )
        await cb.answer()
        return

    kb = []
    for c in rows:
        emoji = db.VERDICT_EMOJI.get(c["verdict"], "❓")
        score = f"{c['score']}/10" if c["score"] is not None else "—"
        label = f"{emoji} {c['manager_name']} • {fmt_dt(c['created_at'])} • {score}"
        kb.append([InlineKeyboardButton(text=label[:60], callback_data=f"call:{c['id']}")])
    kb.append([InlineKeyboardButton(text=back_text, callback_data=back_to)])

    await cb.message.edit_text(
        f"{t('errors_title')}\n\n{t('errors_hint')}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
    )
    await cb.answer()


# ================== ОТЧЁТ ЗА ДЕНЬ ==================

DAILY_REPORT_HOUR = 20  # автоотчёт каждый день в 20:00


async def build_daily_report(manager_ids: list | None = None, scope_title: str = "") -> str | None:
    """Отчёт за день. manager_ids=None — весь отдел; список — только эти операторы."""
    now = datetime.now()
    day_start = int(datetime(now.year, now.month, now.day).timestamp())
    calls = list(db.calls_between_ids(day_start, day_start + 86400, manager_ids))
    if manager_ids is None:
        # белый список нужен только когда смотрим «всех подряд»;
        # при явной привязке к филиалу/оператору фильтруем уже по id
        calls = [c for c in calls if manager_allowed(c["manager_name"])]
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
        *([f"Охват отчёта: {scope_title}"] if scope_title else []),
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


def daily_scope(user) -> tuple[list | None, str]:
    """Что попадёт в отчёт этому смотрящему: (manager_ids, заголовок охвата)."""
    role = role_of(user)
    if role == auth.OPERATOR:
        manager_id = own_manager_id(user)
        return (
            [manager_id] if manager_id else [],
            t("daily_scope_own", name=view_name(user)),
        )
    if role == auth.ROP:
        branch = auth.branch_name(user["branch_id"]) if user["branch_id"] else ""
        return scope_of(user), t("daily_scope_branch", branch=branch or "—")
    return None, t("daily_scope_all")


@dp.callback_query(F.data == "daily")
async def cb_daily(cb: CallbackQuery) -> None:
    user = await cb_viewer(cb)
    if user is None:
        return
    ids, scope_title = daily_scope(user)
    if ids == [] and role_of(user) == auth.OPERATOR:
        await cb.answer(t("auth_operator_unbound"), show_alert=True)
        return

    await cb.answer(t("daily_preparing"))
    msg = await bot.send_message(cb.message.chat.id, t("daily_building"))
    try:
        report = await build_daily_report(ids, scope_title)
        if report is None:
            await msg.edit_text(t("daily_empty") if ids is None else t("daily_empty_scoped"))
            return
        await msg.delete()
        await send_long(
            cb.message.chat.id,
            f"{scope_title}\n\n{report}",
            reply_markup=back_kb("menu", t("btn_menu_plain")),
        )
    except Exception as e:
        log.exception("Ошибка отчёта за день")
        await msg.edit_text(t("daily_error", error=e))


# автоотчёт операторам в 20:00: по умолчанию выключен (каждому — отдельный запрос к ИИ);
# оператор в любой момент берёт свой отчёт кнопкой «Отчёт за день»
DAILY_AUTO_TO_OPERATORS = False


async def send_daily_auto(full_report: str) -> None:
    """Автоотчёт в 20:00 — каждому по его роли (владелец/директор — отдел, РОП — филиал)."""
    sent: set[int] = set()

    async def deliver(chat_id: int, report: str | None, scope_title: str) -> None:
        if not report or chat_id in sent:
            return
        sent.add(chat_id)
        try:
            await bot.send_message(chat_id, t("daily_auto"))
            await send_long(chat_id, f"{scope_title}\n\n{report}")
        except Exception as e:
            log.error("Не удалось отправить отчёт в чат %s: %s", chat_id, e)

    owner = state.get_owner()
    if owner:
        await deliver(owner, full_report, t("daily_scope_all"))

    for u in auth.list_users():
        if not u["tg_id"] or not u["active"]:
            continue
        role = u["role"]
        if role in (auth.DIRECTOR, auth.OWNER):
            await deliver(u["tg_id"], full_report, t("daily_scope_all"))
            continue
        if role == auth.OPERATOR and not DAILY_AUTO_TO_OPERATORS:
            continue
        ids, scope_title = daily_scope(u)
        if not ids:  # РОП без филиала / оператор без привязки к amoCRM
            continue
        try:
            await deliver(u["tg_id"], await build_daily_report(ids, scope_title), scope_title)
        except Exception as e:
            log.error("Ошибка отчёта для %s: %s", u["login"], e)


async def daily_report_loop() -> None:
    while True:
        await asyncio.sleep(300)
        try:
            if state.get_owner() is None:
                continue
            now = datetime.now()
            today = now.strftime("%Y-%m-%d")
            if now.hour >= DAILY_REPORT_HOUR and state.get_last_daily() != today:
                # сначала общий отчёт: если ИИ недоступен — повторим через 5 минут
                full = await build_daily_report(None, t("daily_scope_all"))
                state.set_last_daily(today)
                if full:
                    await send_daily_auto(full)
        except Exception as e:
            log.error("Ошибка автоотчёта: %s", e)


# ================== РУЧНАЯ ЗАГРУЗКА ==================

@dp.message(F.voice | F.audio | F.document)
async def handle_file(message: Message) -> None:
    if not is_owner_chat(message.chat.id):
        # ручная загрузка записей — только владелец; остальным подсказываем, куда идти
        user = viewer(message.chat.id)
        await message.answer(
            t("auth_no_access") if user else f"{t('private_hint')}\n\n{t('auth_login_hint')}"
        )
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
    text = message.text.strip()

    # шаги входа: логин, затем пароль (сообщение с паролем сразу удаляем)
    step = pending_login.get(message.chat.id)
    if step is not None:
        if step["stage"] == "login":
            step["login"] = text
            step["stage"] = "password"
            await message.answer(t("auth_password_prompt"))
        else:
            await do_login(message, step.get("login", ""), text)
        return

    user = viewer(message.chat.id)
    if user is None:
        await message.answer(f"{t('private_hint')}\n\n{t('auth_login_hint')}")
        return

    # ждём имя сотрудника после кнопки «Поиск по имени»
    if message.chat.id in pending_search:
        pending_search.discard(message.chat.id)
        await show_search_results(message.chat.id, text, scope_of(user))
        return

    # ручной аудит присланного текста — только владелец/директор
    if not is_owner_chat(message.chat.id):
        await message.answer(t("auth_no_access"))
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
    auth.seed_default_users()
    asyncio.create_task(amo_poller())
    asyncio.create_task(daily_report_loop())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
