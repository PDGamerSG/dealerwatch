"""FastAPI app for DealerWatch: alert queue, case detail, human decisions, ledger and eval.

Run with ``python -m uvicorn dealerwatch.api:app --port 8077``. Env ``DW_DATA`` (default
``data/generated``) and ``DW_RUNTIME`` (default ``runtime``) choose the data and runtime dirs.
No CORS middleware is installed: the UI is served from the same origin.
"""
from __future__ import annotations

import bisect
import csv
import dataclasses
import json
import logging
import os
import re
import threading
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, AsyncIterator, Iterator, Literal, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from dealerwatch import config, pipeline
from dealerwatch.decisions import apply_decision
from dealerwatch.detect.links import normalize_phone
from dealerwatch.eval.harness import evaluate
from dealerwatch.io import load_universe
from dealerwatch.models import Case, CaseStatus, Recommendation, RunStats
from dealerwatch.store import Store
from toolkit.ledger import Ledger

log = logging.getLogger("dealerwatch.api")

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = Path(__file__).resolve().parent / "web"
CALL_ID_RE = re.compile(r"^C-\d{3}$")
PHONE_RE = re.compile(r"^\+?[\d\s-]{10,16}$")
PRICE_WINDOW = timedelta(minutes=120)
REC_RANK = {Recommendation.ESCALATE: 0, Recommendation.REVIEW: 1, Recommendation.DISMISS: 2}
CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "media-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; "
    "frame-ancestors 'none'; form-action 'self'"
)


class DecisionIn(BaseModel):
    """Body of POST /api/cases/{case_id}/decision."""
    action: Literal["approve_escalation", "request_info", "dismiss", "start_review"]
    reviewer: str = Field(min_length=1, max_length=80)
    note: str = Field(default="", max_length=2000)


