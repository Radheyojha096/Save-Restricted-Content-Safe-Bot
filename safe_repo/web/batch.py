import os
import json
import uuid
import zipfile
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from safe_repo.core.media_links import get_stream_file, _get_cache_dir

MONGO_DIR = Path(__file__).resolve().parent.parent / "core" / "mongo"
BATCH_JOBS_PATH = MONGO_DIR / "batch_jobs.json"
BATCH_TEMP_DIR = MONGO_DIR / "batch_temp"
MAX_CONCURRENT_JOBS = 3
JOB_TTL_HOURS = 1


def _read_jobs() -> Dict[str, Any]:
    if not BATCH_JOBS_PATH.exists():
        return {}
    try:
        data = json.loads(BATCH_JOBS_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _write_jobs(jobs: Dict[str, Any]) -> None:
    BATCH_JOBS_PATH.parent.mkdir(parents=True, exist_ok=True)
    BATCH_JOBS_PATH.write_text(json.dumps(jobs, indent=2, ensure_ascii=False), encoding="utf-8")


def _cleanup_old_jobs() -> None:
    jobs = _read_jobs()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=JOB_TTL_HOURS)
    to_remove = []
    for job_id, job in jobs.items():
        try:
            created = datetime.fromisoformat(job.get("created_at", ""))
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if created < cutoff:
                to_remove.append(job_id)
        except Exception:
            to_remove.append(job_id)
    for job_id in to_remove:
        job = jobs.get(job_id, {})
        zip_path = job.get("zip_path")
        if zip_path and os.path.exists(zip_path):
            try:
                os.remove(zip_path)
            except Exception:
                pass
        jobs.pop(job_id, None)
    if to_remove:
        _write_jobs(jobs)


def _enforce_concurrency_limit() -> None:
    jobs = _read_jobs()
    active = [j for j in jobs.values() if j.get("status") in ("pending", "processing")]
    if len(active) >= MAX_CONCURRENT_JOBS:
        raise ValueError(f"Maximum {MAX_CONCURRENT_JOBS} concurrent batch jobs allowed")


def _get_stream_path(token: str) -> Optional[str]:
    entry = get_stream_file(token)
    if not entry:
        return None
    return entry.get("file_path")


def _download_file(token: str, dest_dir: Path) -> Optional[str]:
    src = _get_stream_path(token)
    if not src or not os.path.exists(src):
        return None
    filename = os.path.basename(src)
    dest = dest_dir / filename
    shutil.copy2(src, dest)
    return str(dest)


def create_batch_job(tokens: List[str], job_name: str = "") -> Dict[str, Any]:
    _cleanup_old_jobs()
    _enforce_concurrency_limit()

    job_id = uuid.uuid4().hex
    temp_dir = BATCH_TEMP_DIR / job_id
    temp_dir.mkdir(parents=True, exist_ok=True)

    job = {
        "job_id": job_id,
        "name": job_name or f"Batch {job_id[:8]}",
        "status": "processing",
        "tokens": tokens,
        "total": len(tokens),
        "completed": 0,
        "failed": 0,
        "zip_path": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    jobs = _read_jobs()
    jobs[job_id] = job
    _write_jobs(jobs)

    downloaded = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(_download_file, token, temp_dir): token for token in tokens}
        for future in as_completed(futures):
            token = futures[future]
            try:
                result = future.result()
                if result:
                    downloaded.append(result)
                    job["completed"] = job.get("completed", 0) + 1
                else:
                    job["failed"] = job.get("failed", 0) + 1
            except Exception:
                job["failed"] = job.get("failed", 0) + 1
            job["updated_at"] = datetime.now(timezone.utc).isoformat()
            jobs[job_id] = job
            _write_jobs(jobs)

    zip_path = str(BATCH_TEMP_DIR / f"{job_id}.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in downloaded:
            zf.write(file_path, os.path.basename(file_path))

    job["status"] = "completed"
    job["zip_path"] = zip_path
    job["updated_at"] = datetime.now(timezone.utc).isoformat()
    jobs[job_id] = job
    _write_jobs(jobs)

    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass

    return job


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    jobs = _read_jobs()
    return jobs.get(job_id)


def get_job_zip_path(job_id: str) -> Optional[str]:
    job = get_job_status(job_id)
    if not job:
        return None
    zip_path = job.get("zip_path")
    if not zip_path or not os.path.exists(zip_path):
        return None
    return zip_path


def cleanup_expired() -> None:
    _cleanup_old_jobs()
    try:
        if BATCH_TEMP_DIR.exists():
            for item in BATCH_TEMP_DIR.iterdir():
                if item.is_file() and item.suffix == ".zip":
                    try:
                        mtime = datetime.fromtimestamp(item.stat().st_mtime, tz=timezone.utc)
                        if mtime < datetime.now(timezone.utc) - timedelta(hours=JOB_TTL_HOURS):
                            item.unlink(missing_ok=True)
                    except Exception:
                        pass
    except Exception:
        pass
