import json
import os
import shutil
import uuid
from datetime import datetime as dt
from pathlib import Path
from typing import Optional, Dict, List

_STREAM_CACHE_DIR = None


def _get_shared_repo_dir():
    return Path(__file__).resolve().parent / "mongo"


def _get_cache_dir(cache_dir=None):
    global _STREAM_CACHE_DIR

    if cache_dir:
        _STREAM_CACHE_DIR = str(Path(cache_dir).expanduser())
        return _STREAM_CACHE_DIR

    if _STREAM_CACHE_DIR:
        return _STREAM_CACHE_DIR

    env_dir = os.environ.get("STREAM_CACHE_DIR")
    if env_dir:
        _STREAM_CACHE_DIR = str(Path(env_dir).expanduser())
        return _STREAM_CACHE_DIR

    base_dir = Path(__file__).resolve().parent / "stream_cache"
    base_dir.mkdir(parents=True, exist_ok=True)
    _STREAM_CACHE_DIR = str(base_dir)
    return _STREAM_CACHE_DIR


def _get_base_url(base_url=None):
    if base_url:
        return base_url.rstrip("/")

    env_url = (
        os.environ.get("PUBLIC_BASE_URL")
        or os.environ.get("APP_URL")
        or os.environ.get("RENDER_EXTERNAL_URL")
        or os.environ.get("BASE_URL")
        or ""
    ).strip()

    if env_url:
        return env_url.rstrip("/")

    return "http://127.0.0.1:5000"


def _get_max_stream_file_size_bytes(max_size_mb=None):
    if max_size_mb is not None:
        try:
            return int(max_size_mb) * 1024 * 1024
        except (TypeError, ValueError):
            return 5000 * 1024 * 1024

    env_value = os.environ.get("MAX_STREAM_FILE_SIZE_MB", "5000")
    try:
        return int(env_value) * 1024 * 1024
    except (TypeError, ValueError):
        return 5000 * 1024 * 1024


def save_stream_file(source_path, base_url=None, cache_dir=None, max_size_mb=None) -> Optional[Dict[str, str]]:
    """Copy a local media file into a public cache directory and return stream URLs."""
    if not source_path or not os.path.exists(source_path):
        return None

    max_bytes = _get_max_stream_file_size_bytes(max_size_mb)
    if os.path.getsize(source_path) > max_bytes:
        return None

    cache_path = Path(_get_cache_dir(cache_dir))
    cache_path.mkdir(parents=True, exist_ok=True)

    token = uuid.uuid4().hex
    safe_name = os.path.basename(source_path).replace(" ", "_")
    target_path = cache_path / f"{token}_{safe_name}"
    shutil.copy2(source_path, target_path)

    base_url = _get_base_url(base_url)
    return {
        "token": token,
        "file_path": str(target_path),
        "stream_url": f"{base_url}/stream/{token}",
        "player_url": f"{base_url}/player/{token}",
    }


def get_archive_path(archive_path=None):
    """Return the path used for storing generated stream links."""
    if archive_path:
        return str(Path(archive_path).expanduser())

    env_path = os.environ.get("STREAM_LINKS_FILE")
    if env_path:
        return str(Path(env_path).expanduser())

    repo_dir = _get_shared_repo_dir()
    repo_dir.mkdir(parents=True, exist_ok=True)
    return str(repo_dir / "stream_links.txt")


def get_catalog_path(catalog_path=None):
    """Return the path used for storing structured stream-link catalog entries."""
    if catalog_path:
        return str(Path(catalog_path).expanduser())

    env_path = os.environ.get("STREAM_CATALOG_FILE")
    if env_path:
        return str(Path(env_path).expanduser())

    repo_dir = _get_shared_repo_dir()
    repo_dir.mkdir(parents=True, exist_ok=True)
    return str(repo_dir / "stream_catalog.json")


def append_stream_link(player_url, stream_url, label="stream", archive_path=None, catalog_path=None, subject=None, description=None, title=None, token=None):
    """Append a generated stream link to a text archive file and save structured metadata."""
    archive_file = Path(get_archive_path(archive_path))
    archive_file.parent.mkdir(parents=True, exist_ok=True)
    stamp = dt.now().strftime("%Y-%m-%d %H:%M:%S")
    with archive_file.open("a", encoding="utf-8") as handle:
        handle.write(f"[{stamp}] {label}\n")
        handle.write(f"Player: {player_url}\n")
        handle.write(f"Stream: {stream_url}\n\n")

    catalog_file = Path(get_catalog_path(catalog_path))
    catalog_file.parent.mkdir(parents=True, exist_ok=True)
    entries = read_stream_entries(catalog_path=str(catalog_file))

    entry = {
        "timestamp": stamp,
        "date": dt.now().strftime("%Y-%m-%d"),
        "label": label,
        "subject": subject or "General",
        "description": description or "",
        "title": title or (subject or "Untitled"),
        "token": token or os.path.basename(player_url).split("/")[-1],
        "player_url": player_url,
        "stream_url": stream_url,
    }
    entries.append(entry)
    with catalog_file.open("w", encoding="utf-8") as handle:
        json.dump(entries, handle, indent=2, ensure_ascii=False)

    return str(archive_file)


def read_stream_entries(catalog_path=None):
    """Read structured stream-link entries from the catalog file."""
    catalog_file = Path(get_catalog_path(catalog_path))
    if not catalog_file.exists():
        return []
    try:
        data = json.loads(catalog_file.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def read_stream_links(archive_path=None):
    """Read the text archive of generated stream links."""
    archive_file = Path(get_archive_path(archive_path))
    if not archive_file.exists():
        return ""
    return archive_file.read_text(encoding="utf-8")


def get_stream_file(token):
    """Fetch a previously stored stream file by token."""
    if not token:
        return None

    cache_dir = Path(_get_cache_dir())
    cache_dir.mkdir(parents=True, exist_ok=True)

    for path in cache_dir.glob(f"{token}_*"):
        if path.is_file():
            return {"token": token, "file_path": str(path)}

    return None


def get_stream_entry(token, catalog_path=None):
    """Fetch the catalog metadata entry for a stream token if present."""
    if not token:
        return None

    for entry in read_stream_entries(catalog_path=catalog_path):
        if str(entry.get("token", "")) == str(token):
            return entry
    return None