class TamperIn(BaseModel):
    """Body of POST /api/ledger/tamper-demo."""
    seq: int = Field(ge=0)


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Attribute or key lookup, so universe items may be models, dataclasses or dicts."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _dump(obj: Any) -> Any:
    """JSON-ready form of a pydantic model, dataclass or plain dict."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    return obj


def _index(items: Any, key: str) -> dict[str, Any]:
    """Map id -> item for a list (or pass a dict through)."""
    if isinstance(items, dict):
        return {str(k): v for k, v in items.items()}
    return {str(_get(it, key)): it for it in (items or [])}


def _resolve(explicit: str | os.PathLike[str] | None, env: str, default: str) -> Path:
    """Explicit arg, else env var (relative to cwd), else default relative to the project root."""
    if explicit is not None:
        return Path(explicit).resolve()
    value = os.environ.get(env)
    return Path(value).resolve() if value else (ROOT / default).resolve()


def _load_prices(path: Path) -> dict[str, tuple[list[str], list[float]]]:
    """Read prices.csv into scrip -> (sorted ISO times, closes)."""
    rows: dict[str, list[tuple[str, float]]] = {}
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            rows.setdefault(row["scrip"], []).append((row["time"].replace(" ", "T"), float(row["close"])))
    series: dict[str, tuple[list[str], list[float]]] = {}
    for scrip, pts in rows.items():
        pts.sort()
        series[scrip] = ([t for t, _ in pts], [c for _, c in pts])
    return series


def _summary(case: Case) -> dict[str, Any]:
    """Queue row for a case."""
    return {
        "case_id": case.case_id,
        "scrip": case.candidate.scrip,
        "account_id": case.account.account_id,
        "holder_name": case.account.holder_name,
        "dealer_id": case.dealer.dealer_id,
        "recommendation": case.recommendation.value,
        "status": case.status.value,
        "score": case.candidate.score,
        "profit_inr": case.candidate.profit_inr,
        "created_at": case.created_at,
        "order_id": case.order.order_id,
        "side": case.order.side.value,
        "order_time": case.order.order_time,
    }


class Services:
    """Holds paths, caches and the pipeline lock for one app instance."""

    def __init__(self, data_dir: Path, runtime_dir: Path) -> None:
        self.data_dir = data_dir
        self.runtime_dir = runtime_dir
        self.lock = threading.RLock()
        self._universe_key: Optional[float] = None
        self._universe: Any = None
        self._indexes: dict[str, dict[str, Any]] = {}
        self._prices: Optional[dict[str, tuple[list[str], list[float]]]] = None

    # ----- storage -----
    def store(self) -> Store:
        """Case store in the runtime dir (Store opens a connection per operation)."""
        return Store(self.runtime_dir / config.DB_FILE)

    @contextmanager
    def ledger(self) -> Iterator[Ledger]:
        """Hash-chained ledger in the runtime dir, closed after use."""
        ledger = Ledger(str(self.runtime_dir / config.LEDGER_FILE))
        try:
            yield ledger
        finally:
            ledger.close()

    def has_data(self) -> bool:
        """True when a generated universe exists in the data dir."""
        return (self.data_dir / "orders.json").is_file()

    # ----- pipeline -----
    def run(self) -> RunStats:
        """Run the full pipeline (it resets the store and ledger itself)."""
        if not self.has_data():
            raise HTTPException(409, f"no data in {self.data_dir.name}; run python -m dealerwatch.data.synth first")
        with self.lock:
            stats = pipeline.run(str(self.data_dir), str(self.runtime_dir))
            self._universe_key = None
            self._prices = None
            return stats

    def bootstrap(self) -> None:
        """Run the pipeline once at startup when the store is empty and data exists."""
        try:
            if self.has_data() and not self.store().list_cases():
                stats = self.run()
                log.info("startup pipeline run: %s cases", stats.cases)
        except Exception:  # startup must not crash the server; /api/run reports errors
            log.exception("startup pipeline run failed")

    # ----- universe lookups -----
    def universe(self) -> Any:
        """Cached universe, reloaded when orders.json changes."""
        key = (self.data_dir / "orders.json").stat().st_mtime
        with self.lock:
            if self._universe is None or key != self._universe_key:
                uni = load_universe(str(self.data_dir))
                self._indexes = {
                    "trades": _index(_get(uni, "trades"), "trade_id"),
                    "calls": _index(_get(uni, "calls"), "call_id"),
                    "clauses": _index(_get(uni, "clauses"), "clause_id"),
                    "dealers": _index(_get(uni, "dealers"), "dealer_id"),
                    "persons": _index(_get(uni, "persons"), "person_id"),
                    "accounts": _index(_get(uni, "accounts"), "account_id"),
                }
                phones: dict[str, str] = {}
                for name, field, key in (("persons", "name", "person_id"), ("accounts", "holder_name", "account_id")):
                    for item in self._indexes[name].values():
                        number = normalize_phone(_get(item, "mobile"))
                        if number:
                            phones.setdefault(number, f"{_get(item, field)} ({_get(item, key)})")
                self._indexes["phones"] = phones
                self._universe, self._universe_key, self._prices = uni, key, None
            return self._universe

    def index(self, name: str) -> dict[str, Any]:
        """Id index over one universe collection."""
        self.universe()
        return self._indexes.get(name, {})

    def price_slice(self, scrip: str, order_time: str) -> list[dict[str, Any]]:
        """Minute closes for scrip within +-120 min of the order time."""
        with self.lock:
            if self._prices is None:
                path = self.data_dir / "prices.csv"
                self._prices = _load_prices(path) if path.is_file() else {}
            times, closes = self._prices.get(scrip, ([], []))
        t0 = datetime.fromisoformat(order_time)
        lo = bisect.bisect_left(times, (t0 - PRICE_WINDOW).isoformat(timespec="seconds"))
        hi = bisect.bisect_right(times, (t0 + PRICE_WINDOW).isoformat(timespec="seconds"))
        return [{"time": times[i], "close": closes[i]} for i in range(lo, hi)]

    def audio_path(self, call_id: str) -> Optional[Path]:
        """Wav path for a call id, or None if the id is invalid or no file exists."""
        if not CALL_ID_RE.fullmatch(call_id):
            return None
        audio_dir = (self.data_dir / "audio").resolve()
        path = (audio_dir / f"{call_id}.wav").resolve()
        return path if path.parent == audio_dir and path.is_file() else None

    def node_label(self, node: str) -> str:
        """Human label for a link-graph node or transcript speaker."""
        for name, field in (("dealers", "name"), ("persons", "name"), ("accounts", "holder_name")):
            item = self.index(name).get(node)
            if item is not None:
                label = str(_get(item, field, node))
                relation = _get(item, "relation") if name == "persons" else None
                return f"{label} ({relation})" if relation else label
        if ":" in node:
            return node.split(":", 1)[1]
        if PHONE_RE.fullmatch(node):
            return self.index("phones").get(normalize_phone(node), node)
        return node

    def case_detail(self, case: Case) -> dict[str, Any]:
        """Full case plus price slice, sandwich trades, call details, clauses and node labels."""
        out = case.model_dump(mode="json")
        trades = self.index("trades")
        calls = self.index("calls")
        clauses = self.index("clauses")
        trade_ids = case.candidate.pre_trade_ids + case.candidate.post_trade_ids
        out["prices"] = self.price_slice(case.order.scrip, case.order.order_time)
        out["trades"] = [_dump(trades[t]) for t in trade_ids if t in trades]
        call_details = []
        for cid in case.calls:
            if cid in calls:
                call = dict(_dump(calls[cid]))
                call["has_audio"] = self.audio_path(cid) is not None
                call_details.append(call)
        out["call_details"] = call_details
        out["clauses"] = [_dump(clauses[c]) for c in case.clause_ids if c in clauses]
        nodes = {case.dealer.dealer_id, case.account.account_id}
        for link in case.link_path:
            nodes.update((link.src, link.dst))
        for call in call_details:
            nodes.add(str(call.get("counterparty_number", "")))
            nodes.update(str(u.get("speaker", "")) for u in call.get("utterances", []))
        out["node_labels"] = {n: self.node_label(n) for n in sorted(nodes) if n}
        return out

    def eval_result(self, refresh: bool) -> dict[str, Any]:
        """Cached eval dict from runtime/eval.json, running the harness when missing."""
        path = self.runtime_dir / "eval.json"
        with self.lock:
            if path.is_file() and not refresh:
                return json.loads(path.read_text(encoding="utf-8"))
            if not self.has_data():
                raise HTTPException(409, "no data to evaluate; generate the synthetic universe first")
            eval_dir = self.runtime_dir / "eval"
            eval_dir.mkdir(parents=True, exist_ok=True)
            result = evaluate(str(self.data_dir), str(eval_dir))
            self.runtime_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
            return json.loads(json.dumps(result, default=str))


def _tampered(payload: dict[str, Any]) -> dict[str, Any]:
    """A plausibly edited payload for the tamper demo (hashes are left untouched)."""
    edited = dict(payload)
    if "recommendation" in edited:
        edited["recommendation"] = "DISMISS"
    if "profit_inr" in edited:
        edited["profit_inr"] = 0
    edited["edited"] = "tamper demo"
    return edited


def create_app(data_dir: str | os.PathLike[str] | None = None,
               runtime_dir: str | os.PathLike[str] | None = None) -> FastAPI:
    """Build the FastAPI app for one data dir and runtime dir."""
    svc = Services(_resolve(data_dir, "DW_DATA", "data/generated"),
                   _resolve(runtime_dir, "DW_RUNTIME", "runtime"))

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        await run_in_threadpool(svc.bootstrap)
        yield

    app = FastAPI(title="DealerWatch", docs_url=None, redoc_url=None,
                  openapi_url="/api/openapi.json", lifespan=lifespan)
    app.state.svc = svc

    @app.middleware("http")
    async def security_headers(request: Request, call_next: Any) -> Any:
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = CSP
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        if not request.url.path.startswith("/audio/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(Exception)
    async def unhandled(_request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error")
        return JSONResponse({"detail": f"internal error ({type(exc).__name__})"}, status_code=500)

    def get_case_or_404(case_id: str) -> Case:
        case = svc.store().get_case(case_id)
        if case is None:
            raise HTTPException(404, f"case {case_id} not found")
        return case

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        stats = svc.store().get_stats()
        return {
            "ok": True,
            "llm": stats.llm_provider if stats else os.environ.get("DW_LLM", "mock"),
            "asr": stats.asr_provider if stats else os.environ.get("DW_ASR", "replay"),
            "cases": len(svc.store().list_cases()),
            "has_data": svc.has_data(),
        }

    @app.post("/api/run")
    def run() -> dict[str, Any]:
        return svc.run().model_dump(mode="json")

    @app.get("/api/stats")
    def stats() -> Optional[dict[str, Any]]:
        current = svc.store().get_stats()
        return current.model_dump(mode="json") if current else None

    @app.get("/api/cases")
    def list_cases(status: Optional[CaseStatus] = None,
                   recommendation: Optional[Recommendation] = None) -> list[dict[str, Any]]:
        cases = [c for c in svc.store().list_cases()
                 if (status is None or c.status == status)
                 and (recommendation is None or c.recommendation == recommendation)]
        cases.sort(key=lambda c: (REC_RANK[c.recommendation], -c.candidate.score, c.case_id))
        return [_summary(c) for c in cases]

    @app.get("/api/cases/{case_id}")
    def case_detail(case_id: str) -> dict[str, Any]:
        return svc.case_detail(get_case_or_404(case_id))

    @app.post("/api/cases/{case_id}/decision")
    def decide(case_id: str, body: DecisionIn) -> dict[str, Any]:
        get_case_or_404(case_id)
        reviewer = body.reviewer.strip()
        if not reviewer:
            raise HTTPException(422, "reviewer is required")
        try:
            with svc.lock, svc.ledger() as ledger:
                case = apply_decision(svc.store(), ledger, case_id, body.action, reviewer, body.note.strip())
        except KeyError as exc:
            raise HTTPException(404, f"case {case_id} not found") from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return case.model_dump(mode="json")

    @app.get("/api/ledger")
    def ledger_entries(limit: int = Query(200, ge=1, le=5000),
                       offset: int = Query(0, ge=0)) -> dict[str, Any]:
        """Entries oldest first (ascending seq), paged."""
        with svc.ledger() as ledger:
            return {"count": ledger.count(), "head": ledger.head(),
                    "entries": ledger.entries(limit=limit, offset=offset)}

    @app.get("/api/ledger/verify")
    def ledger_verify() -> dict[str, Any]:
        with svc.ledger() as ledger:
            return ledger.verify()

    @app.post("/api/ledger/tamper-demo")
    def ledger_tamper(body: TamperIn) -> dict[str, Any]:
        if os.environ.get("DW_DEMO", "1") != "1":
            raise HTTPException(403, "tamper demo disabled (DW_DEMO=0)")
        with svc.lock, svc.ledger() as ledger:
            found = ledger.entries(limit=1, offset=body.seq - 1) if body.seq >= 1 else []
            if not found or found[0]["seq"] != body.seq:  # seqs are contiguous from 1; scan if not
                found = [e for e in ledger.entries() if e["seq"] == body.seq]
            if not found:
                raise HTTPException(404, f"ledger seq {body.seq} not found")
            try:
                ledger.tamper_for_demo(body.seq, _tampered(found[0]["payload"]))
            except ValueError as exc:
                raise HTTPException(404, str(exc)) from exc
            return ledger.verify()

    @app.post("/api/ledger/restore")
    def ledger_restore() -> dict[str, Any]:
        stats = svc.run()
        with svc.ledger() as ledger:
            return {"stats": stats.model_dump(mode="json"), "verify": ledger.verify()}

    @app.get("/api/eval")
    def eval_metrics(refresh: bool = False) -> dict[str, Any]:
        return svc.eval_result(refresh)

    @app.get("/audio/{call_id}")
    def audio(call_id: str) -> FileResponse:
        path = svc.audio_path(call_id)
        if path is None:
            raise HTTPException(404, "audio not found")
        return FileResponse(path, media_type="audio/wav")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html", media_type="text/html")

    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
    return app


app = create_app()
