"""The live checker reads the real app and catches corrupt or misrouted responses."""
from __future__ import annotations

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from scripts.check_deployment import check_deployment, main, validate_base_url

BASE = "https://deployment.example"
ADMIN_TOKEN = "checker-test-administrator"


@pytest.fixture(scope="module")
def deployment(tmp_path_factory):
    from dealerwatch.data.synth import generate
    root = tmp_path_factory.mktemp("deployment-checker")
    generate(7, str(root / "data"))
    with pytest.MonkeyPatch.context() as patch:
        for name, value in {"DW_ADMIN_TOKEN": ADMIN_TOKEN, "DW_REVIEWER_TOKEN": "checker-test-reviewer",
                            "DW_LLM": "mock", "DW_ASR": "replay", "DW_LLM_CACHE_ON": "0", "DW_DEMO": "0"}.items():
            patch.setenv(name, value)
        from dealerwatch.api import create_app
        with TestClient(create_app(root / "data", root / "runtime"), base_url=BASE) as client:
            yield client


def app_transport(deployment, mutate=None, requests=None, bypass=None):
    def respond(request):
        assert request.method == "GET", "The smoke checker must not mutate the deployment"
        assert str(request.url).startswith(BASE + "/"), "Credentials must stay on the deployment origin"
        if bypass:
            assert request.headers["x-vercel-protection-bypass"] == bypass
        if requests is not None:
            requests.append(request.url.path)
        response = deployment.get(str(request.url), headers=request.headers)
        if mutate:
            response = mutate(request, response)
        # Starlette may use httpx2 internally; cross the test boundary as HTTP bytes.
        return httpx.Response(response.status_code, headers=dict(response.headers), content=response.content)
    return httpx.MockTransport(respond)


def test_live_checks_preserve_cases_and_ledger_and_redact_report(deployment):
    store = deployment.app.state.svc.store()
    before = [case.model_dump(mode="json") for case in store.list_cases()]
    with deployment.app.state.svc.ledger() as ledger:
        ledger_before = (ledger.count(), ledger.head())
    requests = []
    bypass = "checker-test-bypass-secret"
    report = check_deployment(BASE, token=ADMIN_TOKEN, require_auth=True, bypass_token=bypass,
                              transport=app_transport(deployment, requests=requests, bypass=bypass))
    assert report["status"] == "passed", json.dumps(report, indent=2)
    assert report["read_only"] is True
    assert report["summary"] == {"expected_cases": 19, "cases": 19, "passed": 12, "failed": 0}
    assert report["checks"][-1] == {"name": "evaluation_case_links", "status": "passed", "links": 19}
    assert [case.model_dump(mode="json") for case in store.list_cases()] == before
    with deployment.app.state.svc.ledger() as ledger:
        assert (ledger.count(), ledger.head()) == ledger_before
    encoded = json.dumps(report)
    assert all(value not in encoded for value in (ADMIN_TOKEN, bypass, "holder_name", "call_details", "utterances"))
    assert "/api/ledger/restore" not in requests and "/api/ledger/tamper-demo" not in requests


@pytest.mark.parametrize(("token", "expected_cases", "check"), [
    (None, 19, "session_and_access"),
    ("wrong-private-token", 19, "session_and_access"),
    (ADMIN_TOKEN, 20, "health"),
])
def test_authentication_and_expected_population_fail_clearly(deployment, token, expected_cases, check):
    report = check_deployment(BASE, token=token, expected_cases=expected_cases, require_auth=True,
                              transport=app_transport(deployment))
    assert report["status"] == "failed" and report["checks"][-1]["name"] == check
    assert report["summary"]["failed"] == 1
    assert "wrong-private-token" not in json.dumps(report)


