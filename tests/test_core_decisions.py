"""Store persistence and the reviewer status machine with ledger logging."""
from __future__ import annotations

from pathlib import Path

import pytest
from toolkit.ledger import Ledger
from toolkit.llm import LLM

from dealerwatch.agent.case import make_case
from dealerwatch.decisions import apply_decision
from dealerwatch.models import Case, CaseStatus, RunStats
from dealerwatch.store import Store
from test_core_verify import chain_of, scenario


def _case(case_id: str = "CASE-0001", **kwargs) -> Case:
    s = scenario(**kwargs)
    return make_case(case_id, s["candidate"], s["order"], s["account"], s["dealer"], path=s["path"],
                     calls=s["calls"], cues=s["cues"], chain=chain_of(s), clauses=s["clauses"],
                     trades=s["trades"], llm=LLM("mock"))


@pytest.fixture
def env(tmp_path: Path):
    store = Store(tmp_path / "dw.db")
    ledger = Ledger(str(tmp_path / "ledger.db"))
    store.save_case(_case("CASE-0001"))
    store.save_case(_case("CASE-0002", path=False, call=None))
    yield store, ledger
    ledger.close()


def test_store_roundtrip(env) -> None:
    store, _ = env
    case = store.get_case("CASE-0001")
    assert case is not None and case == _case("CASE-0001").model_copy(update={"created_at": case.created_at})
    assert store.get_case("CASE-404") is None
    assert [c.case_id for c in store.list_cases()] == ["CASE-0001", "CASE-0002"]
    assert [c.case_id for c in store.list_cases(status="NEW")] == ["CASE-0001", "CASE-0002"]
    assert store.list_cases(status=CaseStatus.CLOSED) == []
    assert store.get_stats() is None
    stats = RunStats(orders=1, trades=3, calls=1, candidates=2, cases=2, escalate=1, review=0, dismiss=1,
                     llm_provider="mock", llm_calls=2, llm_fallbacks=0, asr_provider="replay", total_ms=5)
    store.save_stats(stats)
    assert store.get_stats() == stats
    store.reset()
    assert store.list_cases() == [] and store.get_stats() is None


def test_valid_transitions_are_logged(env) -> None:
    store, ledger = env
    assert apply_decision(store, ledger, "CASE-0001", "start_review", "Asha", "").status == CaseStatus.UNDER_REVIEW
    assert apply_decision(store, ledger, "CASE-0001", "request_info", "Asha", "need KYC").status \
        == CaseStatus.INFO_REQUESTED
    case = apply_decision(store, ledger, "CASE-0001", "approve_escalation", "Asha", "chain complete")
    assert case.status == CaseStatus.ESCALATED
    assert [d.action for d in case.decisions] == ["start_review", "request_info", "approve_escalation"]
    assert store.get_case("CASE-0001").status == CaseStatus.ESCALATED
    entries = ledger.entries()
    assert [e["action"] for e in entries] == ["decision.start_review", "decision.request_info",
                                              "decision.approve_escalation"]
    assert all(e["actor"] == "Asha" for e in entries)
    assert entries[-1]["payload"]["from_status"] == "INFO_REQUESTED"
    assert entries[-1]["payload"]["to_status"] == "ESCALATED"
    assert ledger.verify()["ok"]


@pytest.mark.parametrize("first", ["dismiss", "approve_escalation"])
def test_terminal_states_reject_further_actions(env, first: str) -> None:
    store, ledger = env
    apply_decision(store, ledger, "CASE-0002", first, "Asha", "")
    for action in ("start_review", "request_info", "dismiss", "approve_escalation"):
        with pytest.raises(ValueError):
            apply_decision(store, ledger, "CASE-0002", action, "Asha", "")
    assert ledger.count() == 1 and len(store.get_case("CASE-0002").decisions) == 1


def test_invalid_requests(env) -> None:
    store, ledger = env
    with pytest.raises(ValueError):
        apply_decision(store, ledger, "CASE-0001", "auto_escalate", "Asha", "")
    with pytest.raises(ValueError):
        apply_decision(store, ledger, "CASE-0001", "dismiss", "  ", "")
    with pytest.raises(KeyError):
        apply_decision(store, ledger, "CASE-404", "dismiss", "Asha", "")
    assert ledger.count() == 0 and store.get_case("CASE-0001").status == CaseStatus.NEW
