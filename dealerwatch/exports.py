"""Portable case evidence packages and spreadsheet-safe queue exports."""
from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from typing import Any


def csv_export(rows: list[dict[str, Any]]) -> str:
    columns = ["case_id", "scrip", "account_id", "holder_name", "dealer_id", "recommendation", "status",
               "score", "profit_inr", "order_id", "order_time", "created_at"]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        safe = {}
        for key in columns:
            value = row.get(key, "")
            if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r", "\n")):
                value = "'" + value
            safe[key] = value
        writer.writerow(safe)
    return stream.getvalue()


def evidence_export(detail: dict, entries: list[dict], verification: dict, head: str) -> dict:
    evidence_fields = ("trades", "call_details", "clauses", "prices", "node_labels")
    case = {key: value for key, value in detail.items() if key not in (*evidence_fields, "evidence_snapshot")}
    case_id, candidate_id = case["case_id"], case["candidate"]["candidate_id"]
    dataset_id = case.get("dataset_id")
    relevant = [entry for entry in entries if entry["payload"].get("case_id") == case_id
                or (not entry["payload"].get("case_id") and entry["payload"].get("candidate_id") == candidate_id
                    and (not dataset_id or entry["payload"].get("dataset_id") == dataset_id))]
    out = {"schema_version": "1.0", "exported_at": datetime.now(timezone.utc).isoformat(),
           "case": case, "evidence": {key: detail.get(key, []) for key in evidence_fields},
           "ledger": {"verified": verification["ok"], "verification": verification, "head": head, "entries": relevant},
           "disclaimer": "Synthetic rehearsal evidence. Recommendation requires human review; no regulatory filing is made."}
    canonical = json.dumps(out, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    out["integrity"] = {"algorithm": "sha256", "sha256": hashlib.sha256(canonical.encode()).hexdigest(),
                        "scope": "UTF-8 sorted compact JSON of this document excluding integrity"}
    return out
