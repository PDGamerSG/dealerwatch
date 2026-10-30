"""DealerWatch HTTP API and its basic same-origin frontend.

Run ``python -m uvicorn dealerwatch.api:app --host 127.0.0.1 --port 8077``.
Use one application worker per runtime directory; investigations have a bounded background worker.
"""
from __future__ import annotations

import logging
import os
from collections import Counter
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import Body, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from dealerwatch.datasets import DatasetValidationError, read_bundle, validate_bundle
from dealerwatch.decisions import apply_decision
from dealerwatch.exports import csv_export, evidence_export
from dealerwatch.jobs import BusyError
from dealerwatch.models import Case, CaseStatus, Recommendation
from dealerwatch.security import COOKIE, SESSION_SECONDS, RequestLimits, Security
from dealerwatch.services import CSP, WEB_DIR, Services, _resolve, _summary

log = logging.getLogger(__name__)


class DecisionIn(BaseModel):
    action: Literal["approve_escalation", "request_info", "dismiss", "start_review"]
    reviewer: str = Field(default="", max_length=80)
    note: str = Field(default="", max_length=2000)
    expected_revision: int | None = Field(default=None, ge=0)


class TamperIn(BaseModel):
    seq: int = Field(ge=1)


class SessionIn(BaseModel):
    token: str = Field(min_length=1, max_length=1024, repr=False)


