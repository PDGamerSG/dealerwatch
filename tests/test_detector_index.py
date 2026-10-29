"""Indexed windows must retain scan semantics, including exact timestamps and ties."""
from __future__ import annotations

import random
from collections import defaultdict
from datetime import datetime, timedelta

import pytest

from dealerwatch.detect import sandwich
from dealerwatch.models import FundOrder, Side, Trade
from scripts.benchmark import make_workload, scan_reference


def scan_candidates(orders: list[FundOrder], trades: list[Trade]) -> list[dict]:
    """Deliberately simple independent oracle for the documented detector contract."""
    raw = []
    hits = defaultdict(set)
    for order in orders:
        t0 = datetime.fromisoformat(order.order_time)
        groups = defaultdict(lambda: ([], []))
        for trade in trades:
            delta = (datetime.fromisoformat(trade.time) - t0).total_seconds()
            if trade.scrip == order.scrip:
                if trade.side == order.side and -3600 <= delta < 0:
                    groups[trade.account_id][0].append(trade)
                if trade.side != order.side and 0 < delta <= 5400:
                    groups[trade.account_id][1].append(trade)
        for account_id, (pre, post) in groups.items():
            pre.sort(key=lambda trade: (trade.time, trade.trade_id))
            post.sort(key=lambda trade: (trade.time, trade.trade_id))
            if sum(trade.qty for trade in pre) >= 100 and post:
                raw.append((order, account_id, pre, post))
                hits[account_id].add(order.order_id)
    output = []
    for order, account_id, pre, post in raw:
        before = round((datetime.fromisoformat(order.order_time) - datetime.fromisoformat(pre[0].time)).total_seconds() / 60, 2)
        after = round((datetime.fromisoformat(post[-1].time) - datetime.fromisoformat(order.order_time)).total_seconds() / 60, 2)
        pre_qty, post_qty = sum(t.qty for t in pre), sum(t.qty for t in post)
        change = sum(t.price * t.qty for t in post) / post_qty - sum(t.price * t.qty for t in pre) / pre_qty
        profit = round(min(pre_qty, post_qty) * change * (1 if order.side == Side.BUY else -1), 2)
        hit_count = len(hits[account_id])
        score = round(0.35 * min(1, hit_count / 3) + 0.35 * min(1, max(0, profit) / 200000)
                      + 0.3 * min(1, max(0, 1 - before / 120)), 4)
        output.append({"candidate_id": f"X-{order.order_id}-{account_id}", "order_id": order.order_id,
                       "account_id": account_id, "scrip": order.scrip,
                       "pre_trade_ids": [t.trade_id for t in pre], "post_trade_ids": [t.trade_id for t in post],
                       "pre_qty": pre_qty, "post_qty": post_qty, "profit_inr": profit,
                       "minutes_before": before, "minutes_after": after, "hit_count": hit_count, "score": score})
    return sorted(output, key=lambda candidate: (-candidate["score"], candidate["order_id"], candidate["account_id"]))


def make_order(identifier: str, time: datetime, side: Side = Side.BUY, scrip: str = "INFY") -> FundOrder:
    return FundOrder(order_id=identifier, order_time=time.isoformat(), exec_start=time.isoformat(),
                     exec_end=time.isoformat(), side=side, scrip=scrip, qty=100000, dealer_id="D1", scheme="Synthetic")


@pytest.mark.parametrize("seed", [1, 7, 42])
def test_shuffled_dense_windows_equal_independent_scan(seed: int) -> None:
    rng = random.Random(seed)
    start = datetime(2026, 9, 1, 9)
    scrips = ["INFY", "TCS", "LT"]
    orders = [make_order(f"O-{index}", start + timedelta(minutes=rng.randrange(2 * 1440)),
                         rng.choice(list(Side)), rng.choice(scrips)) for index in range(25)]
    trades = [Trade(trade_id=f"T-{index}", account_id=f"A-{rng.randrange(5)}", scrip=rng.choice(scrips),
                    side=rng.choice(list(Side)), qty=rng.choice([1, 49, 50, 99, 100, 1000]),
                    price=round(rng.uniform(100, 1000), 2),
                    time=(start + timedelta(minutes=rng.randrange(2 * 1440), seconds=rng.randrange(60))).isoformat())
              for index in range(1500)]
    expected = scan_candidates(orders, trades)
    assert expected
    rng.shuffle(orders)
    rng.shuffle(trades)
    assert [c.model_dump(mode="json") for c in sandwich.find_candidates(orders, trades)] == expected


