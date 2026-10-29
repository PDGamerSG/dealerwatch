"""Grounding checks for LLM narratives: every citation must name known evidence and every number
must appear in the evidence text; otherwise the deterministic template is used.

Citations look like `[o:O-0001]`, `[t:T-000123]`, `[u:C-004-u07]`, `[a:A-011]`, `[c:C-004]`,
`[l:PFUTP-4-2-q]` (order, trade, utterance, account, call, clause).

Number normalisation (applied to both the narrative and the evidence):
- citations and ID-like tokens (`O-0001`, `C-004-u07`) are removed first;
- currency markers (₹, Rs, Rs., INR) and thousands separators (Western or Indian `5,00,000`) are
  dropped, trailing decimal zeros are stripped (`182345.50` -> `182345.5`), `5 lakh` -> `500000`,
  `2 crore` -> `20000000`;
- clock times become `HH:MM` tokens (`9:05` -> `09:05`, `1:41 pm` -> `13:41`) and must match a time
  in the evidence; an ISO timestamp in the evidence (`2026-09-03T13:41:00`) supplies the time
  `13:41`, the date `2026-09-03` and its parts (2026, 9, 3) so `3 Sep 2026` also grounds;
- standalone single-digit integers (counts like "2 trades") are not checked.
Ideas (not code) after Kyun's answer validation (MIT, Team Vulcan). Generic: no project imports.
"""
from __future__ import annotations

import logging
import re
from collections.abc import Callable, Iterable
from decimal import Decimal, InvalidOperation
from typing import Any

log = logging.getLogger("toolkit.grounding")

MAX_CHARS = 900
CITE_RE = re.compile(r"\[([otuacl]):([^\[\]\s]+)\]")

_CURRENCY = re.compile(r"₹|\bRs\.?(?=\s*\d)|\bINR\b", re.IGNORECASE)
_ID = re.compile(r"\b[A-Za-z]{1,6}(?:-[A-Za-z0-9]+)*-\d[A-Za-z0-9-]*")
_ISO = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{1,2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?)?(?!\d)")
_CLOCK = re.compile(r"(?<![\d:.])(\d{1,2}):(\d{2})(?::(\d{2}))?(?:\s*([AaPp])\.?[Mm]\b\.?)?(?![\d:])")
_HOUR_AMPM = re.compile(r"(?<![\w.:])(\d{1,2})\s*([AaPp])\.?[Mm]\b\.?")
_NUMBER = re.compile(r"(?<![\w.,])(\d+(?:,\d{2,3})*(?:\.\d+)?)(?:\s*(lakhs?|lacs?|crores?|cr)\b)?", re.IGNORECASE)
_MULTIPLIER = {"lakh": 100_000, "lakhs": 100_000, "lac": 100_000, "lacs": 100_000,
               "crore": 10_000_000, "crores": 10_000_000, "cr": 10_000_000}


def citations(text: str) -> list[tuple[str, str]]:
    """All `[x:ID]` citations in order, as (kind, id)."""
    return [(m.group(1), m.group(2)) for m in CITE_RE.finditer(text or "")]


def _norm_number(raw: str, multiplier: str | None = None) -> str | None:
    try:
        value = Decimal(raw.replace(",", ""))
    except InvalidOperation:
        return None
    if multiplier:
        value *= _MULTIPLIER[multiplier.lower()]
    if value == value.to_integral_value():
        return str(int(value))
    return format(value.normalize(), "f")


def _clock(hour: int, minute: int, second: int | None, ampm: str | None) -> str | None:
    if ampm:
        if not 1 <= hour <= 12:
            return None
        hour = hour % 12 + (12 if ampm.lower() == "p" else 0)
    if hour > 23 or minute > 59 or (second is not None and second > 59):
        return None
    return f"{hour:02d}:{minute:02d}" + (f":{second:02d}" if second else "")


