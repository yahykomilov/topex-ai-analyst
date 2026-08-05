"""Самотест экранов по ролям: собирает тексты и кнопки так же, как бот в Telegram.

Бот НЕ запускается и в сеть не ходит: токен подставной, amoCRM отключён,
база — in-memory (прод calls.db не трогаем). Запуск: python _test_screens.py
"""
import asyncio
import os
import sqlite3
import threading
import time
import types

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "1234567890:TESTtokenTESTtokenTESTtokenTESTtoken")

import auth  # noqa: E402
import db  # noqa: E402
import main  # noqa: E402

main.amo_enabled = lambda: False  # никаких запросов в CRM из тестов

# --- одна in-memory база на db и auth ---
mem = sqlite3.connect(":memory:")
mem.row_factory = sqlite3.Row
ddl = db._conn.execute(
    "SELECT sql FROM sqlite_master WHERE type='table' AND name='calls'"
).fetchone()[0]
mem.execute(ddl)
db._conn, db._lock = mem, threading.Lock()
auth._conn, auth._lock = mem, threading.Lock()
auth.ensure_tables()

TS = int(time.time()) - 60
B_Y = auth.create_branch("Юнусабад")
B_C = auth.create_branch("Чиланзар")
B_S = auth.create_branch("Самарканд")

auth.create_user("boss", "p", auth.DIRECTOR, "Директор Topex")
auth.create_user("ropy", "p", auth.ROP, "РОП Юнусабада", branch_id=B_Y)
auth.create_user("durdona", "p", auth.OPERATOR, "Durdona", branch_id=B_Y, operator_amo_id="111")
auth.create_user("iroda", "p", auth.OPERATOR, "Iroda", branch_id=B_Y, operator_amo_id="222")
auth.create_user("medine", "p", auth.OPERATOR, "Medine", branch_id=B_C, operator_amo_id="333")


def add(mid, name, verdict, score):
    db.save_call(
        source="amo", note_id=None, manager_id=mid, manager_name=name, phone="+998901112233",
        direction="Входящий", duration=95, created_at=TS, transcript="...", report="разбор",
        score=score, verdict=verdict, card_url="", uz_doc="", rec_link="", audio_path="",
        call_status=4,
    )


add("111", "Durdona", "ok", 9)
add("111", "Durdona", "ok", 8)
add("222", "Iroda", "fail", 3)
add("222", "Iroda", "noanswer", None)
add("333", "Medine", "ok", 7)
add("333", "Medine", "doubt", 5)

CHAT_BOSS, CHAT_ROP, CHAT_OP = 900001, 900002, 900003
assert auth.login(CHAT_BOSS, "boss", "p")
assert auth.login(CHAT_ROP, "ropy", "p")
assert auth.login(CHAT_OP, "durdona", "p")


class FakeMessage:
    def __init__(self, chat_id):
        self.chat = types.SimpleNamespace(id=chat_id)
        self.text = ""
        self.markup = None

    async def edit_text(self, text, reply_markup=None):
        self.text, self.markup = text, reply_markup


class FakeCB:
    """Минимальный CallbackQuery: только то, что использует бот."""

    def __init__(self, chat_id, data=""):
        self.message = FakeMessage(chat_id)
        self.data = data
        self.alerts = []

    async def answer(self, text=None, show_alert=False):
        if text:
            self.alerts.append(text)


def screen(chat_id, data, handler):
    cb = FakeCB(chat_id, data)
    asyncio.run(handler(cb))
    buttons = [b.callback_data for row in (cb.message.markup.inline_keyboard if cb.message.markup else []) for b in row]
    return cb.message.text, buttons, cb.alerts


# ---------- экран директора: сводка по 3 филиалам ----------
text, buttons, _ = screen(CHAT_BOSS, "stats", main.cb_stats)
assert "Юнусабад" in text and "Чиланзар" in text and "Самарканд" in text, text
assert "Лучше всех: Юнусабад" in text, text          # 8.5 против 6.0
assert "Слабее всех: Чиланзар" in text, text
assert f"br:{B_Y}" in buttons and f"br:{B_C}" in buttons and "statsall" in buttons, buttons
print("✓ директор: сводка по 3 филиалам")

# ---------- директор проваливается в филиал ----------
text, buttons, _ = screen(CHAT_BOSS, f"br:{B_Y}", main.cb_branch)
assert "Юнусабад" in text and "Durdona" in text and "Iroda" in text, text
assert "Medine" not in text, "в филиале не должно быть чужого оператора"
assert text.index("Durdona") < text.index("Iroda"), "рейтинг: сильный оператор выше"
assert "mgr:111:0" in buttons and "mgr:222:0" in buttons, buttons
print("✓ директор: разбивка по операторам филиала")

