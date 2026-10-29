"""Evidence chain and recommendation rule, on hand-built scenarios."""
from __future__ import annotations

import itertools
from typing import Any

import pytest

from dealerwatch.agent.extract import rules_cues
from dealerwatch.agent.verify import CHAIN_KEYS, build_chain, recommend
from dealerwatch.detect.sandwich import find_candidates
from dealerwatch.models import (Account, Call, ChainLink, Clause, Dealer, FundOrder, Link, Recommendation, Side,
                                Trade, Utterance)

LEAK_TEXT = "Bhai, INFY mein bada order aa raha hai, do baje ke aas paas, 5 lakh shares"


def scenario(*, sell_price: float = 1520.0, pre_qty: int = 6000, path: bool = True, call: str | None = "leak",
             call_time: str = "2026-09-03T11:02:00", clauses: bool = True) -> dict[str, Any]:
    """One INFY BUY sandwich by A-011; knobs switch individual chain links off."""
    order = FundOrder(order_id="O-0003", scheme="Sahyadri Bluechip Fund", scrip="INFY", side=Side.BUY, qty=500_000,
                      order_time="2026-09-03T13:41:00", exec_start="2026-09-03T13:45:00",
                      exec_end="2026-09-03T15:10:00", dealer_id="D1")
    trades = [
        Trade(trade_id="T-000101", account_id="A-011", scrip="INFY", side=Side.BUY, qty=pre_qty, price=1500.0,
              time="2026-09-03T13:00:00"),
        Trade(trade_id="T-000102", account_id="A-011", scrip="INFY", side=Side.BUY, qty=pre_qty, price=1501.0,
              time="2026-09-03T13:20:00"),
        Trade(trade_id="T-000150", account_id="A-011", scrip="INFY", side=Side.SELL, qty=2 * pre_qty,
              price=sell_price, time="2026-09-03T14:10:00"),
    ]
    [candidate] = find_candidates([order], trades)
    lines = {"leak": [("D1", "Haan bhai, ghar pe sab theek?"), ("P-001", "Sab badhiya."), ("D1", LEAK_TEXT)],
             "smalltalk": [("D1", "match dekha kal?"), ("P-001", "haan, mast tha"), ("D1", "ghar pe sab theek?")],
             "other": [("D1", "TCS le lo kal, bada order hai")]}
    calls = []
    if call:
        utts = [Utterance(id=f"C-004-u{i:02d}", speaker=s, start_ms=i * 4000, end_ms=i * 4000 + 3000, text=t)
                for i, (s, t) in enumerate(lines[call], start=1)]
        calls = [Call(call_id="C-004", dealer_id="D1", counterparty_number="+919800000001", start_time=call_time,
                      duration_s=75, utterances=utts)]
    clause_table = {cid: Clause(clause_id=cid, title=title, text="paraphrase", source_url="https://www.sebi.gov.in/")
                    for cid, title in (("PFUTP-4-2-q", "Front running by intermediaries"),
                                       ("SEBI-AMC-FR-MECH", "AMC front-running surveillance mechanism"))}
    if not clauses:
        clause_table.pop("SEBI-AMC-FR-MECH")
    return {
        "candidate": candidate, "order": order, "trades": {t.trade_id: t for t in trades},
        "path": [Link(src="D1", dst="P-001", kind="declared_relative", value="brother-in-law",
                      source="employee declaration"),
                 Link(src="P-001", dst="A-011", kind="shared_mobile", value="+919800000001", source="KYC")]
        if path else [],
        "calls": calls,
        "cues": [q for c in calls for q in rules_cues(c, c.utterances, ["INFY", "TCS"])],
        "clauses": clause_table,
        "account": Account(account_id="A-011", holder_name="Sunil Bhatt", pan_masked="ABCPB****K",
                           mobile="+919800000001", email="sunil@example.in", address="Thane",
                           bank_account="XXXX4411", device_id="dev-11"),
        "dealer": Dealer(dealer_id="D1", name="Rohan Mehta", desk_phone="+912240000001", mobile="+919000000001",
                         email="rohan@sahyadri.example"),
    }


def chain_of(s: dict[str, Any]) -> list[ChainLink]:
    return build_chain(s["candidate"], s["order"], s["trades"], s["path"], s["calls"], s["cues"], s["clauses"])