@pytest.mark.parametrize("side", [Side.BUY, Side.SELL])
def test_bisect_boundaries_exclude_order_time_and_preserve_timestamp_ties(side: Side) -> None:
    t0 = datetime(2026, 9, 1, 12)
    order = make_order("O-boundary", t0, side)
    exit_side = Side.SELL if side == Side.BUY else Side.BUY
    specifications = [
        ("outside-pre", -3600_000001, side), ("pre-b", -3600_000000, side),
        ("pre-a", -3600_000000, side), ("at-order-pre", 0, side),
        ("at-order-post", 0, exit_side), ("post-b", 5400_000000, exit_side),
        ("post-a", 5400_000000, exit_side), ("outside-post", 5400_000001, exit_side),
    ]
    trades = [Trade(trade_id=identifier, account_id="A-1", scrip="INFY", side=trade_side, qty=100,
                    price=1500 if trade_side == side else 1510,
                    time=(t0 + timedelta(microseconds=offset)).isoformat())
              for identifier, offset, trade_side in specifications]
    [candidate] = sandwich.find_candidates([order], trades)
    assert candidate.pre_trade_ids == ["pre-a", "pre-b"]
    assert candidate.post_trade_ids == ["post-a", "post-b"]
    assert (candidate.minutes_before, candidate.minutes_after) == (60, 90)
    assert candidate.model_dump(mode="json") == scan_candidates([order], trades)[0]


def test_only_trades_in_the_scrip_time_window_reach_leg_scan(monkeypatch) -> None:
    t0 = datetime(2026, 9, 2, 12)
    orders = [make_order(f"O-{index}", t0) for index in range(20)]
    trades = [Trade(trade_id=f"history-{index}", account_id="A-1", scrip="INFY", side=Side.BUY,
                    qty=100, price=1500, time=(t0 - timedelta(days=10, seconds=index)).isoformat())
              for index in range(3000)]
    trades += [Trade(trade_id="pre", account_id="A-1", scrip="INFY", side=Side.BUY,
                     qty=100, price=1500, time=(t0 - timedelta(minutes=10)).isoformat()),
               Trade(trade_id="post", account_id="A-1", scrip="INFY", side=Side.SELL,
                     qty=100, price=1510, time=(t0 + timedelta(minutes=10)).isoformat())]
    scanned = 0
    original = sandwich.legs_for_order

    def count_scan(order, window, parsed=None):
        nonlocal scanned
        scanned += len(window)
        return original(order, window, parsed)

    monkeypatch.setattr(sandwich, "legs_for_order", count_scan)
    assert len(sandwich.find_candidates(orders, trades)) == len(orders)
    assert scanned <= 2 * len(orders), "historical trades must be excluded by the time index"


def test_benchmark_workload_is_independent_seeded_and_has_distinct_records() -> None:
    orders, trades = make_workload(seed=7, n_orders=20, n_trades=1000)
    assert len(orders) == len({order.order_id for order in orders}) == 20
    assert len(trades) == len({trade.trade_id for trade in trades}) == 1000
    assert (orders, trades) == make_workload(seed=7, n_orders=20, n_trades=1000)
    assert (orders, trades) != make_workload(seed=8, n_orders=20, n_trades=1000)
    expected = scan_candidates(orders, trades)
    assert len(expected) >= 20
    assert [candidate.model_dump(mode="json") for candidate in scan_reference(orders, trades)] == expected
