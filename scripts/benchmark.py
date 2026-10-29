"""Reproducible detector benchmark; generates independent data in memory, never runs the pipeline.

Run: python scripts/benchmark.py --orders 1000 --trades 100000 --repeat 3 --seed 7
The optional --output path receives only the JSON measurement report, never a dataset or database.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random
import statistics
import sys
from collections import defaultdict
from collections.abc import Callable, Iterable
from datetime import datetime, timedelta
from pathlib import Path
from time import perf_counter

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dealerwatch import config
from dealerwatch.data.prices import SCRIP_LEVELS, TRADING_DAYS
from dealerwatch.detect.sandwich import find_candidates, legs_for_order, opposite, sandwich_profit, sandwich_score
from dealerwatch.io import parse_ts
from dealerwatch.models import Candidate, FundOrder, Side, Trade


def make_workload(seed: int, n_orders: int, n_trades: int) -> tuple[list[FundOrder], list[Trade]]:
    """Unique orders/trades over 20 sessions and 600 accounts, including two legs per order."""
    if n_orders < 1 or n_trades < 2 * n_orders:
        raise ValueError("orders must be positive and trades must be at least twice the order count")
    rng = random.Random(seed)
    scrips = tuple(SCRIP_LEVELS)
    orders, trades = [], []

    def add_trade(account: str, scrip: str, side: Side, qty: int, price: float, time: datetime) -> None:
        trades.append(Trade(trade_id=f"BENCH-T-{len(trades):09d}", account_id=account, scrip=scrip,
                            side=side, qty=qty, price=round(price, 2), time=time.isoformat()))

    for index in range(n_orders):
        day = rng.choice(TRADING_DAYS)
        time = datetime(day.year, day.month, day.day, 10, 30) + timedelta(minutes=rng.randrange(181))
        scrip, side = rng.choice(scrips), rng.choice(list(Side))
        orders.append(FundOrder(order_id=f"BENCH-O-{index:06d}", scheme="Synthetic benchmark fund", scrip=scrip,
                                side=side, qty=rng.randrange(2, 9) * 100000, order_time=time.isoformat(),
                                exec_start=(time + timedelta(minutes=2)).isoformat(),
                                exec_end=(time + timedelta(minutes=40)).isoformat(), dealer_id=f"D{index % 3 + 1}"))
        account, qty = f"BENCH-A-{rng.randrange(600):04d}", rng.randrange(1, 51) * 100
        pre_price = SCRIP_LEVELS[scrip] * rng.uniform(0.98, 1.02)
        post_price = pre_price * (1 + rng.uniform(0.002, 0.01) * (1 if side == Side.BUY else -1))
        add_trade(account, scrip, side, qty, pre_price, time - timedelta(minutes=rng.randrange(5, 56)))
        add_trade(account, scrip, opposite(side), qty, post_price, time + timedelta(minutes=rng.randrange(10, 81)))
    while len(trades) < n_trades:
        day, scrip = rng.choice(TRADING_DAYS), rng.choice(scrips)
        time = datetime(day.year, day.month, day.day, 9, 15) + timedelta(seconds=rng.randrange(375 * 60))
        add_trade(f"BENCH-A-{rng.randrange(600):04d}", scrip, rng.choice(list(Side)), rng.randrange(1, 201) * 10,
                  SCRIP_LEVELS[scrip] * rng.uniform(0.97, 1.03), time)
    rng.shuffle(orders)
    rng.shuffle(trades)
    return orders, trades


def scan_reference(orders: list[FundOrder], trades: list[Trade]) -> list[Candidate]:
    """Previous algorithm: scan every trade of an order's scrip, without a time index."""
    parsed = {trade.trade_id: parse_ts(trade.time) for trade in trades}
    by_scrip = defaultdict(list)
    for trade in trades:
        by_scrip[trade.scrip].append(trade)
    raw, hits = [], defaultdict(set)
    for order in sorted(orders, key=lambda item: (item.order_time, item.order_id)):
        for account, (pre, post) in legs_for_order(order, by_scrip[order.scrip], parsed).items():
            if sum(trade.qty for trade in pre) < config.MIN_PRE_QTY or not post:
                continue
            raw.append((order, account, sorted(pre, key=lambda item: (item.time, item.trade_id)),
                        sorted(post, key=lambda item: (item.time, item.trade_id))))
            hits[account].add(order.order_id)
    output = []
    for order, account, pre, post in raw:
        time = parse_ts(order.order_time)
        before = round((time - parsed[pre[0].trade_id]).total_seconds() / 60, 2)
        after = round((parsed[post[-1].trade_id] - time).total_seconds() / 60, 2)
        profit, hit_count = sandwich_profit(order.side, pre, post), len(hits[account])
        output.append(Candidate(candidate_id=f"X-{order.order_id}-{account}", order_id=order.order_id,
                                account_id=account, scrip=order.scrip,
                                pre_trade_ids=[trade.trade_id for trade in pre],
                                post_trade_ids=[trade.trade_id for trade in post],
                                pre_qty=sum(trade.qty for trade in pre), post_qty=sum(trade.qty for trade in post),
                                profit_inr=profit, minutes_before=before, minutes_after=after, hit_count=hit_count,
                                score=sandwich_score(hit_count, profit, before)))
    return sorted(output, key=lambda candidate: (-candidate.score, candidate.order_id, candidate.account_id))


