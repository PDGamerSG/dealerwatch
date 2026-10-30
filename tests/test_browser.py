"""Chromium workflows; opt in with pytest -m browser.

Remote runs need DW_BROWSER_BASE_URL, DW_BROWSER_ALLOW_RESET=1, and distinct
DW_BROWSER_ADMIN_TOKEN / DW_BROWSER_REVIEWER_TOKEN values. Use a disposable demo
deployment: these workflows import data, make decisions, and reset its ledger.
DW_BROWSER_BYPASS_TOKEN optionally supplies Vercel deployment-protection bypass.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest

pytestmark = pytest.mark.browser
ROOT = Path(__file__).resolve().parents[1]


def bypass_headers():
    value = os.environ.get("DW_BROWSER_BYPASS_TOKEN", "").strip()
    return {"x-vercel-protection-bypass": value} if value else {}


def browser_context(browser, url, **options):
    context = browser.new_context(**options)
    if os.environ.get("DW_BROWSER_BASE_URL") is not None and bypass_headers():
        try:
            response = context.request.get(url + "/", headers={**bypass_headers(), "x-vercel-set-bypass-cookie": "true"},
                                           max_redirects=0)
            if response.status not in (200, 307, 308):
                raise ValueError("bypass rejected")
        except Exception:
            context.close()
            pytest.fail("Remote deployment-protection bypass failed", pytrace=False)
    return context


def remote_target():
    """Validate remote consent and credentials before any test can change data."""
    configured = os.environ.get("DW_BROWSER_BASE_URL")
    if configured is None:
        return None
    from scripts.check_deployment import validate_base_url
    try:
        url = validate_base_url(configured)
    except ValueError as exc:
        pytest.fail(f"DW_BROWSER_BASE_URL: {exc}", pytrace=False)
    if os.environ.get("DW_BROWSER_ALLOW_RESET") != "1":
        pytest.fail("Remote browser tests reset demo cases and the ledger; set DW_BROWSER_ALLOW_RESET=1 "
                    "only for a disposable deployment", pytrace=False)
    if not all(os.environ.get(name, "").strip() for name in ("DW_BROWSER_ADMIN_TOKEN", "DW_BROWSER_REVIEWER_TOKEN")):
        pytest.fail("Remote browser tests require DW_BROWSER_ADMIN_TOKEN and DW_BROWSER_REVIEWER_TOKEN", pytrace=False)
    if os.environ["DW_BROWSER_ADMIN_TOKEN"].strip() == os.environ["DW_BROWSER_REVIEWER_TOKEN"].strip():
        pytest.fail("Remote browser admin and reviewer tokens must be distinct", pytrace=False)
    try:
        with httpx.Client(base_url=url, timeout=60, follow_redirects=False, headers=bypass_headers()) as client:
            ready = client.get("/api/ready")
            if ready.status_code != 200 or ready.json().get("ready") is not True:
                pytest.fail("Remote deployment is not ready", pytrace=False)
            response = client.get("/api/session")
            if response.status_code != 200:
                pytest.fail("Remote session preflight failed", pytrace=False)
            session = response.json()
            if session.get("auth_required") is not True or session.get("demo_enabled") is not True:
                pytest.fail("Remote browser tests require authentication and demo_enabled=true", pytrace=False)
            if client.get("/api/cases").status_code != 401:
                pytest.fail("Remote cases must reject unauthenticated access", pytrace=False)
            for role, name in (("admin", "DW_BROWSER_ADMIN_TOKEN"), ("reviewer", "DW_BROWSER_REVIEWER_TOKEN")):
                response = client.get("/api/session", headers={"Authorization": "Bearer " + os.environ[name].strip()})
                session = response.json() if response.status_code == 200 else {}
                if session.get("authenticated") is not True or session.get("role") != role:
                    pytest.fail(f"{name} did not authenticate with the required {role} role", pytrace=False)
    except (httpx.HTTPError, ValueError, AttributeError):
        pytest.fail("Remote deployment preflight could not read a valid response", pytrace=False)
    return url


def remote_admin_session(context, url, *, reset=False):
    """Use the browser's cookie jar without putting credentials into a page or log."""
    try:
        response = context.request.post(url + "/api/session", data={"token": os.environ["DW_BROWSER_ADMIN_TOKEN"].strip()},
                                        headers=bypass_headers(), max_redirects=0)
        session = response.json() if response.status == 200 else {}
    except Exception:
        pytest.fail("Remote browser administrator sign-in failed", pytrace=False)
    if (session.get("authenticated") is not True or session.get("role") != "admin"
            or session.get("auth_required") is not True or session.get("demo_enabled") is not True):
        pytest.fail("Remote browser administrator session is not authorized for demo resets", pytrace=False)
    if reset:
        try:
            response = context.request.post(url + "/api/ledger/restore", timeout=60000,
                                            headers=bypass_headers(), max_redirects=0)
            verified = response.status == 200 and response.json().get("verify", {}).get("ok") is True
        except Exception:
            pytest.fail("Remote demo reset request failed", pytrace=False)
        if not verified:
            pytest.fail("Remote demo reset failed", pytrace=False)


