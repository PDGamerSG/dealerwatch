"""Bounded background investigations with durable state and restart recovery."""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

log = logging.getLogger(__name__)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class BusyError(ValueError):
    """Another operation owns the active dataset or investigation runner."""


class RunManager:
    """One in-process worker, no unbounded queue; one app worker per runtime directory."""

    def __init__(self, runtime: Path, execute: Callable[..., Any]):
        runtime.mkdir(parents=True, exist_ok=True)
        self.path = runtime / "jobs.db"
        self.execute = execute
        self.lock = threading.Lock()
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="dealerwatch-run")
        self._closed = False
        with self._db() as db:
            db.execute("CREATE TABLE IF NOT EXISTS jobs (run_id TEXT PRIMARY KEY, body TEXT NOT NULL)")

    def recover_interrupted(self) -> None:
        """Run once in application startup, never merely because a module imports this service."""
        with self._db() as db:
            for row in db.execute("SELECT run_id, body FROM jobs").fetchall():
                job = json.loads(row[1])
                if job["status"] in {"QUEUED", "RUNNING"}:
                    job.update(status="FAILED", stage="interrupted", finished_at=now(),
                               error="Server restarted before this run completed; submit a new run.")
                    db.execute("UPDATE jobs SET body=? WHERE run_id=?", (json.dumps(job), row[0]))

    @contextmanager
    def _db(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=30)
        try:
            with db:
                yield db
        finally:
            db.close()

    def get(self, run_id: str) -> dict[str, Any] | None:
        with self._db() as db:
            row = db.execute("SELECT body FROM jobs WHERE run_id=?", (run_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._db() as db:
            rows = db.execute("SELECT body FROM jobs ORDER BY rowid DESC LIMIT ?", (limit,)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def _update(self, run_id: str, **values: Any) -> None:
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT body FROM jobs WHERE run_id=?", (run_id,)).fetchone()
            job = json.loads(row[0])
            job.update(values)
            db.execute("UPDATE jobs SET body=? WHERE run_id=?", (json.dumps(job), run_id))

    def _begin(self) -> dict[str, Any]:
        if self._closed or not self.lock.acquire(blocking=False):
            raise BusyError("An investigation or data operation is already running")
        try:
            job = {"run_id": uuid.uuid4().hex, "status": "QUEUED", "stage": "queued", "completed": 0,
                   "total": 0, "created_at": now(), "started_at": None, "finished_at": None,
                   "stats": None, "error": None}
            with self._db() as db:
                db.execute("INSERT INTO jobs VALUES (?,?)", (job["run_id"], json.dumps(job)))
            return job
        except BaseException:
            self.lock.release()
            raise

    def _work(self, run_id: str, reset: bool) -> Any:
        try:
            self._update(run_id, status="RUNNING", stage="validating", started_at=now())
            def progress(stage: str, completed: int, total: int) -> None:
                self._update(run_id, stage=stage, completed=completed, total=total)
            stats = self.execute(run_id=run_id, progress=progress, reset=reset)
            self._update(run_id, status="SUCCEEDED", stage="complete", finished_at=now(),
                         stats=stats.model_dump(mode="json"), completed=stats.cases, total=stats.cases)
            return stats
        except Exception as exc:
            # Provider exception messages can contain credentials or raw evidence. Do not persist them.
            log.error("investigation %s failed: %s", run_id, type(exc).__name__)
            self._update(run_id, status="FAILED", stage="failed", finished_at=now(),
                         error=f"Investigation failed ({type(exc).__name__}). Validate the data and provider configuration, then retry.")
            raise
        finally:
            self.lock.release()

    def submit(self) -> dict[str, Any]:
        job = self._begin()
        try:
            self.pool.submit(self._work, job["run_id"], False)
        except BaseException:
            self._update(job["run_id"], status="FAILED", stage="failed", finished_at=now(), error="Worker unavailable")
            self.lock.release()
            raise
        return job

    def run_sync(self, *, reset: bool = False) -> Any:
        job = self._begin()
        return self._work(job["run_id"], reset)

    @contextmanager
    def exclusive(self) -> Iterator[None]:
        """Serialize imports and demo mutations with pipeline execution."""
        if not self.lock.acquire(blocking=False):
            raise BusyError("An investigation or data operation is already running")
        try:
            yield
        finally:
            self.lock.release()

    def close(self) -> None:
        self._closed = True
        self.pool.shutdown(wait=True, cancel_futures=False)
