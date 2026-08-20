import os
import time
import threading
import mimetypes
import requests
import json
from flask import Flask, send_file, abort, redirect, request, render_template, jsonify
from safe_repo.core.media_links import get_stream_file, read_stream_entries, get_stream_entry
from safe_repo.web.admin import admin_dashboard_view, admin_login_view, admin_logout_view, toggle_featured_view, toggle_trending_view, delete_entry_view
from safe_repo.web.study import build_public_study_url, build_video_index, load_catalog_entries

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "study-secret-key")

# Auto-ping settings
AUTO_PING_ENABLED = True
AUTO_PING_INTERVAL = 300  # 5 minutes in seconds
APP_URL = None


def auto_ping():
    """Background task to keep the app awake by pinging itself periodically"""
    while AUTO_PING_ENABLED and APP_URL:
        try:
            response = requests.get(APP_URL)
            print(f"Auto-ping successful: {response.status_code}")
        except Exception as e:
            print(f"Auto-ping failed: {str(e)}")
        time.sleep(AUTO_PING_INTERVAL)


@app.route('/')
def home():
    subject_filter = (request.args.get('subject') or '').strip()
    date_filter = (request.args.get('date') or '').strip()
    search_query = (request.args.get('q') or '').strip()
    folder_filter = (request.args.get('folder') or '').strip()
    index = build_video_index(subject=subject_filter, date=date_filter, q=search_query, folder=folder_filter)
    videos = index.get("videos", [])
    featured = index.get("featured", [])
    latest = index.get("latest", [])
    trending = index.get("trending", [])
    subjects = index.get("subjects", [])
    playlists = index.get("playlists", [])
    filter_summary = index.get("filter_summary", {})

    return render_template('home.html', videos=videos, featured=featured, latest=latest, trending=trending, subjects=subjects, playlists=playlists, filter_summary=filter_summary, request=request)


@app.route('/study')
def study_home():
    """Public study-platform landing page built from the stream catalog."""
    subject_filter = (request.args.get('subject') or '').strip()
    date_filter = (request.args.get('date') or '').strip()
    search_query = (request.args.get('q') or '').strip()
    folder_filter = (request.args.get('folder') or '').strip()
    index = build_video_index(subject=subject_filter, date=date_filter, q=search_query, folder=folder_filter)
    videos = index.get("videos", [])
    featured = index.get("featured", [])
    latest = index.get("latest", [])
    trending = index.get("trending", [])
    subjects = index.get("subjects", [])
    categories = index.get("categories", [])
    folders = index.get("folders", [])
    playlists = index.get("playlists", [])
    filter_summary = index.get("filter_summary", {})

    return render_template('study.html', videos=videos, featured=featured, latest=latest, trending=trending, subjects=subjects, categories=categories, folders=folders, playlists=playlists, filter_summary=filter_summary, request=request)


@app.route('/go')
def public_study_redirect():
    """Redirect to the public study catalog, optionally pre-filtered by subject/date/query."""
    subject = (request.args.get('subject') or '').strip()
    date = (request.args.get('date') or '').strip()
    q = (request.args.get('q') or '').strip()
    folder = (request.args.get('folder') or '').strip()
    target = build_public_study_url(request.url_root, subject=subject, date=date, q=q, folder=folder)
    return redirect(target, code=302)


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    return admin_login_view()


@app.route('/admin/dashboard')
def admin_dashboard():
    return admin_dashboard_view()


@app.route('/admin/logout')
def admin_logout():
    return admin_logout_view()


@app.route('/admin/toggle-featured/<token>')
def admin_toggle_featured(token):
    return toggle_featured_view(token)


@app.route('/admin/toggle-trending/<token>')
def admin_toggle_trending(token):
    return toggle_trending_view(token)


@app.route('/admin/delete/<token>')
def admin_delete_entry(token):
    return delete_entry_view(token)


@app.route('/auth/register', methods=['GET', 'POST'])
def auth_register():
    return auth_module.register_view()


@app.route('/auth/login', methods=['GET', 'POST'])
def auth_login():
    return auth_module.login_view()


@app.route('/auth/logout')
def auth_logout():
    return auth_module.logout_view()


@app.route('/auth/profile', methods=['GET', 'POST'])
def auth_profile():
    return users_module.profile_view()


