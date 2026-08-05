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
