from __future__ import annotations

import hashlib
import json

from dealerwatch.exports import csv_export, evidence_export


def test_export_includes_only_the_exact_case_even_when_candidate_is_reused():
    detail = {"case_id": "CASE-old", "candidate": {"candidate_id": "X-1"}, "dataset_id": "dataset-a"}
    entries = [{"payload": {"case_id": case_id, "candidate_id": "X-1", "dataset_id": "dataset-a"}}
               for case_id in ("CASE-old", "CASE-new")]
    export = evidence_export(detail, entries, {"ok": True}, "0" * 64)
    assert len(export["ledger"]["entries"]) == 1
    assert export["ledger"]["entries"][0]["payload"]["case_id"] == "CASE-old"
    integrity = export.pop("integrity")
    encoded = json.dumps(export, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    assert integrity["sha256"] == hashlib.sha256(encoded).hexdigest()


def test_queue_csv_neutralizes_spreadsheet_formula_text():
    exported = csv_export([{"holder_name": "  =1+2", "account_id": "+COMMAND", "profit_inr": -42}])
    assert "'  =1+2" in exported and "'+COMMAND" in exported
    assert ",-42," in exported
