"""
Topex AI Analyst — авторизация и роли (внутренняя иерархия Topex).

Роли и уровни доступа:
  - operator  — оператор колл-центра: видит ТОЛЬКО свои звонки/оценки.
  - rop       — руководитель отдела продаж: видит всех операторов своего филиала.
  - director  — директор: видит сводку по всем филиалам.
  - owner     — владелец системы: заводит филиалы и пользователей (настройка).

Логин/пароль лежат в той же SQLite (data/calls.db). Пароль — pbkdf2-хэш (соль на
пользователя, не хранится в открытом виде). Привязка к Telegram: при успешном
/login записываем tg_id пользователя; current_user(tg_id) отдаёт вошедшего;
/logout снимает привязку.
"""

import hashlib
import hmac
import secrets
import time

import db  # переиспользуем то же соединение SQLite (data/calls.db)

# --- роли ---
OPERATOR = "operator"
ROP = "rop"
DIRECTOR = "director"
OWNER = "owner"
ROLES = (OPERATOR, ROP, DIRECTOR, OWNER)

_PBKDF2_ROUNDS = 200_000

# соединение/локк берём из db (одна база на весь проект).
# В тестах их можно подменить на in-memory до вызова ensure_tables().
_conn = db._conn
_lock = db._lock


def ensure_tables() -> None:
    """Создаёт таблицы branches / app_users, если их ещё нет."""
    _conn.execute(
        """
        CREATE TABLE IF NOT EXISTS branches (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
        """
    )
    _conn.execute(
        """
        CREATE TABLE IF NOT EXISTS app_users (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            login           TEXT NOT NULL UNIQUE,
            pass_salt       TEXT NOT NULL,
            pass_hash       TEXT NOT NULL,
            role            TEXT NOT NULL,
            full_name       TEXT DEFAULT '',
            branch_id       INTEGER,        -- филиал (для operator/rop)
            operator_amo_id TEXT,           -- calls.manager_id этого оператора (для operator)
            tg_id           INTEGER,        -- привязанный Telegram chat_id (сессия)
            active          INTEGER DEFAULT 1,
            created_at      INTEGER DEFAULT 0
        )
        """
    )
    _conn.commit()


ensure_tables()


# --------------------------------------------------------------------------
# Пароли
# --------------------------------------------------------------------------
def _hash(password: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), _PBKDF2_ROUNDS
    ).hex()


def _new_salt() -> str:
    return secrets.token_bytes(16).hex()


# --------------------------------------------------------------------------
# Филиалы
# --------------------------------------------------------------------------
def create_branch(name: str) -> int:
    name = name.strip()
    with _lock:
        _conn.execute("INSERT OR IGNORE INTO branches (name) VALUES (?)", (name,))
        _conn.commit()
    row = _conn.execute("SELECT id FROM branches WHERE name = ?", (name,)).fetchone()
    return row["id"]


def list_branches() -> list:
    return _conn.execute("SELECT id, name FROM branches ORDER BY name").fetchall()


def branch_name(branch_id) -> str:
    if branch_id is None:
        return ""
    row = _conn.execute("SELECT name FROM branches WHERE id = ?", (branch_id,)).fetchone()
    return row["name"] if row else ""


def branch_exists(branch_id) -> bool:
    return (
        _conn.execute("SELECT 1 FROM branches WHERE id = ?", (branch_id,)).fetchone()
        is not None
    )


# --------------------------------------------------------------------------
# Пользователи
# --------------------------------------------------------------------------
def create_user(
    login: str,
    password: str,
    role: str,
    full_name: str = "",
    branch_id=None,
    operator_amo_id=None,
) -> int:
    if role not in ROLES:
        raise ValueError(f"Неизвестная роль: {role}")
    salt = _new_salt()
    with _lock:
        cur = _conn.execute(
            """INSERT INTO app_users
               (login, pass_salt, pass_hash, role, full_name, branch_id,
                operator_amo_id, active, created_at)
               VALUES (?,?,?,?,?,?,?,1,?)""",
            (
                login.strip().lower(),
                salt,
                _hash(password, salt),
                role,
                full_name,
                branch_id,
                str(operator_amo_id) if operator_amo_id is not None else None,
                int(time.time()),
            ),
        )
        _conn.commit()
        return cur.lastrowid


