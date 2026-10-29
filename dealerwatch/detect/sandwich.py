"""Deterministic sandwich detector: retail accounts that trade ahead of a fund order and reverse into it."""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections import defaultdict
from datetime import datetime, timedelta

from dealerwatch import config
from dealerwatch.io import parse_ts
from dealerwatch.models import Candidate, FundOrder, Side, Trade


def opposite(side: Side) -> Side:
    """The other side of a trade."""
    return Side.SELL if side == Side.BUY else Side.BUY


def legs_for_order(order: FundOrder, trades: list[Trade],
                   parsed: dict[str, datetime] | None = None) -> dict[str, tuple[list[Trade], list[Trade]]]:
    """Per account: (pre trades, post trades) around one fund order.

    BUY order at t0: pre = BUY in [t0-PRE, t0), post = SELL in (t0, t0+POST]; mirrored for SELL orders.
    """
    t0 = parse_ts(order.order_time)
    pre_start = t0 - timedelta(minutes=config.PRE_WINDOW_MIN)
    post_end = t0 + timedelta(minutes=config.POST_WINDOW_MIN)
    exit_side = opposite(order.side)
    legs: dict[str, tuple[list[Trade], list[Trade]]] = defaultdict(lambda: ([], []))
    for tr in trades:
        if tr.scrip != order.scrip:
            continue
        ts = parsed[tr.trade_id] if parsed else parse_ts(tr.time)
        if tr.side == order.side and pre_start <= ts < t0:
            legs[tr.account_id][0].append(tr)
        elif tr.side == exit_side and t0 < ts <= post_end:
            legs[tr.account_id][1].append(tr)
    return legs


def sandwich_profit(order_side: Side, pre: list[Trade], post: list[Trade]) -> float:
    """Profit on the matched quantity (min of pre/post qty) using volume-weighted prices."""
    pre_qty = sum(t.qty for t in pre)
    post_qty = sum(t.qty for t in post)
    if pre_qty <= 0 or post_qty <= 0:
        return 0.0
    pre_avg = sum(t.qty * t.price for t in pre) / pre_qty
    post_avg = sum(t.qty * t.price for t in post) / post_qty
    matched = min(pre_qty, post_qty)
    edge = post_avg - pre_avg if order_side == Side.BUY else pre_avg - post_avg
    return round(matched * edge, 2)


def sandwich_score(hit_count: int, profit_inr: float, minutes_before: float) -> float:
    """0.35*hits + 0.35*profit + 0.30*timing, each term normalised to [0, 1]."""
    hits = min(1.0, hit_count / config.SCORE_HIT_NORM)
    profit = min(1.0, max(0.0, profit_inr) / config.SCORE_PROFIT_NORM_INR)
    timing = min(1.0, max(0.0, 1.0 - (minutes_before / config.PRE_WINDOW_MIN) * 0.5))
    return round(0.35 * hits + 0.35 * profit + 0.30 * timing, 4)


def _by_time(trades: list[Trade]) -> list[Trade]:
    return sorted(trades, key=lambda t: (t.time, t.trade_id))


def find_candidates(orders: list[FundOrder], trades: list[Trade]) -> list[Candidate]:
    """All sandwiches, using a scrip/time index; sorted by score desc, order_id, account_id.

    Parse and sort each trade once, then inspect only each order's closed outer window.
    `legs_for_order` still applies the side and open-at-order-time rules.
    """
    parsed = {t.trade_id: parse_ts(t.time) for t in trades}
    by_scrip: dict[str, list[Trade]] = defaultdict(list)
    for tr in trades:
        by_scrip[tr.scrip].append(tr)
    times_by_scrip: dict[str, list[datetime]] = {}
    for scrip, scrip_trades in by_scrip.items():
        scrip_trades.sort(key=lambda t: (parsed[t.trade_id], t.trade_id))
        times_by_scrip[scrip] = [parsed[t.trade_id] for t in scrip_trades]

    raw: list[tuple[FundOrder, str, list[Trade], list[Trade]]] = []
    for order in sorted(orders, key=lambda o: (o.order_time, o.order_id)):
        t0 = parse_ts(order.order_time)
        times = times_by_scrip.get(order.scrip, [])
        lo = bisect_left(times, t0 - timedelta(minutes=config.PRE_WINDOW_MIN))
        hi = bisect_right(times, t0 + timedelta(minutes=config.POST_WINDOW_MIN))
        legs = legs_for_order(order, by_scrip.get(order.scrip, [])[lo:hi], parsed)
        for account_id in sorted(legs):
            pre, post = legs[account_id]
            if sum(t.qty for t in pre) < config.MIN_PRE_QTY or not post:
                continue
            raw.append((order, account_id, _by_time(pre), _by_time(post)))

    hits: dict[str, set[str]] = defaultdict(set)
    for order, account_id, _, _ in raw:
        hits[account_id].add(order.order_id)

    out: list[Candidate] = []
    for order, account_id, pre, post in raw:
        t0 = parse_ts(order.order_time)
        minutes_before = round((t0 - parsed[pre[0].trade_id]).total_seconds() / 60.0, 2)
        minutes_after = round((parsed[post[-1].trade_id] - t0).total_seconds() / 60.0, 2)
        profit = sandwich_profit(order.side, pre, post)
        hit_count = len(hits[account_id])
        out.append(Candidate(
            candidate_id=f"X-{order.order_id}-{account_id}",
            order_id=order.order_id,
            account_id=account_id,
            scrip=order.scrip,
            pre_trade_ids=[t.trade_id for t in pre],
            post_trade_ids=[t.trade_id for t in post],
            pre_qty=sum(t.qty for t in pre),
            post_qty=sum(t.qty for t in post),
            profit_inr=profit,
            minutes_before=minutes_before,
            minutes_after=minutes_after,
            hit_count=hit_count,
            score=sandwich_score(hit_count, profit, minutes_before),
        ))
    out.sort(key=lambda c: (-c.score, c.order_id, c.account_id))
    return out