@app.route('/auth/forgot-password', methods=['GET', 'POST'])
def auth_forgot_password():
    return auth_module.forgot_password_view()


@app.route('/auth/reset-password/<token>', methods=['GET', 'POST'])
def auth_reset_password(token):
    return auth_module.reset_password_view(token)


@app.route('/study/watch/<token>')
def study_watch_page(token):
    """Watch page for a study video using the public stream and player links."""
    video = None
    for entry in load_catalog_entries():
        if str(entry.get("token")) == str(token):
            video = entry
            break

    if not video:
        abort(404)

    related_videos = []
    for entry in load_catalog_entries():
        if str(entry.get("subject")) == str(video.get("subject")) and str(entry.get("token")) != str(token):
            related_videos.append(entry)
    related_videos = related_videos[:6]

    return render_template('watch.html', video=video, related_videos=related_videos)


# ============= API Endpoints for Real-Time Sync & Management =============

@app.route('/api/videos/sync')
def api_videos_sync():
    """API endpoint for real-time video synchronization from bot to website."""
    try:
        entries = read_stream_entries()
        return jsonify({
            "success": True,
            "videos": entries,
            "total": len(entries),
            "timestamp": __import__('datetime').datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/videos/folders')
def api_videos_folders():
    """API endpoint to get all unique folders."""
    try:
        entries = read_stream_entries()
        folders = {}
        for entry in entries:
            folder = entry.get('folder', 'General')
            if folder not in folders:
                folders[folder] = []
            folders[folder].append(entry)
        
        return jsonify({
            "success": True,
            "folders": {k: len(v) for k, v in folders.items()},
            "total_folders": len(folders)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/videos/recent')
def api_videos_recent():
    """API endpoint to get recently added videos."""
    try:
        limit = int(request.args.get('limit', 10))
        entries = read_stream_entries()
        entries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return jsonify({
            "success": True,
            "videos": entries[:limit],
            "total": len(entries)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/videos/featured')
def api_videos_featured():
    """API endpoint to get featured videos."""
    try:
        entries = read_stream_entries()
        featured = [e for e in entries if e.get('featured')]
        return jsonify({
            "success": True,
            "videos": featured,
            "total": len(featured)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/public/folders')
def api_public_folders():
    """API endpoint to get public folder structure."""
    try:
        entries = read_stream_entries()
        folders = {}
        for entry in entries:
            folder = entry.get('folder', 'General')
            if folder not in folders:
                folders[folder] = []
            folders[folder].append({
                "token": entry.get('token'),
                "title": entry.get('title'),
                "subject": entry.get('subject'),
                "description": entry.get('description', ''),
                "stream_url": entry.get('stream_url'),
                "player_url": entry.get('player_url')
            })
        
        return jsonify({
            "success": True,
            "public_folders": folders,
            "folder_count": len(folders)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    return "OK", 200


@app.route('/catalog')
def catalog_page():
    """Show a browseable catalog of generated stream links."""
    subject_filter = (request.args.get('subject') or '').strip()
    date_filter = (request.args.get('date') or '').strip()
    search_query = (request.args.get('q') or '').strip().lower()
    entries = read_stream_entries()

    filtered = []
    for entry in entries:
        title = str(entry.get('title', '') or '').lower()
        subject = str(entry.get('subject', '') or '').lower()
        description = str(entry.get('description', '') or '').lower()
        if search_query and search_query not in title and search_query not in subject and search_query not in description:
            continue
        if subject_filter and str(entry.get('subject', '')).lower() != subject_filter.lower():
            continue
        if date_filter and str(entry.get('date', '')) != date_filter:
            continue
        filtered.append(entry)
    filtered.sort(key=lambda item: item.get('timestamp', ''), reverse=True)

    subjects = sorted({str(entry.get('subject', 'General')) for entry in entries})
    dates = sorted({str(entry.get('date', '')) for entry in entries if entry.get('date')})

    return render_template('catalog.html', subjects=subjects, dates=dates, filtered=filtered, subject_filter=subject_filter, date_filter=date_filter)


@app.route('/stats')
def stats_page():
    index = build_video_index()
    videos = index.get("videos", [])
    featured = index.get("featured", [])
    trending = index.get("trending", [])
    subjects = index.get("subjects", [])
    categories = index.get("categories", [])
    folders = index.get("folders", [])
    return render_template('stats.html', videos=videos, featured=featured, trending=trending, subjects=subjects, categories=categories, folders=folders)


@app.route('/favorites')
def favorites_page():
    index = build_video_index()
    videos = index.get("videos", [])
    featured = [v for v in videos if v.get("featured")]
    return render_template('favorites.html', videos=featured)


@app.route('/batch')
def batch_page():
    index = build_video_index()
    videos = index.get("videos", [])
    return render_template('batch.html', videos=videos)


@app.route('/auth/login', methods=['GET', 'POST'])
def auth_login():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = (request.form.get('password') or '').strip()
        if username and password:
            return redirect('/study')
        error = 'Invalid credentials'
    else:
        error = None
    return render_template('auth/login.html', error=error)


@app.route('/auth/register', methods=['GET', 'POST'])
def auth_register():
    return render_template('auth/register.html')


@app.route('/auth/forgot-password', methods=['GET', 'POST'])
def auth_forgot_password():
    if request.method == 'POST':
        success = 'Password reset link sent to your email'
    else:
        success = None
    return render_template('auth/forgot-password.html', success=success)


@app.route('/auth/profile')
def auth_profile():
    user = {
        'name': 'Demo User',
        'username': 'demouser',
        'email': 'demo@studyhub.com',
        'watched': 42,
        'favorites': 18,
        'watchlist': 7,
        'shared': 3,
    }
    return render_template('auth/profile.html', user=user)


def start_bot_process():
    """Start the safe_repo bot.

    Guard against double-start: if another instance of the bot is already
    running (e.g. a separate Render worker using the same BOT_TOKEN), two
    Pyrogram clients would log in to the same bot and Telegram returns a
    409 Conflict, making the bot stop responding.

    NOTE: we use a lock file instead of `pgrep` because minimal Docker images
    (e.g. Render's python:3.10-slim) do not ship `pgrep`, which previously
    crashed this launcher with FileNotFoundError.
    """
    import subprocess
    import time
    import os
    import signal

    lock_file = "/tmp/safe_repo_bot.lock"

    # If a bot process is already running (lock file with a live PID), do not
    # spawn a second one.
    if os.path.exists(lock_file):
        try:
            with open(lock_file) as f:
                old_pid = int(f.read().strip())
            # Check if that PID is still alive (works without pgrep)
            os.kill(old_pid, 0)
            print(f"safe_repo bot already running (pid {old_pid}); "
                  "not starting a duplicate.")
            return
        except (ValueError, ProcessLookupError, PermissionError):
            # Stale lock file - remove it and continue
            try:
                os.remove(lock_file)
            except Exception:
                pass
        except Exception:
            try:
                os.remove(lock_file)
            except Exception:
                pass

    try:
        # Write our PID to the lock file
        with open(lock_file, "w") as f:
            f.write(str(os.getpid()))

        print("Starting safe_repo bot process...")
        # Explicitly pass environment to subprocess to ensure RENDER_EXTERNAL_URL and other vars are inherited
        bot_proc = subprocess.Popen(["python3", "-m", "safe_repo"], env=os.environ.copy())
        bot_proc.wait()
        print(f"safe_repo exited with code {bot_proc.returncode}")
    except Exception as e:
        print(f"safe_repo launcher error: {e}")
    finally:
        # Clean up lock file on exit
        try:
            if os.path.exists(lock_file):
                os.remove(lock_file)
        except Exception:
            pass


@app.route('/stream/<token>')
def stream_media(token):
    """Serve a cached media file as a direct HTTP stream."""
    entry = get_stream_file(token)
    if not entry:
        abort(404)

    path = entry["file_path"]
    response = build_stream_response(path, as_attachment=request.args.get("download") == "1")
    if response is None:
        abort(404)
    return response


def build_stream_response(path, as_attachment=False):
    """Build a browser-friendly response for stream and download requests."""
    if not os.path.exists(path):
        return None

    mime_type, _ = mimetypes.guess_type(path)
    if not mime_type:
        mime_type = "application/octet-stream"

    try:
        response = send_file(
            path,
            mimetype=mime_type,
            as_attachment=as_attachment,
            download_name=os.path.basename(path),
            conditional=True,
        )
    except RuntimeError:
        with app.test_request_context('/'):
            response = send_file(
                path,
                mimetype=mime_type,
                as_attachment=as_attachment,
                download_name=os.path.basename(path),
                conditional=True,
            )

    response.headers['Content-Type'] = mime_type
    response.headers['Content-Disposition'] = 'inline' if not as_attachment else 'attachment; filename="%s"' % os.path.basename(path)
    return response


@app.route('/player/<token>')
def player_page(token):
    """Return a simple HTML page that opens the stream in a player-friendly way."""
    entry = get_stream_file(token)
    if not entry:
        abort(404)

    stream_url = f"{request.url_root.rstrip('/')}/stream/{token}"
    entry_meta = get_stream_entry(token)
    title = entry_meta.get('title') if entry_meta else 'Media Player'
    description = entry_meta.get('description') if entry_meta else ''
    subject = entry_meta.get('subject') if entry_meta else 'General'
    video = {
        'stream_url': stream_url,
        'title': title,
        'description': description,
        'subject': subject,
        'category': entry_meta.get('category', 'General') if entry_meta else 'General',
        'folder': entry_meta.get('folder', 'General') if entry_meta else 'General',
        'views': entry_meta.get('views', 0) if entry_meta else 0,
        'date': entry_meta.get('date', '') if entry_meta else '',
        'player_url': f"{request.url_root.rstrip('/')}/player/{token}",
    }
    return render_template('player.html', video=video)


def start_bot_process():
    """Start the safe_repo bot.

    Guard against double-start: if another instance of the bot is already
    running (e.g. a separate Render worker using the same BOT_TOKEN), two
    Pyrogram clients would log in to the same bot and Telegram returns a
    409 Conflict, making the bot stop responding.

    NOTE: we use a lock file instead of `pgrep` because minimal Docker images
    (e.g. Render's python:3.10-slim) do not ship `pgrep`, which previously
    crashed this launcher with FileNotFoundError.
    """
    import subprocess
    import time
    import os
    import signal

    lock_file = "/tmp/safe_repo_bot.lock"

    # If a bot process is already running (lock file with a live PID), do not
    # spawn a second one.
    if os.path.exists(lock_file):
        try:
            with open(lock_file) as f:
                old_pid = int(f.read().strip())
            # Check if that PID is still alive (works without pgrep)
            os.kill(old_pid, 0)
            print(f"safe_repo bot already running (pid {old_pid}); "
                  "not starting a duplicate.")
            return
        except (ValueError, ProcessLookupError, PermissionError):
            # Stale lock file - remove it and continue
            try:
                os.remove(lock_file)
            except Exception:
                pass
        except Exception:
            try:
                os.remove(lock_file)
            except Exception:
                pass

    try:
        # Write our PID to the lock file
        with open(lock_file, "w") as f:
            f.write(str(os.getpid()))

        print("Starting safe_repo bot process...")
        # Explicitly pass environment to subprocess to ensure RENDER_EXTERNAL_URL and other vars are inherited
        bot_proc = subprocess.Popen(["python3", "-m", "safe_repo"], env=os.environ.copy())
        bot_proc.wait()
        print(f"safe_repo exited with code {bot_proc.returncode}")
    except Exception as e:
        print(f"safe_repo launcher error: {e}")
    finally:
        # Clean up lock file on exit
        try:
            if os.path.exists(lock_file):
                os.remove(lock_file)
        except Exception:
            pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    # Start bot process in background for all environments
    # This ensures both Flask app (health check) and bot are running
    bot_thread = threading.Thread(target=start_bot_process, daemon=True)
    bot_thread.start()

    # Determine the app URL for auto-ping
    # For Render, the URL will be provided in the RENDER_EXTERNAL_URL environment variable
    if 'RENDER_EXTERNAL_URL' in os.environ:
        APP_URL = os.environ['RENDER_EXTERNAL_URL']
        print(f"App URL: {APP_URL}")

        # Start auto-ping background task
        if AUTO_PING_ENABLED:
            ping_thread = threading.Thread(target=auto_ping, daemon=True)
            ping_thread.start()
            print(f"Auto-ping service started (interval: {AUTO_PING_INTERVAL} seconds)")

    # Always start Flask app to provide health check endpoint
    print(f"Starting Flask app on port {port}")
    register_api_routes(app)
    app.run(host='0.0.0.0', port=port)
