"""Хранилище обработанных звонков: SQLite (data/calls.db)."""

import sqlite3
import threading

from config import DATA_DIR

DB_PATH = DATA_DIR / "calls.db"

_lock = threading.Lock()
_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
_conn.row_factory = sqlite3.Row
_conn.execute(
    """
    CREATE TABLE IF NOT EXISTS calls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,            -- 'amo' | 'manual'
        note_id INTEGER,                 -- id примечания в AmoCRM
        manager_id TEXT NOT NULL,        -- id пользователя AmoCRM или 'manual'
        manager_name TEXT NOT NULL,
        phone TEXT DEFAULT '',
        direction TEXT DEFAULT '',       -- Входящий / Исходящий
        duration INTEGER DEFAULT 0,
        created_at INTEGER DEFAULT 0,    -- unix time звонка
        transcript TEXT DEFAULT '',
        report TEXT DEFAULT '',
        score INTEGER,                   -- оценка 0-10 из отчёта
        verdict TEXT DEFAULT 'doubt',    -- ok | fail | doubt
        call_status INTEGER,             -- amoCRM: 4=разговор, 6=недозвон...
        card_url TEXT DEFAULT ''
    )
    """
)
# миграции: новые колонки
for _col, _typ in (
    ("uz_doc", "TEXT"),
    ("rec_link", "TEXT"),
    ("audio_path", "TEXT"),
    ("call_status", "INTEGER"),
):
    try:
        _conn.execute(f"ALTER TABLE calls ADD COLUMN {_col} {_typ}")
    except sqlite3.OperationalError:
        pass
_conn.commit()

VERDICT_EMOJI = {"ok": "✅", "fail": "❌", "doubt": "❓"}
VERDICT_LABEL = {"ok": "Успешные", "fail": "Неуспешные", "doubt": "Под вопросом"}

# amoCRM call_status: 4=разговор состоялся, 5=пропущенный, 6=недозвон, 7=нет соединения
CALL_STATUS_LABELS = {
    1: "📞 Планируется",
    2: "📅 Запланирован",
    3: "🔄 Совершён",
    4: "✅ Разговор",
    5: "📳 Пропущен",
    6: "❌ Недозвон",
    7: "🚫 Нет соединения",
}
CALL_STATUS_SHORT = {
    1: "план",
    2: "запл.",
    3: "сов.",
    4: "разг.",
    5: "проп.",
    6: "недозв.",
    7: "нет соед.",
}


def save_call(**kw) -> int:
    fields = (
        "source", "note_id", "manager_id", "manager_name", "phone", "direction",
        "duration", "created_at", "transcript", "report", "score", "verdict", "card_url",
        "uz_doc", "rec_link", "audio_path", "call_status",
    )
    values = [kw.get(f) for f in fields]
    with _lock:
        cur = _conn.execute(
            f"INSERT INTO calls ({','.join(fields)}) VALUES ({','.join('?' * len(fields))})",
            values,
        )
        _conn.commit()
        return cur.lastrowid


def managers() -> list[sqlite3.Row]:
    return _conn.execute(
        """
        SELECT manager_id, manager_name, COUNT(*) AS cnt
        FROM calls GROUP BY manager_id
        ORDER BY cnt DESC
        """
    ).fetchall()


def calls_for(manager_id: str, offset: int = 0, limit: int = 8) -> list[sqlite3.Row]:
    return _conn.execute(
        """
        SELECT id, phone, direction, duration, created_at, score, verdict, call_status
        FROM calls WHERE manager_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT ? OFFSET ?
        """,
        (manager_id, limit, offset),
    ).fetchall()


def count_for(manager_id: str) -> int:
    return _conn.execute(
        "SELECT COUNT(*) FROM calls WHERE manager_id = ?", (manager_id,)
    ).fetchone()[0]


def set_uz_doc(call_id: int, uz_doc: str) -> None:
    with _lock:
        _conn.execute("UPDATE calls SET uz_doc = ? WHERE id = ?", (uz_doc, call_id))
        _conn.commit()


def find_by_note(note_id: int) -> sqlite3.Row | None:
    return _conn.execute(
        "SELECT * FROM calls WHERE note_id = ? LIMIT 1", (note_id,)
    ).fetchone()


def has_note(note_id: int) -> bool:
    return (
        _conn.execute(
            "SELECT 1 FROM calls WHERE note_id = ? LIMIT 1", (note_id,)
        ).fetchone()
        is not None
    )


def get_call(call_id: int) -> sqlite3.Row | None:
    return _conn.execute("SELECT * FROM calls WHERE id = ?", (call_id,)).fetchone()


def dates_for(manager_id: str) -> list[tuple[str, int]]:
    """Даты (ГГГГММДД, локальное время), в которые у сотрудника были звонки."""
    rows = _conn.execute(
        """
        SELECT strftime('%Y%m%d', datetime(created_at, 'unixepoch', 'localtime')) AS d,
               COUNT(*) AS cnt
        FROM calls WHERE manager_id = ? AND created_at > 0
        GROUP BY d ORDER BY d DESC
        """,
        (manager_id,),
    ).fetchall()
    return [(r["d"], r["cnt"]) for r in rows]


def calls_for_day(manager_id: str, start_ts: int, end_ts: int) -> list[sqlite3.Row]:
    return _conn.execute(
        """
        SELECT id, phone, direction, duration, created_at, score, verdict, call_status
        FROM calls
        WHERE manager_id = ? AND created_at >= ? AND created_at < ?
        ORDER BY created_at DESC
        """,
        (manager_id, start_ts, end_ts),
    ).fetchall()


def calls_between(start_ts: int, end_ts: int) -> list[sqlite3.Row]:
    return _conn.execute(
        """
        SELECT * FROM calls
        WHERE created_at >= ? AND created_at < ?
        ORDER BY manager_name, created_at
        """,
        (start_ts, end_ts),
    ).fetchall()


def stats_for(manager_id: str | None = None) -> dict:
    where, params = ("WHERE manager_id = ?", (manager_id,)) if manager_id else ("", ())
    rows = _conn.execute(
        f"SELECT verdict, COUNT(*) AS cnt FROM calls {where} GROUP BY verdict", params
    ).fetchall()
    counts = {"ok": 0, "fail": 0, "doubt": 0}
    for r in rows:
        counts[r["verdict"]] = r["cnt"]
    total = sum(counts.values())
    avg = _conn.execute(
        f"SELECT AVG(score) FROM calls {where}"
        + (" AND" if where else " WHERE")
        + " score IS NOT NULL",
        params,
    ).fetchone()[0]
    return {
        "total": total,
        "counts": counts,
        "percent": {
            k: (round(v * 100 / total) if total else 0) for k, v in counts.items()
        },
        "avg_score": round(avg, 1) if avg is not None else None,
    }


def format_stats(stats: dict) -> str:
    c, p = stats["counts"], stats["percent"]
    lines = [
        f"📞 Всего звонков: {stats['total']}",
        f"✅ Успешные: {c['ok']} ({p['ok']}%)",
        f"❌ Неуспешные: {c['fail']} ({p['fail']}%)",
        f"❓ Под вопросом: {c['doubt']} ({p['doubt']}%)",
    ]
    if stats["avg_score"] is not None:
        lines.append(f"⭐ Средний балл: {stats['avg_score']}/10")
    return "\n".join(lines)
