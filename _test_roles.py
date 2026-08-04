"""Проверка вшивания ролей: импорт main, тексты в 2 языках, форматирование,
видимость по ролям, db.stats_for_ids. Прод-БД не портим (auth — in-memory)."""

import sqlite3
import threading

import main  # noqa: F401 — импорт валидирует весь main.py (регистрация хендлеров и т.п.)
import i18n
import db
import auth

# 1. Новые ключи есть в ОБОИХ языках
NEW_KEYS = [
    "need_login", "login_usage", "login_ok", "login_fail", "logout_ok", "access_denied",
    "whoami", "whoami_owner", "whoami_none",
    "role_operator", "role_rop", "role_director", "role_owner",
    "owner_only", "addbranch_usage", "branch_added", "branches_title", "branches_empty",
    "adduser_usage", "adduser_bad_role", "user_added", "user_exists",
    "users_title", "users_empty", "daily_denied", "stats_by_branch", "stats_branch_line",
]
for lang in ("ru", "uz"):
    miss = [k for k in NEW_KEYS if k not in i18n.TEXTS[lang]]
    assert not miss, f"{lang}: нет ключей {miss}"

# 2. Форматирование новых строк с РЕАЛЬНЫМИ kwargs (как в main.py), в обоих языках
for lang in ("ru", "uz"):
    i18n.set_lang(lang)
    i18n.t("login_ok", role="оператор")
    i18n.t("branch_added", name="Юнусабад", id=1)
    i18n.t("user_added", login="durdona", role="оператор", extra=" • филиал 1 • amo 111")
    i18n.t("user_exists", login="durdona")
    i18n.t("whoami", name="Durdona", role="оператор")
    i18n.t("stats_branch_line", name="Юнусабад", total=10, answered=7, noanswer=3,
           ok=50, fail=30, doubt=20, avg=", ср. балл 5.5/10")
    i18n.t("adduser_usage"); i18n.t("need_login"); i18n.t("access_denied")
i18n.set_lang("ru")

# 3. db.stats_for_ids — форма ответа
empty = db.stats_for_ids([])
assert empty["total"] == 0 and empty["avg_score"] is None
assert set(empty["counts"]) == {"ok", "fail", "doubt", "noanswer"}
some = db.stats_for_ids(["manual", "999999"])
assert set(some.keys()) == {"total", "answered", "counts", "percent", "avg_score"}

# 4. Видимость по ролям (in-memory, прод не трогаем)
mem = sqlite3.connect(":memory:"); mem.row_factory = sqlite3.Row
auth._conn = mem; auth._lock = threading.Lock(); auth.ensure_tables()
b1 = auth.create_branch("Ф1"); b2 = auth.create_branch("Ф2")
auth.create_user("boss", "p", auth.DIRECTOR, "Директор")
auth.create_user("rop1", "p", auth.ROP, "РОП1", branch_id=b1)
auth.create_user("op1", "p", auth.OPERATOR, "Опер1", branch_id=b1, operator_amo_id="111")
auth.create_user("op2", "p", auth.OPERATOR, "Опер2", branch_id=b2, operator_amo_id="222")

assert auth.visible_manager_ids(auth.get_user_by_login("boss")) is None
assert auth.visible_manager_ids(auth.get_user_by_login("rop1")) == ["111"]
assert auth.visible_manager_ids(auth.get_user_by_login("op1")) == ["111"]
assert auth.branch_operator_ids(b2) == ["222"]
assert auth.can_see_manager(auth.get_user_by_login("rop1"), "222") is False

# owner-view (как main._OWNER_VIEW) — видит всех
OWNER_VIEW = {"role": auth.OWNER, "branch_id": None, "operator_amo_id": None}
assert auth.visible_manager_ids(OWNER_VIEW) is None
assert auth.can_see_manager(OWNER_VIEW, "любой") is True

# role_label из main работает для всех ролей
for r in (auth.OPERATOR, auth.ROP, auth.DIRECTOR, auth.OWNER):
    assert main.role_label(r)

print("ROLES TEST: ALL PASSED ✅")
