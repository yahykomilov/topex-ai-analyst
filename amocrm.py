"""Опрос AmoCRM: ищем новые звонки (примечания call_in / call_out) и записи разговоров."""

import logging
from pathlib import Path

import httpx

from config import AMO_ACCESS_TOKEN, AMO_SUBDOMAIN, TMP_DIR

log = logging.getLogger("amocrm")

BASE_URL = f"https://{AMO_SUBDOMAIN}.amocrm.ru"
HEADERS = {"Authorization": f"Bearer {AMO_ACCESS_TOKEN}"}

NOTE_TYPES = ("call_in", "call_out")
ENTITIES = ("leads", "contacts")


async def fetch_recent_calls(limit: int = 50) -> list[dict]:
    """Возвращает последние примечания-звонки по сделкам и контактам."""
    calls: list[dict] = []
    async with httpx.AsyncClient(timeout=60, headers=HEADERS) as client:
        for entity in ENTITIES:
            params = {
                "filter[note_type][0]": NOTE_TYPES[0],
                "filter[note_type][1]": NOTE_TYPES[1],
                "order[updated_at]": "desc",
                "limit": limit,
            }
            r = await client.get(f"{BASE_URL}/api/v4/{entity}/notes", params=params)
            if r.status_code == 204:
                continue
            r.raise_for_status()
            data = r.json()
            for note in data.get("_embedded", {}).get("notes", []):
                p = note.get("params") or {}
                calls.append(
                    {
                        "note_id": note["id"],
                        "entity": entity,
                        "entity_id": note.get("entity_id"),
                        "note_type": note.get("note_type"),
                        "duration": int(p.get("duration") or 0),
                        "phone": p.get("phone") or "",
                        "link": p.get("link") or "",
                        "call_status": p.get("call_status"),
                        "created_at": note.get("created_at"),
                        "created_by": note.get("created_by"),
                    }
                )
    return calls


async def download_recording(call: dict, dest_dir: Path | None = None) -> Path:
    """Скачивает запись звонка по ссылке из примечания."""
    url = call["link"]
    if not url:
        raise ValueError("У звонка нет ссылки на запись")
    if url.startswith("/"):
        url = BASE_URL + url

    dest = (dest_dir or TMP_DIR) / f"amo_call_{call['note_id']}.mp3"
    async with httpx.AsyncClient(
        timeout=300, follow_redirects=True, headers=HEADERS
    ) as client:
        r = await client.get(url)
        r.raise_for_status()
        content_type = r.headers.get("content-type", "")
        if "text/html" in content_type and b"<html" in r.content[:500].lower():
            raise ValueError(
                f"Ссылка на запись вернула страницу, а не аудио: {url}"
            )
        # подберём расширение по content-type
        ext = ".mp3"
        if "wav" in content_type:
            ext = ".wav"
        elif "ogg" in content_type:
            ext = ".ogg"
        elif "mp4" in content_type or "m4a" in content_type:
            ext = ".m4a"
        dest = dest.with_suffix(ext)
        dest.write_bytes(r.content)
    return dest


def entity_url(call: dict) -> str:
    """Ссылка на карточку сделки/контакта в AmoCRM."""
    path = "leads/detail" if call["entity"] == "leads" else "contacts/detail"
    return f"{BASE_URL}/{path}/{call['entity_id']}"


_users_cache: dict[int, str] = {}


async def get_users(force: bool = False) -> dict[int, str]:
    """Сотрудники AmoCRM: id -> имя (кэшируется)."""
    global _users_cache
    if _users_cache and not force:
        return _users_cache
    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
        r = await client.get(f"{BASE_URL}/api/v4/users", params={"limit": 250})
        r.raise_for_status()
        users = r.json().get("_embedded", {}).get("users", [])
    _users_cache = {u["id"]: u.get("name") or f"Сотрудник {u['id']}" for u in users}
    return _users_cache


async def check_connection() -> str:
    """Проверка токена: возвращает название аккаунта."""
    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
        r = await client.get(f"{BASE_URL}/api/v4/account")
        r.raise_for_status()
        return r.json().get("name", AMO_SUBDOMAIN)