@pytest.mark.parametrize(("failure", "check"), [
    ("digest", "evidence_export_digest"),
    ("missing_evaluation_link", "evaluation_case_links"),
    ("wrong_evaluation_target", "evaluation_case_links"),
    ("external_asset", "frontend_assets"),
    ("html_asset", "frontend_assets"),
    ("readiness", "readiness"),
    ("private_error", "readiness"),
])
def test_detects_broken_deployments_without_exposing_payloads(deployment, failure, check):
    def mutate(request, response):
        path = request.url.path
        if failure == "digest" and path.startswith("/api/cases/") and path.endswith("/export"):
            body = response.json()
            body["integrity"]["sha256"] = "0" * 64
            return httpx.Response(200, json=body)
        if failure in {"missing_evaluation_link", "wrong_evaluation_target"} and path == "/api/eval":
            body = response.json()
            row = next(row for row in body["rows"] if row.get("case_id"))
            if failure == "missing_evaluation_link":
                row["case_id"] = None
            else:
                row["account_id"] = "private-mismatched-account"
            return httpx.Response(200, json=body)
        if failure == "external_asset" and path == "/":
            html = response.text.replace('/static/app.js', 'https://untrusted.example/app.js')
            return httpx.Response(200, text=html, headers={"content-type": "text/html"})
        if failure == "html_asset" and path == "/static/app.js":
            return httpx.Response(200, text="<!doctype html><html>private-server-page</html>",
                                  headers={"content-type": "text/javascript"})
        if path == "/api/ready" and failure == "readiness":
            return httpx.Response(200, json={"ready": False, "data_valid": False, "database": "ok"})
        if path == "/api/ready" and failure == "private_error":
            return httpx.Response(500, text="private-server-page " + ADMIN_TOKEN)
        return response
    report = check_deployment(BASE, token=ADMIN_TOKEN, transport=app_transport(deployment, mutate))
    assert report["status"] == "failed" and report["checks"][-1]["name"] == check
    assert all(value not in json.dumps(report) for value in (ADMIN_TOKEN, "private-server-page", "private-mismatched-account"))


def test_redirects_and_network_errors_do_not_forward_or_log_credentials():
    requests = []
    def redirect(request):
        requests.append(request.url.host)
        return httpx.Response(307, headers={"location": "https://untrusted.example/"})
    report = check_deployment(BASE, token=ADMIN_TOKEN, transport=httpx.MockTransport(redirect))
    assert report["status"] == "failed" and requests == ["deployment.example"]
    def network_error(request):
        raise httpx.ConnectError("private-connection-details " + ADMIN_TOKEN, request=request)
    report = check_deployment(BASE, token=ADMIN_TOKEN, transport=httpx.MockTransport(network_error))
    assert report["checks"][-1]["error"] == "HTTP request failed (ConnectError)"
    assert ADMIN_TOKEN not in json.dumps(report)


@pytest.mark.parametrize("value", [
    "", "deployment.example", "file:///tmp/private", "https://user:private@deployment.example",
    "https://deployment.example/app", "https://deployment.example?token=private", "https://deployment.example#private",
    "https://deployment.example?", "https://deployment.example:bad", "https://deployment.example:0",
    "https://deployment.example\\@untrusted.example", "https://deployment.example\n", "http://deployment.example",
])
def test_rejects_unsafe_or_ambiguous_base_urls(value):
    with pytest.raises(ValueError):
        validate_base_url(value)


@pytest.mark.parametrize(("value", "expected"), [
    (BASE + "/", BASE), ("http://127.0.0.1:8077/", "http://127.0.0.1:8077"),
    ("http://localhost:8077", "http://localhost:8077"), ("http://[::1]:8077", "http://[::1]:8077"),
])
def test_accepts_https_and_loopback_origins(value, expected):
    assert validate_base_url(value) == expected


