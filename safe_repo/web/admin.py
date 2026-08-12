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
        return render_template_string("""
        <html><body style="font-family:Arial;padding:40px;background:#0f172a;color:white;">
          <h2>Admin Login</h2>
          <form method="post">
            <input name="username" placeholder="Username" /><br/><br/>
            <input name="password" placeholder="Password" type="password" /><br/><br/>
            <button type="submit">Login</button>
          </form>
        </body></html>
        """)
    return render_template_string("""
    <html><body style="font-family:Arial;padding:40px;background:#0f172a;color:white;">
      <h2>Admin Login</h2>
      <form method="post">
        <input name="username" placeholder="Username" /><br/><br/>
        <input name="password" placeholder="Password" type="password" /><br/><br/>
        <button type="submit">Login</button>
      </form>
    </body></html>
    """)


def admin_dashboard_view():
    require_admin()
    entries = _load_entries()
    return render_template_string("""
    <html>
      <head><title>Admin Dashboard</title></head>
      <body style="font-family:Arial;padding:24px;background:#020617;color:white;">
        <h2>Admin Dashboard</h2>
        <p><a href="/admin/logout">Logout</a></p>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse;width:100%;">
          <tr><th>Title</th><th>Subject</th><th>Folder</th><th>Featured</th><th>Trending</th><th>Actions</th></tr>
          {% for entry in entries %}
          <tr>
            <td>{{ entry.title }}</td>
            <td>{{ entry.subject }}</td>
            <td>{{ entry.folder }}</td>
            <td>{{ 'Yes' if entry.featured else 'No' }}</td>
            <td>{{ 'Yes' if entry.trending else 'No' }}</td>
            <td>
              <a href="/admin/toggle-featured/{{ entry.token }}">Toggle Featured</a> |
              <a href="/admin/toggle-trending/{{ entry.token }}">Toggle Trending</a> |
              <a href="/admin/delete/{{ entry.token }}" style="color:#fda4af;">Delete</a>
            </td>
          </tr>
          {% endfor %}
        </table>
      </body>
    </html>
    """, entries=entries)


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
