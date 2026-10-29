"""Sandwich detector: windows, sides, profit, hit_count, score and ordering."""
from __future__ import annotations

import pytest

from dealerwatch.detect.sandwich import find_candidates, sandwich_score
from dealerwatch.models import FundOrder, Side, Trade

DAY = "2026-09-01"


def order(oid: str, scrip: str, side: Side, at: str, qty: int = 500_000, day: str = DAY) -> FundOrder:
    ts = f"{day}T{at}:00"
    return FundOrder(order_id=oid, scheme="Sahyadri Bluechip Fund", scrip=scrip, side=side, qty=qty,
                     order_time=ts, exec_start=ts, exec_end=ts, dealer_id="D1")


def trade(tid: str, acct: str, scrip: str, side: Side, qty: int, price: float, at: str, day: str = DAY) -> Trade:
    return Trade(trade_id=tid, account_id=acct, scrip=scrip, side=side, qty=qty, price=price, time=f"{day}T{at}:00")


def test_buy_order_sandwich_profit_and_score() -> None:
    o = order("O-0001", "INFY", Side.BUY, "13:00")
    trades = [
        trade("T-1", "A-011", "INFY", Side.BUY, 1000, 1500.0, "12:20"),
        trade("T-2", "A-011", "INFY", Side.BUY, 500, 1502.0, "12:50"),
        trade("T-3", "A-011", "INFY", Side.SELL, 1500, 1520.0, "13:30"),
        trade("T-4", "A-011", "TCS", Side.BUY, 900, 3500.0, "12:30"),   # other scrip: ignored
    ]
    [c] = find_candidates([o], trades)
    assert c.candidate_id == "X-O-0001-A-011"
    assert (c.pre_trade_ids, c.post_trade_ids) == (["T-1", "T-2"], ["T-3"])
    assert (c.pre_qty, c.post_qty) == (1500, 1500)
    assert c.profit_inr == pytest.approx(1500 * 1520.0 - (1000 * 1500.0 + 500 * 1502.0))  # 29000
    assert (c.minutes_before, c.minutes_after, c.hit_count) == (40.0, 30.0, 1)
    expected = 0.35 * (1 / 3) + 0.35 * (29_000 / 200_000) + 0.30 * (1 - (40 / 60) * 0.5)
    assert c.score == pytest.approx(round(expected, 4))


def test_sell_order_is_mirrored() -> None:
    o = order("O-0002", "TCS", Side.SELL, "11:00")
    trades = [
        trade("T-1", "A-020", "TCS", Side.SELL, 800, 3500.0, "10:30"),
        trade("T-2", "A-020", "TCS", Side.BUY, 600, 3450.0, "11:45"),
        trade("T-3", "A-021", "TCS", Side.BUY, 800, 3500.0, "10:30"),   # wrong pre side for a SELL order
        trade("T-4", "A-021", "TCS", Side.SELL, 800, 3450.0, "11:45"),
    ]
    [c] = find_candidates([o], trades)
    assert c.account_id == "A-020"
    assert c.profit_inr == pytest.approx(600 * (3500.0 - 3450.0))  # matched qty = min(800, 600)
    assert (c.minutes_before, c.minutes_after) == (30.0, 45.0)


@pytest.mark.parametrize("pre_at,post_at,found", [
    ("12:00", "14:30", True),    # pre exactly t0-60 (closed), post exactly t0+90 (closed)
    ("11:59", "13:30", False),   # pre one minute before the window
    ("13:00", "13:30", False),   # pre at t0 (open end)
    ("12:30", "13:00", False),   # post at t0 (open start)
    ("12:30", "14:31", False),   # post one minute after the window
])
def test_window_edges(pre_at: str, post_at: str, found: bool) -> None:
    o = order("O-0001", "LT", Side.BUY, "13:00")
    trades = [trade("T-1", "A-030", "LT", Side.BUY, 500, 3600.0, pre_at),
              trade("T-2", "A-030", "LT", Side.SELL, 500, 3620.0, post_at)]
    assert bool(find_candidates([o], trades)) is found


def test_min_pre_qty_is_on_the_total() -> None:
    o = order("O-0001", "ITC", Side.BUY, "13:00")
    small = [trade("T-1", "A-040", "ITC", Side.BUY, 99, 450.0, "12:30"),
             trade("T-2", "A-040", "ITC", Side.SELL, 99, 455.0, "13:30")]
    assert find_candidates([o], small) == []
    split = [trade("T-1", "A-040", "ITC", Side.BUY, 60, 450.0, "12:30"),
             trade("T-2", "A-040", "ITC", Side.BUY, 40, 451.0, "12:40"),
             trade("T-3", "A-040", "ITC", Side.SELL, 100, 455.0, "13:30")]
    assert [c.pre_qty for c in find_candidates([o], split)] == [100]


def test_needs_a_post_trade() -> None:
    o = order("O-0001", "SBIN", Side.BUY, "13:00")
    assert find_candidates([o], [trade("T-1", "A-050", "SBIN", Side.BUY, 5000, 800.0, "12:30")]) == []


def test_hit_count_counts_orders_per_account() -> None:
    o1 = order("O-0001", "INFY", Side.BUY, "13:00", day="2026-09-01")
    o2 = order("O-0002", "TCS", Side.SELL, "11:00", day="2026-09-02")
    trades = [
        trade("T-1", "A-011", "INFY", Side.BUY, 1000, 1500.0, "12:30", "2026-09-01"),
        trade("T-2", "A-011", "INFY", Side.SELL, 1000, 1510.0, "13:20", "2026-09-01"),
        trade("T-3", "A-011", "TCS", Side.SELL, 300, 3500.0, "10:40", "2026-09-02"),
        trade("T-4", "A-011", "TCS", Side.BUY, 300, 3480.0, "11:20", "2026-09-02"),
        trade("T-5", "A-077", "INFY", Side.BUY, 200, 1500.0, "12:10", "2026-09-01"),
        trade("T-6", "A-077", "INFY", Side.SELL, 200, 1501.0, "13:10", "2026-09-01"),
    ]
    hits = {(c.order_id, c.account_id): c.hit_count for c in find_candidates([o1, o2], trades)}
    assert hits == {("O-0001", "A-011"): 2, ("O-0002", "A-011"): 2, ("O-0001", "A-077"): 1}


def test_score_bounds_and_ordering() -> None:
    assert sandwich_score(3, 250_000, 0) == 1.0
    assert sandwich_score(0, -5_000, 120) == 0.0          # negative profit and late timing clip to 0
    assert sandwich_score(1, 100_000, 60) == pytest.approx(round(0.35 / 3 + 0.175 + 0.15, 4))
    o = order("O-0001", "RELIANCE", Side.BUY, "13:00")
    trades = [trade("T-1", "A-002", "RELIANCE", Side.BUY, 100, 2900.0, "12:05"),
              trade("T-2", "A-002", "RELIANCE", Side.SELL, 100, 2901.0, "13:05"),
              trade("T-3", "A-001", "RELIANCE", Side.BUY, 5000, 2900.0, "12:55"),
              trade("T-4", "A-001", "RELIANCE", Side.SELL, 5000, 2950.0, "13:05")]
    cands = find_candidates([o], trades)
    assert [c.account_id for c in cands] == ["A-001", "A-002"]
    assert cands[0].score > cands[1].score
    assert find_candidates([o], list(reversed(trades))) == cands   # input order does not matter
