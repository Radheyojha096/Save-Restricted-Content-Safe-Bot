import os
import json
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from flask import request, session, jsonify, abort, send_file, Response
from safe_repo.web.tags import (
    create_tag as tags_create_tag,
    get_tag as tags_get_tag,
    update_tag as tags_update_tag,
    delete_tag as tags_delete_tag,
    list_tags as tags_list_tags,
    get_all_tags_with_counts as tags_get_all_tags_with_counts,
    assign_tag_to_video as tags_assign_tag_to_video,
    remove_tag_from_video as tags_remove_tag_from_video,
    get_tags_for_video as tags_get_tags_for_video,
    get_videos_by_tag as tags_get_videos_by_tag,
    assign_tag_to_user as tags_assign_tag_to_user,
    remove_tag_from_user as tags_remove_tag_from_user,
    get_tags_for_user as tags_get_tags_for_user,
)
from safe_repo.web.batch import create_batch_job, get_job_status, get_job_zip_path, cleanup_expired
from safe_repo.web.stats import compute_stats, get_dashboard_data
from safe_repo.core.media_links import read_stream_entries, get_stream_entry
from safe_repo.web.study import load_catalog_entries

MONGO_DIR = Path(__file__).resolve().parent.parent / "core" / "mongo"
WEB_AUTH_PATH = MONGO_DIR / "web_auth.json"
USER_PREFS_PATH = MONGO_DIR / "user_prefs.json"


def _read_auth() -> Dict[str, Any]:
    if not WEB_AUTH_PATH.exists():
        return {}
    try:
        data = json.loads(WEB_AUTH_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _write_auth(data: Dict[str, Any]) -> None:
    WEB_AUTH_PATH.parent.mkdir(parents=True, exist_ok=True)
    WEB_AUTH_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _read_prefs() -> Dict[str, Any]:
    if not USER_PREFS_PATH.exists():
        return {}
    try:
        data = json.loads(USER_PREFS_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _write_prefs(data: Dict[str, Any]) -> None:
    USER_PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
    USER_PREFS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _get_current_user_id() -> Optional[str]:
    return session.get("user_id")


def _require_auth() -> str:
    user_id = _get_current_user_id()
    if not user_id:
        abort(401)
    return user_id


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# ============= Auth Endpoints =============

def api_auth_register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"success": False, "error": "username and password are required"}), 400

    if len(password) < 4:
        return jsonify({"success": False, "error": "Password must be at least 4 characters"}), 400

    auth = _read_auth()
    if username in auth:
        return jsonify({"success": False, "error": "Username already exists"}), 409

    user_id = f"web_{username}_{int(datetime.now(timezone.utc).timestamp())}"
    auth[username] = {
        "user_id": user_id,
        "password_hash": _hash_password(password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_auth(auth)

    return jsonify({"success": True, "user_id": user_id, "username": username})


def api_auth_login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"success": False, "error": "username and password are required"}), 400

    auth = _read_auth()
    user = auth.get(username)
    if not user or user.get("password_hash") != _hash_password(password):
        return jsonify({"success": False, "error": "Invalid credentials"}), 401

    session["user_id"] = user["user_id"]
    session["username"] = username
    return jsonify({"success": True, "user_id": user["user_id"], "username": username})


def api_auth_logout():
    session.pop("user_id", None)
    session.pop("username", None)
    return jsonify({"success": True})


def api_auth_status():
    user_id = _get_current_user_id()
    if not user_id:
        return jsonify({"authenticated": False})
    return jsonify({"authenticated": True, "user_id": user_id, "username": session.get("username")})


# ============= User Endpoints =============

def api_user_favorites():
    user_id = _require_auth()
    prefs = _read_prefs().get(user_id, {})
    return jsonify({"success": True, "favorites": prefs.get("favorites", [])})


def api_user_favorites_toggle(token: str):
    user_id = _require_auth()
    prefs = _read_prefs()
    user_prefs = prefs.get(user_id, {"favorites": [], "bookmarks": [], "history": []})
    favorites = user_prefs.get("favorites", [])
    if token in favorites:
        favorites.remove(token)
        action = "removed"
    else:
        favorites.append(token)
        action = "added"
    user_prefs["favorites"] = favorites
    prefs[user_id] = user_prefs
    _write_prefs(prefs)
    return jsonify({"success": True, "action": action, "favorites": favorites})


def api_user_bookmarks():
    user_id = _require_auth()
    prefs = _read_prefs().get(user_id, {})
    return jsonify({"success": True, "bookmarks": prefs.get("bookmarks", [])})


def api_user_bookmarks_toggle(token: str):
    user_id = _require_auth()
    prefs = _read_prefs()
    user_prefs = prefs.get(user_id, {"favorites": [], "bookmarks": [], "history": []})
    bookmarks = user_prefs.get("bookmarks", [])
    if token in bookmarks:
        bookmarks.remove(token)
        action = "removed"
    else:
        bookmarks.append(token)
        action = "added"
    user_prefs["bookmarks"] = bookmarks
    prefs[user_id] = user_prefs
    _write_prefs(prefs)
    return jsonify({"success": True, "action": action, "bookmarks": bookmarks})


