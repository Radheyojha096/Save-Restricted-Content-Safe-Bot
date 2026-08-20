import os
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from safe_repo.web.auth import get_user_by_id

PROFILES_FILE = Path(__file__).resolve().parent.parent / "core" / "mongo" / "users_profiles.json"


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: Path, data) -> None:
    _ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _load_profiles() -> Dict[str, Any]:
    data = _read_json(PROFILES_FILE, {"profiles": {}})
    if "profiles" not in data:
        data["profiles"] = {}
    return data


def _save_profiles(data: Dict[str, Any]) -> None:
    _write_json(PROFILES_FILE, data)


def _ensure_profile(user_id: str) -> Dict[str, Any]:
    data = _load_profiles()
    profile = data["profiles"].get(user_id)
    if not profile:
        profile = {
            "user_id": user_id,
            "display_name": "",
            "bio": "",
            "avatar_url": "",
            "favorites": [],
            "bookmarks": [],
            "watch_history": [],
            "preferences": {
                "theme": "dark",
                "notifications": True,
                "autoplay": True,
            },
            "tags": [],
            "stats": {
                "videos_watched": 0,
                "favorites_count": 0,
                "bookmarks_count": 0,
            },
            "updated_at": datetime.utcnow().isoformat(),
        }
        data["profiles"][user_id] = profile
        _save_profiles(data)
    return profile


def get_profile(user_id: str) -> Optional[Dict[str, Any]]:
    data = _load_profiles()
    profile = data["profiles"].get(user_id)
    if not profile:
        profile = _ensure_profile(user_id)
    return profile


def update_profile(user_id: str, **kwargs) -> Optional[Dict[str, Any]]:
    profile = get_profile(user_id)
    if not profile:
        return None
    allowed_fields = {"display_name", "bio", "avatar_url"}
    for key, value in kwargs.items():
        if key in allowed_fields:
            profile[key] = value
    profile["updated_at"] = datetime.utcnow().isoformat()
    data = _load_profiles()
    data["profiles"][user_id] = profile
    _save_profiles(data)
    return profile


def get_favorites(user_id: str) -> List[str]:
    profile = get_profile(user_id)
    if not profile:
        return []
    return list(profile.get("favorites", []))


def add_favorite(user_id: str, token: str) -> bool:
    profile = get_profile(user_id)
    if not profile:
        return False
    favorites = profile.get("favorites", [])
    if token in favorites:
        return False
    favorites.append(token)
    profile["favorites"] = favorites
    profile["stats"]["favorites_count"] = len(favorites)
    profile["updated_at"] = datetime.utcnow().isoformat()
    data = _load_profiles()
    data["profiles"][user_id] = profile
    _save_profiles(data)
    return True


def remove_favorite(user_id: str, token: str) -> bool:
    profile = get_profile(user_id)
    if not profile:
        return False
    favorites = profile.get("favorites", [])
    if token not in favorites:
        return False
    favorites.remove(token)
    profile["favorites"] = favorites
    profile["stats"]["favorites_count"] = len(favorites)
    profile["updated_at"] = datetime.utcnow().isoformat()
    data = _load_profiles()
    data["profiles"][user_id] = profile
    _save_profiles(data)
    return True


def get_bookmarks(user_id: str) -> List[str]:
    profile = get_profile(user_id)
    if not profile:
        return []
    return list(profile.get("bookmarks", []))


def add_bookmark(user_id: str, token: str) -> bool:
    profile = get_profile(user_id)
    if not profile:
        return False
    bookmarks = profile.get("bookmarks", [])
    if token in bookmarks:
        return False
    bookmarks.append(token)
    profile["bookmarks"] = bookmarks
    profile["stats"]["bookmarks_count"] = len(bookmarks)
    profile["updated_at"] = datetime.utcnow().isoformat()
    data = _load_profiles()
    data["profiles"][user_id] = profile
    _save_profiles(data)
    return True


def remove_bookmark(user_id: str, token: str) -> bool:
    profile = get_profile(user_id)
    if not profile:
        return False
    bookmarks = profile.get("bookmarks", [])
    if token not in bookmarks:
        return False
    bookmarks.remove(token)
    profile["bookmarks"] = bookmarks
    profile["stats"]["bookmarks_count"] = len(bookmarks)
    profile["updated_at"] = datetime.utcnow().isoformat()
    data = _load_profiles()
    data["profiles"][user_id] = profile
    _save_profiles(data)
    return True