def set_password(user_id: int, password: str) -> None:
    salt = _new_salt()
    with _lock:
        _conn.execute(
            "UPDATE app_users SET pass_salt=?, pass_hash=? WHERE id=?",
            (salt, _hash(password, salt), user_id),
        )
        _conn.commit()


def set_active(user_id: int, active: bool) -> None:
    with _lock:
        _conn.execute(
            "UPDATE app_users SET active=? WHERE id=?", (1 if active else 0, user_id)
        )
        _conn.commit()


def get_user_by_login(login: str):
    return _conn.execute(
        "SELECT * FROM app_users WHERE login=? AND active=1", (login.strip().lower(),)
    ).fetchone()


def find_login(login: str):
    """Учётка по логину, включая отключённые (чтобы отличить «выключен» от «пароль неверный»)."""
    return _conn.execute(
        "SELECT * FROM app_users WHERE login=?", (login.strip().lower(),)
    ).fetchone()


def set_branch(user_id: int, branch_id) -> None:
    with _lock:
        _conn.execute(
            "UPDATE app_users SET branch_id=? WHERE id=?", (branch_id, user_id)
        )
        _conn.commit()


def bind_operator(user_id: int, operator_amo_id) -> None:
    """Привязывает учётку оператора к его id в amoCRM (calls.manager_id)."""
    with _lock:
        _conn.execute(
            "UPDATE app_users SET operator_amo_id=? WHERE id=?",
            (str(operator_amo_id) if operator_amo_id is not None else None, user_id),
        )
        _conn.commit()


def list_users(role: str | None = None) -> list:
    if role:
        return _conn.execute(
            "SELECT * FROM app_users WHERE role=? ORDER BY full_name, login", (role,)
        ).fetchall()
    return _conn.execute(
        "SELECT * FROM app_users ORDER BY role, full_name, login"
    ).fetchall()


# --------------------------------------------------------------------------
# Сессии (привязка Telegram)
# --------------------------------------------------------------------------
def authenticate(login: str, password: str):
    u = get_user_by_login(login)
    if not u:
        return None
    if hmac.compare_digest(_hash(password, u["pass_salt"]), u["pass_hash"]):
        return u
    return None


def login(tg_id: int, login_name: str, password: str):
    """Проверяет логин/пароль и привязывает tg_id к учётке. None при неудаче."""
    u = authenticate(login_name, password)
    if not u:
        return None
    with _lock:
        # снимаем этот Telegram с других учёток, ставим на эту (одна сессия на tg)
        _conn.execute("UPDATE app_users SET tg_id=NULL WHERE tg_id=?", (tg_id,))
        _conn.execute("UPDATE app_users SET tg_id=? WHERE id=?", (tg_id, u["id"]))
        _conn.commit()
    return get_user_by_login(login_name)


def logout(tg_id: int) -> bool:
    with _lock:
        cur = _conn.execute("UPDATE app_users SET tg_id=NULL WHERE tg_id=?", (tg_id,))
        _conn.commit()
    return cur.rowcount > 0


def current_user(tg_id: int):
    """Вошедший пользователь по Telegram chat_id (или None)."""
    return _conn.execute(
        "SELECT * FROM app_users WHERE tg_id=? AND active=1", (tg_id,)
    ).fetchone()


# --------------------------------------------------------------------------
# Видимость по ролям — кого пользователь имеет право видеть
# --------------------------------------------------------------------------
def visible_manager_ids(user):
    """
    None  = «все операторы» (director/owner).
    список operator_amo_id (str) = кого именно видит (rop → свой филиал, operator → себя).
    []    = никого / не авторизован.
    """
    if user is None:
        return []
    role = user["role"]
    if role in (DIRECTOR, OWNER):
        return None
    if role == ROP:
        if user["branch_id"] is None:
            return []
        return branch_operator_ids(user["branch_id"])
    if role == OPERATOR:
        return [user["operator_amo_id"]] if user["operator_amo_id"] else []
    return []


def can_see_manager(user, manager_id) -> bool:
    vis = visible_manager_ids(user)
    if vis is None:
        return True
    return str(manager_id) in {str(x) for x in vis}