def api_user_history():
    user_id = _require_auth()
    prefs = _read_prefs().get(user_id, {})
    return jsonify({"success": True, "history": prefs.get("history", [])})


# ============= Video Endpoints =============

def api_video_view(token: str):
    entries = read_stream_entries()
    updated = None
    for entry in entries:
        if str(entry.get("token")) == str(token):
            entry["views"] = int(entry.get("views") or 0) + 1
            updated = entry
            break
    if updated:
        catalog_path = Path(__file__).resolve().parent.parent / "core" / "mongo" / "stream_catalog.json"
        catalog_path.parent.mkdir(parents=True, exist_ok=True)
        catalog_path.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")

    user_id = _get_current_user_id()
    if user_id:
        prefs = _read_prefs()
        user_prefs = prefs.get(user_id, {"favorites": [], "bookmarks": [], "history": []})
        history = user_prefs.get("history", [])
        history = [t for t in history if t != token]
        history.insert(0, token)
        history = history[:100]
        user_prefs["history"] = history
        prefs[user_id] = user_prefs
        _write_prefs(prefs)

    return jsonify({"success": True, "views": int(updated.get("views") or 0) if updated else 0})


# ============= Stats Endpoints =============

def api_stats_overview():
    stats = compute_stats()
    return jsonify({"success": True, "stats": stats})


def api_stats_user(user_id: str):
    prefs = _read_prefs().get(user_id, {})
    favorites = prefs.get("favorites", [])
    bookmarks = prefs.get("bookmarks", [])
    history = prefs.get("history", [])
    return jsonify({
        "success": True,
        "user_id": user_id,
        "favorites_count": len(favorites),
        "bookmarks_count": len(bookmarks),
        "history_count": len(history),
        "favorites": favorites,
        "bookmarks": bookmarks,
        "history": history,
    })


# ============= Tags Endpoints =============

def api_tags_list():
    tags = tags_get_all_tags_with_counts()
    return jsonify({"success": True, "tags": tags})


def api_admin_tags_create():
    from safe_repo.web.admin import is_admin, require_admin
    require_admin()
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    color = (data.get("color") or "#2563eb").strip()
    description = (data.get("description") or "").strip()
    if not name:
        return jsonify({"success": False, "error": "Tag name is required"}), 400
    try:
        tag = tags_create_tag(name, color, description)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 409
    return jsonify({"success": True, "tag": tag})


def api_admin_video_tags_assign(token: str):
    from safe_repo.web.admin import is_admin, require_admin
    require_admin()
    data = request.get_json(silent=True) or {}
    tags = data.get("tags", [])
    if not isinstance(tags, list):
        return jsonify({"success": False, "error": "tags must be a list"}), 400
    results = []
    for tag_name in tags:
        tag_name = str(tag_name).strip()
        if not tag_name:
            continue
        try:
            created = tags_assign_tag_to_video(tag_name, token)
            results.append({"tag": tag_name, "assigned": True, "created": created})
        except ValueError as e:
            results.append({"tag": tag_name, "assigned": False, "error": str(e)})
    return jsonify({"success": True, "results": results})


def api_admin_videos_batch_tags():
    from safe_repo.web.admin import is_admin, require_admin
    require_admin()
    data = request.get_json(silent=True) or {}
    tokens = data.get("tokens", [])
    tags = data.get("tags", [])
    if not isinstance(tokens, list) or not isinstance(tags, list):
        return jsonify({"success": False, "error": "tokens and tags must be lists"}), 400
    results = []
    for token in tokens:
        token = str(token).strip()
        if not token:
            continue
        token_result = {"token": token, "tags": []}
        for tag_name in tags:
            tag_name = str(tag_name).strip()
            if not tag_name:
                continue
            try:
                created = tags_assign_tag_to_video(tag_name, token)
                token_result["tags"].append({"tag": tag_name, "assigned": True, "created": created})
            except ValueError as e:
                token_result["tags"].append({"tag": tag_name, "assigned": False, "error": str(e)})
        results.append(token_result)
    return jsonify({"success": True, "results": results})


# ============= Batch Download Endpoints =============

def api_batch_download():
    cleanup_expired()
    data = request.get_json(silent=True) or {}
    tokens_raw = data.get("tokens", "")
    job_name = (data.get("name") or "").strip()

    tokens: List[str] = []
    if isinstance(tokens_raw, list):
        tokens = [str(t).strip() for t in tokens_raw if str(t).strip()]
    elif isinstance(tokens_raw, str):
        tokens = [t.strip() for t in tokens_raw.split(",") if t.strip()]

    if not tokens:
        return jsonify({"success": False, "error": "No tokens provided"}), 400

    try:
        job = create_batch_job(tokens, job_name)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 429
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    return jsonify({"success": True, "job": job})


