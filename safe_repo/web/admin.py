import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from flask import request, session, redirect, render_template_string, abort
from safe_repo.web.study import load_catalog_entries

ADMIN_USERNAME = os.environ.get("STUDY_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("STUDY_ADMIN_PASSWORD", "admin123")


def _get_catalog_path(catalog_path: Optional[str] = None) -> str:
    if catalog_path:
        return str(Path(catalog_path).expanduser())
    env_path = os.environ.get("STREAM_CATALOG_FILE")
    if env_path:
        return str(Path(env_path).expanduser())
    return str(Path(__file__).resolve().parent.parent / "core" / "mongo" / "stream_catalog.json")


def _load_entries(catalog_path: Optional[str] = None) -> List[Dict[str, Any]]:
    return load_catalog_entries(catalog_path)


def _save_entries(entries: List[Dict[str, Any]], catalog_path: Optional[str] = None) -> None:
    path = Path(_get_catalog_path(catalog_path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")


def is_admin() -> bool:
    return bool(session.get("is_admin"))


def require_admin():
    if not is_admin():
        abort(403)


def admin_login_view():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect("/admin/dashboard")
        error = "Invalid credentials"
    else:
        error = None
    
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Admin Login - Safe Bot</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Inter', Arial, sans-serif;
                background: linear-gradient(135deg, #020617 0%, #111827 50%, #0f172a 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                color: #f8fafc;
            }
            .login-container {
                background: rgba(15, 23, 42, 0.95);
                border: 1px solid rgba(148, 163, 184, 0.2);
                border-radius: 18px;
                padding: 40px;
                width: 100%;
                max-width: 400px;
                box-shadow: 0 20px 45px rgba(0, 0, 0, 0.3);
                backdrop-filter: blur(10px);
            }
            .login-header {
                text-align: center;
                margin-bottom: 32px;
            }
            .login-header h1 {
                font-size: 28px;
                margin-bottom: 8px;
                background: linear-gradient(135deg, #2563eb, #0ea5e9);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            .login-header p {
                color: #94a3b8;
                font-size: 14px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            .form-group label {
                display: block;
                margin-bottom: 8px;
                font-weight: 600;
                font-size: 14px;
            }
            .form-group input {
                width: 100%;
                padding: 12px 14px;
                border: 1px solid rgba(148, 163, 184, 0.3);
                border-radius: 8px;
                background: rgba(30, 41, 59, 0.5);
                color: #f8fafc;
                font-size: 14px;
                transition: all 0.3s;
            }
            .form-group input:focus {
                outline: none;
                border-color: #2563eb;
                background: rgba(30, 41, 59, 0.8);
            }
            .form-group input::placeholder {
                color: #64748b;
            }
            .error-message {
                color: #fca5a5;
                font-size: 13px;
                margin-bottom: 16px;
                padding: 10px 12px;
                background: rgba(220, 38, 38, 0.1);
                border-radius: 6px;
                display: none;
            }
            .error-message.show {
                display: block;
            }
            button {
                width: 100%;
                padding: 12px;
                background: linear-gradient(135deg, #2563eb, #1d4ed8);
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
                font-size: 14px;
            }
            button:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(37, 99, 235, 0.3);
            }
            button:active {
                transform: translateY(0);
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="login-header">
                <h1>🔐 Admin Panel</h1>
                <p>Safe Repository - Video Management</p>
            </div>
            {% if error %}
            <div class="error-message show">⚠️ {{ error }}</div>
            {% endif %}
            <form method="post">
                <div class="form-group">
                    <label>Username</label>
                    <input type="text" name="username" placeholder="Enter admin username" required>
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" name="password" placeholder="Enter admin password" required>
                </div>
                <button type="submit">Login</button>
            </form>
        </div>
    </body>
    </html>
    """, error=error)


def admin_dashboard_view():
    require_admin()
    entries = _load_entries()
    
    # Get unique folders and count
    folders = {}
    for entry in entries:
        folder = entry.get('folder', 'General')
        if folder not in folders:
            folders[folder] = 0
        folders[folder] += 1
    
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Admin Dashboard - Safe Bot</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Inter', Arial, sans-serif;
                background: linear-gradient(135deg, #020617 0%, #111827 50%, #0f172a 100%);
                color: #f8fafc;
                min-height: 100vh;
                padding: 20px;
            }
            .container { max-width: 1400px; margin: 0 auto; }
            .header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
                flex-wrap: wrap;
                gap: 16px;
            }
            .header h1 {
                font-size: 32px;
                background: linear-gradient(135deg, #2563eb, #0ea5e9);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            .logout-btn {
                padding: 10px 20px;
                background: rgba(220, 38, 38, 0.2);
                border: 1px solid #dc2626;
                color: #fca5a5;
                border-radius: 8px;
                text-decoration: none;
                cursor: pointer;
                transition: all 0.3s;
                font-weight: 600;
            }
            .logout-btn:hover {
                background: rgba(220, 38, 38, 0.3);
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 16px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: rgba(15, 23, 42, 0.8);
                border: 1px solid rgba(148, 163, 184, 0.2);
                border-radius: 12px;
                padding: 20px;
            }
            .stat-card h3 {
                color: #94a3b8;
                font-size: 13px;
                font-weight: 600;
                margin-bottom: 8px;
            }
            .stat-card .value {
                font-size: 28px;
                font-weight: 700;
                color: #2563eb;
            }
            .filters {
                display: flex;
                gap: 10px;
                margin-bottom: 20px;
                flex-wrap: wrap;
            }
            .filters select {
                padding: 10px 14px;
                background: rgba(30, 41, 59, 0.6);
                border: 1px solid rgba(148, 163, 184, 0.2);
                border-radius: 8px;
                color: #f8fafc;
                cursor: pointer;
            }
            .videos-grid {
                display: grid;
                gap: 16px;
            }
            .video-card {
                background: rgba(15, 23, 42, 0.8);
                border: 1px solid rgba(148, 163, 184, 0.2);
                border-radius: 12px;
                padding: 16px;
                transition: all 0.3s;
            }
            .video-card:hover {
                border-color: rgba(148, 163, 184, 0.4);
                background: rgba(15, 23, 42, 0.9);
            }
            .video-header {
                display: flex;
                justify-content: space-between;
                align-items: start;
                margin-bottom: 12px;
            }
            .video-title {
                font-weight: 600;
                font-size: 16px;
                color: #e2e8f0;
                flex: 1;
                margin-right: 12px;
            }
            .video-meta {
                display: flex;
                gap: 8px;
                margin-bottom: 12px;
                flex-wrap: wrap;
            }
            .badge {
                display: inline-block;
                padding: 4px 8px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
            }
            .badge.subject {
                background: rgba(37, 99, 235, 0.2);
                color: #93c5fd;
            }
            .badge.folder {
                background: rgba(59, 130, 246, 0.2);
                color: #bfdbfe;
            }
            .badge.featured {
                background: rgba(250, 204, 21, 0.2);
                color: #fde047;
            }
            .badge.trending {
                background: rgba(239, 68, 68, 0.2);
                color: #fca5a5;
            }
            .video-actions {
                display: flex;
                gap: 8px;
                flex-wrap: wrap;
            }
            .action-btn {
                padding: 6px 12px;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
            }
            .action-btn.featured {
                background: rgba(250, 204, 21, 0.2);
                color: #fde047;
            }
            .action-btn.featured:hover {
                background: rgba(250, 204, 21, 0.3);
            }
            .action-btn.trending {
                background: rgba(239, 68, 68, 0.2);
                color: #fca5a5;
            }
            .action-btn.trending:hover {
                background: rgba(239, 68, 68, 0.3);
            }
            .action-btn.delete {
                background: rgba(220, 38, 38, 0.2);
                color: #fca5a5;
            }
            .action-btn.delete:hover {
                background: rgba(220, 38, 38, 0.3);
            }
            .empty-state {
                text-align: center;
                padding: 40px;
                color: #94a3b8;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h1>📊 Admin Dashboard</h1>
                    <p style="color: #94a3b8; font-size: 14px; margin-top: 4px;">Video Management & Organization</p>
                </div>
                <a href="/admin/logout" class="logout-btn">Logout</a>
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <h3>Total Videos</h3>
                    <div class="value">{{ entries|length }}</div>
                </div>
                <div class="stat-card">
                    <h3>Featured Videos</h3>
                    <div class="value">{{ entries|selectattr('featured')|list|length }}</div>
                </div>
                <div class="stat-card">
                    <h3>Trending Videos</h3>
                    <div class="value">{{ entries|selectattr('trending')|list|length }}</div>
                </div>
                <div class="stat-card">
                    <h3>Folders</h3>
                    <div class="value">{{ folders|length }}</div>
                </div>
            </div>

            {% if entries %}
            <div class="videos-grid">
                {% for entry in entries %}
                <div class="video-card">
                    <div class="video-header">
                        <div class="video-title">{{ entry.title }}</div>
                    </div>
                    <div class="video-meta">
                        <span class="badge subject">📚 {{ entry.subject }}</span>
                        <span class="badge folder">📁 {{ entry.folder }}</span>
                        {% if entry.featured %}
                        <span class="badge featured">⭐ Featured</span>
                        {% endif %}
                        {% if entry.trending %}
                        <span class="badge trending">🔥 Trending</span>
                        {% endif %}
                    </div>
                    <div class="video-actions">
                        <button class="action-btn featured" onclick="window.location.href='/admin/toggle-featured/{{ entry.token }}'">
                            {% if entry.featured %}Unmark Featured{% else %}Mark Featured{% endif %}
                        </button>
                        <button class="action-btn trending" onclick="window.location.href='/admin/toggle-trending/{{ entry.token }}'">
                            {% if entry.trending %}Unmark Trending{% else %}Mark Trending{% endif %}
                        </button>
                        <button class="action-btn delete" onclick="if(confirm('Delete this video?')) window.location.href='/admin/delete/{{ entry.token }}'">
                            Delete
                        </button>
                        <a href="{{ entry.player_url }}" target="_blank" style="color: #93c5fd; text-decoration: none; padding: 6px 12px; border: 1px solid #2563eb; border-radius: 6px; font-size: 12px; font-weight: 600;">
                            Preview
                        </a>
                    </div>
                </div>
                {% endfor %}
            </div>
            {% else %}
            <div class="empty-state">
                <p style="font-size: 16px; margin-bottom: 8px;">📭 No videos yet</p>
                <p style="font-size: 13px;">Forward videos to the bot to start building your library</p>
            </div>
            {% endif %}
        </div>
    </body>
    </html>
    """, entries=entries, folders=folders)


def admin_logout_view():
    session.pop("is_admin", None)
    return redirect("/admin/login")


def toggle_featured_view(token):
    require_admin()
    entries = _load_entries()
    for entry in entries:
        if str(entry.get("token")) == str(token):
            entry["featured"] = not bool(entry.get("featured"))
            break
    _save_entries(entries)
    return redirect("/admin/dashboard")


def toggle_trending_view(token):
    require_admin()
    entries = _load_entries()
    for entry in entries:
        if str(entry.get("token")) == str(token):
            entry["trending"] = not bool(entry.get("trending"))
            break
    _save_entries(entries)
    return redirect("/admin/dashboard")


def delete_entry_view(token):
    require_admin()
    entries = _load_entries()
    entries = [entry for entry in entries if str(entry.get("token")) != str(token)]
    _save_entries(entries)
    return redirect("/admin/dashboard")
