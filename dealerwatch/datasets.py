"""Validated, content-addressed evidence datasets for repeatable investigations."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import shutil
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

from pydantic import ValidationError

from dealerwatch.io import clauses_path
from dealerwatch.models import (
    Account,
    Call,
    Clause,
    Dealer,
    FundOrder,
    Link,
    Person,
    Trade,
)

MODELS = {"dealers": (Dealer, "dealer_id"), "persons": (Person, "person_id"),
          "accounts": (Account, "account_id"), "links": (Link, None),
          "orders": (FundOrder, "order_id"), "trades": (Trade, "trade_id"),
          "calls": (Call, "call_id"), "clauses": (Clause, "clause_id")}
REQUIRED = ("dealers", "persons", "accounts", "links", "orders", "trades", "calls")
PRICE_FIELDS = ("scrip", "time", "open", "high", "low", "close", "volume")
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}$")
CALL_ID = re.compile(r"^C-\d{3,9}$")
ATTRIBUTE = re.compile(r"^(phone|email|bank|device|address):.+$")
MAX_ROWS = 250_000
MAX_ISSUES = 100
MAX_QUANTITY = 1_000_000_000_000
MAX_PRICE = 1_000_000_000


class DatasetValidationError(ValueError):
    """A report suitable for showing which input records need correction."""

    def __init__(self, report: dict[str, Any]):
        self.report = report
        super().__init__("dataset validation failed")


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_bundle(directory: str | Path) -> dict[str, Any]:
    """Read the directory layout without silently replacing missing required files."""
    base = Path(directory)
    bundle = {name: _json(base / f"{name}.json") for name in REQUIRED if name != "calls"
              and (base / f"{name}.json").is_file()}
    if (base / "calls").is_dir():
        bundle["calls"] = [_json(p) for p in sorted((base / "calls").glob("*.json"))]
    cpath = clauses_path(base)
    if cpath:
        bundle["clauses"] = _json(cpath)
    if (base / "truth.json").is_file():
        bundle["truth"] = _json(base / "truth.json")
    if (base / "prices.csv").is_file():
        with (base / "prices.csv").open(encoding="utf-8", newline="") as stream:
            bundle["prices"] = list(csv.DictReader(stream))
    return bundle


def dataset_fingerprint(bundle: dict[str, Any]) -> str:
    """Digest over the normalized full input, including labels and reference clauses."""
    encoded = json.dumps(bundle, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _validate(bundle: Any, source: str) -> tuple[dict[str, Any], dict[str, Any]]:
    issues: list[dict[str, str]] = []
    error_count = 0

    def issue(location: str, message: str, severity: str = "error") -> None:
        nonlocal error_count
        if severity == "error":
            error_count += 1
        if len(issues) < MAX_ISSUES:
            issues.append({"severity": severity, "location": location, "message": message})

    normalized: dict[str, Any] = {}
    counts: dict[str, int] = {}
    if not isinstance(bundle, dict):
        issue("bundle", "Expected a JSON object containing evidence collections")
        bundle = {}
    for key in REQUIRED:
        if key not in bundle:
            issue(key, "Required collection is missing (use [] for an intentionally empty collection)")
    for key in set(bundle) - set(MODELS) - {"prices", "truth", "schema_version"}:
        issue(str(key), "Unrecognized collection")

    identifiers: dict[str, set[str]] = {}
    for name, (model, id_key) in MODELS.items():
        raw = bundle.get(name, [])
        if name == "clauses" and name not in bundle:
            ref = clauses_path(Path(__file__).resolve().parents[1] / "data/generated")
            raw = _json(ref) if ref else []
        normalized[name] = []
        identifiers[name] = set()
        if not isinstance(raw, list):
            issue(name, "Expected an array")
            continue
        counts[name] = len(raw)
        if len(raw) > MAX_ROWS:
            issue(name, f"Maximum {MAX_ROWS} records per collection")
            continue
        for index, item in enumerate(raw):
            location = f"{name}[{index}]"
            if name in ("orders", "trades") and isinstance(item, dict):
                quantity = item.get("qty")
                if type(quantity) is not int or not 0 < quantity <= MAX_QUANTITY:
                    issue(location + ".qty", f"Expected an integer share quantity from 1 to {MAX_QUANTITY}")
                    continue
            try:
                parsed = model.model_validate(item).model_dump(mode="json")
            except (ValidationError, ValueError, TypeError, OverflowError):
                issue(location, f"Invalid {model.__name__} fields or types")
                continue
            if id_key:
                identifier = parsed[id_key]
                if not SAFE_ID.fullmatch(identifier) or (name == "calls" and not CALL_ID.fullmatch(identifier)):
                    issue(location + "." + id_key, "Invalid identifier; calls use C- followed by 3–9 digits")
                if identifier in identifiers[name]:
                    issue(location + "." + id_key, "Duplicate identifier")
                identifiers[name].add(identifier)
            normalized[name].append(parsed)

    def timestamp(value: Any, where: str) -> datetime | None:
        try:
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is not None or "T" not in value or len(value) < 19:
                raise ValueError
            return parsed
        except (ValueError, TypeError):
            issue(where, "Use a full ISO timestamp in IST without offset, e.g. 2026-09-01T13:00:00")
            return None

    def positive(value: Any, where: str, zero: bool = False, maximum: int = MAX_QUANTITY) -> None:
        if (isinstance(value, bool) or not isinstance(value, (float, int))
                or (value < 0 if zero else value <= 0) or value > maximum or not math.isfinite(value)):
            issue(where, f"Expected a finite {'nonnegative' if zero else 'positive'} number at most {maximum}")

    def reference(value: str, collection: str, where: str) -> None:
        if value not in identifiers[collection]:
            issue(where, f"Unknown {collection} reference: {value[:120]}")

    for name in ("orders", "trades"):
        for index, row in enumerate(normalized[name]):
            where = f"{name}[{index}]"
            positive(row["qty"], where + ".qty")
            if not re.fullmatch(r"[A-Z0-9&_.-]{1,32}", row["scrip"]):
                issue(where + ".scrip", "Expected an uppercase market symbol")
            if name == "trades":
                positive(row["price"], where + ".price", maximum=MAX_PRICE)
                timestamp(row["time"], where + ".time")
                reference(row["account_id"], "accounts", where)
            else:
                times = [timestamp(row[key], where + "." + key) for key in ("order_time", "exec_start", "exec_end")]
                if all(t is not None for t in times) and not times[0] <= times[1] <= times[2]:
                    issue(where, "Require order_time <= exec_start <= exec_end")
                reference(row["dealer_id"], "dealers", where)

    utterance_ids: set[str] = set()
    for index, call in enumerate(normalized["calls"]):
        where = f"calls[{index}]"
        reference(call["dealer_id"], "dealers", where)
        timestamp(call["start_time"], where + ".start_time")
        positive(call["duration_s"], where + ".duration_s", zero=True)
        audio = call.get("audio_file")
        if audio and ("\\" in audio or PurePosixPath(audio).is_absolute() or ".." in PurePosixPath(audio).parts
                      or not audio.startswith("audio/") or not audio.endswith(".wav")):
            issue(where + ".audio_file", "Audio must be a relative audio/*.wav path within the dataset")
        previous_start = -1
        for utt in call["utterances"]:
            uid = utt["id"]
            if uid in utterance_ids or not SAFE_ID.fullmatch(uid):
                issue(where + ".utterances", "Utterance identifiers must be safe and globally unique")
            utterance_ids.add(uid)
            if not (0 <= utt["start_ms"] <= utt["end_ms"] <= call["duration_s"] * 1000):
                issue(where + ".utterances", "Utterance timing must fit the call duration")
            if utt["start_ms"] < previous_start:
                issue(where + ".utterances", "Utterances must be in chronological order")
            previous_start = utt["start_ms"]
            if len(utt["text"]) > 100_000:
                issue(where + ".utterances", "Utterance text exceeds 100000 characters")

    entities = identifiers["dealers"] | identifiers["persons"] | identifiers["accounts"]
    if len(entities) != sum(len(identifiers[key]) for key in ("dealers", "persons", "accounts")):
        issue("entities", "Dealer, person and account identifiers must be globally unique")
    for index, link in enumerate(normalized["links"]):
        for end in ("src", "dst"):
            if link[end] not in entities and not ATTRIBUTE.fullmatch(link[end]):
                issue(f"links[{index}].{end}", "Unknown entity or attribute node")
        if link["src"] == link["dst"]:
            issue(f"links[{index}]", "Self links are not meaningful", "warning")

    prices = bundle.get("prices", [])
    normalized["prices"] = []
    seen_bars: set[tuple[str, str]] = set()
    if not isinstance(prices, list) or len(prices) > MAX_ROWS:
        issue("prices", f"Expected an array of at most {MAX_ROWS} price bars")
    else:
        for index, row in enumerate(prices):
            where = f"prices[{index}]"
            try:
                bar = {"scrip": str(row["scrip"]), "time": str(row["time"]),
                       **{key: float(row[key]) for key in ("open", "high", "low", "close", "volume")}}
            except (KeyError, ValueError, TypeError, OverflowError):
                issue(where, "Price bar requires scrip,time,open,high,low,close,volume")
                continue
            timestamp(bar["time"], where + ".time")
            for key in ("open", "high", "low", "close", "volume"):
                positive(bar[key], where + "." + key, zero=key == "volume",
                         maximum=MAX_QUANTITY if key == "volume" else MAX_PRICE)
            if not bar["low"] <= min(bar["open"], bar["close"]) <= max(bar["open"], bar["close"]) <= bar["high"]:
                issue(where, "OHLC values must fit inside low/high")
            pair = (bar["scrip"], bar["time"])
            if pair in seen_bars:
                issue(where, "Duplicate (scrip,time) price bar")
            seen_bars.add(pair)
            normalized["prices"].append(bar)
    counts["prices"] = len(normalized["prices"])

    truth = bundle.get("truth", {"cases": []})
    normalized["truth"] = truth
    labels: Counter[str] = Counter()
    if not isinstance(truth, dict) or not isinstance(truth.get("cases"), list):
        issue("truth", "Expected an object with a cases array")
    else:
        pairs = set()
        for index, row in enumerate(truth["cases"]):
            where = f"truth.cases[{index}]"
            if not isinstance(row, dict) or not all(isinstance(row.get(k), str) for k in ("order_id", "account_id", "label", "expected")):
                issue(where, "Truth case requires order_id,account_id,label,expected strings")
                continue
            reference(row["order_id"], "orders", where)
            reference(row["account_id"], "accounts", where)
            if row["expected"] not in ("ESCALATE", "REVIEW", "DISMISS"):
                issue(where, "Expected recommendation must be ESCALATE, REVIEW or DISMISS")
            pair = (row["order_id"], row["account_id"])
            if pair in pairs:
                issue(where, "Duplicate labelled pair")
            pairs.add(pair)
            labels[row["label"]] += 1
    if not normalized["orders"]:
        issue("orders", "No fund orders; investigations will produce no cases", "warning")
    if not normalized["prices"]:
        issue("prices", "No price bars; trade evidence works but the price chart is unavailable", "warning")
    if not labels:
        issue("truth", "No labels; accuracy evaluation is unavailable", "warning")
    times = sorted(row["order_time"] for row in normalized["orders"])
    report = {"valid": error_count == 0, "counts": counts, "issues": issues, "errors": error_count,
              "fingerprint": None, "source": source, "date_range": {"start": times[0], "end": times[-1]} if times else None,
              "label_counts": dict(labels)}
    if not error_count:
        try:
            # Per-call files are read in filename order; hash the same canonical order before writing.
            normalized["calls"].sort(key=lambda call: call["call_id"])
            report["fingerprint"] = dataset_fingerprint(normalized)
        except (ValueError, TypeError):
            issue("bundle", "Input must contain finite JSON-compatible values")
            report.update(valid=False, errors=error_count)
    return report, normalized


def validate_bundle(bundle: Any, source: str = "upload") -> dict[str, Any]:
    """Return actionable validation issues without mutating the supplied data."""
    return _validate(bundle, source)[0]


def validate_directory(directory: str | Path) -> dict[str, Any]:
    try:
        return validate_bundle(read_bundle(directory), Path(directory).name)
    except (OSError, ValueError, TypeError) as exc:
        return {"valid": False, "counts": {}, "issues": [{"severity": "error", "location": "dataset",
                "message": f"Cannot read dataset ({type(exc).__name__}); check file formats and permissions"}],
                "errors": 1, "fingerprint": None, "source": Path(directory).name, "date_range": None, "label_counts": {}}


class DatasetRegistry:
    """Persist an active pointer only after a complete validated import is on disk."""

    def __init__(self, runtime: Path, default: Path):
        self.runtime = runtime.resolve()
        self.default = default.resolve()
        self.root = self.runtime / "datasets"
        self.pointer = self.runtime / "active-dataset.json"

    @property
    def active_dir(self) -> Path:
        if self.pointer.is_file():
            value = _json(self.pointer).get("fingerprint", "")
            if not re.fullmatch(r"[a-f0-9]{64}", value):
                raise ValueError("invalid active dataset pointer")
            path = self.root / value
            if not path.is_dir():
                raise ValueError("active dataset is missing")
            return path
        return self.default

    def import_bundle(self, bundle: Any) -> tuple[Path, dict[str, Any]]:
        report, normalized = _validate(bundle, "import")
        if not report["valid"]:
            raise DatasetValidationError(report)
        self.root.mkdir(parents=True, exist_ok=True)
        target = self.root / report["fingerprint"]
        temporary = Path(tempfile.mkdtemp(prefix=".import-", dir=self.root))
        try:
            (temporary / "calls").mkdir()
            for name in MODELS:
                if name == "calls":
                    for call in normalized[name]:
                        (temporary / "calls" / (call["call_id"] + ".json")).write_text(json.dumps(call, ensure_ascii=False), encoding="utf-8")
                else:
                    (temporary / f"{name}.json").write_text(json.dumps(normalized[name], ensure_ascii=False), encoding="utf-8")
            (temporary / "truth.json").write_text(json.dumps(normalized["truth"]), encoding="utf-8")
            with (temporary / "prices.csv").open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=PRICE_FIELDS)
                writer.writeheader()
                writer.writerows(normalized["prices"])
            if target.exists():
                if validate_directory(target).get("fingerprint") != report["fingerprint"]:
                    raise ValueError("existing dataset failed its integrity check")
            else:
                os.replace(temporary, target)
            pointer = self.runtime / (".active-" + temporary.name + ".json")
            try:
                pointer.write_text(json.dumps({"fingerprint": report["fingerprint"]}), encoding="utf-8")
                os.replace(pointer, self.pointer)
            finally:
                pointer.unlink(missing_ok=True)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
        report.update(imported=True, source=target.name)
        return target, report
