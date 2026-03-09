"""
Lightweight in-memory job tracker for long-running background operations.

Usage:
    job_id = jobs.start("bulk_price_update")
    jobs.update(job_id, progress=5, total=100)
    jobs.finish(job_id, success=5, failed=0)

    # In an API endpoint:
    status = jobs.get(job_id)   # {"id", "name", "state", "progress", "total", ...}
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional


JobState = Literal["running", "done", "error"]

_store: Dict[str, Dict[str, Any]] = {}
# Keep only the last N completed jobs to avoid unbounded memory growth
_MAX_COMPLETED = 20


def start(name: str, total: int = 0) -> str:
    job_id = uuid.uuid4().hex
    _store[job_id] = {
        "id": job_id,
        "name": name,
        "state": "running",
        "progress": 0,
        "total": total,
        "success": 0,
        "failed": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": None,
        "error": None,
    }
    return job_id


def update(job_id: str, *, progress: int, total: Optional[int] = None) -> None:
    job = _store.get(job_id)
    if not job:
        return
    job["progress"] = progress
    if total is not None:
        job["total"] = total


def finish(job_id: str, *, success: int, failed: int) -> None:
    job = _store.get(job_id)
    if not job:
        return
    job["state"] = "done"
    job["success"] = success
    job["failed"] = failed
    job["progress"] = job.get("total", 0)
    job["finished_at"] = datetime.now(timezone.utc).isoformat()
    _prune()


def fail(job_id: str, *, message: str) -> None:
    job = _store.get(job_id)
    if not job:
        return
    job["state"] = "error"
    job["error"] = message
    job["finished_at"] = datetime.now(timezone.utc).isoformat()
    _prune()


def get(job_id: str) -> Optional[Dict[str, Any]]:
    return _store.get(job_id)


def list_active() -> list:
    return [j for j in _store.values() if j["state"] == "running"]


def _prune() -> None:
    """Remove oldest completed jobs when we exceed the limit."""
    completed = [j for j in _store.values() if j["state"] != "running"]
    completed.sort(key=lambda j: j.get("finished_at") or "", reverse=True)
    for job in completed[_MAX_COMPLETED:]:
        _store.pop(job["id"], None)
