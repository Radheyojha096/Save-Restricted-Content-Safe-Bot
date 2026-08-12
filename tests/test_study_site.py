import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import safe_repo.core.media_links as media_links
from app import app as flask_app
from safe_repo.web.study import build_public_study_url, build_video_index, load_catalog_entries


def test_load_catalog_entries_normalizes_video_metadata(tmp_path):
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps([
        {
            "token": "abc123",
            "title": "Motion Chapter 1",
            "description": "Study video",
            "subject": "Physics",
            "category": "Class 11",
            "player_url": "https://example.com/player/abc123",
            "stream_url": "https://example.com/stream/abc123",
            "timestamp": "2026-08-02 10:00:00"
        }
    ]), encoding="utf-8")

    entries = load_catalog_entries(str(catalog_path))
    assert len(entries) == 1
    assert entries[0]["watch_url"].endswith("/watch/abc123")
    assert entries[0]["subject"] == "Physics"
    assert entries[0]["category"] == "Class 11"


def test_home_route_renders_filtered_catalog_for_subject_date_queries(monkeypatch, tmp_path):
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps([
        {
            "token": "one",
            "title": "Alpha",
            "description": "Folder: Mechanics\nStudy video",
            "subject": "Physics",
            "category": "Class 11",
            "player_url": "https://example.com/player/one",
            "stream_url": "https://example.com/stream/one",
            "timestamp": "2026-08-02 10:00:00",
            "date": "2026-08-02"
        }
    ]), encoding="utf-8")
    monkeypatch.setenv("STREAM_CATALOG_FILE", str(catalog_path))

    client = flask_app.test_client()
    response = client.get("/?subject=Physics&date=2026-08-02&q=Alpha")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Showing results for" in html
    assert "Physics" in html
    assert "Alpha" in html


def test_build_video_index_groups_latest_and_featured(tmp_path):
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps([
        {
            "token": "one",
            "title": "Alpha",
            "description": "A",
            "subject": "Physics",
            "category": "Class 11",
            "player_url": "https://example.com/player/one",
            "stream_url": "https://example.com/stream/one",
            "timestamp": "2026-08-02 10:00:00",
            "featured": True,
            "trending": True,
            "views": 12
        },
        {
            "token": "two",
            "title": "Beta",
            "description": "B",
            "subject": "Chemistry",
            "category": "Class 12",
            "player_url": "https://example.com/player/two",
            "stream_url": "https://example.com/stream/two",
            "timestamp": "2026-08-02 11:00:00",
            "views": 5
        }
    ]), encoding="utf-8")

    index = build_video_index(str(catalog_path))
    assert index["featured"][0]["token"] == "one"
    assert index["latest"][0]["token"] == "two"
    assert index["trending"][0]["token"] == "one"
    assert index["subjects"][0]["name"] == "Physics"


def test_build_video_index_filters_by_subject_and_date(tmp_path):
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps([
        {
            "token": "one",
            "title": "Alpha",
            "description": "A",
            "subject": "Physics",
            "category": "Class 11",
            "player_url": "https://example.com/player/one",
            "stream_url": "https://example.com/stream/one",
            "timestamp": "2026-08-02 10:00:00",
            "date": "2026-08-02"
        },
        {
            "token": "two",
            "title": "Beta",
            "description": "B",
            "subject": "Chemistry",
            "category": "Class 12",
            "player_url": "https://example.com/player/two",
            "stream_url": "https://example.com/stream/two",
            "timestamp": "2026-08-03 11:00:00",
            "date": "2026-08-03"
        }
    ]), encoding="utf-8")

    index = build_video_index(str(catalog_path), subject="Physics", date="2026-08-02")
    assert [video["token"] for video in index["videos"]] == ["one"]
    assert index["filter_summary"]["subject"] == "Physics"
    assert index["filter_summary"]["date"] == "2026-08-02"


