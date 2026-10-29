"""SQLite case storage with atomic publication and case/audit reviewer transactions."""
from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

from toolkit.ledger import Ledger, canonical_json, sha256_hex

from dealerwatch.models import Case, CaseStatus, Decision, Recommendation, RunStats
from dealerwatch.persistence import AuditEvent, append_events

_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS cases (case_id TEXT PRIMARY KEY, status TEXT NOT NULL, "
    "recommendation TEXT NOT NULL, score REAL NOT NULL, body TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS stats (id INTEGER PRIMARY KEY CHECK (id = 1), body TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS decision_requests "
    "(idempotency_key TEXT PRIMARY KEY, request_hash TEXT NOT NULL, response TEXT NOT NULL)",
)
_SEARCH_FIELDS = {
    "scrip": "$.order.scrip", "dealer_id": "$.dealer.dealer_id",
    "account_id": "$.account.account_id", "holder_name": "$.account.holder_name",
}
_TERMINAL = frozenset({CaseStatus.CLOSED, CaseStatus.ESCALATED})


class Store:
    """Short-lived connections; SQLite write locks serialize independent instances/processes."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        with self._conn() as db:
            db.execute("BEGIN IMMEDIATE")
            for stmt in _SCHEMA:
                db.execute(stmt)
            columns = {row[1] for row in db.execute("PRAGMA table_info(cases)")}
            for name, json_path in _SEARCH_FIELDS.items():
                if name not in columns:
                    db.execute(f"ALTER TABLE cases ADD COLUMN {name} TEXT NOT NULL DEFAULT ''")
                    db.execute(f"UPDATE cases SET {name} = COALESCE(json_extract(body, ?), '')", (json_path,))
            for name in ("status", "recommendation", "scrip", "dealer_id", "account_id"):
                db.execute(f"CREATE INDEX IF NOT EXISTS cases_{name} ON cases ({name})")

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            db = sqlite3.connect(self.path, timeout=30.0)
            try:
                with db:
                    yield db
            finally:
                db.close()

    @contextmanager
    def _write(self, ledger: Ledger | None = None) -> Iterator[sqlite3.Connection]:
        """Use rollback journals so SQLite's super-journal commits both files atomically.

        WAL and in-memory databases cannot guarantee an atomic attached-file commit,
        so audited operations reject them instead of weakening the durability contract.
        No network/filesystem or model calls run while this transaction is held.
        """
        with self._conn() as db:
            if ledger is not None:
                if self.path == ":memory:" or ledger.path == ":memory:":
                    raise ValueError("atomic audit writes require on-disk SQLite databases")
                if Path(self.path).resolve() == Path(ledger.path).resolve():
                    raise ValueError("case and ledger databases must have distinct paths")
                db.execute("ATTACH DATABASE ? AS audit", (str(Path(ledger.path).resolve()),))
                for schema in ("main", "audit"):
                    mode = db.execute(f"PRAGMA {schema}.journal_mode").fetchone()[0]
                    if mode not in {"delete", "persist", "truncate"}:
                        raise ValueError("atomic audit writes require SQLite rollback journal mode")
                    db.execute(f"PRAGMA {schema}.synchronous = FULL")
            db.execute("BEGIN IMMEDIATE")
            yield db

    @staticmethod
    def _save_case(db: sqlite3.Connection, case: Case) -> None:
        # Pydantic encodes non-finite floats as null; reject them before a corrupt row can be committed.
        body = json.dumps(case.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        db.execute("INSERT INTO cases "
                   "(case_id, status, recommendation, score, body, scrip, dealer_id, account_id, holder_name) "
                   "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(case_id) DO UPDATE SET "
                   "status=excluded.status, recommendation=excluded.recommendation, score=excluded.score, "
                   "body=excluded.body, scrip=excluded.scrip, dealer_id=excluded.dealer_id, "
                   "account_id=excluded.account_id, holder_name=excluded.holder_name",
                   (case.case_id, case.status.value, case.recommendation.value, case.candidate.score,
                    body, case.order.scrip, case.dealer.dealer_id,
                    case.account.account_id, case.account.holder_name))

    @staticmethod
    def _get_case(db: sqlite3.Connection, case_id: str) -> Case | None:
        row = db.execute("SELECT body FROM cases WHERE case_id = ?", (case_id,)).fetchone()
        return Case.model_validate_json(row[0]) if row else None

    @staticmethod
    def _save_stats(db: sqlite3.Connection, stats: RunStats) -> None:
        db.execute("INSERT OR REPLACE INTO stats (id, body) VALUES (1, ?)", (stats.model_dump_json(),))

    def reset(self) -> None:
        """Explicitly delete cases, statistics and request replay records."""
        with self._write() as db:
            db.execute("DELETE FROM cases")
            db.execute("DELETE FROM stats")
            db.execute("DELETE FROM decision_requests")

    def save_case(self, case: Case) -> None:
        """Insert or replace a case; publication and human updates use dedicated transactions."""
        with self._write() as db:
            self._save_case(db, case)

    def get_case(self, case_id: str) -> Case | None:
        with self._conn() as db:
            return self._get_case(db, case_id)

    def count_cases(self) -> int:
        with self._conn() as db:
            return int(db.execute("SELECT COUNT(*) FROM cases").fetchone()[0])

    def query_cases(self, status: CaseStatus | str | None = None,
                    recommendation: Recommendation | str | None = None, q: str = "",
                    scrip: str | None = None, dealer_id: str | None = None,
                    limit: int | None = None, offset: int = 0) -> tuple[list[Case], int]:
        """Filter before decoding evidence JSON and return a consistent page and total."""
        clauses: list[str] = []
        params: list[str | int] = []
        for name, value in (("status", status), ("recommendation", recommendation),
                            ("scrip", scrip), ("dealer_id", dealer_id)):
            if value is not None:
                clauses.append(f"{name} = ?")
                params.append(value.value if isinstance(value, (CaseStatus, Recommendation)) else str(value))
        if q.strip():
            pattern = "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            fields = ("case_id", "account_id", "holder_name", "scrip", "dealer_id")
            clauses.append("(" + " OR ".join(f"{name} LIKE ? ESCAPE '\\'" for name in fields) + ")")
            params.extend([pattern] * len(fields))
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self._conn() as db:
            db.execute("BEGIN")
            total = db.execute("SELECT COUNT(*) FROM cases" + where, params).fetchone()[0]
            rows = db.execute("SELECT body FROM cases" + where + " ORDER BY "
                              "CASE recommendation WHEN 'ESCALATE' THEN 0 WHEN 'REVIEW' THEN 1 ELSE 2 END, "
                              "score DESC, case_id LIMIT ? OFFSET ?",
                              [*params, -1 if limit is None else max(0, int(limit)), max(0, int(offset))]).fetchall()
        return [Case.model_validate_json(row[0]) for row in rows], int(total)

    def list_cases(self, status: CaseStatus | str | None = None) -> list[Case]:
        """Cases ordered by stable case_id, optionally filtered by status."""
        with self._conn() as db:
            if status is None:
                rows = db.execute("SELECT body FROM cases ORDER BY case_id").fetchall()
            else:
                value = status.value if isinstance(status, CaseStatus) else str(status)
                rows = db.execute("SELECT body FROM cases WHERE status = ? ORDER BY case_id", (value,)).fetchall()
        return [Case.model_validate_json(row[0]) for row in rows]

    def publish_run(self, cases: Sequence[Case], stats: RunStats, events: Sequence[AuditEvent],
                    ledger: Ledger, *, reset: bool = False) -> None:
        """Publish a completed analysis, statistics and audit as one transaction.

        Matching identities keep their original evidence and reviewer history, including
        decisions committed while this run was analysing. Unrelated/old cases remain.
        """
        with self._write(ledger) as db:
            if reset:
                for table in ("cases", "stats", "decision_requests", "audit.ledger"):
                    db.execute(f"DELETE FROM {table}")
            retained: dict[str, Case] = {}
            for case in cases:
                previous = self._get_case(db, case.case_id)
                if previous is None:
                    self._save_case(db, case)
                else:
                    retained[case.case_id] = previous
            self._save_stats(db, stats)
            audited = []
            for event in events:
                previous = retained.get(event.payload.get("case_id", ""))
                if event.action == "case.created" and previous is not None:
                    event = replace(event, action="case.reused", payload={
                        **event.payload, "original_run_id": previous.run_id,
                        "revision": previous.revision, "status": previous.status.value,
                    })
                audited.append(event)
            append_events(db, audited)

    def add_decision(self, decision: Decision, status: CaseStatus | None = None, *,
                     ledger: Ledger | None = None, expected_revision: int | None = None,
                     idempotency_key: str | None = None) -> Case:
        """Atomically validate, update, audit and remember a successful reviewer request."""
        request_hash = sha256_hex(canonical_json({
            "case_id": decision.case_id, "action": decision.action, "reviewer": decision.reviewer,
            "note": decision.note, "status": status, "expected_revision": expected_revision,
        }))
        with self._write(ledger) as db:
            if idempotency_key is not None:
                row = db.execute("SELECT request_hash, response FROM decision_requests WHERE idempotency_key = ?",
                                 (idempotency_key,)).fetchone()
                if row:
                    if row[0] != request_hash:
                        raise ValueError("idempotency key was already used for a different decision request")
                    return Case.model_validate_json(row[1])
            case = self._get_case(db, decision.case_id)
            if case is None:
                raise KeyError(decision.case_id)
            if expected_revision is not None and expected_revision != case.revision:
                raise ValueError(f"stale revision: expected {expected_revision}, current {case.revision}")
            if case.status in _TERMINAL:
                raise ValueError(f"case {case.case_id} is {case.status.value}; no further actions allowed")
            updated = case.model_copy(update={"decisions": [*case.decisions, decision],
                                               "status": status or case.status, "revision": case.revision + 1})
            self._save_case(db, updated)
            if ledger is not None:
                append_events(db, [AuditEvent(decision.reviewer, f"decision.{decision.action}", {
                    "case_id": case.case_id, "action": decision.action, "from_status": case.status.value,
                    "to_status": updated.status.value, "note": decision.note, "time": decision.time,
                    "recommendation": case.recommendation.value, "revision": updated.revision,
                    "dataset_id": case.dataset_id, "run_id": case.run_id,
                })])
            if idempotency_key is not None:
                db.execute("INSERT INTO decision_requests (idempotency_key, request_hash, response) VALUES (?, ?, ?)",
                           (idempotency_key, request_hash, updated.model_dump_json()))
            return updated

    def save_stats(self, stats: RunStats) -> None:
        with self._write() as db:
            self._save_stats(db, stats)

    def get_stats(self) -> RunStats | None:
        with self._conn() as db:
            row = db.execute("SELECT body FROM stats WHERE id = 1").fetchone()
        return RunStats.model_validate_json(row[0]) if row else None
