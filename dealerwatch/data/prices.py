"""Synthetic 1-minute OHLCV bars for the DealerWatch universe. Every price here is SYNTHETIC.

Geometric Brownian motion per scrip over 20 weekdays from 2026-09-01, 09:15-15:29 IST, plus a
deterministic price-impact ramp after each fund order (up for a BUY, down for a SELL) so that
accounts trading ahead of the fund visibly profit.
"""
from __future__ import annotations

import csv
import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

SCRIP_LEVELS: dict[str, float] = {
    "INFY": 1500.0, "TCS": 3200.0, "HDFCBANK": 1650.0, "RELIANCE": 2900.0,
    "SBIN": 800.0, "ITC": 450.0, "LT": 3600.0, "BAJFINANCE": 7000.0,
}
SCRIPS: tuple[str, ...] = tuple(SCRIP_LEVELS)
ANNUAL_VOL: dict[str, float] = {
    "INFY": 0.24, "TCS": 0.20, "HDFCBANK": 0.20, "RELIANCE": 0.22,
    "SBIN": 0.28, "ITC": 0.18, "LT": 0.22, "BAJFINANCE": 0.30,
}
BASE_VOLUME: dict[str, int] = {
    "INFY": 18000, "TCS": 6000, "HDFCBANK": 25000, "RELIANCE": 20000,
    "SBIN": 40000, "ITC": 50000, "LT": 5000, "BAJFINANCE": 2500,
}
START_DATE = date(2026, 9, 1)
N_DAYS = 20
SESSION_OPEN_MIN = 9 * 60 + 15          # 09:15
N_BARS = 375                            # 09:15 .. 15:29 inclusive
TICK = 0.05
CSV_HEADER = ("scrip", "time", "open", "high", "low", "close", "volume")
_EPOCH = datetime(2026, 1, 1)
_MINUTES_PER_YEAR = 252 * N_BARS


def trading_days(start: date = START_DATE, n: int = N_DAYS) -> list[date]:
    """First `n` weekdays from `start` (holidays ignored)."""
    days: list[date] = []
    d = start
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


TRADING_DAYS: list[date] = trading_days()
_DAY_INDEX: dict[date, int] = {d: i for i, d in enumerate(TRADING_DAYS)}


def bar_time(index: int) -> str:
    """ISO timestamp of a flattened bar index (day * N_BARS + minute)."""
    day, minute = divmod(index, N_BARS)
    m = SESSION_OPEN_MIN + minute
    return f"{TRADING_DAYS[day].isoformat()}T{m // 60:02d}:{m % 60:02d}:00"


def bar_index(ts: str) -> int | None:
    """Flattened bar index of the minute containing `ts`, or None outside the session."""
    dt = datetime.fromisoformat(ts)
    day = _DAY_INDEX.get(dt.date())
    minute = dt.hour * 60 + dt.minute - SESSION_OPEN_MIN
    if day is None or not 0 <= minute < N_BARS:
        return None
    return day * N_BARS + minute


def minute_key(ts: str) -> float:
    """Minutes since 2026-01-01 (float, keeps seconds) for ordering and nearest-bar lookups."""
    return (datetime.fromisoformat(ts) - _EPOCH).total_seconds() / 60.0


def round_tick(x: float) -> float:
    """Round a price to the 0.05 tick."""
    return round(round(x / TICK) * TICK, 2)


def _round_ticks(a: np.ndarray) -> np.ndarray:
    return np.round(np.round(a / TICK) * TICK, 2)


@dataclass(frozen=True)
class Impact:
    """Price impact of one fund order: log price ramps linearly by `pct` from start to end, then persists."""
    scrip: str
    start: str
    end: str
    pct: float          # signed fraction, +0.005 = +0.5 %
    qty: int

    def span(self) -> tuple[int, int]:
        i0, i1 = bar_index(self.start), bar_index(self.end)
        if i0 is None or i1 is None or i1 <= i0:
            raise ValueError(f"impact window outside session: {self.start}..{self.end}")
        return i0, i1

    def offsets(self) -> np.ndarray:
        """Additive log-price offsets over all bars."""
        i0, i1 = self.span()
        out = np.zeros(N_DAYS * N_BARS)
        full = math.log1p(self.pct)
        out[i0:i1] = full * (np.arange(i1 - i0) / (i1 - i0))
        out[i1:] = full
        return out


