"""Самотест статистики по ролям (дорожка C) — на in-memory БД, прод calls.db не трогаем.

Проверяет: экран директора (сводка по филиалам), экран РОПа (операторы филиала),
экран оператора (только свои звонки), ошибки (❌/❓) и охват дневного отчёта.
Запуск: python _test_roles.py
"""
import sqlite3
import threading
import time

import auth
import db

# --- подменяем обе базы на одну in-memory (схему берём из уже созданной прод-базы) ---
mem = sqlite3.connect(":memory:")
mem.row_factory = sqlite3.Row
for (ddl,) in db._conn.execute(
    "SELECT sql FROM sqlite_master WHERE type='table' AND name='calls'"
).fetchall():
    mem.execute(ddl)

db._conn, db._lock = mem, threading.Lock()
auth._conn, auth._lock = mem, threading.Lock()
auth.ensure_tables()

# --- филиалы и люди ---
b_yunus = auth.create_branch("Юнусабад")
b_chilan = auth.create_branch("Чиланзар")
b_samar = auth.create_branch("Самарканд")

auth.create_user("boss", "p", auth.DIRECTOR, "Директор")
auth.create_user("rop_y", "p", auth.ROP, "РОП Юнусабада", branch_id=b_yunus)
auth.create_user("rop_c", "p", auth.ROP, "РОП Чиланзара", branch_id=b_chilan)
auth.create_user("durdona", "p", auth.OPERATOR, "Durdona", branch_id=b_yunus, operator_amo_id="111")
auth.create_user("iroda", "p", auth.OPERATOR, "Iroda", branch_id=b_yunus, operator_amo_id="222")
auth.create_user("medine", "p", auth.OPERATOR, "Medine", branch_id=b_chilan, operator_amo_id="333")
auth.create_user("nobody", "p", auth.OPERATOR, "Без филиала", operator_amo_id="999")

NOW = int(time.time())
TODAY = NOW - 60  # сегодня, минуту назад


def add(manager_id, name, verdict, score, ts=NOW, phone="+998900000000"):
    db.save_call(
        source="amo", note_id=None, manager_id=manager_id, manager_name=name,
        phone=phone, direction="Входящий", duration=90, created_at=ts,
        transcript="...", report="разбор", score=score, verdict=verdict,
        card_url="", uz_doc="", rec_link="", audio_path="", call_status=4,
    )


# Юнусабад: Durdona сильная, Iroda слабая + недозвон
add("111", "Durdona", "ok", 9, TODAY)
add("111", "Durdona", "ok", 8, TODAY)
add("222", "Iroda", "fail", 3, TODAY)
add("222", "Iroda", "doubt", 5, TODAY)
add("222", "Iroda", "noanswer", None, TODAY)
# Чиланзар: Medine средняя
add("333", "Medine", "ok", 7, TODAY)
add("333", "Medine", "fail", 4, TODAY)
# оператор без филиала — не должен попадать ни в один филиал
add("999", "Без филиала", "ok", 10, TODAY)

# --- экран директора: сводка по филиалам ---
summary = auth.branches_with_operators()
assert len(summary) == 3, "директор видит все 3 филиала"
by_name = {name: ids for _, name, ids in summary}
assert set(by_name["Юнусабад"]) == {"111", "222"}
assert set(by_name["Чиланзар"]) == {"333"}
assert by_name["Самарканд"] == [], "филиал без операторов — пустой, но в сводке есть"

s_yunus = db.stats_for_ids(by_name["Юнусабад"])
assert s_yunus["total"] == 5 and s_yunus["answered"] == 4, s_yunus
assert s_yunus["counts"]["noanswer"] == 1, "недозвон отдельно от провала"
assert s_yunus["percent"]["ok"] == 50, "проценты — от отвеченных"
assert s_yunus["avg_score"] == 6.2, s_yunus["avg_score"]  # (9+8+3+5)/4

s_chilan = db.stats_for_ids(by_name["Чиланзар"])
assert s_chilan["total"] == 2 and s_chilan["avg_score"] == 5.5
s_samar = db.stats_for_ids(by_name["Самарканд"])
assert s_samar["total"] == 0 and s_samar["avg_score"] is None, "пустой филиал не падает"

ranked = sorted(
    [(db.stats_for_ids(ids)["avg_score"], name) for _, name, ids in summary
     if db.stats_for_ids(ids)["avg_score"] is not None],
    key=lambda x: -x[0],
)
assert ranked[0][1] == "Юнусабад" and ranked[-1][1] == "Чиланзар", ranked

# оператор без филиала виден директору как «неприкреплённый»
assert "999" not in auth.assigned_operator_ids()
assert "111" in auth.assigned_operator_ids()

# --- экран РОПа: только свой филиал ---
rop_y = auth.get_user_by_login("rop_y")
rop_c = auth.get_user_by_login("rop_c")
ids_y = auth.visible_manager_ids(rop_y)
assert set(ids_y) == {"111", "222"}, ids_y
assert db.stats_for_ids(ids_y)["total"] == 5
assert {r["manager_id"] for r in db.managers_scoped(ids_y)} == {"111", "222"}, "чужих в списке нет"
assert auth.can_see_manager(rop_y, "333") is False, "РОП не видит чужой филиал"
assert auth.can_see_manager(rop_c, "333") is True
# рейтинг операторов филиала: Durdona выше Iroda
rating = sorted(
    [(db.stats_for(m)["avg_score"], m) for m in ids_y], key=lambda x: -(x[0] or -1)
)
assert rating[0][1] == "111" and rating[-1][1] == "222", rating

# --- экран оператора: только свои звонки ---
durdona = auth.get_user_by_login("durdona")
ids_d = auth.visible_manager_ids(durdona)
assert ids_d == ["111"]
s_d = db.stats_for_ids(ids_d)
assert s_d["total"] == 2 and s_d["avg_score"] == 8.5, s_d
assert auth.can_see_manager(durdona, "222") is False, "оператор не видит коллегу"
assert {r["manager_id"] for r in db.managers_scoped(ids_d)} == {"111"}

# оператор без привязки к amoCRM не видит ничего (а не «всё»)
unbound = auth.get_user_by_login("nobody")
auth.bind_operator(unbound["id"], None)
unbound = auth.get_user_by_login("nobody")
assert auth.visible_manager_ids(unbound) == []
assert db.stats_for_ids([])["total"] == 0, "пустой доступ = пустая статистика, не вся база"

# --- ошибки (где ошибся) ---
errs_y = db.problem_calls(ids_y, limit=10)
assert len(errs_y) == 2, errs_y
assert {e["verdict"] for e in errs_y} == {"fail", "doubt"}, "только ❌ и ❓"
assert all(e["manager_id"] in ("111", "222") for e in errs_y)
assert db.problem_calls(["111"]) == [], "у Durdona ошибок нет"
assert len(db.problem_calls(None)) == 3, "директор видит все ошибки (вкл. неприкреплённых)"

# --- дневной отчёт: охват по роли ---
day_start = TODAY - 3600
day_end = TODAY + 3600
assert len(db.calls_between_ids(day_start, day_end, None)) == 8, "директор — весь отдел"
assert len(db.calls_between_ids(day_start, day_end, ids_y)) == 5, "РОП — свой филиал"
assert len(db.calls_between_ids(day_start, day_end, ids_d)) == 2, "оператор — только свои"
assert db.calls_between_ids(day_start, day_end, []) == [], "нет доступа — пустой отчёт"

print("ROLES SELF-TEST: ALL PASSED")
