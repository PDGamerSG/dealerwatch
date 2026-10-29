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


def apply_decision(store: Store, ledger: Ledger, case_id: str, action: str, reviewer: str, note: str = "", *,
                   expected_revision: int | None = None, idempotency_key: str | None = None) -> Case:
    """Apply a reviewer action. Raises KeyError for an unknown case, ValueError for an invalid action,
    an empty reviewer, or any action on a terminal (CLOSED / ESCALATED) case."""
    if action not in TRANSITIONS:
        raise ValueError(f"unknown action {action!r}; expected one of {', '.join(TRANSITIONS)}")
    reviewer = (reviewer or "").strip()
    if not reviewer:
        raise ValueError("reviewer is required")
    if expected_revision is not None and (type(expected_revision) is not int or expected_revision < 0):
        raise ValueError("expected_revision must be a nonnegative integer")
    if idempotency_key is not None and (not isinstance(idempotency_key, str)
                                       or not idempotency_key.strip() or len(idempotency_key) > 200):
        raise ValueError("idempotency key must contain 1 to 200 characters")
    new_status = TRANSITIONS[action]
    decision = Decision(case_id=case_id, action=action, reviewer=reviewer, note=note or "",
                        time=datetime.now().isoformat(timespec="seconds"))
    return store.add_decision(decision, new_status, ledger=ledger, expected_revision=expected_revision,
                              idempotency_key=idempotency_key)
