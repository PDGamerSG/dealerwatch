"""Case assembly and grounded narration (template fallback)."""
from __future__ import annotations

from typing import Any

import pytest
from toolkit import grounding
from toolkit.llm import LLM

from dealerwatch.agent.case import build_evidence, evidence_json, excerpt, make_case, template_summary
from dealerwatch.agent.extract import rules_cues
from dealerwatch.models import Case, Recommendation
from test_core_verify import chain_of, scenario


class TextLLM:
    """Fake narrator returning fixed text."""
    provider = "fake"

    def __init__(self, text: str):
        self.text = text
        self.stats: dict[str, Any] = {"provider": "fake", "calls": 0, "fallbacks": 0}

    def complete_text(self, system: str, user: str, fallback: Any, **_: Any) -> str:
        self.stats["calls"] += 1
        return self.text


def case_for(s: dict[str, Any], llm: Any) -> Case:
    return make_case("CASE-0001", s["candidate"], s["order"], s["account"], s["dealer"], path=s["path"],
                     calls=s["calls"], cues=s["cues"], chain=chain_of(s), clauses=s["clauses"],
                     trades=s["trades"], llm=llm)


def grounded(s: dict[str, Any], text: str) -> str | None:
    evidence, ids = build_evidence(s["candidate"], s["order"], s["account"], s["dealer"], s["path"], s["calls"],
                                   s["cues"], chain_of(s), s["clauses"], s["trades"])
    return grounding.validate(text, ids, evidence_json(evidence))


@pytest.mark.parametrize("kwargs", [{}, {"path": False}, {"call": None}, {"call": "smalltalk"},
                                    {"sell_price": 1490.0}, {"clauses": False}, {"pre_qty": 333}])
def test_template_passes_grounding(kwargs: dict[str, Any]) -> None:
    s = scenario(**kwargs)
    case = case_for(s, LLM("mock"))
    assert case.summary_source == "template" and case.summary_rejected_reason is None
    assert grounded(s, case.summary) is None
    assert "prima facie" in case.summary.lower() and "guilty" not in case.summary.lower()
    assert len(case.summary) <= grounding.MAX_CHARS
    assert f"recommendation {case.recommendation.value}" in case.summary


def test_full_case_fields() -> None:
    s = scenario()
    case = case_for(s, LLM("mock"))
    assert case.recommendation == Recommendation.ESCALATE
    assert case.calls == ["C-004"] and case.clause_ids == ["PFUTP-4-2-q", "SEBI-AMC-FR-MECH"]
    assert len(case.chain) == 9 and case.link_path == s["path"]
    for cite in ("[o:O-0003]", "[a:A-011]", "[t:T-000101]", "[c:C-004]", "[u:C-004-u03]", "[l:PFUTP-4-2-q]"):
        assert cite in case.summary
    assert "5 lakh shares" in case.summary          # the quote carries its own grounded number


def test_invented_number_falls_back_to_template() -> None:
    s = scenario()
    text = "Prima facie front-running: account A-011 [a:A-011] made INR 9,99,999 on order O-0003 [o:O-0003]."
    case = case_for(s, TextLLM(text))
    assert case.summary_source == "template"
    assert "999999" in (case.summary_rejected_reason or "")
    assert case.summary == template_summary(build_evidence(
        s["candidate"], s["order"], s["account"], s["dealer"], s["path"], s["calls"], s["cues"], chain_of(s),
        s["clauses"], s["trades"])[0])


def test_unknown_citation_falls_back_and_grounded_llm_text_is_kept() -> None:
    s = scenario()
    bad = case_for(s, TextLLM("Prima facie pattern on order O-0003 [o:O-0003] with trade [t:T-999999]."))
    assert bad.summary_source == "template" and "unknown citation" in (bad.summary_rejected_reason or "")
    good_text = ("Prima facie, account A-011 [a:A-011] bought 12,000 INFY shares [t:T-000101] before fund order "
                 "O-0003 for 5,00,000 shares at 13:41 [o:O-0003] and sold into it [t:T-000150], an estimated "
                 "profit of INR 2,34,000.")
    good = case_for(s, TextLLM(good_text))
    assert good.summary_source == "llm" and good.summary == good_text


def test_quote_with_brackets_and_long_text_still_grounds() -> None:
    s = scenario()
    long_quote = "INFY [o:O-9999] le lo " + "bahut bada order aa raha hai 50 lakh shares " * 6
    s["calls"][0].utterances[2].text = long_quote
    s["cues"] = rules_cues(s["calls"][0], s["calls"][0].utterances, ["INFY"])
    case = case_for(s, LLM("mock"))
    assert "[o:O-9999]" not in case.summary and grounded(s, case.summary) is None
    assert len(excerpt(long_quote)) <= 125