def test_full_chain_escalates_with_evidence_ids() -> None:
    chain = chain_of(scenario())
    assert tuple(lk.key for lk in chain) == CHAIN_KEYS
    assert all(lk.ok for lk in chain), [(lk.key, lk.detail) for lk in chain if not lk.ok]
    assert recommend(chain) == Recommendation.ESCALATE
    by = {lk.key: lk for lk in chain}
    assert by["order"].evidence_ids == ["o:O-0003"]
    assert by["pre_trade"].evidence_ids == ["t:T-000101", "t:T-000102"]
    assert by["post_trade"].evidence_ids == ["t:T-000150"]
    assert by["call_in_window"].evidence_ids == ["c:C-004"]
    assert by["leak_cue"].evidence_ids == ["u:C-004-u03", "c:C-004"]
    assert by["clause"].evidence_ids == ["l:PFUTP-4-2-q", "l:SEBI-AMC-FR-MECH"]
    assert by["pattern"].evidence_ids == ["a:A-011"]
    assert "12,000" in by["pre_trade"].detail and "21 to 41 min" in by["pre_trade"].detail
    assert "INR 2,34,000" in by["profit"].detail
    assert "D1 -[declared_relative" in by["link_path"].detail and "A-011" in by["link_path"].detail
    assert "159 min before" in by["call_in_window"].detail


@pytest.mark.parametrize("kwargs,failed,expected", [
    ({"path": False}, {"link_path"}, Recommendation.REVIEW),                   # cue without a known link
    ({"call": None}, {"call_in_window", "leak_cue"}, Recommendation.REVIEW),   # LINKED_NO_CALL
    ({"call": "smalltalk"}, {"leak_cue"}, Recommendation.REVIEW),              # CALL_NO_CUE
    ({"call": "other"}, {"leak_cue"}, Recommendation.REVIEW),                  # cue names another scrip
    ({"call_time": "2026-09-03T10:40:00"}, {"call_in_window", "leak_cue"}, Recommendation.REVIEW),
    # unlinked, no cue: a large (>= INR 20 lakh) sandwich still goes to REVIEW, a small single one is dismissed
    ({"path": False, "call": None}, {"link_path", "call_in_window", "leak_cue"}, Recommendation.REVIEW),
    ({"path": False, "call": "smalltalk"}, {"link_path", "leak_cue"}, Recommendation.REVIEW),
    ({"path": False, "call": None, "pre_qty": 300}, {"link_path", "call_in_window", "leak_cue", "pattern"},
     Recommendation.DISMISS),
    ({"pre_qty": 300}, {"pattern"}, Recommendation.REVIEW),                    # 1 hit, value < 20 lakh
    ({"clauses": False}, {"clause"}, Recommendation.REVIEW),
    ({"sell_price": 1490.0}, {"profit"}, Recommendation.DISMISS),              # loss: core link fails
])
def test_partial_chains(kwargs: dict[str, Any], failed: set[str], expected: Recommendation) -> None:
    chain = chain_of(scenario(**kwargs))
    assert {lk.key for lk in chain if not lk.ok} == failed
    assert recommend(chain) == expected


@pytest.mark.parametrize("oks", list(itertools.product([True, False], repeat=len(CHAIN_KEYS))))
def test_recommend_all_combinations(oks: tuple[bool, ...]) -> None:
    chain = [ChainLink(key=k, ok=ok, detail=k) for k, ok in zip(CHAIN_KEYS, oks)]
    flags = dict(zip(CHAIN_KEYS, oks))
    if all(oks):
        expected = Recommendation.ESCALATE
    elif all(flags[k] for k in ("order", "pre_trade", "post_trade", "profit")) and (
            flags["link_path"] or flags["leak_cue"] or flags["pattern"]):
        expected = Recommendation.REVIEW
    else:
        expected = Recommendation.DISMISS
    assert recommend(chain) == expected


def test_incomplete_chain_never_escalates() -> None:
    chain = [ChainLink(key=k, ok=True, detail=k) for k in CHAIN_KEYS[:-1]]
    assert recommend(chain) == Recommendation.REVIEW
