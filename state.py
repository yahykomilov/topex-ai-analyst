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


# ================== ПОДКЛЮЧЕНИЕ AMOCRM (владелец вводит ключи в боте) ==================

def get_amo() -> dict | None:
    """Ключи amoCRM, введённые владельцем. None, пока не подключён."""
    a = _state.get("amo") or {}
    if a.get("host") and a.get("token"):
        return a
    return None


def set_amo(host: str, token: str, secret: str = "", integration_id: str = "") -> None:
    """Сохраняет ключи и сбрасывает слежение — чтобы новый аккаунт не вывалил всю историю."""
    with _lock:
        _state["amo"] = {
            "host": host,
            "token": token,
            "secret": secret,
            "integration_id": integration_id,
        }
        _state["amo_initialized"] = False
        _state["processed_notes"] = []
        _save()


def clear_amo() -> None:
    with _lock:
        _state.pop("amo", None)
        _save()


def get_setup() -> dict | None:
    """Незавершённый ввод ключей владельцем (шаг + уже введённые значения)."""
    return _state.get("amo_setup")


def set_setup(data: dict | None) -> None:
    with _lock:
        if data is None:
            _state.pop("amo_setup", None)
        else:
            _state["amo_setup"] = data
        _save()


# ================== ЯЗЫК ИНТЕРФЕЙСА (владелец переключает) ==================

def get_lang() -> str:
    """Язык бота: 'ru' | 'uz'. По умолчанию русский (как было исторически)."""
    lang = _state.get("lang", "ru")
    return lang if lang in ("ru", "uz") else "ru"


def set_lang(lang: str) -> None:
    with _lock:
        _state["lang"] = lang if lang in ("ru", "uz") else "ru"
        _save()


# ================== РЕЖИМ ПОИСКА СОТРУДНИКА ==================

def is_awaiting_search() -> bool:
    """True, если владелец нажал «Поиск» и следующий текст — это имя для поиска."""
    return bool(_state.get("awaiting_search"))


def set_awaiting_search(flag: bool) -> None:
    with _lock:
        _state["awaiting_search"] = bool(flag)
        _save()