def api_batch_download_status(job_id: str):
    job = get_job_status(job_id)
    if not job:
        return jsonify({"success": False, "error": "Job not found"}), 404
    return jsonify({"success": True, "job": job})


def api_batch_download_file(job_id: str):
    zip_path = get_job_zip_path(job_id)
    if not zip_path:
        return jsonify({"success": False, "error": "File not found or job not completed"}), 404
    return send_file(zip_path, as_attachment=True, download_name=f"batch_{job_id}.zip")


# ============= Advanced Search Endpoint =============

def api_search_advanced():
    q = (request.args.get("q") or "").strip().lower()
    subject = (request.args.get("subject") or "").strip()
    category = (request.args.get("category") or "").strip()
    folder = (request.args.get("folder") or "").strip()
    tag = (request.args.get("tag") or "").strip()
    date_from = (request.args.get("date_from") or "").strip()
    date_to = (request.args.get("date_to") or "").strip()
    featured = request.args.get("featured")
    trending = request.args.get("trending")

    videos = load_catalog_entries()

    token_pool = None
    if tag:
        token_pool = set(tags_get_videos_by_tag(tag))

    results = []
    for video in videos:
        if token_pool is not None and video.get("token") not in token_pool:
            continue
        if q:
            title = str(video.get("title", "") or "").lower()
            description = str(video.get("description", "") or "").lower()
            subject_name = str(video.get("subject", "") or "").lower()
            if q not in title and q not in description and q not in subject_name:
                continue
        if subject and str(video.get("subject", "")).lower() != subject.lower():
            continue
        if category and str(video.get("category", "")).lower() != category.lower():
            continue
        if folder and str(video.get("folder", "") or "General").lower() != folder.lower():
            continue
        if date_from and str(video.get("date", "")) < date_from:
            continue
        if date_to and str(video.get("date", "")) > date_to:
            continue
        if featured is not None and featured not in ("", "0", "false", "False"):
            if not video.get("featured"):
                continue
        if trending is not None and trending not in ("", "0", "false", "False"):
            if not video.get("trending"):
                continue
        results.append(video)

    results.sort(key=lambda v: v.get("timestamp", ""), reverse=True)
    return jsonify({"success": True, "videos": results, "total": len(results)})


def register_api_routes(app):
    app.add_url_rule('/api/auth/register', 'api_auth_register', api_auth_register, methods=['POST'])
    app.add_url_rule('/api/auth/login', 'api_auth_login', api_auth_login, methods=['POST'])
    app.add_url_rule('/api/auth/logout', 'api_auth_logout', api_auth_logout, methods=['POST'])
    app.add_url_rule('/api/auth/status', 'api_auth_status', api_auth_status, methods=['GET'])
    app.add_url_rule('/api/user/favorites', 'api_user_favorites', api_user_favorites, methods=['GET'])
    app.add_url_rule('/api/user/favorites/<token>', 'api_user_favorites_toggle', api_user_favorites_toggle, methods=['POST'])
    app.add_url_rule('/api/user/bookmarks', 'api_user_bookmarks', api_user_bookmarks, methods=['GET'])
    app.add_url_rule('/api/user/bookmarks/<token>', 'api_user_bookmarks_toggle', api_user_bookmarks_toggle, methods=['POST'])
    app.add_url_rule('/api/user/history', 'api_user_history', api_user_history, methods=['GET'])
    app.add_url_rule('/api/videos/<token>/view', 'api_video_view', api_video_view, methods=['POST'])
    app.add_url_rule('/api/stats/overview', 'api_stats_overview', api_stats_overview, methods=['GET'])
    app.add_url_rule('/api/stats/user/<user_id>', 'api_stats_user', api_stats_user, methods=['GET'])
    app.add_url_rule('/api/tags', 'api_tags_list', api_tags_list, methods=['GET'])
    app.add_url_rule('/api/admin/tags', 'api_admin_tags_create', api_admin_tags_create, methods=['POST'])
    app.add_url_rule('/api/admin/videos/<token>/tags', 'api_admin_video_tags_assign', api_admin_video_tags_assign, methods=['POST'])
    app.add_url_rule('/api/admin/videos/batch-tags', 'api_admin_videos_batch_tags', api_admin_videos_batch_tags, methods=['POST'])
    app.add_url_rule('/api/batch/download', 'api_batch_download', api_batch_download, methods=['POST'])
    app.add_url_rule('/api/batch/download/<job_id>/status', 'api_batch_download_status', api_batch_download_status, methods=['GET'])
    app.add_url_rule('/api/batch/download/<job_id>/file', 'api_batch_download_file', api_batch_download_file, methods=['GET'])
    app.add_url_rule('/api/search/advanced', 'api_search_advanced', api_search_advanced, methods=['GET'])
