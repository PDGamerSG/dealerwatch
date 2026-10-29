"""Application services connecting datasets, durable runs and immutable case evidence."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from toolkit.ledger import Ledger

from dealerwatch import config, pipeline
from dealerwatch.datasets import DatasetRegistry, DatasetValidationError, validate_directory
from dealerwatch.eval.harness import evaluate
from dealerwatch.io import clauses_path
from dealerwatch.jobs import RunManager
from dealerwatch.models import Case, RunStats
from dealerwatch.store import Store

log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = Path(__file__).resolve().parent / "web"
CALL_ID_RE = re.compile(r"^C-\d{3,9}$")
CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "media-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; "
    "frame-ancestors 'none'; form-action 'self'"
)


def _resolve(explicit: str | os.PathLike | None, env: str, default: str) -> Path:
    if explicit is not None:
        return Path(explicit).resolve()
    value = os.environ.get(env)
    return Path(value).resolve() if value else (ROOT / default).resolve()


def _summary(case: Case) -> dict[str, Any]:
    return {"case_id": case.case_id, "scrip": case.candidate.scrip, "account_id": case.account.account_id,
            "holder_name": case.account.holder_name, "dealer_id": case.dealer.dealer_id,
            "recommendation": case.recommendation.value, "status": case.status.value,
            "score": case.candidate.score, "profit_inr": case.candidate.profit_inr,
            "created_at": case.created_at, "order_id": case.order.order_id, "side": case.order.side.value,
            "order_time": case.order.order_time, "dataset_id": case.dataset_id, "revision": case.revision}


class Services:
    """One runtime, validation cache, and bounded background investigation worker."""

    def __init__(self, data_dir: Path, runtime_dir: Path):
        self.registry = DatasetRegistry(runtime_dir, data_dir)
        self.runtime_dir = runtime_dir
        self.lock = threading.RLock()
        self._report_key = None
        self._report = None
        self._store = Store(runtime_dir / config.DB_FILE)
        self.jobs = RunManager(runtime_dir, self._execute)

    @property
    def data_dir(self) -> Path:
        return self.registry.active_dir

    def signature(self) -> tuple:
        base = self.data_dir
        paths = set([*base.glob("*.json"), *base.glob("*.csv"), *base.glob("calls/*.json")])
        reference = clauses_path(base)
        if reference:
            paths.add(reference)
        return (str(base), *((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in sorted(paths)))

    def data_report(self) -> dict:
        key = self.signature()
        with self.lock:
            if self._report is None or key != self._report_key:
                self._report = validate_directory(self.data_dir)
                self._report_key = key
            return self._report

    def invalidate(self):
        with self.lock:
            self._report_key = self._report = None

    def store(self) -> Store:
        return self._store

    @contextmanager
    def ledger(self) -> Iterator[Ledger]:
        ledger = Ledger(str(self.runtime_dir / config.LEDGER_FILE))
        try:
            yield ledger
        finally:
            ledger.close()

    def has_data(self) -> bool:
        return (self.data_dir / "orders.json").is_file()

    def _execute(self, *, run_id: str, progress, reset: bool = False) -> RunStats:
        report = self.data_report()
        if not report["valid"]:
            raise DatasetValidationError(report)
        stats = pipeline.run(str(self.data_dir), str(self.runtime_dir), reset=reset, run_id=run_id,
                             progress=progress, dataset_id=report["fingerprint"])
        self.invalidate()
        return stats

    def run(self, *, reset: bool = False) -> RunStats:
        if not self.has_data():
            raise HTTPException(409, "No dataset. Generate synthetic data or import a JSON bundle first.")
        report = self.data_report()
        if not report["valid"]:
            raise DatasetValidationError(report)
        return self.jobs.run_sync(reset=reset)

    def bootstrap(self):
        self.jobs.recover_interrupted()
        try:
            if self.has_data() and not self.store().count_cases():
                stats = self.run()
                log.info("startup investigation: %s cases", stats.cases)
        except Exception as exc:
            log.error("startup investigation failed: %s", type(exc).__name__)

    def audio_path(self, call_id: str, case: Case | None = None) -> Path | None:
        if not CALL_ID_RE.fullmatch(call_id):
            return None
        if case is None:
            audio_dir = (self.data_dir / "audio").resolve()
            path = (audio_dir / f"{call_id}.wav").resolve()
            return path if path.is_relative_to(audio_dir) and path.is_file() else None
        if call_id not in case.calls or not case.evidence_snapshot:
            return None
        snapshot = case.evidence_snapshot
        call = next((item for item in snapshot.get("call_details", []) if item["call_id"] == call_id), None)
        if not call:
            return None
        name = call.get("snapshot_audio_file", "")
        if not re.fullmatch(r"[a-f0-9]{64}\.wav", name):
            return None
        audio_dir = (self.runtime_dir / "evidence" / "audio").resolve()
        path = (audio_dir / name).resolve()
        return path if path.is_relative_to(audio_dir) and path.is_file() else None

    def case_detail(self, case: Case) -> dict[str, Any]:
        out = case.model_dump(mode="json", exclude={"evidence_snapshot"})
        for key in ("trades", "call_details", "clauses", "prices", "node_labels"):
            out[key] = case.evidence_snapshot.get(key, {} if key == "node_labels" else [])
        out["call_details"] = [{**call, "has_audio": self.audio_path(call["call_id"], case) is not None}
                               for call in out["call_details"]]
        out["evidence_available"] = bool(case.evidence_snapshot)
        return out

    def _evaluation_links(self, result: dict, dataset_id: str) -> dict:
        """Evaluation uses isolated databases; links must address actual published cases."""
        for row in result.get("rows", []):
            row["evaluation_case_id"] = row.get("evaluation_case_id", row.get("case_id"))
            published = self.store().get_case(row["evaluation_case_id"]) if row["evaluation_case_id"] else None
            row["case_id"] = published.case_id if published and published.dataset_id == dataset_id else None
        return result

    def eval_result(self, refresh: bool) -> dict[str, Any]:
        report = self.data_report()
        if not report["valid"]:
            raise DatasetValidationError(report)
        if not report["label_counts"]:
            raise HTTPException(409, "This dataset has no ground-truth labels for evaluation")
        signature = (report["fingerprint"], os.environ.get("DW_LLM", "mock"),
                     os.environ.get("DW_LLM_MODEL", ""), os.environ.get("DW_ASR", "replay"))
        key = hashlib.sha256(json.dumps(signature).encode()).hexdigest()
        path = self.runtime_dir / "eval-cache" / (key + ".json")
        with self.jobs.exclusive():
            if path.is_file() and not refresh:
                result = json.loads(path.read_text(encoding="utf-8"))
            else:
                result = evaluate(str(self.data_dir), str(self.runtime_dir / "evaluations" / key), dataset_id=report["fingerprint"])
                path.parent.mkdir(parents=True, exist_ok=True)
                temporary = path.with_suffix(".tmp")
                temporary.write_text(json.dumps(result, indent=2), encoding="utf-8")
                os.replace(temporary, path)
            return self._evaluation_links(result, report["fingerprint"])
