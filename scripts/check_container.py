"""Exercise a built image over HTTP using a disposable container and data volume."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path


def command(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()


def check(image: str) -> dict:
    name = "dealerwatch-check-" + uuid.uuid4().hex[:12]
    volume = name + "-data"
    checks = []
    try:
        command("docker", "run", "--detach", "--name", name, "--publish", "127.0.0.1::8077",
                "--mount", f"type=volume,source={volume},target=/data",
                "--security-opt", "no-new-privileges:true", "--cap-drop", "ALL", "--init",
                "-e", "DW_LLM=mock", "-e", "DW_ASR=replay", "-e", "DW_DEMO=0", image)
        port = command("docker", "port", name, "8077/tcp").split(":")[-1]
        base = "http://127.0.0.1:" + port

        def request(path: str, body=None, headers=None):
            req = urllib.request.Request(
                base + path, data=json.dumps(body).encode() if body is not None else None,
                headers={"Content-Type": "application/json", **(headers or {})})
            with urllib.request.urlopen(req, timeout=30) as response:
                data = response.read()
                return json.loads(data) if "application/json" in response.headers.get("Content-Type", "") else data

        def ready():
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                try:
                    if request("/api/ready")["ready"]:
                        return
                except (urllib.error.URLError, OSError):
                    pass
                time.sleep(0.25)
            raise TimeoutError("Container readiness timed out")

        ready()
        checks.append("Readiness and automatic first-run data/investigation")
        assert command("docker", "exec", name, "id", "-u") == "10001"
        checks.append("Non-root UID 10001 with dropped capabilities and named-volume writes")
        html = request("/")
        assert b"DealerWatch" in html and b"/static/app.js" in html and b"/static/style.css" in html
        assert b"loadCases" in request("/static/app.js")
        assert len(request("/static/style.css")) > 100
        checks.append("Packaged frontend HTML, JavaScript and CSS")
        rows = request("/api/cases")
        assert len(rows) == 19
        assert request("/api/dashboard")["by_recommendation"] == {"ESCALATE": 6, "REVIEW": 10, "DISMISS": 3}
        checks.append("19 cases, 6 ESCALATE / 10 REVIEW / 3 DISMISS")
        case_path = "/api/cases/" + rows[0]["case_id"]
        detail = request(case_path)
        assert detail["clauses"] and detail["call_details"] and detail["trades"] and detail["prices"]
        checks.append("Packaged reference clauses, transcript, trade and price evidence")
        decision = {"action": "start_review", "reviewer": "Container Validation",
                    "expected_revision": detail["revision"], "note": "Container smoke test"}
        headers = {"Idempotency-Key": "container-review-1"}
        assert request(case_path + "/decision", decision, headers)["status"] == "UNDER_REVIEW"
        assert len(request(case_path + "/decision", decision, headers)["decisions"]) == 1
        checks.append("Human review with idempotent retry")
        job = request("/api/runs", {})
        deadline = time.monotonic() + 60
        finished = job
        while time.monotonic() < deadline:
            finished = request("/api/runs/" + job["run_id"])
            if finished["status"] in ("SUCCEEDED", "FAILED"):
                break
            time.sleep(0.2)
        assert finished["status"] == "SUCCEEDED", finished
        assert request(case_path)["status"] == "UNDER_REVIEW"
        checks.append("Background rerun succeeds and preserves review")
        exported = request(case_path + "/export")
        digest = exported.pop("integrity")["sha256"]
        canonical = json.dumps(exported, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        assert hashlib.sha256(canonical).hexdigest() == digest
        assert exported["ledger"]["verified"]
        assert b"case_id" in request("/api/export/cases.csv")
        assert len(request("/api/data/export")["orders"]) == 40
        checks.append("JSON evidence integrity, CSV and dataset exports")
        verified = request("/api/ledger/verify")
        assert verified["ok"]
        command("docker", "restart", "--timeout", "3", name)
        # Docker can reassign an automatically selected host port on restart.
        port = command("docker", "port", name, "8077/tcp").split(":")[-1]
        base = "http://127.0.0.1:" + port
        ready()
        after = request(case_path)
        assert after["status"] == "UNDER_REVIEW" and len(after["decisions"]) == 1
        assert request("/api/runs/" + job["run_id"])["status"] == "SUCCEEDED"
        assert request("/api/ledger/verify")["ok"]
        checks.append("Container restart preserves case, decision, job history and audit integrity")
        return {"checked_at": datetime.now(timezone.utc).isoformat(),
                "docker_server": command("docker", "version", "--format", "{{.Server.Version}}"),
                "image": command("docker", "image", "inspect", image, "--format", "{{.Id}}"),
                "platform": command("docker", "image", "inspect", image, "--format", "{{.Os}}/{{.Architecture}}"),
                "status": "passed", "checks": checks, "case_count": len(rows), "ledger": verified}
    except BaseException:
        subprocess.run(["docker", "logs", "--tail", "80", name], check=False)
        raise
    finally:
        subprocess.run(["docker", "rm", "--force", name], stdout=subprocess.DEVNULL, check=False)
        subprocess.run(["docker", "volume", "rm", volume], stdout=subprocess.DEVNULL, check=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="dealerwatch:check", help="An already-built local image")
    parser.add_argument("--output", type=Path, help="Optional JSON verification report")
    args = parser.parse_args()
    report = json.dumps(check(args.image), indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report)
    print(report, end="")


if __name__ == "__main__":
    main()