def test_build_public_study_url_includes_filters():
    url = build_public_study_url("https://example.com", subject="Physics", date="2026-08-02", q="motion")
    assert url == "https://example.com/study?subject=Physics&date=2026-08-02&q=motion"


def test_build_public_study_url_defaults_to_home_page_when_no_filters():
    url = build_public_study_url("https://example.com")
    assert url == "https://example.com/"


def test_append_stream_link_is_visible_to_study_catalog_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv("STREAM_CATALOG_FILE", raising=False)
    monkeypatch.setattr(media_links, "_STREAM_CACHE_DIR", str(tmp_path / "cache"))

    catalog_path = Path("safe_repo/core/mongo/stream_catalog.json")
    backup_text = catalog_path.read_text(encoding="utf-8") if catalog_path.exists() else None

    try:
        media_links.append_stream_link(
            "https://example.com/player/test",
            "https://example.com/stream/test",
            subject="Physics",
            description="Forwarded task media",
            title="Task Media",
            token="task-token",
        )
        entries = load_catalog_entries()
        assert any(entry.get("token") == "task-token" for entry in entries)
    finally:
        if backup_text is None:
            catalog_path.unlink(missing_ok=True)
        else:
            catalog_path.write_text(backup_text, encoding="utf-8")


def test_build_video_index_groups_videos_by_folder_from_description(tmp_path):
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps([
        {
            "token": "one",
            "title": "Alpha",
            "description": "Folder: Mechanics\nStudy video",
            "subject": "Physics",
            "category": "Class 11",
            "player_url": "https://example.com/player/one",
            "stream_url": "https://example.com/stream/one",
            "timestamp": "2026-08-02 10:00:00",
            "date": "2026-08-02"
        }
    ]), encoding="utf-8")

    index = build_video_index(str(catalog_path))
    assert index["folders"][0]["name"] == "Mechanics"
    assert index["folders"][0]["count"] == 1


def test_build_video_index_exposes_subject_playlists(tmp_path):
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps([
        {
            "token": "one",
            "title": "Alpha",
            "description": "Folder: Mechanics\nA",
            "subject": "Physics",
            "category": "Class 11",
            "player_url": "https://example.com/player/one",
            "stream_url": "https://example.com/stream/one",
            "timestamp": "2026-08-02 10:00:00",
            "date": "2026-08-02"
        },
        {
            "token": "two",
            "title": "Beta",
            "description": "Folder: Mechanics\nB",
            "subject": "Physics",
            "category": "Class 11",
            "player_url": "https://example.com/player/two",
            "stream_url": "https://example.com/stream/two",
            "timestamp": "2026-08-03 10:00:00",
            "date": "2026-08-03"
        }
    ]), encoding="utf-8")

    index = build_video_index(str(catalog_path))
    assert index["playlists"][0]["subject"] == "Physics"
    assert index["playlists"][0]["folder"] == "Mechanics"
    assert len(index["playlists"][0]["videos"]) == 2


def test_build_video_index_filters_by_folder(tmp_path):
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps([
        {
            "token": "one",
            "title": "Alpha",
            "description": "Folder: Mechanics\nA",
            "subject": "Physics",
            "category": "Class 11",
            "player_url": "https://example.com/player/one",
            "stream_url": "https://example.com/stream/one",
            "timestamp": "2026-08-02 10:00:00",
            "date": "2026-08-02"
        },
        {
            "token": "two",
            "title": "Beta",
            "description": "Folder: Waves\nB",
            "subject": "Physics",
            "category": "Class 11",
            "player_url": "https://example.com/player/two",
            "stream_url": "https://example.com/stream/two",
            "timestamp": "2026-08-03 10:00:00",
            "date": "2026-08-03"
        }
    ]), encoding="utf-8")

    index = build_video_index(str(catalog_path), subject="Physics", folder="Mechanics")
    assert [video["token"] for video in index["videos"]] == ["one"]
