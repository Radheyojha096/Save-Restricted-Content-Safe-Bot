import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

MONGO_DIR = Path(__file__).resolve().parent.parent / "core" / "mongo"
TAGS_PATH = MONGO_DIR / "tags.json"
VIDEO_TAGS_PATH = MONGO_DIR / "video_tags.json"
USER_TAGS_PATH = MONGO_DIR / "user_tags.json"


def _read_tags() -> List[Dict[str, Any]]:
    if not TAGS_PATH.exists():
        return []
    try:
        data = json.loads(TAGS_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [t for t in data if isinstance(t, dict)]
    except Exception:
        pass
    return []


def _write_tags(tags: List[Dict[str, Any]]) -> None:
    TAGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    TAGS_PATH.write_text(json.dumps(tags, indent=2, ensure_ascii=False), encoding="utf-8")


def _read_video_tags() -> Dict[str, List[str]]:
    if not VIDEO_TAGS_PATH.exists():
        return {}
    try:
        data = json.loads(VIDEO_TAGS_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if isinstance(v, list)}
    except Exception:
        pass
    return {}


def _write_video_tags(video_tags: Dict[str, List[str]]) -> None:
    VIDEO_TAGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    VIDEO_TAGS_PATH.write_text(json.dumps(video_tags, indent=2, ensure_ascii=False), encoding="utf-8")


def _read_user_tags() -> Dict[str, List[str]]:
    if not USER_TAGS_PATH.exists():
        return {}
    try:
        data = json.loads(USER_TAGS_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if isinstance(v, list)}
    except Exception:
        pass
    return {}


def _write_user_tags(user_tags: Dict[str, List[str]]) -> None:
    USER_TAGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    USER_TAGS_PATH.write_text(json.dumps(user_tags, indent=2, ensure_ascii=False), encoding="utf-8")


def create_tag(name: str, color: str, description: str = "") -> Dict[str, Any]:
    tags = _read_tags()
    if any(t.get("name") == name for t in tags):
        raise ValueError(f"Tag '{name}' already exists")
    tag = {
        "name": name,
        "color": color,
        "description": description,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    tags.append(tag)
    _write_tags(tags)
    return tag


def get_tag(name: str) -> Optional[Dict[str, Any]]:
    for tag in _read_tags():
        if tag.get("name") == name:
            return tag
    return None


def update_tag(name: str, color: Optional[str] = None, description: Optional[str] = None) -> Optional[Dict[str, Any]]:
    tags = _read_tags()
    for tag in tags:
        if tag.get("name") == name:
            if color is not None:
                tag["color"] = color
            if description is not None:
                tag["description"] = description
            _write_tags(tags)
            return tag
    return None


def delete_tag(name: str) -> bool:
    tags = _read_tags()
    new_tags = [t for t in tags if t.get("name") != name]
    if len(new_tags) == len(tags):
        return False
    _write_tags(new_tags)
    video_tags = _read_video_tags()
    for token, tag_list in list(video_tags.items()):
        video_tags[token] = [t for t in tag_list if t != name]
        if not video_tags[token]:
            del video_tags[token]
    _write_video_tags(video_tags)
    user_tags = _read_user_tags()
    for user_id, tag_list in list(user_tags.items()):
        user_tags[user_id] = [t for t in tag_list if t != name]
        if not user_tags[user_id]:
            del user_tags[user_id]
    _write_user_tags(user_tags)
    return True


def list_tags() -> List[Dict[str, Any]]:
    return _read_tags()


def get_all_tags_with_counts() -> List[Dict[str, Any]]:
    tags = _read_tags()
    video_tags = _read_video_tags()
    user_tags = _read_user_tags()
    result = []
    for tag in tags:
        name = tag.get("name", "")
        video_count = sum(1 for v in video_tags.values() if name in v)
        user_count = sum(1 for u in user_tags.values() if name in u)
        result.append({**tag, "video_count": video_count, "user_count": user_count})
    return result


def assign_tag_to_video(tag_name: str, token: str) -> bool:
    tags = _read_tags()
    if not any(t.get("name") == tag_name for t in tags):
        raise ValueError(f"Tag '{tag_name}' does not exist")
    video_tags = _read_video_tags()
    current = video_tags.get(token, [])
    if tag_name in current:
        return False
    current.append(tag_name)
    video_tags[token] = current
    _write_video_tags(video_tags)
    return True


def remove_tag_from_video(tag_name: str, token: str) -> bool:
    video_tags = _read_video_tags()
    current = video_tags.get(token, [])
    if tag_name not in current:
        return False
    current = [t for t in current if t != tag_name]
    if current:
        video_tags[token] = current
    else:
        video_tags.pop(token, None)
    _write_video_tags(video_tags)
    return True


def get_tags_for_video(token: str) -> List[str]:
    return _read_video_tags().get(token, [])


def get_videos_by_tag(tag_name: str) -> List[str]:
    video_tags = _read_video_tags()
    return [token for token, tags in video_tags.items() if tag_name in tags]


def assign_tag_to_user(tag_name: str, user_id: str) -> bool:
    tags = _read_tags()
    if not any(t.get("name") == tag_name for t in tags):
        raise ValueError(f"Tag '{tag_name}' does not exist")
    user_tags = _read_user_tags()
    current = user_tags.get(str(user_id), [])
    if tag_name in current:
        return False
    current.append(tag_name)
    user_tags[str(user_id)] = current
    _write_user_tags(user_tags)
    return True


def remove_tag_from_user(tag_name: str, user_id: str) -> bool:
    user_tags = _read_user_tags()
    current = user_tags.get(str(user_id), [])
    if tag_name not in current:
        return False
    current = [t for t in current if t != tag_name]
    if current:
        user_tags[str(user_id)] = current
    else:
        user_tags.pop(str(user_id), None)
    _write_user_tags(user_tags)
    return True


def get_tags_for_user(user_id: str) -> List[str]:
    return _read_user_tags().get(str(user_id), [])