def fill_reviewer_token(page):
    try:
        page.locator("#session-token").fill(os.environ["DW_BROWSER_REVIEWER_TOKEN"].strip()
                                             if os.environ.get("DW_BROWSER_BASE_URL") is not None
                                             else "browser-reviewer-token")
    except Exception:
        # Playwright's normal fill error includes the supplied string in its call log.
        pytest.fail("Could not enter the reviewer access token", pytrace=False)


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture(scope="module")
def serve(tmp_path_factory):
    from dealerwatch.data.synth import generate
    processes = []
    remote = remote_target()

    def start(auth=False):
        if remote:
            return remote
        root = tmp_path_factory.mktemp("browser-auth" if auth else "browser-demo")
        generate(7, str(root / "data"))
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = {**os.environ, "DW_DATA": str(root / "data"), "DW_RUNTIME": str(root / "runtime"),
               "DW_DEMO": "1", "DW_LLM": "mock", "DW_ASR": "replay", "DW_LLM_CACHE_ON": "0",
               "DW_ADMIN_TOKEN": "browser-admin-token" if auth else "",
               "DW_REVIEWER_TOKEN": "browser-reviewer-token" if auth else "",
               "DW_REVIEWER_NAME": "Browser Reviewer"}
        log = (root / "server.log").open("w")
        process = subprocess.Popen([sys.executable, "-m", "uvicorn", "dealerwatch.api:app", "--host", "127.0.0.1",
                                    "--port", str(port)], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        processes.append((process, log))
        url = f"http://127.0.0.1:{port}"
        for _ in range(400):
            if process.poll() is not None:
                pytest.fail((root / "server.log").read_text())
            try:
                if httpx.get(url + "/api/ready", timeout=0.5).status_code == 200:
                    return url
            except httpx.HTTPError:
                pass
            time.sleep(0.05)
        pytest.fail("server readiness timeout")

    yield start
    for process, log in processes:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        log.close()


def test_complete_investigation_workflow(browser, serve, tmp_path):
    from playwright.sync_api import expect
    url = serve()
    context = browser_context(browser, url, viewport={"width": 1366, "height": 768}, accept_downloads=True)
    page = context.new_page()
    errors, external = [], []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    page.on("request", lambda request: external.append(request.url) if request.url.startswith("http")
            and urlsplit(request.url).netloc != urlsplit(url).netloc else None)
    try:
        if os.environ.get("DW_BROWSER_BASE_URL") is not None:
            remote_admin_session(context, url, reset=True)
        page.goto(url)
        expect(page.locator("#queue-list .queue-item")).to_have_count(19)
        expect(page.locator("#case-header .rec-ESCALATE")).to_be_visible()
        expect(page.locator("#chain > li")).to_have_count(9)
        expect(page.locator("#timeline svg")).to_be_visible()
        case_id = page.locator("#queue-list .queue-item").first.get_attribute("data-case-id")

        with page.expect_download() as downloaded:
            page.locator("#case-export").click()
        evidence = json.loads(Path(downloaded.value.path()).read_text())
        assert evidence["case"]["case_id"] == case_id and evidence["ledger"]["verified"]

        if os.environ.get("DW_BROWSER_BASE_URL") is not None:
            expect(page.locator("#reviewer")).to_have_attribute("readonly", "")
        else:
            page.locator("#reviewer").fill("Browser Analyst")
        page.locator("#note").fill("Evidence checked in browser")
        page.get_by_role("button", name="Start review", exact=True).click()
        expect(page.locator("#case-header .st-UNDER_REVIEW")).to_be_visible()
        page.get_by_role("button", name="Request info", exact=True).click()
        expect(page.locator("#case-header .st-INFO_REQUESTED")).to_be_visible()
        page.get_by_role("button", name="Approve escalation", exact=True).click()
        page.locator("#confirm-ok").click()
        expect(page.locator("#case-header .st-ESCALATED")).to_be_visible()
        expect(page.locator("#history > li")).to_have_count(3)

        with page.expect_response(lambda res: res.url == url + "/api/runs" and res.request.method == "POST") as started:
            page.locator("#run-btn").click()
        expect(page.locator("#run-progress")).to_contain_text(started.value.json()["run_id"])
        expect(page.locator("#run-progress")).to_contain_text("SUCCEEDED", timeout=30000)
        page.get_by_role("tab", name="Cases", exact=True).click()
        expect(page.locator("#case-header .st-ESCALATED")).to_be_visible()
        expect(page.locator("#queue-list .queue-item")).to_have_count(19)

        page.locator("#filter-rec").select_option("REVIEW")
        expect(page.locator("#queue-list .queue-item")).to_have_count(10)
        page.locator("#filter-rec").select_option("DISMISS")
        expect(page.locator("#queue-list .queue-item")).to_have_count(3)
        page.get_by_role("button", name="Dismiss", exact=True).click()
        page.locator("#confirm-ok").click()
        expect(page.locator("#case-header .st-CLOSED")).to_be_visible()
        with page.expect_download() as downloaded:
            page.locator("#queue-export").click()
        assert "DISMISS" in Path(downloaded.value.path()).read_text()
        page.locator("#filter-query").fill("no-such-case")
        page.get_by_role("button", name="Search", exact=True).click()
        expect(page.locator("#queue-list")).to_contain_text("No cases match")
        page.locator("#queue-clear").click()
        expect(page.locator("#queue-list .queue-item")).to_have_count(19)

        page.get_by_role("tab", name="Overview", exact=True).click()
        expect(page.locator("#overview-body")).to_contain_text("Recommendations")
        page.get_by_role("tab", name="Data", exact=True).click()
        expect(page.locator("#data-report")).to_contain_text("Dataset is valid")
        page.locator("#dataset-json").fill("{bad-json")
        page.locator("#data-validate").click()
        expect(page.locator("#data-candidate-report")).to_contain_text("Invalid JSON")
        page.locator("#dataset-json").fill('{"orders": []}')
        page.locator("#data-validate").click()
        expect(page.locator("#data-candidate-report")).to_contain_text("Dataset is invalid")
        with page.expect_download() as downloaded:
            page.locator("#data-export").click()
        dataset_path = tmp_path / "bundle.json"
        downloaded.value.save_as(dataset_path)
        page.locator("#dataset-file").set_input_files(dataset_path)
        expect(page.locator("#data-candidate-report")).to_contain_text("loaded")
        page.locator("#data-validate").click()
        expect(page.locator("#data-candidate-report")).to_contain_text("Dataset is valid", timeout=30000)
        page.locator("#data-import").click()
        expect(page.locator("#data-candidate-report")).to_contain_text("Dataset imported and activated", timeout=30000)
        with page.expect_response(lambda res: res.url == url + "/api/runs" and res.request.method == "POST") as started:
            page.locator("#run-btn").click()
        expect(page.locator("#run-progress")).to_contain_text(started.value.json()["run_id"])
        expect(page.locator("#run-progress")).to_contain_text("SUCCEEDED", timeout=30000)

        page.get_by_role("tab", name="Ledger", exact=True).click()
        page.locator("#ledger-verify").click()
        expect(page.locator("#verify-banner")).to_contain_text("Chain intact")
        page.locator("#tamper-seq").fill("3")
        page.locator("#ledger-tamper").click()
        page.locator("#confirm-ok").click()
        expect(page.locator("#verify-banner")).to_contain_text("3")
        expect(page.locator("#verify-banner")).to_contain_text("Tampering detected")
        page.locator("#ledger-restore").click()
        page.locator("#confirm-ok").click()
        expect(page.locator("#verify-banner")).to_contain_text("Chain intact", timeout=30000)

        page.get_by_role("tab", name="Eval", exact=True).click()
        expect(page.locator("#eval-body")).to_contain_text("UNLINKED_PATTERN", timeout=30000)
        case_link = page.locator("#eval-body button.chip").first
        case_link.click()
        expect(page.locator("#case-body")).to_be_visible()
        assert not errors, errors
        assert not external, external
    except BaseException:
        out = ROOT / "test-results"
        out.mkdir(exist_ok=True)
        page.screenshot(path=str(out / "workflow-failure.png"), full_page=True)
        raise
    finally:
        context.close()


def test_mobile_tabs_and_authenticated_reviewer(browser, serve):
    from playwright.sync_api import expect
    url = serve(auth=True)
    context = browser_context(browser, url, viewport={"width": 390, "height": 844})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        if os.environ.get("DW_BROWSER_BASE_URL") is not None:
            remote_admin_session(context, url, reset=True)
            assert context.request.delete(url + "/api/session").status == 200
        page.goto(url)
        expect(page.locator("#login-form")).to_be_visible()
        expect(page.locator("#main-views")).to_be_hidden()
        fill_reviewer_token(page)
        page.get_by_role("button", name="Sign in", exact=True).click()
        expect(page.locator("#case-body")).to_be_visible()
        session = context.request.get(url + "/api/session").json()
        assert session["authenticated"] and session["role"] == "reviewer"
        expect(page.locator("#session-status")).to_contain_text(session["reviewer"])
        assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")
        expect(page.locator("#run-btn")).to_be_disabled()
        expect(page.locator("#reviewer")).to_have_attribute("readonly", "")
        page.get_by_role("button", name="Start review", exact=True).click()
        expect(page.locator("#case-header .st-UNDER_REVIEW")).to_be_visible()
        page.get_by_role("tab", name="Data", exact=True).click()
        expect(page.locator("#data-import")).to_be_hidden()
        expect(page.locator("#data-report")).to_contain_text("Dataset is valid")
        for name in ("Overview", "Cases", "Data", "Runs", "Ledger", "Eval"):
            page.get_by_role("tab", name=name, exact=True).click()
            expect(page.get_by_role("tab", name=name, exact=True)).to_have_attribute("aria-selected", "true")
        # Evaluate a function, not a string body, to respect the application's strict CSP.
        assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")
        page.get_by_role("button", name="Sign out", exact=True).click()
        expect(page.locator("#main-views")).to_be_hidden()
        assert context.request.get(url + "/api/cases").status == 401
        assert not errors, errors
    finally:
        context.close()
