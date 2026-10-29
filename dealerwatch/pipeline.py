"""Detect, gather and analyse in memory; atomically publish evidence, statistics and audit."""
from __future__ import annotations

import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

from toolkit.ledger import Ledger
from toolkit.llm import get_llm

from dealerwatch import config
from dealerwatch.agent.case import make_case
from dealerwatch.agent.extract import extract_cues
from dealerwatch.agent.gather import TranscriptCache, gather_calls
from dealerwatch.agent.verify import build_chain, recommend
from dealerwatch.detect.links import build_graph, link_path, network_numbers
from dealerwatch.detect.sandwich import find_candidates
from dealerwatch.evidence_snapshot import EvidenceIndex, case_identity
from dealerwatch.io import load_universe
from dealerwatch.models import Account, Case, Dealer, LeakCue, Recommendation, RunStats
from dealerwatch.persistence import AuditEvent
from dealerwatch.store import Store

ACTOR = "pipeline"


def _unknown_account(account_id: str) -> Account:
    return Account(account_id=account_id, holder_name="UNKNOWN (no KYC record)", pan_masked="", mobile="",
                   email="", address="", bank_account="", device_id="")


def _unknown_dealer(dealer_id: str) -> Dealer:
    return Dealer(dealer_id=dealer_id, name="UNKNOWN (not in dealer master)", desk_phone="", mobile="", email="")