# ---------- экран РОПа: только его филиал ----------
text, buttons, _ = screen(CHAT_ROP, "stats", main.cb_stats)
assert "Юнусабад" in text and "Medine" not in text, text
assert "mgr:111:0" in buttons and "mgr:333:0" not in buttons, buttons
print("✓ РОП: только операторы своего филиала")

# РОП не может открыть чужой филиал
text, buttons, alerts = screen(CHAT_ROP, f"br:{B_C}", main.cb_branch)
assert alerts and "нет доступа" in alerts[0].lower(), alerts
print("✓ РОП: чужой филиал закрыт")

# ---------- экран оператора: только своё ----------
text, buttons, _ = screen(CHAT_OP, "stats", main.cb_stats)
assert "Durdona" in text and "Iroda" not in text and "Medine" not in text, text
assert "mycalls" in buttons and "errs:all" in buttons, buttons
print("✓ оператор: только своя статистика")

# оператор не может открыть карточку коллеги
_, _, alerts = screen(CHAT_OP, "mgr:222:0", main.cb_manager)
assert alerts and "нет доступа" in alerts[0].lower(), alerts
print("✓ оператор: чужие звонки закрыты")

# ---------- ошибки: где именно ошиблись ----------
text, buttons, _ = screen(CHAT_ROP, "errs:all", main.cb_errors)
assert "Iroda" in text or any(b.startswith("call:") for b in buttons), (text, buttons)
assert len([b for b in buttons if b.startswith("call:")]) == 1, "у филиала одна ошибка (❌ Iroda)"
print("✓ РОП: экран ошибок филиала")

text, buttons, _ = screen(CHAT_OP, "errs:all", main.cb_errors)
assert "Звонков с ошибками не найдено" in text, text
print("✓ оператор: своих ошибок нет — так и написано")

text, buttons, _ = screen(CHAT_BOSS, "errs:all", main.cb_errors)
assert len([b for b in buttons if b.startswith("call:")]) == 2, "директор видит ошибки всех филиалов"
print("✓ директор: ошибки по всему отделу")

# ошибки филиала с кнопки «Ошибки филиала» (errs:b<id>)
text, buttons, _ = screen(CHAT_BOSS, f"errs:b{B_C}", main.cb_errors)
assert len([b for b in buttons if b.startswith("call:")]) == 1, "у Чиланзара одна ошибка (❓ Medine)"
_, _, alerts = screen(CHAT_ROP, f"errs:b{B_C}", main.cb_errors)
assert alerts and "нет доступа" in alerts[0].lower(), "РОП не смотрит ошибки чужого филиала"
print("✓ ошибки филиала: доступ по роли")

# ---------- «Итого по отделу» и «Мои звонки» ----------
text, buttons, _ = screen(CHAT_BOSS, "statsall", main.cb_stats_all)
assert "Durdona" in text and "Medine" in text, "директору — все операторы"
text, buttons, _ = screen(CHAT_ROP, "statsall", main.cb_stats_all)
assert "Durdona" in text and "Medine" not in text, "РОПу — только его филиал"
print("✓ итог по отделу: сам ограничивается ролью")

text, buttons, _ = screen(CHAT_OP, "mycalls", main.cb_my_calls)
assert "Durdona" in text and "errs:111" in buttons, (text, buttons)
assert len([b for b in buttons if b.startswith("call:")]) == 2, "оператор видит 2 своих звонка"
print("✓ оператор: свои звонки с оценкой")

# ---------- меню под роль ----------
for chat_id, must in ((CHAT_BOSS, "statsall"), (CHAT_ROP, "errs:all"), (CHAT_OP, "mycalls")):
    user = main.viewer(chat_id)
    kb = [b.callback_data for row in main.main_menu_kb(user).inline_keyboard for b in row]
    assert must in kb, (chat_id, kb)
assert "Оператор" in main.menu_screen_text(main.viewer(CHAT_OP))
assert "Юнусабад" in main.menu_screen_text(main.viewer(CHAT_ROP))
print("✓ меню и подпись роли — под каждого")

# ---------- охват дневного отчёта ----------
ids_boss, title_boss = main.daily_scope(main.viewer(CHAT_BOSS))
ids_rop, title_rop = main.daily_scope(main.viewer(CHAT_ROP))
ids_op, title_op = main.daily_scope(main.viewer(CHAT_OP))
assert ids_boss is None and "весь отдел" in title_boss
assert set(ids_rop) == {"111", "222"} and "Юнусабад" in title_rop
assert ids_op == ["111"] and "Durdona" in title_op
print("✓ дневной отчёт: охват по роли")

print("\nSCREENS SELF-TEST: ALL PASSED")