def branch_operator_ids(branch_id) -> list:
    rows = _conn.execute(
        "SELECT operator_amo_id FROM app_users "
        "WHERE role=? AND branch_id=? AND operator_amo_id IS NOT NULL",
        (OPERATOR, branch_id),
    ).fetchall()
    return [r["operator_amo_id"] for r in rows]


def has_any_users() -> bool:
    """Заведён ли хоть один пользователь (для онбординга владельца)."""
    return _conn.execute("SELECT 1 FROM app_users LIMIT 1").fetchone() is not None


# --------------------------------------------------------------------------
# Дефолтный посев (Topex Texnikum) — восстанавливает реальных пользователей,
# если БД пустая (без persistent disk на Render каждый деплой = чистая БД).
# --------------------------------------------------------------------------
_DEFAULT_BRANCH = "Основной филиал"
_DEFAULT_USERS = (
    # login, password, role, full_name, operator_amo_id
    ("bobur", "bobur5296", ROP, "Bobur Xolov", None),
    ("durdona", "durdona5707", OPERATOR, "Durdona", "11549990"),
    ("iroda", "iroda1127", OPERATOR, "Iroda", "11549998"),
    ("ruxshona", "ruxshona3964", OPERATOR, "Ruxshona", "12580670"),
    ("medine", "medine2523", OPERATOR, "Medine", "13711654"),
    ("sarvinoz", "sarvinoz8750", OPERATOR, "Sarvinoz", "13711662"),
    ("oybek", "oybek8905", DIRECTOR, "Oybek", None),
)


def seed_default_users() -> None:
    if has_any_users():
        return
    branch_id = create_branch(_DEFAULT_BRANCH)
    for login_name, password, role, full_name, operator_amo_id in _DEFAULT_USERS:
        create_user(
            login_name,
            password,
            role,
            full_name=full_name,
            branch_id=branch_id if role in (OPERATOR, ROP) else None,
            operator_amo_id=operator_amo_id,
        )


# --------------------------------------------------------------------------
# Филиалы ↔ операторы (для экранов директора и РОПа)
# --------------------------------------------------------------------------
def list_operators(branch_id=None) -> list:
    """Учётки операторов: всех или одного филиала."""
    if branch_id is None:
        return _conn.execute(
            "SELECT * FROM app_users WHERE role=? AND active=1 ORDER BY full_name, login",
            (OPERATOR,),
        ).fetchall()
    return _conn.execute(
        "SELECT * FROM app_users WHERE role=? AND branch_id=? AND active=1 "
        "ORDER BY full_name, login",
        (OPERATOR, branch_id),
    ).fetchall()


def branches_with_operators() -> list:
    """[(branch_id, name, [operator_amo_id, ...]), ...] — основа сводки директора."""
    out = []
    for b in list_branches():
        out.append((b["id"], b["name"], branch_operator_ids(b["id"])))
    return out


def branch_of_manager(manager_id):
    """(branch_id, branch_name) оператора по его amoCRM-id; (None, "") если не привязан."""
    row = _conn.execute(
        "SELECT branch_id FROM app_users WHERE role=? AND operator_amo_id=? LIMIT 1",
        (OPERATOR, str(manager_id)),
    ).fetchone()
    if not row or row["branch_id"] is None:
        return None, ""
    return row["branch_id"], branch_name(row["branch_id"])


def assigned_operator_ids() -> set:
    """Все amoCRM-id, уже привязанные к какому-нибудь филиалу."""
    rows = _conn.execute(
        "SELECT operator_amo_id FROM app_users "
        "WHERE role=? AND operator_amo_id IS NOT NULL AND branch_id IS NOT NULL",
        (OPERATOR,),
    ).fetchall()
    return {str(r["operator_amo_id"]) for r in rows}


def operator_name(manager_id) -> str:
    """ФИО оператора из учётки (если заведена) — иначе пусто."""
    row = _conn.execute(
        "SELECT full_name FROM app_users WHERE role=? AND operator_amo_id=? LIMIT 1",
        (OPERATOR, str(manager_id)),
    ).fetchone()
    return row["full_name"] if row else ""
