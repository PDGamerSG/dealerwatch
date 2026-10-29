"""Human reviewer decisions: the case status machine, with every decision written to the ledger."""
from __future__ import annotations

from datetime import datetime

from toolkit.ledger import Ledger

from dealerwatch.models import Case, CaseStatus, Decision
from dealerwatch.store import Store

TRANSITIONS: dict[str, CaseStatus] = {
    "start_review": CaseStatus.UNDER_REVIEW,
    "request_info": CaseStatus.INFO_REQUESTED,
    "approve_escalation": CaseStatus.ESCALATED,
    "dismiss": CaseStatus.CLOSED,
}
TERMINAL = frozenset({CaseStatus.CLOSED, CaseStatus.ESCALATED})


def apply_decision(store: Store, ledger: Ledger, case_id: str, action: str, reviewer: str, note: str = "") -> Case:
    """Apply a reviewer action. Raises KeyError for an unknown case, ValueError for an invalid action,
    an empty reviewer, or any action on a terminal (CLOSED / ESCALATED) case."""
    if action not in TRANSITIONS:
        raise ValueError(f"unknown action {action!r}; expected one of {', '.join(TRANSITIONS)}")
    reviewer = (reviewer or "").strip()
    if not reviewer:
        raise ValueError("reviewer is required")
    case = store.get_case(case_id)
    if case is None:
        raise KeyError(case_id)
    if case.status in TERMINAL:
        raise ValueError(f"case {case_id} is {case.status.value}; no further actions allowed")
    new_status = TRANSITIONS[action]
    decision = Decision(case_id=case_id, action=action, reviewer=reviewer, note=note or "",
                        time=datetime.now().isoformat(timespec="seconds"))
    updated = store.add_decision(decision, new_status)
    ledger.append(reviewer, f"decision.{action}", {
        "case_id": case_id, "action": action, "from_status": case.status.value,
        "to_status": new_status.value, "note": decision.note, "time": decision.time,
        "recommendation": case.recommendation.value,
    })
    return updated
