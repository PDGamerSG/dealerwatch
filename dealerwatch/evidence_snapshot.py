"""Immutable raw evidence and content-derived identity for published investigations."""
from __future__ import annotations

import bisect
import csv
import hashlib
import os
import re
from datetime import timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from toolkit.ledger import canonical_json, sha256_hex

from dealerwatch.detect.links import normalize_phone
from dealerwatch.io import Universe, parse_ts
from dealerwatch.models import Call, Case


def _audio_path(base: Path, relative: str | None) -> Path | None:
    if not relative:
        return None
    path = (base / relative).resolve()
    return path if path.is_relative_to(base) and path.is_file() else None


class EvidenceIndex:
    """Load price bars once and preserve exactly the inputs used to form each case."""

    def __init__(self, universe: Universe, runtime_dir: str | Path):
        self.universe = universe
        self.base = Path(universe.data_dir).resolve()
        self.audio_dir = Path(runtime_dir).resolve() / "evidence" / "audio"
        self.audio_hashes = self._archive_audio()
        self.calls = [call.model_copy(update={
            "audio_file": f"{self.audio_hashes[call.call_id]}.wav" if call.call_id in self.audio_hashes else None,
        }) for call in universe.calls]
        self.source_calls = {call.call_id: call for call in universe.calls}
        self.trades = {trade.trade_id: trade for trade in universe.trades}
        self.clauses = {clause.clause_id: clause for clause in universe.clauses}
        self.bars: dict[str, list[dict[str, Any]]] = {}
        path = self.base / "prices.csv"
        if path.is_file():
            with path.open(newline="", encoding="utf-8-sig") as fh:
                for row in csv.DictReader(fh):
                    bar: dict[str, Any] = {"scrip": row["scrip"], "time": row["time"],
                                           "close": float(row["close"])}
                    for key in ("open", "high", "low", "volume"):
                        if row.get(key) not in (None, ""):
                            bar[key] = float(row[key])
                    self.bars.setdefault(row["scrip"], []).append(bar)
        self.times = {}
        for scrip, bars in self.bars.items():
            bars.sort(key=lambda bar: parse_ts(bar["time"]))
            self.times[scrip] = [parse_ts(bar["time"]) for bar in bars]
        self.labels = {dealer.dealer_id: dealer.name for dealer in universe.dealers}
        self.labels.update({person.person_id: f"{person.name} ({person.relation})" if person.relation else person.name
                            for person in universe.persons})
        self.labels.update({account.account_id: account.holder_name for account in universe.accounts})
        self.phones: dict[str, str] = {}
        for person in universe.persons:
            if person.mobile:
                self.phones.setdefault(normalize_phone(person.mobile), f"{person.name} ({person.person_id})")
        for account in universe.accounts:
            if account.mobile:
                self.phones.setdefault(normalize_phone(account.mobile), f"{account.holder_name} ({account.account_id})")

    def _archive_audio(self) -> dict[str, str]:
        """Fsync immutable recording bytes before publishing database references to them."""
        digests = {}
        for call in self.universe.calls:
            source = _audio_path(self.base, call.audio_file)
            if source is None:
                continue
            self.audio_dir.mkdir(parents=True, exist_ok=True)
            temporary = None
            try:
                with source.open("rb") as src, NamedTemporaryFile(dir=self.audio_dir, delete=False) as dst:
                    temporary = Path(dst.name)
                    digest = hashlib.sha256()
                    while block := src.read(1024 * 1024):
                        digest.update(block)
                        dst.write(block)
                    dst.flush()
                    os.fsync(dst.fileno())
                value = digest.hexdigest()
                os.replace(temporary, self.audio_dir / f"{value}.wav")
                digests[call.call_id] = value
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
        if digests and hasattr(os, "O_DIRECTORY"):
            descriptor = os.open(self.audio_dir, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        return digests

    def fingerprint(self) -> str:
        """Hash loaded evidence, full prices and available audio; exclude paths and truth labels."""
        evidence = {name: sorted((item.model_dump(mode="json") for item in getattr(self.universe, name)),
                                 key=canonical_json)
                    for name in ("dealers", "persons", "accounts", "links", "orders", "trades", "calls", "clauses")}
        evidence["prices"] = self.bars
        evidence["audio"] = self.audio_hashes
        return sha256_hex(canonical_json(evidence))

    def snapshot(self, case: Case, calls: list[Call]) -> dict[str, Any]:
        """Capture transcribed calls, full trades/clauses, bounded OHLCV bars and labels."""
        t0 = parse_ts(case.order.order_time)
        times = self.times.get(case.order.scrip, [])
        lo = bisect.bisect_left(times, t0 - timedelta(minutes=120))
        hi = bisect.bisect_right(times, t0 + timedelta(minutes=120))
        call_details = []
        for call in calls:
            digest = self.audio_hashes.get(call.call_id)
            detail = {**call.model_dump(mode="json"), "audio_file": self.source_calls[call.call_id].audio_file,
                      "has_audio": digest is not None}
            if digest is not None:
                detail.update({"snapshot_audio_file": f"{digest}.wav", "audio_sha256": digest})
            call_details.append(detail)
        nodes = {case.dealer.dealer_id, case.account.account_id}
        for link in case.link_path:
            nodes.update((link.src, link.dst))
        for call in calls:
            nodes.add(call.counterparty_number)
            nodes.update(utterance.speaker for utterance in call.utterances)

        def node_label(node: str) -> str:
            if node in self.labels:
                return self.labels[node]
            if ":" in node:
                return node.split(":", 1)[1]
            if re.fullmatch(r"\+?[\d\s()-]{7,}", node):
                return self.phones.get(normalize_phone(node), node)
            return node

        return {
            "data_dir": str(self.base),
            "audio_dir": str(self.audio_dir),
            "trades": [self.trades[tid].model_dump(mode="json")
                       for tid in case.candidate.pre_trade_ids + case.candidate.post_trade_ids if tid in self.trades],
            "call_details": call_details,
            "clauses": [self.clauses[cid].model_dump(mode="json") for cid in case.clause_ids if cid in self.clauses],
            "prices": self.bars.get(case.order.scrip, [])[lo:hi],
            "node_labels": {node: node_label(node) for node in sorted(nodes) if node},
        }


def case_identity(case: Case, dataset_id: str, fingerprint: str, snapshot: dict[str, Any]) -> str:
    """Dataset scope prevents a reused source ID from attaching new evidence to old decisions."""
    digest = sha256_hex(canonical_json({
        "dataset_id": dataset_id, "fingerprint": fingerprint,
        "candidate": case.candidate, "link_path": case.link_path,
        "recommendation": case.recommendation,
        "chain": [{"key": link.key, "ok": link.ok, "evidence_ids": link.evidence_ids} for link in case.chain],
        "cues": [cue.model_dump(exclude={"extractor"}) for cue in case.cues],
        "evidence": {key: value for key, value in snapshot.items() if key not in {"data_dir", "audio_dir"}},
    }))
    return f"CASE-{digest[:24]}"
