"""End-to-end pipeline and eval harness on the seed-7 synthetic universe (DW_LLM=mock, DW_ASR=replay)."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from toolkit import grounding
from toolkit.ledger import Ledger

from dealerwatch import config
from dealerwatch.agent.case import build_evidence, evidence_json, template_summary
from dealerwatch.eval.harness import evaluate, main
from dealerwatch.io import load_universe
from dealerwatch.models import Case, RunStats
from dealerwatch.pipeline import run
from dealerwatch.store import Store

EXPECTED = {"TRUE_FR": "ESCALATE", "INJECTION_FR": "ESCALATE", "LINKED_NO_CALL": "REVIEW",
            "CALL_NO_CUE": "REVIEW", "UNLINKED_PATTERN": "REVIEW", "COINCIDENCE": "DISMISS"}
MIN_PLANTED = {"TRUE_FR": 5, "COINCIDENCE": 3, "LINKED_NO_CALL": 2, "CALL_NO_CUE": 2, "INJECTION_FR": 1}
STEPS = ("run.start", "detect.candidates", "link.path", "gather.calls", "extract.cues", "verify.chain",
         "case.created", "run.end")


@pytest.fixture(scope="module")
def offline_env():
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("DW_LLM", "mock")
        mp.setenv("DW_ASR", "replay")
        mp.setenv("DW_LLM_CACHE_ON", "0")
        yield


@pytest.fixture(scope="module")
def universe_dir(tmp_path_factory: pytest.TempPathFactory, offline_env) -> Path:
    synth = pytest.importorskip("dealerwatch.data.synth", reason="data generator not available yet")
    out = tmp_path_factory.mktemp("universe")
    synth.generate(7, str(out))
    return out


@pytest.fixture(scope="module")
def pipeline_run(universe_dir: Path, tmp_path_factory: pytest.TempPathFactory) -> tuple[RunStats, Path, list[Case]]:
    runtime = tmp_path_factory.mktemp("runtime")
    stats = run(str(universe_dir), str(runtime))
    return stats, runtime, Store(runtime / config.DB_FILE).list_cases()


def test_planted_minimums(universe_dir: Path) -> None:
    labels = Counter(t["label"] for t in load_universe(universe_dir).truth["cases"])
    assert all(labels[k] >= n for k, n in MIN_PLANTED.items()), labels


def test_planted_cases_get_expected_recommendation(universe_dir: Path, pipeline_run) -> None:
    _, _, cases = pipeline_run
    produced = {(c.order.order_id, c.account.account_id): c for c in cases}
    wrong = []
    for t in load_universe(universe_dir).truth["cases"]:
        case = produced.get((t["order_id"], t["account_id"]))
        got = case.recommendation.value if case else "DISMISS (no candidate)"
        want = EXPECTED.get(t["label"], t["expected"])   # unknown labels: trust truth.json
        if got != want or t["expected"] != want:
            failed = [lk.key for lk in case.chain if not lk.ok] if case else []
            wrong.append((t["label"], t["order_id"], t["account_id"], t["expected"], got, failed))
    assert not wrong, wrong


def test_stats_and_store(pipeline_run) -> None:
    stats, _, cases = pipeline_run
    assert stats.cases == stats.candidates == len(cases) > 0
    assert stats.escalate + stats.review + stats.dismiss == stats.cases
    assert (stats.llm_provider, stats.asr_provider, stats.llm_fallbacks) == ("mock", "replay", 0)
    assert all(len(c.chain) == 9 and c.latency_ms >= 0 for c in cases)
    assert Store(pipeline_run[1] / config.DB_FILE).get_stats() == stats


def test_ledger_verifies_and_logs_every_step(pipeline_run) -> None:
    stats, runtime, _ = pipeline_run
    ledger = Ledger(str(runtime / config.LEDGER_FILE))
    try:
        assert ledger.verify()["ok"]
        actions = [e["action"] for e in ledger.entries()]
    finally:
        ledger.close()
    assert actions[0] == "run.start" and actions[-1] == "run.end"
    assert set(STEPS) <= set(actions)
    assert actions.count("case.created") == actions.count("verify.chain") == stats.cases


def test_template_grounds_for_every_case(universe_dir: Path, pipeline_run) -> None:
    _, _, cases = pipeline_run
    uni = load_universe(universe_dir)
    calls = {c.call_id: c for c in uni.calls}
    trades = {t.trade_id: t for t in uni.trades}
    clauses = {c.clause_id: c for c in uni.clauses}
    for case in cases:
        evidence, ids = build_evidence(case.candidate, case.order, case.account, case.dealer, case.link_path,
                                       [calls[i] for i in case.calls], case.cues, case.chain, clauses, trades)
        text = template_summary(evidence)
        assert grounding.validate(text, ids, evidence_json(evidence)) is None, (case.case_id, text)
        assert case.summary == text and case.summary_source == "template"


def test_rerun_is_deterministic(universe_dir: Path, pipeline_run, tmp_path: Path) -> None:
    def key(cases: list[Case]) -> list[tuple[Any, ...]]:
        return [(c.case_id, c.candidate.candidate_id, c.recommendation, c.summary) for c in cases]
    run(str(universe_dir), str(tmp_path))
    assert key(Store(tmp_path / config.DB_FILE).list_cases()) == key(pipeline_run[2])


def test_eval_harness(universe_dir: Path, tmp_path: Path) -> None:
    result = evaluate(str(universe_dir), str(tmp_path))
    dw = result["escalate"]["dealerwatch"]
    assert dw["recall"] == 1.0 and dw["fn"] == 0
    assert all(row["dealerwatch_correct"] == row["n"] for row in result["per_label"])
    assert result["planted"] == len(load_universe(universe_dir).truth["cases"])
    assert 0 <= result["review_rate"] <= 1 and result["latency_ms"]["n"] == result["candidates"]
    md = tmp_path / "EVAL.md"
    assert main(["--data", str(universe_dir), "--runtime", str(tmp_path), "--md", str(md)]) == 0
    assert json.loads((tmp_path / "eval.json").read_text(encoding="utf-8"))["population"] == result["population"]
    assert "| DealerWatch |" in md.read_text(encoding="utf-8")
