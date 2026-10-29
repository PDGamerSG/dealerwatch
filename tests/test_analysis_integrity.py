"""Analysis versions, finite persistence and isolated evaluation regression checks."""
from __future__ import annotations

from pathlib import Path

import pytest

from dealerwatch.evidence_snapshot import case_identity
from dealerwatch.models import Recommendation
from dealerwatch.store import Store
from test_core_decisions import _case


def test_material_recommendation_change_creates_a_new_case_version():
    case = _case()
    snapshot = {"trades": [], "call_details": []}
    first = case_identity(case, "dataset", "fingerprint", snapshot)
    changed = case.model_copy(update={"recommendation": Recommendation.REVIEW,
                                     "chain": [link.model_copy(update={"ok": False}) if link.key == "leak_cue" else link
                                               for link in case.chain]})
    assert case_identity(changed, "dataset", "fingerprint", snapshot) != first
    paraphrased = case.model_copy(update={"summary": "A different narrative of exactly the same evidence"})
    assert case_identity(paraphrased, "dataset", "fingerprint", snapshot) == first


def test_nonfinite_case_cannot_poison_persisted_cases(tmp_path: Path):
    store = Store(tmp_path / "cases.db")
    case = _case()
    store.save_case(case)
    bad = case.model_copy(update={"candidate": case.candidate.model_copy(update={"profit_inr": float("nan")})})
    with pytest.raises(ValueError):
        store.save_case(bad)
    assert store.get_case(case.case_id) == case


def test_evaluation_replaces_its_previous_dataset_population(tmp_path: Path, monkeypatch):
    import json
    from dealerwatch.eval.harness import evaluate
    from test_api import build_fixture
    monkeypatch.setenv("DW_LLM", "mock")
    monkeypatch.setenv("DW_ASR", "replay")
    source, runtime = tmp_path / "data", tmp_path / "eval"
    build_fixture(source)
    assert evaluate(str(source), str(runtime))["candidates"] == 2
    trades = json.loads((source / "trades.json").read_text())
    (source / "trades.json").write_text(json.dumps([row for row in trades if row["account_id"] != "A-050"]))
    result = evaluate(str(source), str(runtime))
    assert result["candidates"] == 1
    assert result["planted_without_candidate"] == 1


def test_evaluation_cannot_reset_a_live_review_runtime(tmp_path, monkeypatch):
    from dealerwatch import config
    from dealerwatch.decisions import apply_decision
    from dealerwatch.eval.harness import evaluate
    from dealerwatch.pipeline import run
    from test_api import build_fixture
    from toolkit.ledger import Ledger
    monkeypatch.setenv("DW_LLM", "mock")
    monkeypatch.setenv("DW_ASR", "replay")
    source, runtime = tmp_path / "data", tmp_path / "runtime"
    build_fixture(source)
    run(str(source), str(runtime))
    store = Store(runtime / config.DB_FILE)
    case = store.list_cases()[0]
    ledger = Ledger(str(runtime / config.LEDGER_FILE))
    try:
        apply_decision(store, ledger, case.case_id, "start_review", "Analyst")
        with pytest.raises(ValueError, match="isolated"):
            evaluate(str(source), str(runtime))
        assert store.get_case(case.case_id).decisions
        assert ledger.verify()["ok"]
    finally:
        ledger.close()
