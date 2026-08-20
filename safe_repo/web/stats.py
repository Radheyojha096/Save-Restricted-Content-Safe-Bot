import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from safe_repo.web.study import load_catalog_entries

MONGO_DIR = Path(__file__).resolve().parent.parent / "core" / "mongo"
STATS_CACHE_PATH = MONGO_DIR / "stats_cache.json"
CACHE_TTL_SECONDS = 300


def _read_cache() -> Optional[Dict[str, Any]]:
    if not STATS_CACHE_PATH.exists():
        return None
    try:
        data = json.loads(STATS_CACHE_PATH.read_text(encoding="utf-8"))
        cached_at = data.get("cached_at")
        if cached_at:
            cached_time = datetime.fromisoformat(cached_at)
            if cached_time.tzinfo is None:
                cached_time = cached_time.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) - cached_time < timedelta(seconds=CACHE_TTL_SECONDS):
                return data.get("data")
    except Exception:
        pass
    return None


def _write_cache(data: Dict[str, Any]) -> None:
    STATS_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
    STATS_CACHE_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _parse_date(date_str: str) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return None


def compute_stats(catalog_path: Optional[str] = None) -> Dict[str, Any]:
    cached = _read_cache()
    if cached is not None:
        return cached

    videos = load_catalog_entries(catalog_path)
    now = datetime.now(timezone.utc)

    daily: Dict[str, int] = defaultdict(int)
    weekly: Dict[str, int] = defaultdict(int)
    monthly: Dict[str, int] = defaultdict(int)
    subject_counts: Dict[str, int] = defaultdict(int)
    category_counts: Dict[str, int] = defaultdict(int)
    folder_counts: Dict[str, int] = defaultdict(int)
    total_views = 0
    featured_count = 0
    trending_count = 0

    for video in videos:
        date_str = str(video.get("date") or "")
        dt_obj = _parse_date(date_str)
        if dt_obj:
            daily[date_str] += 1
            weekly[dt_obj.strftime("%Y-W%W")] += 1
            monthly[dt_obj.strftime("%Y-%m")] += 1

        subject = str(video.get("subject") or "General")
        category = str(video.get("category") or "General")
        folder = str(video.get("folder") or "General")
        subject_counts[subject] += 1
        category_counts[category] += 1
        folder_counts[folder] += 1

        total_views += int(video.get("views") or 0)
        if video.get("featured"):
            featured_count += 1
        if video.get("trending"):
            trending_count += 1

    popular = sorted(videos, key=lambda v: (int(v.get("views") or 0), v.get("timestamp", "")), reverse=True)[:20]

    stats = {
        "total_videos": len(videos),
        "total_views": total_views,
        "featured_count": featured_count,
        "trending_count": trending_count,
        "daily": sorted([{"date": k, "count": v} for k, v in daily.items()], key=lambda x: x["date"]),
        "weekly": sorted([{"week": k, "count": v} for k, v in weekly.items()], key=lambda x: x["week"]),
        "monthly": sorted([{"month": k, "count": v} for k, v in monthly.items()], key=lambda x: x["month"]),
        "subjects": sorted([{"name": k, "count": v} for k, v in subject_counts.items()], key=lambda x: (-x["count"], x["name"])),
        "categories": sorted([{"name": k, "count": v} for k, v in category_counts.items()], key=lambda x: (-x["count"], x["name"])),
        "folders": sorted([{"name": k, "count": v} for k, v in folder_counts.items()], key=lambda x: (-x["count"], x["name"])),
        "popular_videos": [
            {
                "token": v.get("token"),
                "title": v.get("title"),
                "subject": v.get("subject"),
                "views": int(v.get("views") or 0),
            }
            for v in popular
        ],
        "generated_at": now.isoformat(),
    }

    _write_cache(stats)
    return stats


def get_dashboard_data(catalog_path: Optional[str] = None]) -> Dict[str, Any]:
    stats = compute_stats(catalog_path)
    videos = load_catalog_entries(catalog_path)

    latest = sorted(videos, key=lambda v: v.get("timestamp", ""), reverse=True)[:10]
    featured = [v for v in videos if v.get("featured")][:10]
    trending = sorted([v for v in videos if v.get("trending") or v.get("views", 0) > 0], key=lambda v: (v.get("views", 0), v.get("timestamp", "")), reverse=True)[:10]

    return {
        "overview": {
            "total_videos": stats["total_videos"],
            "total_views": stats["total_views"],
            "featured_count": stats["featured_count"],
            "trending_count": stats["trending_count"],
        },
        "charts": {
            "daily": stats["daily"][-30:],
            "subjects": stats["subjects"],
            "categories": stats["categories"],
            "folders": stats["folders"],
        },
        "popular": stats["popular_videos"],
        "latest": [
            {
                "token": v.get("token"),
                "title": v.get("title"),
                "subject": v.get("subject"),
                "date": v.get("date"),
            }
            for v in latest
        ],
        "featured": [
            {
                "token": v.get("token"),
                "title": v.get("title"),
                "subject": v.get("subject"),
            }
            for v in featured
        ],
        "trending": [
            {
                "token": v.get("token"),
                "title": v.get("title"),
                "subject": v.get("subject"),
                "views": int(v.get("views") or 0),
            }
            for v in trending
        ],
    }
