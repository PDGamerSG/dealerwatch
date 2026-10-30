"""DW_PUBLIC_ROLE opens the console to anonymous reviewers without exposing admin actions."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

ADMIN = "public-role-test-administrator-token-0123"
REVIEWER = "public-role-test-reviewer-token-0123456"


def make_client(tmp_path, monkeypatch, public_role):
    from dealerwatch.api import create_app
    monkeypatch.setenv("DW_ADMIN_TOKEN", ADMIN)
    monkeypatch.setenv("DW_REVIEWER_TOKEN", REVIEWER)
    monkeypatch.setenv("DW_PUBLIC_ROLE", public_role)
    return TestClient(create_app(tmp_path / "missing", tmp_path / "runtime"))


def test_public_reviewer_role_skips_sign_in_but_keeps_admin_gated(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch, "reviewer") as client:
        session = client.get("/api/session").json()
        assert session["auth_required"] is False and session["authenticated"] is False
        assert session["role"] == "reviewer" and session["public_role"] == "reviewer"
        assert client.post("/api/run").status_code == 403
        assert client.get("/api/cases").status_code != 401

        elevated = client.get("/api/session", headers={"Authorization": f"Bearer {ADMIN}"}).json()
        assert elevated["role"] == "admin" and elevated["authenticated"] is True
        assert client.get("/api/cases", headers={"Authorization": "Bearer not-a-token"}).status_code == 401


def test_tokens_alone_still_require_sign_in(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch, "") as client:
        session = client.get("/api/session").json()
        assert session["auth_required"] is True and session["role"] is None and session["public_role"] is None
        assert client.get("/api/cases").status_code == 401


def test_rejects_public_admin_role(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match="DW_PUBLIC_ROLE"):
        make_client(tmp_path, monkeypatch, "admin")