def test_cli_reads_credentials_from_named_environment_and_writes_report(monkeypatch, tmp_path, capsys):
    import scripts.check_deployment as checker
    monkeypatch.setenv("CHECKER_ACCESS", "private-access-value")
    monkeypatch.setenv("CHECKER_BYPASS", "private-bypass-value")
    def check(url, **options):
        assert url == BASE
        assert options["token"] == "private-access-value" and options["bypass_token"] == "private-bypass-value"
        assert options["require_auth"] and options["expected_cases"] == 23
        return {"status": "passed", "checks": [{"name": "example", "status": "passed"}]}
    monkeypatch.setattr(checker, "check_deployment", check)
    output = tmp_path / "reports" / "live.json"
    assert main(["--url", BASE, "--token-env", "CHECKER_ACCESS", "--bypass-token-env", "CHECKER_BYPASS",
                 "--require-auth", "--expected-cases", "23", "--output", str(output)]) == 0
    report = capsys.readouterr().out
    assert report == output.read_text() and "private-" not in report
    monkeypatch.setattr(checker, "check_deployment", lambda *args, **kwargs: {"status": "failed", "checks": []})
    assert main(["--url", BASE]) == 1


def test_cli_missing_env_fails_without_echoing_a_token(monkeypatch, capsys):
    monkeypatch.delenv("CHECKER_MISSING_TOKEN", raising=False)
    with pytest.raises(SystemExit) as error:
        main(["--url", BASE, "--token-env", "CHECKER_MISSING_TOKEN"])
    assert error.value.code == 2
    assert "nonempty line" in capsys.readouterr().err


@pytest.mark.parametrize(("settings", "message"), [
    ({}, "DW_BROWSER_ALLOW_RESET=1"),
    ({"DW_BROWSER_ALLOW_RESET": "1"}, "require DW_BROWSER_ADMIN_TOKEN and DW_BROWSER_REVIEWER_TOKEN"),
    ({"DW_BROWSER_ALLOW_RESET": "1", "DW_BROWSER_ADMIN_TOKEN": "same-private-value",
      "DW_BROWSER_REVIEWER_TOKEN": "same-private-value"}, "tokens must be distinct"),
])
def test_remote_browser_requires_consent_and_distinct_roles_before_network(monkeypatch, settings, message):
    import test_browser as browser_tests
    for name in ("DW_BROWSER_ALLOW_RESET", "DW_BROWSER_ADMIN_TOKEN", "DW_BROWSER_REVIEWER_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DW_BROWSER_BASE_URL", BASE)
    for name, value in settings.items():
        monkeypatch.setenv(name, value)
    def unexpected_network(*args, **kwargs):
        raise AssertionError("Remote safety checks must precede network access")
    monkeypatch.setattr(browser_tests.httpx, "Client", unexpected_network)
    with pytest.raises(pytest.fail.Exception, match=message) as error:
        browser_tests.remote_target()
    assert "same-private-value" not in str(error.value)


@pytest.mark.parametrize(("auth", "demo"), [(False, True), (True, False)])
def test_remote_browser_rejects_unprotected_or_non_demo_targets(monkeypatch, auth, demo):
    import test_browser as browser_tests
    for name, value in {"DW_BROWSER_BASE_URL": BASE, "DW_BROWSER_ALLOW_RESET": "1",
                        "DW_BROWSER_ADMIN_TOKEN": ADMIN_TOKEN, "DW_BROWSER_REVIEWER_TOKEN": "checker-test-reviewer"}.items():
        monkeypatch.setenv(name, value)
    requests = []
    def respond(request):
        requests.append(request.url.path)
        assert request.method == "GET"
        if request.url.path == "/api/ready":
            return httpx.Response(200, json={"ready": True})
        return httpx.Response(200, json={"auth_required": auth, "demo_enabled": demo})
    client = httpx.Client
    monkeypatch.setattr(browser_tests.httpx, "Client", lambda **kwargs: client(**kwargs, transport=httpx.MockTransport(respond)))
    with pytest.raises(pytest.fail.Exception, match="require authentication and demo_enabled=true"):
        browser_tests.remote_target()
    assert requests == ["/api/ready", "/api/session"]
