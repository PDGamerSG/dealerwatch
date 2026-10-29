"""Load a DealerWatch data directory (see CONTRACT.md "Data directory layout")."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from dealerwatch.models import Account, Call, Clause, Dealer, FundOrder, Link, Person, Trade

REPO_ROOT = Path(__file__).resolve().parent.parent


def parse_ts(value: str) -> datetime:
    """Parse an ISO-8601 IST timestamp without offset."""
    return datetime.fromisoformat(value)


def minutes_between(earlier: str, later: str) -> float:
    """Minutes from `earlier` to `later` (negative if `later` is before `earlier`)."""
    return (parse_ts(later) - parse_ts(earlier)).total_seconds() / 60.0


@dataclass
class Universe:
    """Everything the pipeline reads from one data directory."""
    data_dir: str
    dealers: list[Dealer] = field(default_factory=list)
    persons: list[Person] = field(default_factory=list)
    accounts: list[Account] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    orders: list[FundOrder] = field(default_factory=list)
    trades: list[Trade] = field(default_factory=list)
    calls: list[Call] = field(default_factory=list)
    clauses: list[Clause] = field(default_factory=list)
    truth: dict[str, Any] = field(default_factory=lambda: {"cases": []})


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def clauses_path(data_dir: str | Path) -> Path | None:
    """Locate clauses.json: in the data dir, its sibling reference dir, or the repo's data/reference."""
    base = Path(data_dir)
    for cand in (base / "clauses.json",
                 base.parent / "reference" / "clauses.json",
                 REPO_ROOT / "data" / "reference" / "clauses.json"):
        if cand.exists():
            return cand
    return None


def load_universe(data_dir: str | Path) -> Universe:
    """Parse all JSON files of a data directory into models. Missing files load as empty."""
    base = Path(data_dir)
    if not base.is_dir():
        raise FileNotFoundError(f"data directory not found: {base}")
    calls_dir = base / "calls"
    calls = [Call.model_validate(_read_json(p, {})) for p in sorted(calls_dir.glob("*.json"))] \
        if calls_dir.is_dir() else []
    cpath = clauses_path(base)
    return Universe(
        data_dir=str(base),
        dealers=[Dealer.model_validate(x) for x in _read_json(base / "dealers.json", [])],
        persons=[Person.model_validate(x) for x in _read_json(base / "persons.json", [])],
        accounts=[Account.model_validate(x) for x in _read_json(base / "accounts.json", [])],
        links=[Link.model_validate(x) for x in _read_json(base / "links.json", [])],
        orders=[FundOrder.model_validate(x) for x in _read_json(base / "orders.json", [])],
        trades=[Trade.model_validate(x) for x in _read_json(base / "trades.json", [])],
        calls=calls,
        clauses=[Clause.model_validate(x) for x in _read_json(cpath, [])] if cpath else [],
        truth=_read_json(base / "truth.json", {"cases": []}),
    )