def get_watch_history(user_id: str) -> List[Dict[str, Any]]:
    profile = get_profile(user_id)
    if not profile:
        return []
    return list(profile.get("watch_history", []))


def add_watch_history(user_id: str, token: str, progress: float = 0.0) -> bool:
    profile = get_profile(user_id)
    if not profile:
        return False
    watch_history = profile.get("watch_history", [])
    watch_history = [entry for entry in watch_history if entry.get("token") != token]
    watch_history.insert(0, {
        "token": token,
        "watched_at": datetime.utcnow().isoformat(),
        "progress": progress,
    })
    profile["watch_history"] = watch_history[:100]
    profile["stats"]["videos_watched"] = len(set(entry.get("token") for entry in watch_history))
    profile["updated_at"] = datetime.utcnow().isoformat()
    data = _load_profiles()
    data["profiles"][user_id] = profile
    _save_profiles(data)
    return True


def get_statistics(user_id: str) -> Dict[str, Any]:
    profile = get_profile(user_id)
    if not profile:
        return {}
    stats = profile.get("stats", {})
    stats["favorites_count"] = len(profile.get("favorites", []))
    stats["bookmarks_count"] = len(profile.get("bookmarks", []))
    stats["watch_history_count"] = len(profile.get("watch_history", []))
    return stats


def get_preferences(user_id: str) -> Dict[str, Any]:
    profile = get_profile(user_id)
    if not profile:
        return {}
    return profile.get("preferences", {})


def update_preferences(user_id: str, **kwargs) -> Optional[Dict[str, Any]]:
    profile = get_profile(user_id)
    if not profile:
        return None
    preferences = profile.get("preferences", {})
    preferences.update(kwargs)
    profile["preferences"] = preferences
    profile["updated_at"] = datetime.utcnow().isoformat()
    data = _load_profiles()
    data["profiles"][user_id] = profile
    _save_profiles(data)
    return preferences


def get_tags(user_id: str) -> List[str]:
    profile = get_profile(user_id)
    if not profile:
        return []
    return list(profile.get("tags", []))


def assign_tag(user_id: str, tag: str) -> bool:
    profile = get_profile(user_id)
    if not profile:
        return False
    tags = profile.get("tags", [])
    if tag in tags:
        return False
    tags.append(tag)
    profile["tags"] = tags
    profile["updated_at"] = datetime.utcnow().isoformat()
    data = _load_profiles()
    data["profiles"][user_id] = profile
    _save_profiles(data)
    return True


def remove_tag(user_id: str, tag: str) -> bool:
    profile = get_profile(user_id)
    if not profile:
        return False
    tags = profile.get("tags", [])
    if tag not in tags:
        return False
    tags.remove(tag)
    profile["tags"] = tags
    profile["updated_at"] = datetime.utcnow().isoformat()
    data = _load_profiles()
    data["profiles"][user_id] = profile
    _save_profiles(data)
    return True


def profile_view():
    user = current_user()
    if not user:
        return redirect("/auth/login")

    if request.method == "POST":
        display_name = (request.form.get("display_name") or "").strip()
        bio = (request.form.get("bio") or "").strip()
        avatar_url = (request.form.get("avatar_url") or "").strip()
        update_profile(user["id"], display_name=display_name, bio=bio, avatar_url=avatar_url)
        return redirect("/auth/profile")

    profile = get_profile(user["id"])
    stats = get_statistics(user["id"])
    return render_template_string(PROFILE_TEMPLATE, user=user, profile=profile, stats=stats)


def current_user():
    from flask import session
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_user_by_id(user_id)


