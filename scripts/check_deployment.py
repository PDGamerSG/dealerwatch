"""Read-only HTTP smoke checks for a running DealerWatch deployment.

Example: uv run python scripts/check_deployment.py --url https://preview.example.com
         --token-env DW_BROWSER_ADMIN_TOKEN --require-auth --output test-results/deployment.json

Only GET requests are sent. Evaluation may populate the server's isolated evaluation
cache; this checker never resets data, submits a run, or records a human decision.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import ipaddress
import json
import math
import os
import re
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urljoin, urlsplit

import httpx


def validate_base_url(value: str) -> str:
    """Accept an origin, never credentials or URL parameters that could reach logs."""
    message = "Use an absolute HTTP(S) origin without credentials, path, query, or fragment"
    if not value or any(char.isspace() or ord(char) < 32 for char in value) or "\\" in value:
        raise ValueError(message)
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError:
        raise ValueError(message) from None
    if (parts.scheme not in {"http", "https"} or not parts.hostname or parts.username is not None
            or parts.password is not None or parts.path not in {"", "/"} or parts.query or parts.fragment
            or "?" in value or "#" in value or port == 0):
        raise ValueError(message)
    try:
        loopback = ipaddress.ip_address(parts.hostname).is_loopback
    except ValueError:
        loopback = parts.hostname.lower() == "localhost"
    if parts.scheme == "http" and not loopback:
        raise ValueError("Use HTTPS for remote deployments; HTTP is allowed only for loopback hosts")
    try:
        parsed = httpx.URL(value)
    except httpx.InvalidURL:
        raise ValueError(message) from None
    if not parsed.host or any(char in parsed.host for char in "%@/\\"):
        raise ValueError(message)
    return str(parsed).rstrip("/")


class CheckFailure(Exception):
    """A safe diagnostic constructed by the checker, never a server response body."""


def require(condition, message):
    if not condition:
        raise CheckFailure(message)


class FrontendAssets(HTMLParser):
    VERCEL_FEEDBACK = "https://vercel.live/_next-live/feedback/feedback.js"

    def __init__(self):
        super().__init__()
        self.assets = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.ids.add(attributes.get("id"))
        if tag == "script" and attributes.get("src"):
            source = attributes["src"]
            # Vercel injects this preview-only helper outside the application bundle.
            # It is infrastructure-owned and does not represent an app dependency.
            if source != self.VERCEL_FEEDBACK:
                self.assets.append((source, "javascript"))
        if tag == "link" and "stylesheet" in (attributes.get("rel") or "").split() and attributes.get("href"):
            self.assets.append((attributes["href"], "css"))


def check_deployment(url: str, *, token: str | None = None, expected_cases: int = 19,
                     timeout: float = 30, require_auth: bool = False,
                     bypass_token: str | None = None,
                     transport: httpx.BaseTransport | None = None) -> dict:
    """Return a sanitized, fail-fast report; transport supports isolated API tests."""
    base = validate_base_url(url)
    if expected_cases < 1 or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Expected cases and timeout must be positive")
    checks = []
    summary = {"expected_cases": expected_cases}
    current = "readiness"

    def passed(**details):
        checks.append({"name": current, "status": "passed", **details})

    try:
        headers = {"x-vercel-protection-bypass": bypass_token} if bypass_token else {}
        with httpx.Client(base_url=base, timeout=timeout, follow_redirects=False, transport=transport, headers=headers) as client:
            def get(path, content_type=None):
                response = client.get(path)
                require(response.status_code == 200, f"Expected HTTP 200; received HTTP {response.status_code}")
                if content_type:
                    actual = response.headers.get("content-type", "").split(";", 1)[0].lower()
                    require(actual == content_type, f"Expected a {content_type} response")
                return response

            def document(path):
                return get(path, "application/json").json()

            ready = document("/api/ready")
            require(ready.get("ready") is True and ready.get("data_valid") is True
                    and ready.get("database") == "ok", "Deployment is not ready with valid data and database")
            passed()

            current = "health"
            health = document("/api/health")
            require(health.get("ok") is True and health.get("has_data") is True, "Health or dataset availability failed")
            require(health.get("cases") == expected_cases, "Health case count does not match --expected-cases")
            passed()

            current = "session_and_access"
            session = document("/api/session")
            require(type(session.get("auth_required")) is bool, "Session response has no authentication status")
            if require_auth or token:
                require(session["auth_required"] is True, "Deployment must require authentication")
            if session["auth_required"]:
                require(client.get("/api/cases").status_code == 401, "Anonymous access to cases was not rejected")
                require(bool(token), "Authentication is required; supply --token-env with a populated environment variable")
                client.headers["Authorization"] = "Bearer " + token
                session = document("/api/session")
                require(session.get("authenticated") is True and session.get("role") in {"admin", "reviewer"},
                        "Configured token did not authenticate an admin or reviewer session")
            passed(auth_required=session["auth_required"], authenticated=session.get("authenticated") is True)

            current = "frontend_assets"
            frontend = FrontendAssets()
            frontend.feed(get("/", "text/html").text)
            require({"main-views", "queue-list", "session-token"} <= frontend.ids, "DealerWatch workspace HTML is missing")
            require({kind for _, kind in frontend.assets} == {"javascript", "css"}, "Workspace scripts or stylesheets are missing")
            for source, kind in frontend.assets:
                asset = urlsplit(urljoin(base + "/", source))
                require((asset.scheme, asset.netloc) == (urlsplit(base).scheme, urlsplit(base).netloc)
                        and asset.path.startswith("/static/") and not asset.fragment,
                        "Workspace asset must use this deployment's /static/ path")
                response = get(asset.path + ("?" + asset.query if asset.query else ""))
                content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                expected = {"text/css"} if kind == "css" else {"text/javascript", "application/javascript"}
                require(content_type in expected and bool(response.content.strip())
                        and not response.content.lstrip().lower().startswith((b"<!doctype", b"<html")),
                        "Static asset is empty, has the wrong content type, or contains HTML")
            passed(assets=len(frontend.assets))

            current = "queue"
            response = get("/api/cases", "application/json")
            rows = response.json()
            require(isinstance(rows, list) and len(rows) == expected_cases, "Queue count does not match --expected-cases")
            require(response.headers.get("x-total-count") == str(expected_cases), "Queue total-count header is inconsistent")
            ids = {row["case_id"] for row in rows}
            require(len(ids) == expected_cases and all(isinstance(value, str) and value for value in ids),
                    "Queue case identifiers are missing or duplicated")
            summary["cases"] = len(rows)
            passed(cases=len(rows))

            current = "case_evidence"
            case_path = "/api/cases/" + quote(rows[0]["case_id"], safe="")
            detail = document(case_path)
            require(detail.get("case_id") == rows[0]["case_id"] and detail.get("evidence_available") is True,
                    "Case detail does not identify the queued case and its evidence")
            evidence_fields = ("clauses", "call_details", "trades", "prices")
            require(all(isinstance(detail.get(key), list) and detail[key] for key in evidence_fields),
                    "First case is missing clauses, transcript, trades, or prices")
            passed()

            current = "evidence_export_digest"
            exported = document(case_path + "/export")
            integrity = exported.pop("integrity")
            require(integrity.get("algorithm") == "sha256", "Evidence export must declare SHA-256 integrity")
            canonical = json.dumps(exported, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
            require(hashlib.sha256(canonical.encode()).hexdigest() == integrity.get("sha256"), "Evidence export digest mismatch")
            require(exported.get("schema_version") == "1.0" and exported["case"]["case_id"] == detail["case_id"]
                    and exported["ledger"].get("verified") is True, "Evidence export case or ledger verification is inconsistent")
            require(all(exported["evidence"].get(key) == detail[key] for key in evidence_fields),
                    "Exported evidence does not match the case detail")
            passed(digest_verified=True)

            current = "dataset_and_queue_exports"
            data = document("/api/data")
            require(data.get("valid") is True, "Active dataset validation failed")
            bundle = document("/api/data/export")
            collections = ("dealers", "persons", "accounts", "links", "orders", "trades", "calls", "clauses", "prices")
            require(all(isinstance(bundle.get(key), list) and len(bundle[key]) == data["counts"].get(key)
                        for key in collections), "Dataset export counts do not match the validation report")
            csv_rows = list(csv.DictReader(io.StringIO(get("/api/export/cases.csv", "text/csv").text)))
            require(len(csv_rows) == expected_cases and {row.get("case_id") for row in csv_rows} == ids,
                    "CSV export does not contain exactly the queued cases")
            passed(collections=len(collections), csv_cases=len(csv_rows))

            current = "ledger"
            ledger = document("/api/ledger?limit=1")
            verified = document("/api/ledger/verify")
            require(verified.get("ok") is True and verified.get("checked") == ledger["count"]
                    and ledger["count"] > 0 and len(ledger["entries"]) == 1, "Audit ledger count or verification failed")
            require(isinstance(ledger.get("head"), str) and re.fullmatch(r"[a-f0-9]{64}", ledger["head"]),
                    "Audit ledger head is invalid")
            passed(entries=ledger["count"])

            current = "stats_and_dashboard"
            stats, dashboard = document("/api/stats"), document("/api/dashboard")
            require(stats.get("cases") == expected_cases and dashboard.get("cases") == expected_cases,
                    "Stats or dashboard case count does not match the queue")
            require(dashboard.get("by_recommendation") == dict(Counter(row["recommendation"] for row in rows))
                    and dashboard.get("by_status") == dict(Counter(row["status"] for row in rows)),
                    "Dashboard recommendation or status totals do not match the queue")
            passed()

            current = "run_history"
            runs = document("/api/runs")
            require(isinstance(runs, list), "Run history must be a list")
            if runs:
                run = document("/api/runs/" + quote(runs[0]["run_id"], safe=""))
                require(run.get("run_id") == runs[0]["run_id"] and run.get("status") == runs[0]["status"],
                        "Run history detail does not match its summary")
            passed(runs=len(runs))

            current = "evaluation_case_links"
            evaluation = document("/api/eval")
            require(evaluation.get("candidates") == expected_cases and isinstance(evaluation.get("rows"), list),
                    "Evaluation candidates or rows are inconsistent")
            links = set()
            for row in evaluation["rows"]:
                case_id = row.get("case_id")
                if case_id is None:
                    require(row.get("evaluation_case_id") is None, "Evaluation case has no link to a published case")
                    continue
                require(case_id in ids, "Evaluation links to a case missing from the queue")
                case = document("/api/cases/" + quote(case_id, safe=""))
                require(case.get("case_id") == case_id and case["account"]["account_id"] == row["account_id"]
                        and case["order"]["order_id"] == row["order_id"] and case["recommendation"] == row["produced"],
                        "Evaluation link resolves to a different account, order, or recommendation")
                links.add(case_id)
            require(links == ids, "Evaluation does not link to every queued case")
            passed(links=len(links))
    except CheckFailure as exc:
        checks.append({"name": current, "status": "failed", "error": str(exc)})
    except httpx.HTTPError as exc:
        checks.append({"name": current, "status": "failed", "error": f"HTTP request failed ({type(exc).__name__})"})
    except (KeyError, ValueError, TypeError, AttributeError, IndexError, csv.Error):
        checks.append({"name": current, "status": "failed", "error": "Response contains missing or invalid fields"})
    summary.update(passed=sum(check["status"] == "passed" for check in checks),
                   failed=sum(check["status"] == "failed" for check in checks))
    return {"checked_at": datetime.now(timezone.utc).isoformat(), "url": base, "read_only": True,
            "status": "failed" if summary["failed"] else "passed", "checks": checks, "summary": summary}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Deployment origin; HTTPS except for loopback hosts")
    parser.add_argument("--token-env", help="Name of the environment variable holding an admin or reviewer token")
    parser.add_argument("--bypass-token-env", help="Optional environment variable holding a Vercel protection bypass secret")
    parser.add_argument("--require-auth", action="store_true", help="Fail if the deployment permits anonymous API access")
    parser.add_argument("--expected-cases", type=int, default=19, help="Expected queue size (default: 19)")
    parser.add_argument("--timeout", type=float, default=30, help="HTTP timeout in seconds per request (default: 30)")
    parser.add_argument("--output", type=Path, help="Optional path for the same sanitized JSON report printed to stdout")
    args = parser.parse_args(argv)
    try:
        url = validate_base_url(args.url)
    except ValueError as exc:
        parser.error(str(exc))
    if args.expected_cases < 1 or not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--expected-cases and --timeout must be positive")
    def from_environment(name):
        if name is None:
            return None
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            parser.error("Token arguments must name an environment variable, never a token value")
        value = os.environ.get(name, "").strip()
        if not value or "\r" in value or "\n" in value:
            parser.error("The token environment variable must contain one nonempty line")
        return value
    token, bypass_token = from_environment(args.token_env), from_environment(args.bypass_token_env)
    result = check_deployment(url, token=token, expected_cases=args.expected_cases,
                              timeout=args.timeout, require_auth=args.require_auth, bypass_token=bypass_token)
    report = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    print(report, end="")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
