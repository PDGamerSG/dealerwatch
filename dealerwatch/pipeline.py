"""End-to-end run: detect -> link -> gather -> extract -> verify -> narrate, into the store and ledger."""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from toolkit.ledger import Ledger
from toolkit.llm import get_llm

from dealerwatch import config
from dealerwatch.agent.case import make_case
from dealerwatch.agent.extract import extract_cues
from dealerwatch.agent.gather import TranscriptCache, gather_calls
from dealerwatch.agent.verify import build_chain, recommend
from dealerwatch.detect.links import build_graph, link_path, network_numbers
from dealerwatch.detect.sandwich import find_candidates
from dealerwatch.io import load_universe
from dealerwatch.models import Account, Dealer, LeakCue, Recommendation, RunStats
from dealerwatch.store import Store

ACTOR = "pipeline"


def _unknown_account(account_id: str) -> Account:
    return Account(account_id=account_id, holder_name="UNKNOWN (no KYC record)", pan_masked="", mobile="",
                   email="", address="", bank_account="", device_id="")


def _unknown_dealer(dealer_id: str) -> Dealer:
    return Dealer(dealer_id=dealer_id, name="UNKNOWN (not in dealer master)", desk_phone="", mobile="", email="")


def run(data_dir: str, runtime_dir: str, llm: Any = None) -> RunStats:
    """Run the full pipeline on a data directory. Resets runtime/dealerwatch.db and runtime/ledger.db."""
    started = time.perf_counter()
    runtime = Path(runtime_dir)
    runtime.mkdir(parents=True, exist_ok=True)
    store = Store(runtime / config.DB_FILE)
    store.reset()
    ledger = Ledger(str(runtime / config.LEDGER_FILE))
    ledger.reset()
    llm = llm if llm is not None else get_llm()
    calls_before = int(llm.stats.get("calls", 0))
    fallbacks_before = int(llm.stats.get("fallbacks", 0))
    try:
        uni = load_universe(data_dir)
        ledger.append(ACTOR, "run.start", {
            "data_dir": str(data_dir), "orders": len(uni.orders), "trades": len(uni.trades),
            "calls": len(uni.calls), "accounts": len(uni.accounts), "links": len(uni.links),
            "llm_provider": llm.stats.get("provider"), "llm_model": llm.stats.get("model"),
            "asr_env": os.environ.get("DW_ASR", "replay"),
            "params": {"pre_window_min": config.PRE_WINDOW_MIN, "post_window_min": config.POST_WINDOW_MIN,
                       "call_lookback_min": config.CALL_LOOKBACK_MIN, "min_pre_qty": config.MIN_PRE_QTY},
        })

        candidates = find_candidates(uni.orders, uni.trades)
        ledger.append(ACTOR, "detect.candidates", {
            "count": len(candidates),
            "candidates": [{"candidate_id": c.candidate_id, "score": c.score} for c in candidates],
        })

        graph = build_graph(uni.dealers, uni.persons, uni.accounts, uni.links)
        orders = {o.order_id: o for o in uni.orders}
        accounts = {a.account_id: a for a in uni.accounts}
        dealers = {d.dealer_id: d for d in uni.dealers}
        trades = {t.trade_id: t for t in uni.trades}
        clauses = {c.clause_id: c for c in uni.clauses}
        scrips = list(dict.fromkeys([*config.SCRIPS, *(o.scrip for o in uni.orders)]))
        transcripts: TranscriptCache = {}
        cue_cache: dict[str, list[LeakCue]] = {}
        asr_used: set[str] = set()
        counts = {r: 0 for r in Recommendation}

        for n, cand in enumerate(candidates, start=1):
            t0 = time.perf_counter()
            order = orders[cand.order_id]
            path = link_path(graph, order.dealer_id, cand.account_id)
            numbers = network_numbers(graph, order.dealer_id, cand.account_id)
            ledger.append(ACTOR, "link.path", {
                "candidate_id": cand.candidate_id,
                "hops": [{"src": lk.src, "dst": lk.dst, "kind": lk.kind} for lk in path],
                "network_numbers": len(numbers),
            })

            calls, providers = gather_calls(order, uni.calls, numbers, uni.data_dir, transcripts)
            asr_used |= providers
            ledger.append(ACTOR, "gather.calls", {"candidate_id": cand.candidate_id,
                                                  "call_ids": [c.call_id for c in calls],
                                                  "asr": sorted(providers)})

            cues: list[LeakCue] = []
            for call in calls:
                if call.call_id not in cue_cache:
                    cue_cache[call.call_id] = extract_cues(call, call.utterances, scrips, llm)
                cues.extend(cue_cache[call.call_id])
            ledger.append(ACTOR, "extract.cues", {
                "candidate_id": cand.candidate_id,
                "cues": [{"call_id": q.call_id, "utterance_ids": q.utterance_ids, "scrip": q.scrip,
                          "extractor": q.extractor} for q in cues],
            })

            chain = build_chain(cand, order, trades, path, calls, cues, clauses)
            ledger.append(ACTOR, "verify.chain", {"candidate_id": cand.candidate_id,
                                                  "chain": {lk.key: lk.ok for lk in chain},
                                                  "recommendation": recommend(chain).value})
            case = make_case(f"CASE-{n:04d}", cand, order,
                             accounts.get(cand.account_id) or _unknown_account(cand.account_id),
                             dealers.get(order.dealer_id) or _unknown_dealer(order.dealer_id),
                             path=path, calls=calls, cues=cues, chain=chain, clauses=clauses,
                             trades=trades, llm=llm)
            case = case.model_copy(update={"latency_ms": int(round((time.perf_counter() - t0) * 1000))})
            store.save_case(case)
            counts[case.recommendation] += 1
            ledger.append(ACTOR, "case.created", {
                "case_id": case.case_id, "candidate_id": cand.candidate_id,
                "recommendation": case.recommendation.value, "summary_source": case.summary_source,
                "summary_rejected_reason": case.summary_rejected_reason, "latency_ms": case.latency_ms,
            })

        stats = RunStats(
            orders=len(uni.orders), trades=len(uni.trades), calls=len(uni.calls),
            candidates=len(candidates), cases=len(candidates),
            escalate=counts[Recommendation.ESCALATE], review=counts[Recommendation.REVIEW],
            dismiss=counts[Recommendation.DISMISS],
            llm_provider=str(llm.stats.get("provider", "mock")),
            llm_calls=int(llm.stats.get("calls", 0)) - calls_before,
            llm_fallbacks=int(llm.stats.get("fallbacks", 0)) - fallbacks_before,
            asr_provider="+".join(sorted(asr_used)) or os.environ.get("DW_ASR", "replay"),
            total_ms=int(round((time.perf_counter() - started) * 1000)),
        )
        store.save_stats(stats)
        ledger.append(ACTOR, "run.end", stats.model_dump(mode="json"))
        return stats
    finally:
        ledger.close()
