"""Public workflows, failure handling and authorization through the real HTTP app."""
from __future__ import annotations

import threading
import time

import pytest
from fastapi.testclient import TestClient
from test_api import build_fixture


@pytest.fixture
def app_env(tmp_path, monkeypatch):
    for key in ("DW_ADMIN_TOKEN", "DW_REVIEWER_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("DW_LLM", "mock")
    monkeypatch.setenv("DW_ASR", "replay")
    monkeypatch.setenv("DW_DEMO", "0")
    monkeypatch.setenv("DW_LLM_CACHE_ON", "0")
    build_fixture(tmp_path / "data")
    return tmp_path / "data", tmp_path / "runtime"


def wait_job(client, run_id):
    for _ in range(200):
        job = client.get(f"/api/runs/{run_id}").json()
        if job["status"] in ("SUCCEEDED", "FAILED"):
            return job
        time.sleep(0.01)
    pytest.fail("background run did not finish")


def test_dashboard_validation_filtered_queue_exports(app_env):
    from dealerwatch.api import create_app
    with TestClient(create_app(*app_env)) as client:
        assert client.get("/api/ready").status_code == 200
        report = client.get("/api/data").json()
        assert report["valid"] and report["counts"]["trades"] == 5
        overview = client.get("/api/dashboard").json()
        assert overview["cases"] == 2 and overview["by_recommendation"]["ESCALATE"] == 1
        response = client.get("/api/cases", params={"q": "Neha", "limit": 1})
        assert response.headers["X-Total-Count"] == "1"
        assert response.json()[0]["account_id"] == "A-011"
        assert client.get("/api/cases", params={"q": "%_"}).json() == []
        assert client.get("/api/cases", params={"limit": 0}).status_code == 422
        assert client.get("/api/cases", params={"scrip": "TCS"}).json() == []
        csv = client.get("/api/export/cases.csv", params={"recommendation": "ESCALATE"})
        assert csv.status_code == 200 and "attachment" in csv.headers["content-disposition"]
        assert "A-011" in csv.text and "A-050" not in csv.text
        case_id = response.json()[0]["case_id"]
        evidence = client.get(f"/api/cases/{case_id}/export").json()
        assert evidence["schema_version"] == "1.0"
        assert evidence["case"]["case_id"] == case_id
        assert evidence["ledger"]["verified"] is True
        assert evidence["evidence"]["call_details"][0]["call_id"] == "C-001"
        assert len(evidence["integrity"]["sha256"]) == 64


def test_import_keeps_prior_case_evidence_and_runs_separately(app_env):
    from dealerwatch.api import create_app
    with TestClient(create_app(*app_env)) as client:
        old_row = client.get("/api/cases").json()[0]
        old = client.get(f"/api/cases/{old_row['case_id']}").json()
        original = client.get("/api/data/export").json()
        original["calls"][0]["utterances"][0]["text"] = "Different evidence"
        assert client.post("/api/data/validate", json=original).json()["valid"]
        assert client.post("/api/data/import", json=original).status_code == 201
        assert client.get(f"/api/cases/{old_row['case_id']}").json()["call_details"] == old["call_details"]
        job = client.post("/api/runs")
        assert job.status_code == 202
        finished = wait_job(client, job.json()["run_id"])
        assert finished["status"] == "SUCCEEDED", finished
        assert finished["stats"]["cases"] == 2
        assert client.get("/api/runs").json()[0]["run_id"] == finished["run_id"]
        bad = dict(original, trades=[{"invalid": True}])
        assert client.post("/api/data/import", json=bad).status_code == 422
        assert client.get("/api/data/export").json()["calls"][0]["utterances"][0]["text"] == "Different evidence"


def test_duplicate_jobs_are_rejected_and_health_remains_responsive(app_env, monkeypatch):
    from dealerwatch import pipeline
    from dealerwatch.api import create_app
    with TestClient(create_app(*app_env)) as client:
        entered, release = threading.Event(), threading.Event()
        original = pipeline.run
        def slow(*args, **kwargs):
            entered.set()
            assert release.wait(5)
            return original(*args, **kwargs)
        monkeypatch.setattr(pipeline, "run", slow)
        first = client.post("/api/runs")
        try:
            assert first.status_code == 202
            assert entered.wait(2)
            assert client.post("/api/runs").status_code == 409
            assert client.post("/api/run").status_code == 409
            assert client.get("/api/health").status_code == 200
            assert client.get("/api/cases").status_code == 200
            assert client.post("/api/data/import", json=client.get("/api/data/export").json()).status_code == 409
        finally:
            release.set()
        assert wait_job(client, first.json()["run_id"])["status"] == "SUCCEEDED"


def test_roles_sessions_origins_and_demo_guards(app_env, monkeypatch):
    from dealerwatch.api import create_app
    monkeypatch.setenv("DW_ADMIN_TOKEN", "test-admin-secret-123456789")
    monkeypatch.setenv("DW_REVIEWER_TOKEN", "test-reviewer-secret-12345")
    monkeypatch.setenv("DW_REVIEWER_NAME", "Authenticated Analyst")
    with TestClient(create_app(*app_env)) as client:
        assert client.get("/api/cases").status_code == 401
        assert client.get("/api/session").json()["auth_required"]
        assert client.post("/api/session", json={"token": "bad"}).status_code == 401
        login = client.post("/api/session", json={"token": "test-reviewer-secret-12345"})
        assert login.status_code == 200 and "httponly" in login.headers["set-cookie"].lower()
        assert login.json()["role"] == "reviewer"
        assert client.post("/api/runs").status_code == 403
        case = client.get("/api/cases").json()[0]
        url = f"/api/cases/{case['case_id']}/decision"
        body = {"action": "start_review", "reviewer": "Spoofed", "note": "review"}
        assert client.post(url, json=body, headers={"Origin": "https://hostile.example"}).status_code == 403
        changed = client.post(url, json=body)
        assert changed.status_code == 200
        assert changed.json()["decisions"][-1]["reviewer"] == "Authenticated Analyst"
        client.delete("/api/session")
        assert client.get("/api/cases").status_code == 401
        headers = {"Authorization": "Bearer test-admin-secret-123456789"}
        assert client.get("/api/cases", headers=headers).status_code == 200
        assert client.post("/api/ledger/restore", headers=headers).status_code == 403
        assert client.post("/api/ledger/tamper-demo", json={"seq": 1}, headers=headers).status_code == 403


def test_cross_origin_evaluation_cannot_trigger_provider_work(app_env):
    from dealerwatch.api import create_app
    with TestClient(create_app(*app_env)) as client:
        response = client.get("/api/eval?refresh=true", headers={"Origin": "https://hostile.example", "Sec-Fetch-Site": "cross-site"})
        assert response.status_code == 403


def test_revision_and_idempotent_decisions_at_http_boundary(app_env):
    from dealerwatch.api import create_app
    with TestClient(create_app(*app_env)) as client:
        case_id = client.get("/api/cases").json()[0]["case_id"]
        case = client.get(f"/api/cases/{case_id}").json()
        body = {"action": "start_review", "reviewer": "Reviewer", "expected_revision": case["revision"]}
        url = f"/api/cases/{case_id}/decision"
        first = client.post(url, json=body, headers={"Idempotency-Key": "review-click-1"})
        assert first.status_code == 200
        retry = client.post(url, json=body, headers={"Idempotency-Key": "review-click-1"})
        assert retry.status_code == 200 and len(retry.json()["decisions"]) == 1
        assert client.post(url, json=body).status_code == 409


def test_request_limits_and_request_ids(app_env, monkeypatch):
    from dealerwatch.api import create_app
    monkeypatch.setenv("DW_MAX_BODY_BYTES", "1024")
    with TestClient(create_app(*app_env)) as client:
        response = client.post("/api/data/import", content=b"x" * 1025, headers={"Content-Type": "application/json"})
        assert response.status_code == 413
        response = client.get("/api/health")
        assert response.headers["X-Request-ID"]
        assert "nosniff" == response.headers["X-Content-Type-Options"]


def test_run_error_is_recorded_without_exposing_exception_message(app_env, monkeypatch):
    from dealerwatch import pipeline
    from dealerwatch.api import create_app
    with TestClient(create_app(*app_env)) as client:
        def fail(*args, **kwargs):
            raise RuntimeError("private-provider-token")
        monkeypatch.setattr(pipeline, "run", fail)
        run = client.post("/api/runs").json()
        failed = wait_job(client, run["run_id"])
        assert failed["status"] == "FAILED"
        assert "private-provider-token" not in str(failed)
        assert len(client.get("/api/cases").json()) == 2


def test_evaluation_case_links_resolve_to_live_cases(app_env):
    from dealerwatch.api import create_app
    with TestClient(create_app(*app_env)) as client:
        result = client.get("/api/eval").json()
        for row in result["rows"]:
            assert row["case_id"]
            response = client.get(f"/api/cases/{row['case_id']}")
            assert response.status_code == 200
            assert response.json()["account"]["account_id"] == row["account_id"]


def test_legacy_cases_do_not_acquire_new_dataset_evidence(app_env):
    from dealerwatch.api import create_app
    with TestClient(create_app(*app_env)) as client:
        store = client.app.state.svc.store()
        case = store.list_cases()[0]
        store.save_case(case.model_copy(update={"evidence_snapshot": {}, "dataset_id": ""}))
        result = client.get(f"/api/cases/{case.case_id}").json()
        assert result["trades"] == [] and result["call_details"] == []
        assert result["evidence_available"] is False


def test_evaluation_with_no_labels_reports_unavailable(app_env):
    from dealerwatch.api import create_app
    with TestClient(create_app(*app_env)) as client:
        data = client.get("/api/data/export").json()
        data.pop("truth")
        assert client.post("/api/data/import", json=data).status_code == 201
        assert client.get("/api/eval").status_code == 409


def test_evaluation_links_match_current_material_analysis(app_env, monkeypatch):
    from dealerwatch.api import create_app
    from toolkit import asr
    with TestClient(create_app(*app_env)) as client:
        def neutral_transcript(call, data_dir, provider=None):
            return [{**utterance, "text": "A neutral personal conversation."} for utterance in call["utterances"]], "replay"
        monkeypatch.setattr(asr, "transcribe", neutral_transcript)
        assert client.post("/api/run").status_code == 200
        result = client.get("/api/eval", params={"refresh": True}).json()
        for row in result["rows"]:
            assert row["case_id"]
            assert client.get(f"/api/cases/{row['case_id']}").json()["recommendation"] == row["produced"]