def _scan(text: str, *, evidence: bool) -> set[str]:
    """Normalised number/time/date tokens. Evidence mode adds the variants a narrative may use."""
    tokens: set[str] = set()
    body = CITE_RE.sub(" ", text or "")
    body = _CURRENCY.sub(" ", body)
    body = _ID.sub(" ", body)

    def iso(m: re.Match) -> str:
        year, month, day = m.group(1), m.group(2), m.group(3)
        tokens.add(f"{year}-{month}-{day}")
        if evidence:
            tokens.update({str(int(year)), str(int(month)), str(int(day))})
        if m.group(4) is not None:
            add_time(_clock(int(m.group(4)), int(m.group(5)), int(m.group(6) or 0), None))
        return " "

    def add_time(token: str | None) -> None:
        if token:
            tokens.add(token)
            if evidence and len(token) > 5:
                tokens.add(token[:5])  # a narrative may drop the seconds

    def clock(m: re.Match) -> str:
        add_time(_clock(int(m.group(1)), int(m.group(2)), int(m.group(3) or 0), m.group(4)))
        return " "

    def hour_ampm(m: re.Match) -> str:
        token = _clock(int(m.group(1)), 0, None, m.group(2))
        if token:
            tokens.add(token)
        return " "

    body = _ISO.sub(iso, body)
    body = _CLOCK.sub(clock, body)
    body = _HOUR_AMPM.sub(hour_ampm, body)
    for m in _NUMBER.finditer(body):
        token = _norm_number(m.group(1), m.group(2))
        if token is None:
            continue
        if not evidence and not m.group(2) and "." not in token and int(token) < 10:
            continue  # single-digit counts are not checked
        tokens.add(token)
    return tokens


def numbers(text: str) -> set[str]:
    """Normalised numbers, `HH:MM` times and ISO dates in `text` that must be grounded."""
    return _scan(text, evidence=False)


def evidence_numbers(evidence_text: str) -> set[str]:
    """Every token a grounded narrative may use, derived from the evidence text."""
    return _scan(evidence_text, evidence=True)


def validate(text: str, evidence_ids: Iterable[str], evidence_text: str) -> str | None:
    """None when the narrative is grounded, else a short reason it was rejected."""
    if not text or not text.strip():
        return "empty narrative"
    if len(text) > MAX_CHARS:
        return f"too long ({len(text)} chars > {MAX_CHARS})"
    cited = citations(text)
    if not cited:
        return "no citations"
    known = set(evidence_ids)
    for kind, ident in cited:
        if ident not in known and f"{kind}:{ident}" not in known:
            return f"unknown citation [{kind}:{ident}]"
    allowed = evidence_numbers(evidence_text)
    for token in sorted(numbers(text)):
        if token not in allowed:
            return f"number {token} not in evidence"
    return None


def compose(llm: Any, system: str, user: str, evidence_ids: Iterable[str], evidence_text: str,
            template: Callable[[], str]) -> dict:
    """LLM narrative when it validates, else `template()`. Returns {text, source, rejected_reason}."""
    ids = set(evidence_ids)
    if llm is None:
        return {"text": template(), "source": "template", "rejected_reason": None}
    try:
        text = llm.complete_text(system, user, fallback=lambda: "")
    except Exception as exc:  # noqa: BLE001 - the template is always available
        log.warning("narrative LLM call failed: %s", type(exc).__name__)
        return {"text": template(), "source": "template", "rejected_reason": f"llm error: {type(exc).__name__}"}
    text = (text or "").strip()
    if not text:
        if getattr(llm, "provider", None) == "mock":
            return {"text": template(), "source": "template", "rejected_reason": None}
        error = (getattr(llm, "stats", None) or {}).get("last_error")
        reason = f"llm unavailable: {error}" if error else "llm unavailable"
        return {"text": template(), "source": "template", "rejected_reason": reason}
    reason = validate(text, ids, evidence_text)
    if reason:
        log.info("narrative rejected (%s); using template", reason)
        return {"text": template(), "source": "template", "rejected_reason": reason}
    return {"text": text, "source": "llm", "rejected_reason": None}
