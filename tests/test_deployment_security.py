"""Vercel proxy requests must permit only explicitly configured public origins."""
from __future__ import annotations

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from dealerwatch.security import RequestLimits


def proxy_app():
    app = FastAPI()
    app.add_middleware(RequestLimits)

    @app.post("/mutation")
    async def mutation(request: Request):
        return {"body": (await request.body()).decode()}

    return app


def test_configured_vercel_origin_can_mutate_through_backend_host(monkeypatch):
    monkeypatch.setenv("DW_PUBLIC_ORIGINS", "https://dealerwatch.vercel.app,https://preview.example.com")
    with TestClient(proxy_app(), base_url="https://backend.example.com") as client:
        for origin in ("https://dealerwatch.vercel.app", "https://preview.example.com"):
            response = client.post("/mutation", content="review", headers={"Origin": origin, "Sec-Fetch-Site": "same-origin"})
            assert response.status_code == 200
            assert response.json() == {"body": "review"}


@pytest.mark.parametrize("configured", ["https://DealerWatch.vercel.app", "https://dealerwatch.vercel.app:443"])
def test_public_origin_uses_browser_hostname_and_default_port_normalization(monkeypatch, configured):
    monkeypatch.setenv("DW_PUBLIC_ORIGINS", configured)
    with TestClient(proxy_app(), base_url="https://backend.example.com") as client:
        assert client.post("/mutation", headers={"Origin": "https://dealerwatch.vercel.app"}).status_code == 200
        assert client.post("/mutation", headers={"Origin": "https://dealerwatch.vercel.app:444"}).status_code == 403


def test_proxy_headers_cannot_authorize_foreign_origins(monkeypatch):
    monkeypatch.setenv("DW_PUBLIC_ORIGINS", "https://dealerwatch.vercel.app")
    with TestClient(proxy_app(), base_url="https://backend.example.com") as client:
        for origin in ("https://evil.example", "https://dealerwatch.vercel.app.evil.example",
                       "https://dealerwatch.vercel.app?spoof=true", "https://dealerwatch.vercel.app/#fragment",
                       "https://@dealerwatch.vercel.app", "https://dealerwatch.vercel.app?", "https://dealerwatch.vercel.app#"):
            response = client.post("/mutation", headers={"Origin": origin, "X-Forwarded-Host": "dealerwatch.vercel.app"})
            assert response.status_code == 403
        assert client.post("/mutation", headers={"Origin": "https://dealerwatch.vercel.app", "Sec-Fetch-Site": "cross-site"}).status_code == 403


def test_no_public_origin_implicitly_trusts_forwarded_host(monkeypatch):
    monkeypatch.delenv("DW_PUBLIC_ORIGINS", raising=False)
    with TestClient(proxy_app(), base_url="https://backend.example.com") as client:
        assert client.post("/mutation", headers={"Origin": "https://dealerwatch.vercel.app", "X-Forwarded-Host": "dealerwatch.vercel.app"}).status_code == 403
        assert client.post("/mutation", headers={"Origin": "https://backend.example.com"}).status_code == 200


@pytest.mark.parametrize("origin", ["*", "https://*.vercel.app", "https://user:password@example.com",
                                   "https://example.com/path", "https://example.com?query=true", "null",
                                   "https://@example.com", "https://example.com?", "https://example.com#"])
def test_invalid_public_origins_fail_closed(monkeypatch, origin):
    monkeypatch.setenv("DW_PUBLIC_ORIGINS", origin)
    with pytest.raises(ValueError, match="DW_PUBLIC_ORIGINS"):
        with TestClient(proxy_app()) as client:
            client.post("/mutation")