def _digest(items: Iterable) -> str:
    digest = hashlib.sha256()
    for item in items:
        digest.update(item.model_dump_json().encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def measure(seed: int = 7, n_orders: int = 1000, n_trades: int = 100000, repeat: int = 3) -> dict:
    """Time both algorithms after a warmup, checking all candidate fields for equality."""
    if repeat < 1:
        raise ValueError("repeat must be positive")
    orders, trades = make_workload(seed, n_orders, n_trades)
    expected = scan_reference(orders, trades)
    indexed = find_candidates(orders, trades)
    if indexed != expected:
        raise AssertionError("indexed detector differs from the scan reference")
    expected_digest = _digest(expected)

    def timings(detector: Callable) -> dict:
        elapsed = []
        for _ in range(repeat):
            started = perf_counter()
            candidates = detector(orders, trades)
            elapsed.append((perf_counter() - started) * 1000)
            if _digest(candidates) != expected_digest:
                raise AssertionError("detector result changed between repetitions")
        return {"runs_ms": [round(value, 3) for value in elapsed],
                "median_ms": round(statistics.median(elapsed), 3), "min_ms": round(min(elapsed), 3)}

    indexed_times, reference_times = timings(find_candidates), timings(scan_reference)
    return {
        "environment": {"python": platform.python_version(), "platform": platform.platform(),
                        "machine": platform.machine(), "processor": platform.processor(),
                        "logical_cpus": os.cpu_count()},
        "workload": {"seed": seed, "orders": len(orders), "trades": len(trades), "accounts": 600,
                     "scrips": len(SCRIP_LEVELS), "trading_days": len(TRADING_DAYS),
                     "orders_sha256": _digest(orders), "trades_sha256": _digest(trades)},
        "method": "In-memory independent seeded data; one untimed warmup per algorithm; parsing/indexing included; generation, IO and pipeline excluded.",
        "repetitions": repeat, "candidates": len(expected), "equivalent": True,
        "candidate_sha256": expected_digest,
        "indexed": indexed_times, "scan_reference": reference_times,
        "median_speedup": round(reference_times["median_ms"] / indexed_times["median_ms"], 2),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--orders", type=int, default=1000)
    parser.add_argument("--trades", type=int, default=100000)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--output", type=Path, help="optional JSON report path")
    args = parser.parse_args(argv)
    try:
        result = measure(args.seed, args.orders, args.trades, args.repeat)
    except ValueError as exc:
        parser.error(str(exc))
    report = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
