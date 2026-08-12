import os
import time
import threading
import mimetypes
import requests
from flask import Flask, send_file, abort, redirect, request, render_template_string
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

    return render_template_string("""
    <html>
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>StudyHub by Safe Repo</title>
        <style>
          :root { color-scheme: dark; }
          body { margin:0; font-family:Inter, Arial, sans-serif; background:linear-gradient(135deg,#020617,#111827 50%,#0f172a); color:#f8fafc; }
          .wrap { max-width: 1280px; margin:0 auto; padding:24px; }
          .topbar { position:sticky; top:0; z-index:20; display:flex; justify-content:space-between; align-items:center; padding:12px 16px; margin:0 auto 16px; max-width:1280px; border-radius:999px; background:rgba(2,6,23,0.75); border:1px solid rgba(148,163,184,0.25); backdrop-filter:blur(12px); }
          .topbar a { color:white; text-decoration:none; margin-right:12px; font-weight:600; }
          .topbar .right { display:flex; align-items:center; gap:10px; }
          .theme-toggle { border:none; border-radius:999px; padding:8px 10px; background:#2563eb; color:white; cursor:pointer; }
          .hero { padding:32px; border-radius:24px; background:linear-gradient(135deg,#1d4ed8,#0f766e); box-shadow:0 20px 45px rgba(0,0,0,0.25); }
          .hero h1 { margin:0 0 8px; font-size:2rem; }
          .hero p { color:#e2e8f0; margin:0 0 16px; }
          .search-box { display:flex; gap:10px; flex-wrap:wrap; margin-top:14px; }
          .search-box input { flex:1; min-width:220px; padding:12px 14px; border-radius:999px; border:1px solid rgba(255,255,255,0.25); background:rgba(255,255,255,0.16); color:white; }
          .search-box button { padding:12px 16px; border-radius:999px; border:none; background:#fff; color:#0f172a; font-weight:700; }
          .stats { display:grid; gap:16px; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); margin-top:18px; }
          .card { background:rgba(15,23,42,0.86); border:1px solid rgba(148,163,184,0.2); border-radius:18px; padding:16px; backdrop-filter:blur(8px); }
          .pill { display:inline-block; background:linear-gradient(135deg,#2563eb,#0ea5e9); padding:6px 10px; border-radius:999px; font-size:0.8rem; margin-right:6px; margin-bottom:6px; font-weight:600; }
          .muted { color:#94a3b8; font-size:0.92rem; }
          .featured { display:grid; gap:14px; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); margin-top:16px; }
          .featured-card { padding:16px; background:linear-gradient(135deg,#111827,#0f172a); border:1px solid rgba(148,163,184,0.2); border-radius:18px; }
          .thumb { height:136px; border-radius:14px; display:flex; align-items:center; justify-content:center; font-size:1.3rem; font-weight:700; color:white; margin-bottom:12px; background:linear-gradient(135deg,#7c3aed,#2563eb); }
          .section { margin-top:24px; }
          .subject-banner { padding:16px 18px; border-radius:16px; background:linear-gradient(135deg,#111827,#1e293b); border:1px solid rgba(148,163,184,0.2); margin-bottom:14px; display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; }
          .subject-banner a { color:#93c5fd; text-decoration:none; font-weight:600; }
          .video-grid { display:grid; gap:14px; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); }
          .video-item { display:flex; flex-direction:column; gap:10px; padding:14px; background:#111827; border:1px solid rgba(148,163,184,0.2); border-radius:14px; min-height:190px; }
          .actions a { color:#93c5fd; text-decoration:none; margin-right:8px; }
          a { color:#93c5fd; }
          .theme-note { font-size:0.84rem; color:#cbd5e1; margin-top:6px; }
          body[data-theme="light"] { background:#f8fafc; color:#0f172a; }
          body[data-theme="light"] .card,
          body[data-theme="light"] .featured-card,
          body[data-theme="light"] .video-item,
          body[data-theme="light"] .subject-banner,
          body[data-theme="light"] .hero { background:#ffffff; color:#0f172a; border-color:#dbeafe; }
          body[data-theme="light"] .muted { color:#475569; }
          body[data-theme="light"] .topbar { background:rgba(255,255,255,0.9); border-color:#dbeafe; }
          body[data-theme="light"] .topbar a { color:#0f172a; }
        </style>
      </head>
      <body>
        <div class="topbar">
          <div><strong>StudyHub</strong></div>
          <div class="right">
            <a href="/">Home</a>
            <a href="/study">Study</a>
            <button class="theme-toggle" type="button" onclick="toggleTheme()">☀️</button>
          </div>
        </div>
        <div class="wrap">
          <div class="hero">
            <h1>StudyHub by Safe Repo</h1>
            <p>Premium study videos, subject-wise playlists, and instant public playback links from the same media archive.</p>
            {% if filter_summary.subject or filter_summary.date or filter_summary.q or filter_summary.folder %}
            <div class="theme-note" style="margin-bottom:10px;">Showing results for: {% if filter_summary.subject %}subject={{ filter_summary.subject }}{% endif %}{% if filter_summary.folder %} · folder={{ filter_summary.folder }}{% endif %}{% if filter_summary.date %} · date={{ filter_summary.date }}{% endif %}{% if filter_summary.q %} · search={{ filter_summary.q }}{% endif %}</div>
            {% endif %}
            <form class="search-box" action="/" method="get" style="margin-top:14px;">
              <input type="text" name="q" value="{{ request.args.get('q','') }}" placeholder="Search chapters, topics, or subjects" />
              <input type="text" name="subject" value="{{ request.args.get('subject','') }}" placeholder="Subject" />
              <input type="text" name="folder" value="{{ request.args.get('folder','') }}" placeholder="Folder" />
              <input type="text" name="date" value="{{ request.args.get('date','') }}" placeholder="Date (YYYY-MM-DD)" />
              <button type="submit">Apply</button>
              <a href="/" style="padding:12px 16px; border-radius:999px; border:none; background:rgba(255,255,255,0.14); color:white; text-decoration:none; font-weight:700;">Clear</a>
            </form>
            <div class="stats">
              <div class="card">
                <div><strong>{{ videos|length }}</strong></div>
                <div class="muted">Saved study videos</div>
              </div>
              <div class="card">
                <div><strong>{{ subjects|length }}</strong></div>
                <div class="muted">Subject categories</div>
              </div>
              <div class="card">
                <div><strong>{{ featured|length }}</strong></div>
                <div class="muted">Featured picks</div>
              </div>
            </div>
          </div>

          <div class="section">
            <h2>Featured</h2>
            <div class="featured">
              {% if featured %}
                {% for item in featured %}
                  <div class="featured-card">
                    <div class="thumb">{{ (item.subject or 'Study')[:2].upper() }}</div>
                    <strong>{{ item.title }}</strong>
                    <div class="muted">{{ item.subject }} · {{ item.category }}</div>
                    <div class="theme-note">Popular pick for quick revision and revision notes.</div>
                    <div class="actions" style="margin-top:10px;">
                      <a href="{{ item.watch_url }}">Watch</a>
                      <a href="{{ item.player_url }}">Player</a>
                    </div>
                  </div>
                {% endfor %}
              {% else %}
                <div class="card">No featured videos yet.</div>
              {% endif %}
            </div>
          </div>

          {% if playlists %}
            <div class="section">
              <h2>Subject playlists</h2>
              <div class="video-grid">
                {% for playlist in playlists %}
                  <div class="video-item">
                    <div class="thumb">{{ playlist.subject[:2].upper() }}</div>
                    <div>
                      <strong>{{ playlist.subject }}</strong>
                      <div class="muted">{{ playlist.videos|length }} videos ready for quick study</div>
                    </div>
                    <div class="actions">
                      <a href="/study?subject={{ playlist.subject|urlencode }}&folder={{ playlist.folder|urlencode }}">Open playlist</a>
                    </div>
                  </div>
                {% endfor %}
              </div>
            </div>
          {% endif %}

          {% if subjects %}
            {% for subject in subjects %}
              {% set subject_videos = [] %}
              {% for item in videos if item.subject == subject.name %}
                {% set _ = subject_videos.append(item) %}
              {% endfor %}
              {% if subject_videos %}
                <div class="section">
                  <div class="subject-banner">
                    <div>
                      <h3 style="margin:0 0 6px;">{{ subject.name }}</h3>
                      <div class="muted">{{ subject_videos|length }} videos • curated for focused study</div>
                    </div>
                    <a href="/study?subject={{ subject.name|urlencode }}">Open {{ subject.name }} page</a>
                  </div>
                  <div class="video-grid">
                    {% for item in subject_videos[:6] %}
                      <div class="video-item">
                        <div class="thumb">{{ subject.name[:2].upper() }}</div>
                        <div>
                          <strong>{{ item.title }}</strong>
                          <div class="muted">{{ (item.description or 'Study video')[:120] }}{% if item.description and item.description|length > 120 %}...{% endif %}</div>
                        </div>
                        <div class="actions">
                          <a href="{{ item.watch_url }}">Watch</a>
                          <a href="{{ item.player_url }}">Player</a>
                        </div>
                      </div>
                    {% endfor %}
                  </div>
                </div>
              {% endif %}
            {% endfor %}
          {% else %}
            <div class="section">
              <div class="card">No videos yet.</div>
            </div>
          {% endif %}
        </div>
        <script>
        function toggleTheme() {
          const body = document.body;
          const next = body.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
          body.setAttribute('data-theme', next);
          document.documentElement.style.colorScheme = next;
        }
        </script>
      </body>
    </html>
    """, videos=videos, featured=featured, latest=latest, trending=trending, subjects=subjects, playlists=playlists, filter_summary=filter_summary, request=request)


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

    return render_template_string("""
    <html>
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Study Platform</title>
        <style>
          body { margin:0; font-family:Inter, Arial, sans-serif; background:#0f172a; color:#f8fafc; }
          .wrap { max-width: 1200px; margin:0 auto; padding:24px; }
          .topbar { position:sticky; top:0; z-index:20; display:flex; justify-content:space-between; align-items:center; padding:12px 16px; margin:0 auto 16px; max-width:1200px; border-radius:999px; background:rgba(2,6,23,0.75); border:1px solid rgba(148,163,184,0.25); backdrop-filter:blur(12px); }
          .topbar a { color:white; text-decoration:none; margin-right:12px; font-weight:600; }
          .topbar .right { display:flex; align-items:center; gap:10px; }
          .theme-toggle { border:none; border-radius:999px; padding:8px 10px; background:#2563eb; color:white; cursor:pointer; }
          .hero { padding:28px; border-radius:24px; background:linear-gradient(135deg,#1d4ed8,#2563eb); box-shadow:0 20px 45px rgba(0,0,0,0.24); }
          .grid { display:grid; gap:16px; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); margin-top:16px; }
          .card { background:#111827; border:1px solid #334155; border-radius:18px; padding:16px; }
          .card h3 { margin-top:0; }
          .pill { display:inline-block; background:#1d4ed8; padding:4px 8px; border-radius:999px; font-size:0.8rem; margin:4px 4px 0 0; }
          .pill.secondary { background:#0f766e; }
          .list a { color:#93c5fd; text-decoration:none; display:block; padding:6px 0; border-bottom:1px solid #1f2937; }
          .list a:last-child { border-bottom:none; }
          .stat { font-size:1.2rem; font-weight:bold; }
          .muted { color:#94a3b8; font-size:0.92rem; }
          body[data-theme="light"] { background:#f8fafc; color:#0f172a; }
          body[data-theme="light"] .card,
          body[data-theme="light"] .hero { background:#ffffff; color:#0f172a; border-color:#dbeafe; }
          body[data-theme="light"] .muted { color:#475569; }
          body[data-theme="light"] .topbar { background:rgba(255,255,255,0.9); border-color:#dbeafe; }
          body[data-theme="light"] .topbar a { color:#0f172a; }
        </style>
      </head>
      <body>
        <div class="topbar">
          <div><strong>StudyHub</strong></div>
          <div class="right">
            <a href="/">Home</a>
            <a href="/study">Study</a>
            <button class="theme-toggle" type="button" onclick="toggleTheme()">☀️</button>
          </div>
        </div>
        <div class="wrap">
          <div class="hero">
            <h1>Study Platform</h1>
            <p>Browse videos by subject, folder, category, and recent uploads in one clean place.</p>
            <div class="muted" style="margin-top:8px;">Home / Study{% if filter_summary.subject %} / {{ filter_summary.subject }}{% endif %}</div>
            <form method="get" action="/study" style="margin-top:12px; display:flex; gap:8px; flex-wrap:wrap;">
              <input type="text" name="q" value="{{ request.args.get('q','') }}" placeholder="Search title / topic" style="padding:10px; border-radius:8px; border:1px solid #1d4ed8; min-width:220px;" />
              <input type="text" name="subject" value="{{ request.args.get('subject','') }}" placeholder="Subject" style="padding:10px; border-radius:8px; border:1px solid #1d4ed8; min-width:140px;" />
              <input type="text" name="folder" value="{{ request.args.get('folder','') }}" placeholder="Folder" style="padding:10px; border-radius:8px; border:1px solid #1d4ed8; min-width:140px;" />
              <input type="text" name="date" value="{{ request.args.get('date','') }}" placeholder="Date (YYYY-MM-DD)" style="padding:10px; border-radius:8px; border:1px solid #1d4ed8; min-width:160px;" />
              <button type="submit" style="padding:10px 14px; border-radius:8px; border:none; background:#0f172a; color:white;">Filter</button>
              <a href="/study" style="padding:10px 14px; border-radius:8px; background:#1d4ed8; color:white; text-decoration:none;">Clear</a>
            </form>
            {% if filter_summary.subject or filter_summary.date or filter_summary.q or filter_summary.folder %}
            <p style="margin-top:10px; color:#e2e8f0;">Showing results for: {% if filter_summary.subject %}subject={{ filter_summary.subject }}{% endif %}{% if filter_summary.folder %} · folder={{ filter_summary.folder }}{% endif %}{% if filter_summary.date %} · date={{ filter_summary.date }}{% endif %}{% if filter_summary.q %} · search={{ filter_summary.q }}{% endif %}</p>
            {% endif %}
          </div>
          <div class="card" style="margin-top:16px;">
            <h3>Subject playlists</h3>
            {% for playlist in playlists %}
              <a href="/study?subject={{ playlist.subject|urlencode }}&folder={{ playlist.folder|urlencode }}" class="pill" style="text-decoration:none; color:white;">{{ playlist.subject }} / {{ playlist.folder }} ({{ playlist.videos|length }})</a>
            {% endfor %}
          </div>
          <div class="grid">
            <div class="card">
              <h3>Subjects</h3>
              {% for subject in subjects %}
                <a href="/study?subject={{ subject.name|urlencode }}" class="pill" style="text-decoration:none; color:white;">{{ subject.name }} ({{ subject.count }})</a>
              {% endfor %}
            </div>
            <div class="card">
              <h3>Categories</h3>
              {% for category in categories %}
                <span class="pill secondary">{{ category.name }} ({{ category.count }})</span>
              {% endfor %}
            </div>
            <div class="card">
              <h3>Folders</h3>
              {% for folder in folders %}
                <span class="pill">{{ folder.name }} ({{ folder.count }})</span>
              {% endfor %}
            </div>
          </div>
          <div class="grid" style="margin-top:16px;">
            <div class="card">
              <h3>Videos</h3>
              <div class="list">
                {% for item in videos %}
                  <a href="{{ item.watch_url }}">
                    <strong>{{ item.title }}</strong>
                    <div class="muted">{{ item.subject }} · {{ item.folder or 'General' }}</div>
                    <div class="muted">▶ Watch now</div>
                  </a>
                {% endfor %}
              </div>
            </div>
            <div class="card">
              <h3>Featured</h3>
              <div class="list">
                {% for item in featured %}
                  <a href="{{ item.watch_url }}">
                    <strong>{{ item.title }}</strong>
                    <div class="muted">⭐ Featured · {{ item.subject }}</div>
                  </a>
                {% endfor %}
              </div>
            </div>
            <div class="card">
              <h3>Latest</h3>
              <div class="list">
                {% for item in latest %}
                  <a href="{{ item.watch_url }}">
                    <strong>{{ item.title }}</strong>
                    <div class="muted">🕒 {{ item.date or item.timestamp }}</div>
                  </a>
                {% endfor %}
              </div>
            </div>
            <div class="card">
              <h3>Trending</h3>
              <div class="list">
                {% for item in trending %}
                  <a href="{{ item.watch_url }}">
                    <strong>{{ item.title }}</strong>
                    <div class="muted">🔥 {{ item.views }} views</div>
                  </a>
                {% endfor %}
              </div>
            </div>
          </div>
        </div>
        <script>
        function toggleTheme() {
          const body = document.body;
          const next = body.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
          body.setAttribute('data-theme', next);
          document.documentElement.style.colorScheme = next;
        }
        </script>
      </body>
    </html>
    """, videos=videos, featured=featured, latest=latest, trending=trending, subjects=subjects, categories=categories, folders=folders, playlists=playlists, filter_summary=filter_summary, request=request)


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

    return render_template_string("""
    <html>
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>{{ video.title }}</title>
        <style>
          body { margin:0; font-family:Inter, Arial, sans-serif; background:#020617; color:#f8fafc; }
          .wrap { max-width: 980px; margin:0 auto; padding:24px; }
          .player { border-radius:18px; overflow:hidden; background:#111827; border:1px solid #334155; }
          video { width:100%; height:auto; display:block; background:#000; }
          .meta { padding:16px; background:#111827; border-top:1px solid #334155; }
          .pill { display:inline-block; background:#2563eb; padding:4px 8px; border-radius:999px; font-size:0.8rem; margin-right:6px; }
          a { color:#93c5fd; }
        </style>
      </head>
      <body>
        <div class="wrap">
          <div class="player">
            <video controls autoplay playsinline>
              <source src="{{ video.stream_url }}" />
            </video>
          </div>
          <div class="meta">
            <h1>{{ video.title }}</h1>
            <div>
              <span class="pill">{{ video.subject }}</span>
              <span class="pill">{{ video.category }}</span>
            </div>
            <p>{{ video.description or 'Study video from the Safe Repo media archive.' }}</p>
            <div style="display:flex; gap:8px; flex-wrap:wrap; margin:12px 0;">
              <a href="{{ video.player_url }}" target="_blank">Open player page</a>
              <a href="{{ video.stream_url }}" target="_blank">Open direct stream</a>
              <a href="{{ video.stream_url }}?download=1" target="_blank">Download</a>
              <a href="javascript:void(0);" onclick="copyLink()">Copy link</a>
            </div>
            {% if related_videos %}
            <div style="margin-top:10px;">
              <strong>More in this subject</strong>
              <ul>
                {% for item in related_videos %}
                <li><a href="/study/watch/{{ item.token }}">{{ item.title }}</a></li>
                {% endfor %}
              </ul>
            </div>
            {% endif %}
          </div>
        </div>
        <script>
          function copyLink() {
            navigator.clipboard.writeText(window.location.href).then(() => alert('Link copied'));
          }
        </script>
      </body>
    </html>
    """, video=video, related_videos=related_videos)


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

    return render_template_string("""
    <html>
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>LinkByRK Catalog</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 0; background: #0f172a; color: #f8fafc; }
          .wrap { max-width: 1100px; margin: 0 auto; padding: 24px; }
          .filters { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }
          input, select, button { padding: 8px 10px; border-radius: 6px; border: 1px solid #334155; background: #111827; color: #f8fafc; }
          .card { background: #111827; border: 1px solid #334155; border-radius: 12px; padding: 16px; margin-bottom: 14px; }
          .meta-line { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-bottom: 8px; }
          .topline { display: flex; justify-content: space-between; gap: 10px; flex-wrap: wrap; margin-bottom: 8px; }
          .pill { display: inline-block; background: #2563eb; color: white; padding: 4px 8px; border-radius: 999px; font-size: 0.8rem; }
          .actions a, .actions button { display: inline-block; margin-right: 8px; margin-top: 8px; color: #93c5fd; text-decoration: none; }
          .muted { color: #94a3b8; font-size: 0.95rem; }
          .desc { margin: 8px 0; color: #e2e8f0; }
        </style>
      </head>
      <body>
        <div class="wrap">
          <h1>LinkByRK Catalog</h1>
          <p class="muted">Browse links by subject, date, and description.</p>
          <form class="filters" method="get" action="/catalog">
            <input type="text" name="q" placeholder="Search title / subject / description" value="{{ request.args.get('q','') }}" />
            <select name="subject">
              <option value="">All subjects</option>
              {% for subject in subjects %}
              <option value="{{ subject }}" {% if subject_filter == subject %}selected{% endif %}>{{ subject }}</option>
              {% endfor %}
            </select>
            <select name="date">
              <option value="">All dates</option>
              {% for date in dates %}
              <option value="{{ date }}" {% if date_filter == date %}selected{% endif %}>{{ date }}</option>
              {% endfor %}
            </select>
            <button type="submit">Filter</button>
            <a href="/catalog" style="color:#93c5fd; padding: 8px 0;">Clear</a>
          </form>
          {% if filtered %}
            {% for entry in filtered %}
            <div class="card">
              <div class="topline">
                <div>
                  <strong>{{ entry.title or entry.subject or 'Untitled' }}</strong>
                  <div class="meta-line">
                    <span class="pill">{{ entry.subject or 'General' }}</span>
                    <span class="muted">{{ entry.date }} · {{ entry.timestamp }}</span>
                  </div>
                </div>
              </div>
              {% if entry.description %}<div class="desc">{{ entry.description }}</div>{% endif %}
              <div class="actions">
                <a href="{{ entry.player_url }}" target="_blank">▶ Open Player</a>
                <a href="{{ entry.stream_url }}" target="_blank">🔗 Open Direct Link</a>
                <button onclick="navigator.clipboard.writeText('{{ entry.stream_url }}')">📋 Copy Stream</button>
                <button onclick="navigator.clipboard.writeText('{{ entry.player_url }}')">📋 Copy Player</button>
              </div>
            </div>
            {% endfor %}
          {% else %}
            <div class="card">No links yet.</div>
          {% endif %}
        </div>
      </body>
    </html>
    """, subjects=subjects, dates=dates, filtered=filtered, subject_filter=subject_filter, date_filter=date_filter)


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
    html = f"""
    <html>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>{title}</title>
        <style>
          body {{ margin:0; background:#000; color:#fff; font-family:Arial,sans-serif; }}
          .wrap {{ min-height:100vh; display:flex; flex-direction:column; justify-content:center; align-items:center; padding:16px; box-sizing:border-box; }}
          .box {{ width:100%; max-width:900px; background:#111; border-radius:12px; overflow:hidden; box-shadow:0 10px 30px rgba(0,0,0,0.4); }}
          .top {{ padding:12px 16px; background:#1a1a1a; display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; }}
          .controls {{ display:flex; gap:8px; flex-wrap:wrap; align-items:center; }}
          select, button {{ border:none; border-radius:6px; padding:6px 10px; background:#222; color:#fff; }}
          video {{ width:100%; height:auto; background:#000; display:block; }}
          a {{ color:#4da3ff; text-decoration:none; }}
          .small {{ font-size:0.85rem; color:#aaa; }}
          .meta {{ padding: 12px 16px; background:#0f172a; color:#e2e8f0; }}
        </style>
      </head>
      <body>
        <div class="wrap">
          <div class="box">
            <div class="top">
              <div>
                <div>🎬 {title}</div>
                <div class="small">Subject: {subject}</div>
              </div>
              <div class="controls">
                <select id="speed">
                  <option value="1">1x</option>
                  <option value="1.25">1.25x</option>
                  <option value="1.5">1.5x</option>
                  <option value="2">2x</option>
                  <option value="4">4x</option>
                </select>
                <a href="{stream_url}" target="_blank">Open Direct Link</a>
                <a href="javascript:void(0);" onclick="window.open('{stream_url}', 'streamPopup', 'width=900,height=600');">Popup Player</a>
                <a href="{stream_url}?download=1" target="_blank">Download</a>
                <button onclick="navigator.clipboard.writeText('{stream_url}')">Copy Stream</button>
              </div>
            </div>
            <div class="meta">
              <div><strong>Description:</strong> {description}</div>
            </div>
            <video id="player" controls autoplay playsinline>
              <source src="{stream_url}" />
            </video>
          </div>
        </div>
        <script>
          const player = document.getElementById('player');
          const speedSelect = document.getElementById('speed');
          speedSelect.addEventListener('change', () => {{ player.playbackRate = parseFloat(speedSelect.value); }});
        </script>
      </body>
    </html>
    """
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


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
        bot_proc = subprocess.Popen(["python3", "-m", "safe_repo"])
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
    app.run(host='0.0.0.0', port=port)
