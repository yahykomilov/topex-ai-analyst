"""Изолированный самотест auth.py — на in-memory БД, прод calls.db не трогаем."""
import sqlite3
import threading

import auth

# подменяем соединение на in-memory ДО работы с данными
mem = sqlite3.connect(":memory:")
mem.row_factory = sqlite3.Row
auth._conn = mem
auth._lock = threading.Lock()
auth.ensure_tables()

# --- филиалы ---
b1 = auth.create_branch("Юнусабад")
b2 = auth.create_branch("Чиланзар")
auth.create_branch("Самарканд")
assert len(auth.list_branches()) == 3, "должно быть 3 филиала"
assert auth.create_branch("Юнусабад") == b1, "дубль филиала не создаёт новый"

# --- пользователи ---
auth.create_user("boss", "pass1", auth.DIRECTOR, "Директор")
auth.create_user("rop1", "pass2", auth.ROP, "РОП Юнусабад", branch_id=b1)
auth.create_user("op1", "pass3", auth.OPERATOR, "Durdona", branch_id=b1, operator_amo_id="111")
auth.create_user("op2", "pass4", auth.OPERATOR, "Iroda", branch_id=b1, operator_amo_id="222")
auth.create_user("op3", "pass5", auth.OPERATOR, "Sarvinoz", branch_id=b2, operator_amo_id="333")

# --- аутентификация ---
assert auth.authenticate("boss", "wrong") is None, "неверный пароль -> None"
assert auth.authenticate("boss", "pass1") is not None, "верный пароль -> user"
assert auth.authenticate("BOSS", "pass1") is not None, "логин без учёта регистра"

# --- вход/выход (привязка Telegram) ---
u = auth.login(1001, "rop1", "pass2")
assert u is not None and u["role"] == auth.ROP
assert auth.current_user(1001)["login"] == "rop1", "current_user видит вошедшего"
assert auth.logout(1001) is True
assert auth.current_user(1001) is None, "после выхода сессии нет"
# один Telegram — одна активная учётка
auth.login(1002, "op1", "pass3")
auth.login(1002, "op2", "pass4")
assert auth.current_user(1002)["login"] == "op2", "повторный вход переключает учётку"

# --- видимость по ролям ---
director = auth.get_user_by_login("boss")
rop = auth.get_user_by_login("rop1")
op1 = auth.get_user_by_login("op1")
assert auth.visible_manager_ids(director) is None, "директор видит всех"
assert set(auth.visible_manager_ids(rop)) == {"111", "222"}, "РОП — свой филиал"
assert auth.visible_manager_ids(op1) == ["111"], "оператор — только себя"
assert auth.can_see_manager(rop, "111") is True
assert auth.can_see_manager(rop, "333") is False, "РОП не видит чужой филиал"
assert auth.can_see_manager(op1, "222") is False, "оператор не видит коллегу"
assert auth.can_see_manager(director, "999") is True
assert auth.visible_manager_ids(None) == [], "нет сессии — никого"

print("AUTH SELF-TEST: ALL PASSED ✅")
