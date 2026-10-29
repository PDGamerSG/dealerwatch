"""Hash-chained, append-only audit ledger on SQLite.

Every entry stores its payload as canonical JSON (sorted keys, no spaces) plus
`payload_hash = sha256(payload_json)` and `hash = sha256(canonical(header))`, where the
header carries seq, ts, actor, action, payload_hash and prev_hash. The first entry chains
to the genesis hash "0" * 64, so editing, deleting or reordering any row breaks `verify()`.
Generic: no project imports.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

GENESIS = "0" * 64

_SCHEMA = """
CREATE TABLE IF NOT EXISTS ledger (
    seq          INTEGER PRIMARY KEY,
    ts           TEXT NOT NULL,
    actor        TEXT NOT NULL,
    action       TEXT NOT NULL,
    payload      TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    prev_hash    TEXT NOT NULL,
    hash         TEXT NOT NULL
)
"""
_COLUMNS = "seq, ts, actor, action, payload, payload_hash, prev_hash, hash"


def _key(key: Any) -> str:
    if isinstance(key, Enum):
        key = key.value
    if isinstance(key, bool):
        return "true" if key else "false"
    return str(key)


def _normalise(obj: Any) -> Any:
    """Plain JSON values with string keys (pydantic models, enums, sets, datetimes converted)."""
    if isinstance(obj, Enum):
        return _normalise(obj.value)
    if obj is None or isinstance(obj, (str, int, float)):
        return obj
    if isinstance(obj, dict):
        return {_key(k): _normalise(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_normalise(v) for v in obj]
    if isinstance(obj, (set, frozenset)):
        return sorted((_normalise(v) for v in obj), key=lambda v: json.dumps(v, sort_keys=True))
    if hasattr(obj, "model_dump"):
        return _normalise(obj.model_dump(mode="json"))
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return str(obj)


def canonical_json(obj: Any) -> str:
    """Deterministic JSON: string keys sorted, no whitespace, UTF-8 kept as is."""
    return json.dumps(_normalise(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def entry_hash(seq: int, ts: str, actor: str, action: str, payload_hash: str, prev_hash: str) -> str:
    """Hash of an entry header; the payload enters only through its own hash."""
    header = {"seq": seq, "ts": ts, "actor": actor, "action": action,
              "payload_hash": payload_hash, "prev_hash": prev_hash}
    return sha256_hex(canonical_json(header))


class Ledger:
    """Thread-safe append-only ledger stored in one SQLite file (or ":memory:")."""

    def __init__(self, path: str):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        # autocommit mode; appends use explicit BEGIN IMMEDIATE so other processes serialise too
        self._db = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None, timeout=30.0)
        self._db.row_factory = sqlite3.Row
        with self._lock:
            self._db.execute(_SCHEMA)

    # -- writes ---------------------------------------------------------------------------------
    def append(self, actor: str, action: str, payload: dict) -> dict:
        """Append one entry and return it (seq, ts, actor, action, payload, payload_hash, prev_hash, hash)."""
        payload_json = canonical_json(payload)
        payload_hash = sha256_hex(payload_json)
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                row = self._db.execute("SELECT seq, hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
                seq = (row["seq"] + 1) if row else 1
                prev_hash = row["hash"] if row else GENESIS
                ts = datetime.now().isoformat(timespec="milliseconds")
                digest = entry_hash(seq, ts, str(actor), str(action), payload_hash, prev_hash)
                self._db.execute(
                    f"INSERT INTO ledger ({_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (seq, ts, str(actor), str(action), payload_json, payload_hash, prev_hash, digest),
                )
                self._db.execute("COMMIT")
            except BaseException:
                self._db.execute("ROLLBACK")
                raise
        return {"seq": seq, "ts": ts, "actor": str(actor), "action": str(action),
                "payload": json.loads(payload_json), "payload_hash": payload_hash,
                "prev_hash": prev_hash, "hash": digest}

    def tamper_for_demo(self, seq: int, new_payload: dict) -> None:
        """Overwrite one entry's payload WITHOUT fixing any hash, so `verify()` fails at `seq` (demo only)."""
        with self._lock:
            cur = self._db.execute("UPDATE ledger SET payload = ? WHERE seq = ?", (canonical_json(new_payload), int(seq)))
            if cur.rowcount == 0:
                raise ValueError(f"no ledger entry with seq {seq}")

    def reset(self) -> None:
        """Delete every entry; the next append starts again at seq 1 on the genesis hash."""
        with self._lock:
            self._db.execute("DELETE FROM ledger")

    def close(self) -> None:
        with self._lock:
            self._db.close()

    # -- reads ----------------------------------------------------------------------------------
    def entries(self, limit: int | None = None, offset: int = 0) -> list[dict]:
        """Entries in ascending seq order, with payloads decoded."""
        sql = f"SELECT {_COLUMNS} FROM ledger ORDER BY seq ASC LIMIT ? OFFSET ?"
        with self._lock:
            rows = self._db.execute(sql, (-1 if limit is None else int(limit), max(0, int(offset)))).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def count(self) -> int:
        with self._lock:
            return int(self._db.execute("SELECT COUNT(*) FROM ledger").fetchone()[0])

    def head(self) -> str:
        """Hash of the newest entry, or the genesis hash when the ledger is empty."""
        with self._lock:
            row = self._db.execute("SELECT hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
        return row["hash"] if row else GENESIS

    def verify(self) -> dict:
        """Walk the chain from genesis. Returns {ok, checked, first_bad_seq, reason}."""
        with self._lock:
            rows = self._db.execute(f"SELECT {_COLUMNS} FROM ledger ORDER BY seq ASC").fetchall()
        prev = GENESIS
        checked = 0
        for expected_seq, r in enumerate(rows, start=1):
            checked += 1
            seq = r["seq"]
            reason = None
            if seq != expected_seq:
                reason = f"sequence gap: expected seq {expected_seq}, found {seq}"
            elif r["prev_hash"] != prev:
                reason = "prev_hash does not match the previous entry's hash"
            else:
                try:
                    recomputed = sha256_hex(canonical_json(json.loads(r["payload"])))
                except ValueError:
                    recomputed = None
                if recomputed != r["payload_hash"]:
                    reason = "payload does not match payload_hash"
                elif entry_hash(seq, r["ts"], r["actor"], r["action"], r["payload_hash"], r["prev_hash"]) != r["hash"]:
                    reason = "entry hash does not match its contents"
            if reason:
                return {"ok": False, "checked": checked, "first_bad_seq": seq, "reason": reason}
            prev = r["hash"]
        return {"ok": True, "checked": checked, "first_bad_seq": None, "reason": None}

    @staticmethod
    def _row_to_entry(r: sqlite3.Row) -> dict:
        try:
            payload = json.loads(r["payload"])
        except ValueError:
            payload = {"_raw": r["payload"]}
        return {"seq": r["seq"], "ts": r["ts"], "actor": r["actor"], "action": r["action"],
                "payload": payload, "payload_hash": r["payload_hash"],
                "prev_hash": r["prev_hash"], "hash": r["hash"]}