def run(data_dir: str, runtime_dir: str, llm: Any = None, *, reset: bool = False,
        run_id: str | None = None, progress: Callable[[str, int, int], None] | None = None,
        dataset_id: str | None = None) -> RunStats:
    """Publish a completed run; ordinary reruns preserve all cases and reviewer decisions.

    Explicit ``reset=True`` replaces the demo store/audit only after analysis succeeds.
    Progress callbacks run before publication; a callback error cannot leave a partial run.
    """
    started = time.perf_counter()
    run_id = run_id or uuid4().hex
    events: list[AuditEvent] = []

    def report(stage: str, completed: int, total: int) -> None:
        if progress is not None:
            progress(stage, completed, total)

    def record(action: str, payload: dict[str, Any]) -> None:
        events.append(AuditEvent(ACTOR, action, {**payload, "run_id": run_id, "dataset_id": dataset_id}))

    report("loading", 0, 1)
    uni = load_universe(data_dir)
    evidence = EvidenceIndex(uni, runtime_dir)
    fingerprint = evidence.fingerprint()
    dataset_id = dataset_id or fingerprint
    llm = llm if llm is not None else get_llm()
    calls_before = int(llm.stats.get("calls", 0))
    fallbacks_before = int(llm.stats.get("fallbacks", 0))
    record("run.start", {
        "data_dir": str(data_dir), "orders": len(uni.orders), "trades": len(uni.trades),
        "calls": len(uni.calls), "accounts": len(uni.accounts), "links": len(uni.links),
        "evidence_fingerprint": fingerprint,
        "llm_provider": llm.stats.get("provider"), "llm_model": llm.stats.get("model"),
        "asr_env": os.environ.get("DW_ASR", "replay"),
        "params": {"pre_window_min": config.PRE_WINDOW_MIN, "post_window_min": config.POST_WINDOW_MIN,
                   "call_lookback_min": config.CALL_LOOKBACK_MIN, "min_pre_qty": config.MIN_PRE_QTY},
    })
    report("detecting", 0, 1)
    candidates = find_candidates(uni.orders, uni.trades)
    record("detect.candidates", {
        "count": len(candidates),
        "candidates": [{"candidate_id": candidate.candidate_id, "score": candidate.score}
                       for candidate in candidates],
    })

    graph = build_graph(uni.dealers, uni.persons, uni.accounts, uni.links)
    orders = {order.order_id: order for order in uni.orders}
    accounts = {account.account_id: account for account in uni.accounts}
    dealers = {dealer.dealer_id: dealer for dealer in uni.dealers}
    trades = evidence.trades
    clauses = evidence.clauses
    scrips = list(dict.fromkeys([*config.SCRIPS, *(order.scrip for order in uni.orders)]))
    transcripts: TranscriptCache = {}
    cue_cache: dict[str, list[LeakCue]] = {}
    asr_used: set[str] = set()
    counts = {recommendation: 0 for recommendation in Recommendation}
    cases: list[Case] = []
    report("investigating", 0, len(candidates))

    for n, cand in enumerate(candidates, start=1):
        t0 = time.perf_counter()
        first_event = len(events)
        order = orders[cand.order_id]
        path = link_path(graph, order.dealer_id, cand.account_id)
        numbers = network_numbers(graph, order.dealer_id, cand.account_id)
        record("link.path", {
            "candidate_id": cand.candidate_id,
            "hops": [{"src": link.src, "dst": link.dst, "kind": link.kind} for link in path],
            "network_numbers": len(numbers),
        })
        calls, providers = gather_calls(order, evidence.calls, numbers, str(evidence.audio_dir), transcripts)
        asr_used |= providers
        record("gather.calls", {"candidate_id": cand.candidate_id,
                                "call_ids": [call.call_id for call in calls], "asr": sorted(providers)})
        cues: list[LeakCue] = []
        for call in calls:
            if call.call_id not in cue_cache:
                cue_cache[call.call_id] = extract_cues(call, call.utterances, scrips, llm)
            cues.extend(cue_cache[call.call_id])
        record("extract.cues", {
            "candidate_id": cand.candidate_id,
            "cues": [{"call_id": cue.call_id, "utterance_ids": cue.utterance_ids, "scrip": cue.scrip,
                      "extractor": cue.extractor} for cue in cues],
        })
        chain = build_chain(cand, order, trades, path, calls, cues, clauses)
        record("verify.chain", {"candidate_id": cand.candidate_id,
                                "chain": {link.key: link.ok for link in chain},
                                "recommendation": recommend(chain).value})
        case = make_case(cand.candidate_id, cand, order,
                         accounts.get(cand.account_id) or _unknown_account(cand.account_id),
                         dealers.get(order.dealer_id) or _unknown_dealer(order.dealer_id),
                         path=path, calls=calls, cues=cues, chain=chain, clauses=clauses,
                         trades=trades, llm=llm)
        snapshot = evidence.snapshot(case, calls)
        identity = case_identity(case, dataset_id, fingerprint, snapshot)
        case = case.model_copy(update={
            "case_id": identity, "dataset_id": dataset_id, "run_id": run_id, "evidence_snapshot": snapshot,
            "latency_ms": int(round((time.perf_counter() - t0) * 1000)),
        })
        # Include exact case identities on candidate events so historical exports cannot
        # accidentally collect another dataset's events for the same source candidate id.
        for event in events[first_event:]:
            event.payload["case_id"] = identity
        cases.append(case)
        counts[case.recommendation] += 1
        record("case.created", {
            "case_id": identity, "candidate_id": cand.candidate_id,
            "recommendation": case.recommendation.value, "summary_source": case.summary_source,
            "summary_rejected_reason": case.summary_rejected_reason, "latency_ms": case.latency_ms,
        })
        report("investigating", n, len(candidates))

    stats = RunStats(
        orders=len(uni.orders), trades=len(uni.trades), calls=len(uni.calls),
        candidates=len(candidates), cases=len(candidates),
        escalate=counts[Recommendation.ESCALATE], review=counts[Recommendation.REVIEW],
        dismiss=counts[Recommendation.DISMISS],
        llm_provider=str(llm.stats.get("provider", "mock")),
        llm_calls=int(llm.stats.get("calls", 0)) - calls_before,
        llm_fallbacks=int(llm.stats.get("fallbacks", 0)) - fallbacks_before,
        asr_provider="+".join(sorted(asr_used)) or os.environ.get("DW_ASR", "replay"),
        total_ms=int(round((time.perf_counter() - started) * 1000)), run_id=run_id, dataset_id=dataset_id,
    )
    record("run.end", stats.model_dump(mode="json"))
    report("publishing", len(cases), len(cases))
    runtime = Path(runtime_dir)
    runtime.mkdir(parents=True, exist_ok=True)
    store = Store(runtime / config.DB_FILE)
    ledger = Ledger(str(runtime / config.LEDGER_FILE))
    try:
        store.publish_run(cases, stats, events, ledger, reset=reset)
    finally:
        ledger.close()
    return stats
