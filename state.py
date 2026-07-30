import json
import threading

from config import STATE_FILE

_lock = threading.Lock()


def _load() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"owner_chat_id": None, "processed_notes": [], "amo_initialized": False}


_state = _load()


def _save() -> None:
    STATE_FILE.write_text(
        json.dumps(_state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def get_owner() -> int | None:
    return _state.get("owner_chat_id")


def set_owner(chat_id: int) -> None:
    with _lock:
        _state["owner_chat_id"] = chat_id
        _save()


def is_processed(note_id: int) -> bool:
    return note_id in _state.get("processed_notes", [])


def mark_processed(note_id: int) -> None:
    with _lock:
        notes = _state.setdefault("processed_notes", [])
        if note_id not in notes:
            notes.append(note_id)
            # держим только последние 10000 id, чтобы файл не разрастался
            if len(notes) > 10000:
                del notes[: len(notes) - 10000]
        _save()


def get_last_daily() -> str | None:
    return _state.get("last_daily_report")


def set_last_daily(day: str) -> None:
    with _lock:
        _state["last_daily_report"] = day
        _save()


def amo_initialized() -> bool:
    return bool(_state.get("amo_initialized"))


def set_amo_initialized() -> None:
    with _lock:
        _state["amo_initialized"] = True
        _save()
