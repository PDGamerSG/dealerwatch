"""Restart recovery and request guard behavior independent of provider availability."""
from __future__ import annotations

import json
import sqlite3

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from dealerwatch.jobs import RunManager
from dealerwatch.security import RequestLimits


def test_restart_marks_incomplete_jobs_failed_and_releases_worker(tmp_path):
    manager = RunManager(tmp_path, lambda **kwargs: None)
    manager.close()
    job = {"run_id": "interrupted-run", "status": "RUNNING", "stage": "investigating", "completed": 2,
           "total": 3, "error": None, "finished_at": None}
    with sqlite3.connect(tmp_path / "jobs.db") as db:
        db.execute("INSERT INTO jobs VALUES (?,?)", (job["run_id"], json.dumps(job)))
    recovered = RunManager(tmp_path, lambda **kwargs: None)
    try:
        recovered.recover_interrupted()
        interrupted = recovered.get("interrupted-run")
        assert interrupted["status"] == "FAILED" and interrupted["finished_at"]
        assert "restarted" in interrupted["error"]
        with recovered.exclusive():
            assert recovered.get("missing") is None
    finally:
        recovered.close()


def test_constructing_a_service_does_not_interrupt_another_live_job(tmp_path):
    import threading
    from dealerwatch.models import RunStats
    started, release = threading.Event(), threading.Event()
    def execute(**kwargs):
        started.set()
        assert release.wait(5)
        return RunStats(orders=0, trades=0, calls=0, candidates=0, cases=0, escalate=0, review=0, dismiss=0,
                        llm_provider="mock", llm_calls=0, llm_fallbacks=0, asr_provider="replay", total_ms=1)
    first = RunManager(tmp_path, execute)
    second = None
    try:
        job = first.submit()
        assert started.wait(2)
        second = RunManager(tmp_path, execute)
        assert first.get(job["run_id"])["status"] == "RUNNING"
    finally:
        release.set()
        first.close()
        if second:
            second.close()


def test_chunked_upload_limit_applies_without_content_length():
    app = FastAPI()
    app.add_middleware(RequestLimits, max_bytes=10)
    @app.post("/upload")
    async def upload(request: Request):
        return {"body": (await request.body()).decode()}
    with TestClient(app) as client:
        assert client.post("/upload", content=iter([b"123456", b"78901"])).status_code == 413
        assert client.post("/upload", content=iter([b"123", b"456"])).json()["body"] == "123456"


def test_login_rate_limit_and_no_token_in_responses(tmp_path, monkeypatch):
    from dealerwatch.api import create_app
    monkeypatch.setenv("DW_ADMIN_TOKEN", "test-rate-limit-token")
    with TestClient(create_app(tmp_path / "missing", tmp_path / "runtime")) as client:
        for _ in range(10):
            response = client.post("/api/session", json={"token": "wrong-sensitive-value"})
            assert response.status_code == 401 and "wrong-sensitive-value" not in response.text
        assert client.post("/api/session", json={"token": "test-rate-limit-token"}).status_code == 429
