"""Audit writes that participate in the case store's attached SQLite transaction."""
from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from toolkit.ledger import GENESIS, canonical_json, entry_hash, sha256_hex


@dataclass(frozen=True)
class AuditEvent:
    actor: str
    action: str
    payload: dict[str, Any]
    ts: str = field(default_factory=lambda: datetime.now().isoformat(timespec="milliseconds"))


def append_events(db: sqlite3.Connection, events: Iterable[AuditEvent]) -> None:
    """Append to the attached ``audit`` database; the caller owns the transaction."""
    row = db.execute("SELECT seq, hash FROM audit.ledger ORDER BY seq DESC LIMIT 1").fetchone()
    seq, previous = (row[0], row[1]) if row else (0, GENESIS)
    for event in events:
        seq += 1
        payload = canonical_json(event.payload)
        payload_hash = sha256_hex(payload)
        digest = entry_hash(seq, event.ts, event.actor, event.action, payload_hash, previous)
        db.execute("INSERT INTO audit.ledger "
                   "(seq, ts, actor, action, payload, payload_hash, prev_hash, hash) "
                   "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   (seq, event.ts, event.actor, event.action, payload, payload_hash, previous, digest))
        previous = digest
