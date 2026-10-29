"""SQLite case store: each Case and the latest RunStats kept as JSON blobs."""
from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from dealerwatch.models import Case, CaseStatus, Decision, RunStats

_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS cases (case_id TEXT PRIMARY KEY, status TEXT NOT NULL, "
    "recommendation TEXT NOT NULL, score REAL NOT NULL, body TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS stats (id INTEGER PRIMARY KEY CHECK (id = 1), body TEXT NOT NULL)",
)


class Store:
    """Thread-safe store; opens a short-lived connection per operation."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        with self._conn() as db:
            for stmt in _SCHEMA:
                db.execute(stmt)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            db = sqlite3.connect(self.path, timeout=30.0)
            try:
                with db:
                    yield db
            finally:
                db.close()

    def reset(self) -> None:
        """Delete all cases and stats."""
        with self._conn() as db:
            db.execute("DELETE FROM cases")
            db.execute("DELETE FROM stats")

    def save_case(self, case: Case) -> None:
        """Insert or replace a case."""
        with self._conn() as db:
            db.execute("INSERT OR REPLACE INTO cases (case_id, status, recommendation, score, body) "
                       "VALUES (?, ?, ?, ?, ?)",
                       (case.case_id, case.status.value, case.recommendation.value,
                        case.candidate.score, case.model_dump_json()))

    def get_case(self, case_id: str) -> Case | None:
        with self._conn() as db:
            row = db.execute("SELECT body FROM cases WHERE case_id = ?", (case_id,)).fetchone()
        return Case.model_validate_json(row[0]) if row else None

    def list_cases(self, status: CaseStatus | str | None = None) -> list[Case]:
        """Cases ordered by case_id, optionally filtered by status."""
        with self._conn() as db:
            if status is None:
                rows = db.execute("SELECT body FROM cases ORDER BY case_id").fetchall()
            else:
                value = status.value if isinstance(status, CaseStatus) else str(status)
                rows = db.execute("SELECT body FROM cases WHERE status = ? ORDER BY case_id", (value,)).fetchall()
        return [Case.model_validate_json(r[0]) for r in rows]

    def add_decision(self, decision: Decision, status: CaseStatus | None = None) -> Case:
        """Append a decision (and optionally set the new status); raises KeyError for an unknown case."""
        with self._lock:
            case = self.get_case(decision.case_id)
            if case is None:
                raise KeyError(decision.case_id)
            update: dict = {"decisions": [*case.decisions, decision]}
            if status is not None:
                update["status"] = status
            case = case.model_copy(update=update)
            self.save_case(case)
            return case

    def save_stats(self, stats: RunStats) -> None:
        with self._conn() as db:
            db.execute("INSERT OR REPLACE INTO stats (id, body) VALUES (1, ?)", (stats.model_dump_json(),))

    def get_stats(self) -> RunStats | None:
        with self._conn() as db:
            row = db.execute("SELECT body FROM stats WHERE id = 1").fetchone()
        return RunStats.model_validate_json(row[0]) if row else None
