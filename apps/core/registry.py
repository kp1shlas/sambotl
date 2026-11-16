"""Registry of per-tournament SQLite files ("file per tournament" storage).

Layout::

    data/
      tournaments.json            <- catalogue of all tournaments
      active_tournament.json      <- which file the server currently serves
      tournaments/
        <slug>.sqlite3            <- one database per tournament

Keeping a separate database per tournament makes an event self-contained and
easy to archive: copy a single ``.sqlite3`` file and the whole tournament
moves with it.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings

_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "",
    "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def slugify(name: str) -> str:
    """Turn a human tournament name into a filesystem-safe slug."""
    parts = []
    for char in (name or "").lower():
        if char in _TRANSLIT:
            parts.append(_TRANSLIT[char])
        elif char.isascii() and char.isalnum():
            parts.append(char)
        else:
            parts.append("-")
    slug = re.sub(r"-+", "-", "".join(parts)).strip("-")
    return slug or "tournament"


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def index_file() -> Path:
    return Path(settings.TOURNAMENTS_INDEX_FILE)


def active_file() -> Path:
    return Path(settings.ACTIVE_TOURNAMENT_FILE)


def tournaments_dir() -> Path:
    return Path(settings.TOURNAMENTS_DIR)


def load_index() -> list[dict]:
    """Return the list of registered tournaments."""
    data = _read_json(index_file(), [])
    return data if isinstance(data, list) else []


def save_index(entries: list[dict]) -> None:
    _write_json(index_file(), entries)


def get_entry(slug: str) -> dict | None:
    for entry in load_index():
        if entry.get("slug") == slug:
            return entry
    return None


def db_path(filename: str) -> Path:
    return Path(settings.TOURNAMENTS_DIR) / filename


def _unique_slug(base: str, taken: set[str]) -> str:
    if base not in taken:
        return base
    counter = 2
    while f"{base}-{counter}" in taken:
        counter += 1
    return f"{base}-{counter}"


def create_entry(
    name: str,
    *,
    system: str,
    audience: str,
    mats: int = 4,
    password_hash: str = "",
    slug: str | None = None,
) -> dict:
    """Register a new tournament and return its registry entry."""
    entries = load_index()
    taken = {entry.get("slug") for entry in entries}

    if slug:
        slug = slugify(slug)
        if slug in taken:
            raise ValueError(f"Турнир с кодом «{slug}» уже существует")
    else:
        slug = _unique_slug(slugify(name), taken)

    entry = {
        "slug": slug,
        "name": name,
        "db": f"{slug}.sqlite3",
        "system": system,
        "audience": audience,
        "mats": mats,
        "password_hash": password_hash,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    entries.append(entry)
    save_index(entries)
    return entry


def set_active(slug: str) -> dict:
    """Mark ``slug`` as the working tournament (used on next server start)."""
    entry = get_entry(slug)
    if entry is None:
        raise ValueError(f"Турнир «{slug}» не найден в реестре")
    _write_json(
        active_file(),
        {
            "slug": entry["slug"],
            "name": entry["name"],
            "db": entry["db"],
            "activated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
    )
    return entry


def get_active() -> dict | None:
    return _read_json(active_file(), None)


def delete_entry(slug: str, *, remove_file: bool = False) -> None:
    entries = [entry for entry in load_index() if entry.get("slug") != slug]
    save_index(entries)
    if remove_file:
        target = get_entry(slug)
        if target:
            path = db_path(target["db"])
            for suffix in ("", "-wal", "-shm"):
                candidate = Path(str(path) + suffix)
                if candidate.exists():
                    candidate.unlink()
