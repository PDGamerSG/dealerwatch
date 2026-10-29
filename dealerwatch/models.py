"""Shared data model for DealerWatch. Every module imports from here.

All timestamps are ISO-8601 strings in IST without offset, e.g. "2026-10-05T13:41:00".
All money is INR (float). Quantities are shares (int).
"""
from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class FundOrder(BaseModel):
    """A large order placed by the AMC dealing desk (from the MFund-style order blotter)."""
    order_id: str                  # "O-0001"
    scheme: str                    # "Sahyadri Bluechip Fund"
    scrip: str                     # "INFY"
    side: Side
    qty: int
    order_time: str                # when the dealer received/placed it
    exec_start: str
    exec_end: str
    dealer_id: str                 # "D1"


class Dealer(BaseModel):
    dealer_id: str
    name: str
    desk_phone: str
    mobile: str
    email: str


class Account(BaseModel):
    """A retail trading account (UCC) seen in market trades. KYC attributes are synthetic."""
    account_id: str                # "A-017"
    holder_name: str
    pan_masked: str                # "ABCPX****K"
    mobile: str
    email: str
    address: str
    bank_account: str
    device_id: str


class Person(BaseModel):
    """A known relative/associate (from declarations or KYC) used to build the link graph."""
    person_id: str                 # "P-003"
    name: str
    relation: str                  # "brother-in-law of D1"
    mobile: str
    email: str


class Link(BaseModel):
    """An edge in the link graph with the attribute that connects the two nodes."""
    src: str                       # node id: dealer_id, person_id, account_id or "phone:+91..."
    dst: str
    kind: Literal["shared_mobile", "shared_email", "shared_bank", "shared_device",
                  "shared_address", "declared_relative", "called"]
    value: str                     # the shared value, e.g. the phone number
    source: str                    # where the edge came from, e.g. "KYC", "employee declaration", "call log"


class Trade(BaseModel):
    trade_id: str                  # "T-000123"
    account_id: str
    scrip: str
    side: Side
    qty: int
    price: float
    time: str


class Utterance(BaseModel):
    id: str                        # "C-004-u07"  (call_id + "-u" + 2 digits)
    speaker: str                   # "D1" or a phone / person label such as "P-003" or "UNKNOWN"
    start_ms: int
    end_ms: int
    text: str


class Call(BaseModel):
    call_id: str                   # "C-004"
    dealer_id: str
    counterparty_number: str
    start_time: str
    duration_s: int
    audio_file: Optional[str] = None   # relative path under data dir, e.g. "audio/C-004.wav"
    utterances: list[Utterance] = Field(default_factory=list)


class Clause(BaseModel):
    clause_id: str                 # "PFUTP-4-2-q"
    title: str
    text: str                      # short paraphrase; never invented by the LLM
    source_url: str


# ----- pipeline outputs -----

class Candidate(BaseModel):
    """Output of the deterministic sandwich detector for one (order, account) pair."""
    candidate_id: str              # "X-O-0001-A-017"
    order_id: str
    account_id: str
    scrip: str
    pre_trade_ids: list[str]
    post_trade_ids: list[str]
    pre_qty: int
    post_qty: int
    profit_inr: float
    minutes_before: float          # first pre-trade minutes before order_time
    minutes_after: float           # last post-trade minutes after order_time
    hit_count: int                 # number of distinct fund orders this account sandwiched
    score: float                   # 0..1, deterministic


class LeakCue(BaseModel):
    """A spoken hint about the fund order, extracted from a call and grounded to utterance ids."""
    call_id: str
    utterance_ids: list[str]
    quote: str                     # exact substring(s) of the cited utterance text
    scrip: Optional[str] = None
    side: Optional[Side] = None
    qty_hint: Optional[str] = None
    time_hint: Optional[str] = None
    extractor: Literal["llm", "rules"] = "rules"


class ChainLink(BaseModel):
    key: Literal["order", "pre_trade", "post_trade", "profit", "pattern",
                 "link_path", "call_in_window", "leak_cue", "clause"]
    ok: bool
    detail: str
    evidence_ids: list[str] = Field(default_factory=list)


class Recommendation(str, Enum):
    ESCALATE = "ESCALATE"          # full evidence chain: recommend escalation to compliance head / exchange
    REVIEW = "REVIEW"              # partial chain: analyst must look
    DISMISS = "DISMISS"            # sandwich only, likely coincidence


class CaseStatus(str, Enum):
    NEW = "NEW"
    UNDER_REVIEW = "UNDER_REVIEW"
    INFO_REQUESTED = "INFO_REQUESTED"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


class Decision(BaseModel):
    case_id: str
    action: Literal["approve_escalation", "request_info", "dismiss", "start_review"]
    reviewer: str
    note: str = ""
    time: str


class Case(BaseModel):
    case_id: str                   # "CASE-0001"
    candidate: Candidate
    order: FundOrder
    account: Account
    dealer: Dealer
    link_path: list[Link] = Field(default_factory=list)   # dealer -> ... -> account
    calls: list[str] = Field(default_factory=list)        # call_ids in window that touch the network
    cues: list[LeakCue] = Field(default_factory=list)
    chain: list[ChainLink] = Field(default_factory=list)  # always 9 entries, fixed order
    recommendation: Recommendation
    clause_ids: list[str] = Field(default_factory=list)
    summary: str                   # grounded narrative with [o:..] [t:..] [u:..] [a:..] citations
    summary_source: Literal["llm", "template"]
    summary_rejected_reason: Optional[str] = None
    status: CaseStatus = CaseStatus.NEW
    decisions: list[Decision] = Field(default_factory=list)
    created_at: str
    latency_ms: int = 0


class RunStats(BaseModel):
    orders: int
    trades: int
    calls: int
    candidates: int
    cases: int
    escalate: int
    review: int
    dismiss: int
    llm_provider: str
    llm_calls: int
    llm_fallbacks: int
    asr_provider: str
    total_ms: int