PROFILE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>My Profile - StudyHub</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', Arial, sans-serif;
            background: linear-gradient(135deg, #020617 0%, #111827 50%, #0f172a 100%);
            min-height: 100vh;
            color: #f8fafc;
            padding: 24px;
        }
        .wrap { max-width: 900px; margin: 0 auto; }
        .topbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 16px;
            margin-bottom: 24px;
            border-radius: 999px;
            background: rgba(2,6,23,0.75);
            border: 1px solid rgba(148,163,184,0.25);
            backdrop-filter: blur(12px);
        }
        .topbar a { color: white; text-decoration: none; margin-right: 12px; font-weight: 600; }
        .profile-card {
            background: rgba(15, 23, 42, 0.95);
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 18px;
            padding: 32px;
            margin-bottom: 24px;
        }
        .profile-header {
            display: flex;
            align-items: center;
            gap: 20px;
            margin-bottom: 24px;
        }
        .avatar {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            background: linear-gradient(135deg, #2563eb, #0ea5e9);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            font-weight: 700;
            color: white;
            flex-shrink: 0;
        }
        .profile-info h1 {
            font-size: 24px;
            margin-bottom: 4px;
        }
        .profile-info p {
            color: #94a3b8;
            font-size: 14px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .stat-card {
            background: rgba(30, 41, 59, 0.5);
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 12px;
            padding: 16px;
            text-align: center;
        }
        .stat-card .value {
            font-size: 24px;
            font-weight: 700;
            color: #2563eb;
        }
        .stat-card .label {
            font-size: 13px;
            color: #94a3b8;
            margin-top: 4px;
        }
        .section-title {
            font-size: 18px;
            margin-bottom: 12px;
            color: #e2e8f0;
        }
        .form-group {
            margin-bottom: 16px;
        }
        .form-group label {
            display: block;
            margin-bottom: 6px;
            font-weight: 600;
            font-size: 14px;
        }
        .form-group input,
        .form-group textarea {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid rgba(148, 163, 184, 0.3);
            border-radius: 8px;
            background: rgba(30, 41, 59, 0.5);
            color: #f8fafc;
            font-size: 14px;
        }
        .form-group textarea {
            resize: vertical;
            min-height: 80px;
        }
        button {
            padding: 10px 16px;
            background: linear-gradient(135deg, #2563eb, #1d4ed8);
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(37, 99, 235, 0.3);
        }
        .secondary-btn {
            background: rgba(30, 41, 59, 0.6);
            border: 1px solid rgba(148, 163, 184, 0.3);
        }
        .tag {
            display: inline-block;
            background: rgba(37, 99, 235, 0.2);
            color: #93c5fd;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 12px;
            margin-right: 6px;
            margin-bottom: 6px;
        }
        .empty {
            color: #94a3b8;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="wrap">
        <div class="topbar">
            <div><strong>StudyHub</strong></div>
            <div>
                <a href="/">Home</a>
                <a href="/study">Study</a>
                <a href="/auth/logout" style="color:#fca5a5;">Logout</a>
            </div>
        </div>

        <div class="profile-card">
            <div class="profile-header">
                <div class="avatar">{{ (user.username or 'U')[:2].upper() }}</div>
                <div class="profile-info">
                    <h1>{{ user.username }}</h1>
                    <p>{{ user.email }}</p>
                    {% if profile and profile.display_name %}
                    <p>{{ profile.display_name }}</p>
                    {% endif %}
                </div>
            </div>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="value">{{ stats.videos_watched }}</div>
                    <div class="label">Videos Watched</div>
                </div>
                <div class="stat-card">
                    <div class="value">{{ stats.favorites_count }}</div>
                    <div class="label">Favorites</div>
                </div>
                <div class="stat-card">
                    <div class="value">{{ stats.bookmarks_count }}</div>
                    <div class="label">Bookmarks</div>
                </div>
                <div class="stat-card">
                    <div class="value">{{ stats.watch_history_count }}</div>
                    <div class="label">History Entries</div>
                </div>
            </div>

            <h2 class="section-title">Edit Profile</h2>
            <form method="post">
                <div class="form-group">
                    <label>Display Name</label>
                    <input type="text" name="display_name" value="{{ profile.display_name if profile else '' }}" placeholder="Your display name">
                </div>
                <div class="form-group">
                    <label>Bio</label>
                    <textarea name="bio" placeholder="Tell us about yourself">{{ profile.bio if profile else '' }}</textarea>
                </div>
                <div class="form-group">
                    <label>Avatar URL</label>
                    <input type="text" name="avatar_url" value="{{ profile.avatar_url if profile else '' }}" placeholder="https://example.com/avatar.png">
                </div>
                <button type="submit">Save Changes</button>
            </form>
        </div>

        {% if profile and profile.tags %}
        <div class="profile-card">
            <h2 class="section-title">Tags</h2>
            {% for tag in profile.tags %}
            <span class="tag">{{ tag }}</span>
            {% endfor %}
        </div>
        {% endif %}
    </div>
</body>
</html>
"""
