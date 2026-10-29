"""Detector, verifier and pipeline parameters for DealerWatch (see CONTRACT.md)."""
from __future__ import annotations

# Sandwich detector windows (minutes relative to the fund order time).
PRE_WINDOW_MIN = 60
POST_WINDOW_MIN = 90
CALL_LOOKBACK_MIN = 180
MIN_PRE_QTY = 100

# Score normalisers.
SCORE_HIT_NORM = 3
SCORE_PROFIT_NORM_INR = 200_000.0

# Evidence-chain thresholds.
PATTERN_MIN_HITS = 2
PATTERN_MIN_PRE_VALUE_INR = 2_000_000.0

# Rules-only baseline used by the eval harness.
BASELINE_ESCALATE_SCORE = 0.5

# Fixed clause table entries resolved for a front-running case.
FRONT_RUNNING_CLAUSES = ("PFUTP-4-2-q", "SEBI-AMC-FR-MECH")

SCRIPS = ("INFY", "TCS", "HDFCBANK", "RELIANCE", "SBIN", "ITC", "LT", "BAJFINANCE")

# Spoken names a dealer may use instead of the exchange symbol (lower case).
SCRIP_ALIASES: dict[str, tuple[str, ...]] = {
    "INFY": ("infosys", "infy"),
    "TCS": ("tcs", "tata consultancy"),
    "HDFCBANK": ("hdfcbank", "hdfc bank", "hdfc"),
    "RELIANCE": ("reliance", "ril"),
    "SBIN": ("sbin", "sbi", "state bank"),
    "ITC": ("itc",),
    "LT": ("lt", "l&t", "larsen"),
    "BAJFINANCE": ("bajfinance", "bajaj finance", "bajaj fin"),
}

# Runtime file names inside the runtime directory.
DB_FILE = "dealerwatch.db"
LEDGER_FILE = "ledger.db"