def create_app(data_dir: str | os.PathLike | None = None,
               runtime_dir: str | os.PathLike | None = None) -> FastAPI:
    svc = Services(_resolve(data_dir, "DW_DATA", "data/generated"),
                   _resolve(runtime_dir, "DW_RUNTIME", "runtime"))
    security = Security()

    @asynccontextmanager
    async def lifespan(_app):
        await run_in_threadpool(svc.bootstrap)
        try:
            yield
        finally:
            await run_in_threadpool(svc.jobs.close)

    app = FastAPI(title="DealerWatch", version="1.0.0", docs_url=None, redoc_url=None,
                  openapi_url="/api/openapi.json", lifespan=lifespan)
    app.state.svc, app.state.security = svc, security

    @app.middleware("http")
    async def guard(request: Request, call_next):
        public = {"/api/health", "/api/ready", "/api/session"}
        response = None
        if (request.url.path.startswith("/api/") or request.url.path.startswith("/audio/")) and request.url.path not in public:
            try:
                security.require(request)
            except HTTPException as exc:
                response = JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers)
        if response is None:
            response = await call_next(request)
        response.headers.update({"Content-Security-Policy": CSP, "X-Content-Type-Options": "nosniff",
                                 "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY",
                                 "Cache-Control": "no-store"})
        return response

    app.add_middleware(RequestLimits, max_bytes=int(os.environ.get("DW_MAX_BODY_BYTES", str(32 * 1024 * 1024))))

    @app.exception_handler(DatasetValidationError)
    async def invalid_data(_request, exc):
        return JSONResponse({"detail": exc.report}, status_code=422)

    @app.exception_handler(BusyError)
    async def busy(_request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(Exception)
    async def unhandled(request, exc):
        request_id = getattr(request.state, "request_id", "unknown")
        log.error("request %s failed: %s", request_id, type(exc).__name__)
        return JSONResponse({"detail": f"Internal error ({type(exc).__name__})", "request_id": request_id}, status_code=500)

    def find_case(case_id: str) -> Case:
        case = svc.store().get_case(case_id)
        if case is None:
            raise HTTPException(404, f"Case {case_id} not found")
        return case

    def demo(request: Request):
        security.require(request, "admin")
        if os.environ.get("DW_DEMO", "0") != "1":
            raise HTTPException(403, "Demo mutations are disabled; enable DW_DEMO=1 explicitly")

    @app.get("/api/session")
    def session(request: Request):
        return security.status(request)

    @app.post("/api/session")
    def login(request: Request, body: SessionIn, response: Response):
        cookie, principal = security.login(request, body.token)
        response.set_cookie(COOKIE, cookie, max_age=SESSION_SECONDS, httponly=True, samesite="strict",
                            secure=request.url.scheme == "https" or os.environ.get("DW_COOKIE_SECURE") == "1")
        return {"auth_required": security.required, "authenticated": True, "role": principal.role,
                "reviewer": principal.reviewer, "demo_enabled": os.environ.get("DW_DEMO", "0") == "1"}

    @app.delete("/api/session")
    def logout(request: Request, response: Response):
        security.logout(request)
        response.delete_cookie(COOKIE)
        return {"ok": True}

    @app.get("/api/health")
    def health():
        stats = svc.store().get_stats()
        return {"ok": True, "llm": stats.llm_provider if stats else os.environ.get("DW_LLM", "mock"),
                "asr": stats.asr_provider if stats else os.environ.get("DW_ASR", "replay"),
                "cases": svc.store().count_cases(), "has_data": svc.has_data(), "version": "1.0.0"}

    @app.get("/api/ready")
    def ready(response: Response):
        report = svc.data_report()
        svc.store().count_cases()
        if not report["valid"]:
            response.status_code = 503
        return {"ready": report["valid"], "data_valid": report["valid"], "database": "ok"}

    @app.get("/api/data")
    def data_report():
        return svc.data_report()

    @app.post("/api/data/validate")
    def validate(request: Request, body: Any = Body(...)):
        security.require(request, "admin")
        return validate_bundle(body)

    @app.post("/api/data/import", status_code=201)
    def import_data(request: Request, body: Any = Body(...)):
        principal = security.require(request, "admin")
        with svc.jobs.exclusive():
            _path, report = svc.registry.import_bundle(body)
            svc.invalidate()
            with svc.ledger() as ledger:
                ledger.append(principal.reviewer or "operator", "data.imported",
                              {"dataset_id": report["fingerprint"], "counts": report["counts"]})
        return report

    @app.get("/api/data/export")
    def export_data():
        if not svc.has_data():
            raise HTTPException(404, "No dataset to export")
        return JSONResponse(read_bundle(svc.data_dir), headers={"Content-Disposition": 'attachment; filename="dealerwatch-dataset.json"'})

    @app.post("/api/run")
    def run(request: Request):
        security.require(request, "admin")
        return svc.run().model_dump(mode="json")

    @app.post("/api/runs", status_code=202)
    def submit_run(request: Request):
        security.require(request, "admin")
        report = svc.data_report()
        if not report["valid"]:
            raise DatasetValidationError(report)
        return svc.jobs.submit()

    @app.get("/api/runs")
    def runs(limit: int = Query(50, ge=1, le=200)):
        return svc.jobs.list(limit)

    @app.get("/api/runs/{run_id}")
    def run_detail(run_id: str):
        job = svc.jobs.get(run_id)
        if job is None:
            raise HTTPException(404, "Run not found")
        return job

    @app.get("/api/stats")
    def stats():
        current = svc.store().get_stats()
        return current.model_dump(mode="json") if current else None

    @app.get("/api/dashboard")
    def dashboard():
        cases = svc.store().list_cases()
        def group(key):
            result = {}
            for case in cases:
                label = key(case)
                item = result.setdefault(label, {"count": 0, "profit_inr": 0})
                item["count"] += 1
                item["profit_inr"] = round(item["profit_inr"] + case.candidate.profit_inr, 2)
            return result
        return {"cases": len(cases), "by_recommendation": dict(Counter(c.recommendation.value for c in cases)),
                "by_status": dict(Counter(c.status.value for c in cases)),
                "total_profit_inr": round(sum(c.candidate.profit_inr for c in cases), 2),
                "by_scrip": group(lambda c: c.candidate.scrip), "by_dealer": group(lambda c: c.dealer.dealer_id),
                "latest_run": next(iter(svc.jobs.list(1)), None)}

    @app.get("/api/cases")
    def cases(response: Response, status: CaseStatus | None = None, recommendation: Recommendation | None = None,
              q: str = Query("", max_length=200), scrip: str | None = None, dealer_id: str | None = None,
              limit: int | None = Query(None, ge=1, le=1000), offset: int = Query(0, ge=0)):
        rows, count = svc.store().query_cases(status=status, recommendation=recommendation, q=q, scrip=scrip,
                                             dealer_id=dealer_id, limit=limit, offset=offset)
        response.headers["X-Total-Count"] = str(count)
        return [_summary(case) for case in rows]

    @app.get("/api/export/cases.csv")
    def export_cases(status: CaseStatus | None = None, recommendation: Recommendation | None = None,
                     q: str = Query("", max_length=200), scrip: str | None = None, dealer_id: str | None = None):
        rows, _ = svc.store().query_cases(status=status, recommendation=recommendation, q=q, scrip=scrip, dealer_id=dealer_id)
        return Response(csv_export([_summary(case) for case in rows]), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": 'attachment; filename="dealerwatch-cases.csv"'})

    @app.get("/api/cases/{case_id}")
    def case_detail(case_id: str):
        return svc.case_detail(find_case(case_id))

    @app.get("/api/cases/{case_id}/export")
    def case_export(case_id: str):
        detail = svc.case_detail(find_case(case_id))
        with svc.ledger() as ledger:
            bundle = evidence_export(detail, ledger.entries(), ledger.verify(), ledger.head())
        return JSONResponse(bundle, headers={"Content-Disposition": f'attachment; filename="{case_id}-evidence.json"'})

    @app.post("/api/cases/{case_id}/decision")
    def decide(case_id: str, request: Request, body: DecisionIn,
               idempotency_key: str | None = Header(None, min_length=1, max_length=120)):
        principal = security.require(request)
        reviewer = principal.reviewer or body.reviewer.strip()
        if not reviewer:
            raise HTTPException(422, "Reviewer is required")
        try:
            with svc.ledger() as ledger:
                case = apply_decision(svc.store(), ledger, case_id, body.action, reviewer, body.note.strip(),
                                      expected_revision=body.expected_revision, idempotency_key=idempotency_key)
        except KeyError as exc:
            raise HTTPException(404, f"Case {case_id} not found") from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return case.model_dump(mode="json", exclude={"evidence_snapshot"})

    @app.get("/api/ledger")
    def ledger_entries(limit: int = Query(200, ge=1, le=5000), offset: int = Query(0, ge=0)):
        with svc.ledger() as ledger:
            return {"count": ledger.count(), "head": ledger.head(), "entries": ledger.entries(limit, offset)}

    @app.get("/api/ledger/verify")
    def verify_ledger():
        with svc.ledger() as ledger:
            return ledger.verify()

    @app.post("/api/ledger/tamper-demo")
    def tamper(request: Request, body: TamperIn):
        demo(request)
        with svc.jobs.exclusive(), svc.ledger() as ledger:
            found = [entry for entry in ledger.entries(1, body.seq - 1) if entry["seq"] == body.seq]
            if not found:
                raise HTTPException(404, "Ledger sequence not found")
            ledger.tamper_for_demo(body.seq, {**found[0]["payload"], "edited": "tamper demo"})
            return ledger.verify()

    @app.post("/api/ledger/restore")
    def restore(request: Request):
        demo(request)
        stats = svc.run(reset=True)
        with svc.ledger() as ledger:
            return {"stats": stats.model_dump(mode="json"), "verify": ledger.verify()}

    @app.get("/api/eval")
    def evaluation(request: Request, refresh: bool = False):
        if refresh:
            security.require(request, "admin")
        return svc.eval_result(refresh)

    @app.get("/audio/{call_id}")
    def audio(call_id: str, case_id: str | None = None):
        path = svc.audio_path(call_id, find_case(case_id) if case_id else None)
        if path is None:
            raise HTTPException(404, "Audio not found")
        return FileResponse(path, media_type="audio/wav")

    @app.get("/", include_in_schema=False)
    @app.get("/app", include_in_schema=False)  # same path the hosted site uses next to the landing page
    def index():
        return FileResponse(WEB_DIR / "index.html", media_type="text/html")

    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
    return app


app = create_app()
