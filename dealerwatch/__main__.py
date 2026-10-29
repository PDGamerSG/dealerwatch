"""One-command local startup: seed missing demo data, validate, then serve the app."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from dealerwatch.data.synth import generate
from dealerwatch.datasets import DatasetRegistry, validate_directory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default=os.environ.get("DW_DATA", "data/generated"))
    parser.add_argument("--runtime", default=os.environ.get("DW_RUNTIME", "runtime"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8077)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--audio", action="store_true", help="Render optional synthetic speech using installed OS voices")
    parser.add_argument("--demo", action="store_true", help="Enable explicit ledger tamper/restore demo controls")
    parser.add_argument("--check", action="store_true", help="Generate if missing and validate data, without starting a server")
    args = parser.parse_args(argv)
    data, runtime = Path(args.data).resolve(), Path(args.runtime).resolve()
    active = DatasetRegistry(runtime, data).active_dir
    if not (active / "orders.json").exists():
        if active != data:
            parser.error("Active imported dataset is missing; restore its runtime backup")
        generate(args.seed, str(data))
    if args.audio:
        if active != data:
            parser.error("Imported datasets are immutable. Render audio in the source demo directory before importing.")
        renderer = Path(__file__).resolve().parents[1] / "scripts" / "make_audio.py"
        result = subprocess.run([sys.executable, str(renderer), "--data-dir", str(data)], check=False)
        if result.returncode:
            return result.returncode
    report = validate_directory(active)
    if args.check or not report["valid"]:
        print(json.dumps(report, indent=2))
        return 0 if report["valid"] else 1
    os.environ["DW_DATA"], os.environ["DW_RUNTIME"] = str(data), str(runtime)
    if args.demo:
        os.environ["DW_DEMO"] = "1"
    import uvicorn
    print(f"DealerWatch: http://{args.host}:{args.port} | {report['counts']['orders']} orders | Ctrl+C to stop")
    uvicorn.run("dealerwatch.api:app", host=args.host, port=args.port, workers=1, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