class PriceBook:
    """1-minute bars for every scrip on a shared minute grid, with nearest-minute lookups."""

    def __init__(self, times: list[str], bars: dict[str, dict[str, list]]) -> None:
        self.times = times
        self._bars = bars
        self._keys = np.array([minute_key(t) for t in times])

    @property
    def scrips(self) -> list[str]:
        return list(self._bars)

    def _nearest(self, time: str) -> int:
        k = minute_key(time)
        i = int(np.searchsorted(self._keys, k))
        if i <= 0:
            return 0
        if i >= len(self._keys):
            return len(self._keys) - 1
        return i if self._keys[i] - k < k - self._keys[i - 1] else i - 1

    def price_at(self, scrip: str, time: str) -> float:
        """Close of the bar nearest to `time` (ties go to the earlier bar)."""
        return self._bars[scrip]["close"][self._nearest(time)]

    def window(self, scrip: str, start: str, end: str) -> list[tuple[str, float]]:
        """(time, close) pairs for bars with start <= time <= end."""
        lo, hi = minute_key(start), minute_key(end)
        closes = self._bars[scrip]["close"]
        return [(t, closes[i]) for i, t in enumerate(self.times) if lo <= self._keys[i] <= hi]

    def to_csv(self, path: str | Path) -> int:
        """Write `scrip,time,open,high,low,close,volume` rows; returns the row count."""
        rows = 0
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(",".join(CSV_HEADER) + "\n")
            for scrip, b in self._bars.items():
                for i, t in enumerate(self.times):
                    fh.write(f"{scrip},{t},{b['open'][i]:.2f},{b['high'][i]:.2f},{b['low'][i]:.2f},"
                             f"{b['close'][i]:.2f},{b['volume'][i]}\n")
                    rows += 1
        return rows

    @classmethod
    def from_csv(cls, path: str | Path) -> PriceBook:
        """Load bars written by `to_csv`."""
        bars: dict[str, dict[str, list]] = {}
        times: dict[str, list[str]] = {}
        with open(path, encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                b = bars.setdefault(row["scrip"], {"open": [], "high": [], "low": [], "close": [], "volume": []})
                times.setdefault(row["scrip"], []).append(row["time"])
                for col in ("open", "high", "low", "close"):
                    b[col].append(float(row[col]))
                b["volume"].append(int(row["volume"]))
        grid = next(iter(times.values()))
        if any(t != grid for t in times.values()):
            raise ValueError("all scrips must share the same minute grid")
        return cls(grid, bars)


class PriceModel:
    """Seeded GBM base log-paths; `book(impacts)` adds fund-order impact and renders OHLCV bars."""

    def __init__(self, seed: int) -> None:
        self._seed = seed
        rng = np.random.default_rng([seed, 101])
        self._log: dict[str, np.ndarray] = {}
        for scrip in SCRIPS:
            sig = ANNUAL_VOL[scrip] / math.sqrt(_MINUTES_PER_YEAR)
            r = rng.normal(-0.5 * sig * sig, sig, size=(N_DAYS, N_BARS))
            r[1:, 0] += rng.normal(0.0, sig * math.sqrt(N_BARS) * 0.35, size=N_DAYS - 1)  # overnight gaps
            self._log[scrip] = np.cumsum(r.ravel())

    def log_path(self, scrip: str, impacts: Iterable[Impact] = ()) -> np.ndarray:
        """Log(close / level) for every bar, base GBM plus the impacts on this scrip."""
        path = self._log[scrip].copy()
        for imp in impacts:
            if imp.scrip == scrip:
                path += imp.offsets()
        return path

    def book(self, impacts: list[Impact]) -> PriceBook:
        """Render bars with all impacts applied (fund execution volume added to the bars it spans)."""
        rng = np.random.default_rng([self._seed, 202])
        n = N_DAYS * N_BARS
        times = [bar_time(i) for i in range(n)]
        minute = np.tile(np.arange(N_BARS), N_DAYS)
        u_shape = 1.0 + 1.5 * np.exp(-minute / 25.0) + 1.0 * np.exp(-(N_BARS - 1 - minute) / 25.0)
        bars: dict[str, dict[str, list]] = {}
        for scrip in SCRIPS:
            level = SCRIP_LEVELS[scrip]
            sig = ANNUAL_VOL[scrip] / math.sqrt(_MINUTES_PER_YEAR)
            close = _round_ticks(level * np.exp(self.log_path(scrip, impacts)))
            open_ = np.concatenate(([round_tick(level)], close[:-1]))
            wick = np.abs(rng.normal(0.0, sig * 0.6, size=(2, n)))
            high = np.maximum(_round_ticks(np.maximum(open_, close) * np.exp(wick[0])), np.maximum(open_, close))
            low = np.minimum(_round_ticks(np.minimum(open_, close) * np.exp(-wick[1])), np.minimum(open_, close))
            volume = BASE_VOLUME[scrip] * u_shape * rng.lognormal(0.0, 0.35, size=n)
            for imp in impacts:
                if imp.scrip == scrip:
                    i0, i1 = imp.span()
                    volume[i0:i1 + 1] += imp.qty / (i1 - i0 + 1)
            bars[scrip] = {
                "open": open_.tolist(), "high": high.tolist(), "low": low.tolist(),
                "close": close.tolist(), "volume": np.round(volume).astype(int).tolist(),
            }
        return PriceBook(times, bars)
