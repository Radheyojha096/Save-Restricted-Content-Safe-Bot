import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode


def _get_catalog_path(catalog_path: Optional[str] = None) -> str:
    if catalog_path:
        return str(Path(catalog_path).expanduser())

    env_path = os.environ.get("STREAM_CATALOG_FILE")
    if env_path:
        return str(Path(env_path).expanduser())

    return str(Path(__file__).resolve().parent.parent / "core" / "mongo" / "stream_catalog.json")


def _read_catalog_entries(catalog_path: Optional[str] = None) -> List[Dict[str, Any]]:
    path = Path(_get_catalog_path(catalog_path))
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    if isinstance(data, list):
        return [entry for entry in data if isinstance(entry, dict)]
    return []


def _build_watch_url(token: str) -> str:
    token = str(token or "").strip()
    if not token:
        return "/study"
    return f"/study/watch/{token}"


def build_public_study_url(base_url: str, subject: Optional[str] = None, date: Optional[str] = None, q: Optional[str] = None, folder: Optional[str] = None) -> str:
    """Build a public study URL that defaults to the home page and only uses /study when filters are present."""
    base = (base_url or "/").rstrip("/")
    params = {}
    if subject:
        params["subject"] = subject
    if date:
        params["date"] = date
    if q:
        params["q"] = q
    if folder:
        params["folder"] = folder

    if not params:
        return f"{base}/"

    if base.endswith("/study"):
        return f"{base}?{urlencode(params)}"
    return f"{base}/study?{urlencode(params)}"


def _extract_folder_name(description: str) -> str:
    text = (description or "").strip()
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("folder:"):
            return line.split(":", 1)[1].strip() or "General"
        if line.lower().startswith("topic:"):
            return line.split(":", 1)[1].strip() or "General"
    return "General"


def load_catalog_entries(catalog_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Normalize stored stream links into study-site video entries."""
    entries: List[Dict[str, Any]] = []
    for raw_entry in _read_catalog_entries(catalog_path):
        token = str(raw_entry.get("token") or raw_entry.get("id") or "").strip()
        subject = str(raw_entry.get("subject") or "General").strip() or "General"
        category = str(raw_entry.get("category") or raw_entry.get("class") or "General").strip() or "General"
        title = str(raw_entry.get("title") or subject or "Untitled").strip() or "Untitled"
        description = str(raw_entry.get("description") or "").strip()
        folder_name = _extract_folder_name(description)
        stream_url = str(raw_entry.get("stream_url") or "").strip()
        player_url = str(raw_entry.get("player_url") or "").strip()

        entries.append(
            {
                "token": token,
                "title": title,
                "description": description,
                "folder": folder_name,
                "subject": subject,
                "category": category,
                "timestamp": str(raw_entry.get("timestamp") or ""),
                "date": str(raw_entry.get("date") or ""),
                "featured": bool(raw_entry.get("featured")),
                "trending": bool(raw_entry.get("trending")),
                "views": int(raw_entry.get("views") or 0),
                "player_url": player_url,
                "stream_url": stream_url,
                "watch_url": _build_watch_url(token),
            }
        )

    return entries


def build_video_index(catalog_path: Optional[str] = None, subject: Optional[str] = None, date: Optional[str] = None, q: Optional[str] = None, folder: Optional[str] = None) -> Dict[str, Any]:
    """Build a study-site index from catalog entries and optional filters."""
    videos = load_catalog_entries(catalog_path)

    subject_param = (subject or "").strip()
    date_param = (date or "").strip()
    query_param = (q or "").strip()
    folder_param = (folder or "").strip()
    subject_filter = subject_param.lower()
    date_filter = date_param
    search_query = query_param.lower()
    folder_filter = folder_param.lower()

    filtered = []
    for video in videos:
        title = str(video.get("title", "") or "").lower()
        subject_name = str(video.get("subject", "") or "").lower()
        description = str(video.get("description", "") or "").lower()
        folder_name = str(video.get("folder") or "General").lower()
        if search_query and search_query not in title and search_query not in subject_name and search_query not in description:
            continue
        if subject_filter and subject_filter != str(video.get("subject", "")).lower():
            continue
        if date_filter and str(video.get("date", "")) != date_filter:
            continue
        if folder_filter and folder_filter != folder_name:
            continue
        filtered.append(video)

    featured = [video for video in filtered if video.get("featured")]
    latest = sorted(filtered, key=lambda item: item.get("timestamp", ""), reverse=True)
    trending = sorted(
        [video for video in filtered if video.get("trending") or video.get("views", 0) > 0],
        key=lambda item: (item.get("views", 0), item.get("timestamp", "")),
        reverse=True,
    )

    subject_counts: Dict[str, int] = {}
    subject_weights: Dict[str, int] = {}
    for video in videos:
        subject = video.get("subject") or "General"
        subject_counts[subject] = subject_counts.get(subject, 0) + 1
        weight = 1
        if video.get("featured"):
            weight += 10
        if video.get("trending"):
            weight += 6
        weight += max(0, int(video.get("views") or 0) // 10)
        subject_weights[subject] = subject_weights.get(subject, 0) + weight

    subjects = [
        {"name": name, "count": subject_counts[name], "weight": subject_weights.get(name, 0)}
        for name in subject_counts.keys()
    ]
    subjects.sort(key=lambda item: (-item["weight"], -item["count"], item["name"]))
    for subject in subjects:
        subject.pop("weight", None)

    categories: Dict[str, int] = {}
    folders: Dict[str, int] = {}
    for video in videos:
        category = video.get("category") or "General"
        categories[category] = categories.get(category, 0) + 1
        folder = video.get("folder") or "General"
        folders[folder] = folders.get(folder, 0) + 1

    playlists = []
    playlist_map = {}
    for video in videos:
        subject_name = video.get("subject") or "General"
        folder_name = video.get("folder") or "General"
        key = f"{subject_name}:::{folder_name}"
        playlist_map.setdefault(key, []).append(video)
    for key, subject_videos in sorted(playlist_map.items(), key=lambda item: item[0].lower()):
        subject_name, folder_name = key.split(":::", 1)
        subject_videos_sorted = sorted(subject_videos, key=lambda item: (item.get("timestamp", "")), reverse=True)
        playlists.append({
            "subject": subject_name,
            "folder": folder_name,
            "videos": subject_videos_sorted[:6],
        })

    return {
        "videos": filtered,
        "featured": featured[:6],
        "latest": latest[:8],
        "trending": trending[:8],
        "subjects": subjects,
        "categories": [
            {"name": name, "count": count}
            for name, count in sorted(categories.items(), key=lambda item: (-item[1], item[0]))
        ],
        "folders": [
            {"name": name, "count": count}
            for name, count in sorted(folders.items(), key=lambda item: (-item[1], item[0]))
        ],
        "playlists": playlists[:8],
        "filter_summary": {
            "subject": subject_param if subject_param else "",
            "date": date_param if date_param else "",
            "q": query_param if query_param else "",
            "folder": folder_param if folder_param else "",
        },
    }
