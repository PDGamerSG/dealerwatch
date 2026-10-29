"""Deterministic 9-link evidence chain and the recommendation rule (code only, no LLM)."""
from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta

from dealerwatch import config
from dealerwatch.detect.sandwich import opposite, sandwich_profit
from dealerwatch.io import parse_ts
from dealerwatch.models import (Call, Candidate, ChainLink, Clause, FundOrder, LeakCue, Link,
                                Recommendation, Side, Trade)

CHAIN_KEYS = ("order", "pre_trade", "post_trade", "profit", "pattern",
              "link_path", "call_in_window", "leak_cue", "clause")
CORE_KEYS = ("order", "pre_trade", "post_trade", "profit")
REVIEW_ANY_KEYS = ("link_path", "leak_cue", "pattern")
QUOTE_DETAIL_CHARS = 100


def _verb(side: Side) -> str:
    return "bought" if side == Side.BUY else "sold"


def indian(value: float, decimals: int = 0) -> str:
    """Indian digit grouping (12,34,567.50); an all-zero fraction is dropped."""
    whole, _, frac = f"{abs(value):.{decimals}f}".partition(".")
    head, groups = whole[:-3], [whole[-3:]]
    while head:
        groups.insert(0, head[-2:])
        head = head[:-2]
    sign = "-" if value < 0 and whole.strip("0") else ""
    return sign + ",".join(groups) + (f".{frac}" if frac.strip("0") else "")


def _inr(value: float, decimals: int = 0) -> str:
    return f"INR {indian(value, decimals)}"


def _span(values: list[float]) -> str:
    lo, hi = min(values), max(values)
    return f"{lo:.0f}" if round(lo) == round(hi) else f"{lo:.0f} to {hi:.0f}"


def _minutes(trade: Trade, order: FundOrder) -> float:
    """Minutes from the order time to the trade (negative = before)."""
    return (parse_ts(trade.time) - parse_ts(order.order_time)).total_seconds() / 60.0


def _leg_ok(legs: list[Trade], ids: list[str], account_id: str, order: FundOrder, side: Side,
            lo: float, hi: float, closed_open: bool) -> bool:
    """All ids resolve to trades by the account on the scrip and side, inside [lo, hi) or (lo, hi]."""
    if not ids or len(legs) != len(ids):
        return False
    for t in legs:
        m = _minutes(t, order)
        in_window = lo <= m < hi if closed_open else lo < m <= hi
        if t.account_id != account_id or t.scrip != order.scrip or t.side != side or not in_window:
            return False
    return True


def _order_link(candidate: Candidate, order: FundOrder) -> ChainLink:
    ok = order.order_id == candidate.order_id and order.scrip == candidate.scrip
    return ChainLink(key="order", ok=ok, evidence_ids=[f"o:{order.order_id}"],
                     detail=f"Fund {order.side.value} order {order.order_id}: {indian(order.qty)} {order.scrip} for "
                            f"{order.scheme}, dealer {order.dealer_id}, received {order.order_time}")


def _pre_link(candidate: Candidate, order: FundOrder, pre: list[Trade]) -> ChainLink:
    ok = _leg_ok(pre, candidate.pre_trade_ids, candidate.account_id, order, order.side,
                 -config.PRE_WINDOW_MIN, 0, closed_open=True) and sum(t.qty for t in pre) >= config.MIN_PRE_QTY
    ids = [f"t:{t.trade_id}" for t in pre]
    if not ok:
        return ChainLink(key="pre_trade", ok=False, evidence_ids=ids,
                         detail=f"No valid {order.side.value} trades by {candidate.account_id} of at least "
                                f"{config.MIN_PRE_QTY} shares in the {config.PRE_WINDOW_MIN} min before the order")
    mins = [-_minutes(t, order) for t in pre]
    return ChainLink(key="pre_trade", ok=True, evidence_ids=ids,
                     detail=f"{candidate.account_id} {_verb(order.side)} {indian(sum(t.qty for t in pre))} {order.scrip} "
                            f"in {len(pre)} trade(s), {_span(mins)} min before the order "
                            f"(window {config.PRE_WINDOW_MIN} min)")


def _post_link(candidate: Candidate, order: FundOrder, post: list[Trade]) -> ChainLink:
    side = opposite(order.side)
    ok = _leg_ok(post, candidate.post_trade_ids, candidate.account_id, order, side,
                 0, config.POST_WINDOW_MIN, closed_open=False)
    ids = [f"t:{t.trade_id}" for t in post]
    if not ok:
        return ChainLink(key="post_trade", ok=False, evidence_ids=ids,
                         detail=f"No valid {side.value} trades by {candidate.account_id} in the "
                                f"{config.POST_WINDOW_MIN} min after the order")
    mins = [_minutes(t, order) for t in post]
    return ChainLink(key="post_trade", ok=True, evidence_ids=ids,
                     detail=f"{candidate.account_id} {_verb(side)} {indian(sum(t.qty for t in post))} {order.scrip} "
                            f"in {len(post)} trade(s), {_span(mins)} min after the order "
                            f"(window {config.POST_WINDOW_MIN} min)")


def _profit_link(order: FundOrder, pre: list[Trade], post: list[Trade]) -> ChainLink:
    profit = sandwich_profit(order.side, pre, post)
    ids = [f"t:{t.trade_id}" for t in pre + post]
    pre_qty, post_qty = sum(t.qty for t in pre), sum(t.qty for t in post)
    if pre_qty <= 0 or post_qty <= 0:
        return ChainLink(key="profit", ok=False, evidence_ids=ids, detail="No matched quantity to value")
    pre_avg = sum(t.qty * t.price for t in pre) / pre_qty
    post_avg = sum(t.qty * t.price for t in post) / post_qty
    return ChainLink(key="profit", ok=profit > 0, evidence_ids=ids,
                     detail=f"Matched {indian(min(pre_qty, post_qty))} shares: avg {_verb(order.side)} at "
                            f"{_inr(pre_avg, 2)}, avg {_verb(opposite(order.side))} at {_inr(post_avg, 2)}; "
                            f"estimated profit {_inr(profit)}")


def _pattern_link(candidate: Candidate, pre: list[Trade]) -> ChainLink:
    value = sum(t.qty * t.price for t in pre)
    ok = candidate.hit_count >= config.PATTERN_MIN_HITS or value >= config.PATTERN_MIN_PRE_VALUE_INR
    return ChainLink(key="pattern", ok=ok, evidence_ids=[f"a:{candidate.account_id}"],
                     detail=f"Account sandwiched {candidate.hit_count} fund order(s); pre-trade value {_inr(value)} "
                            f"(threshold: {config.PATTERN_MIN_HITS} orders or "
                            f"{_inr(config.PATTERN_MIN_PRE_VALUE_INR)})")


def _path_link(candidate: Candidate, order: FundOrder, path: list[Link]) -> ChainLink:
    ok = bool(path) and path[0].src == order.dealer_id and path[-1].dst == candidate.account_id
    if not ok:
        return ChainLink(key="link_path", ok=False, evidence_ids=[f"a:{candidate.account_id}"],
                         detail=f"No link path from {order.dealer_id} to {candidate.account_id} in KYC, "
                                f"declarations or call logs")
    hops = "".join(f" -[{lk.kind}: {lk.source}]-> {lk.dst}" for lk in path)
    return ChainLink(key="link_path", ok=True, evidence_ids=[f"a:{candidate.account_id}"],
                     detail=f"{order.dealer_id}{hops} ({len(path)} hop(s))")


def _window_calls(order: FundOrder, calls: list[Call]) -> list[Call]:
    """Calls by the order's dealer starting within the lookback window before the order."""
    t0 = parse_ts(order.order_time)
    lo = t0 - timedelta(minutes=config.CALL_LOOKBACK_MIN)
    return [c for c in calls if c.dealer_id == order.dealer_id and lo <= parse_ts(c.start_time) <= t0]


def _call_link(order: FundOrder, valid: list[Call]) -> ChainLink:
    t0 = parse_ts(order.order_time)
    if not valid:
        return ChainLink(key="call_in_window", ok=False, evidence_ids=[],
                         detail=f"No call by {order.dealer_id} to the account network in the "
                                f"{config.CALL_LOOKBACK_MIN} min before the order")
    parts = [f"{c.call_id} to {c.counterparty_number} at {c.start_time} "
             f"({(t0 - parse_ts(c.start_time)).total_seconds() / 60:.0f} min before, {c.duration_s}s)"
             for c in valid]
    return ChainLink(key="call_in_window", ok=True, evidence_ids=[f"c:{c.call_id}" for c in valid],
                     detail=f"{len(valid)} call(s) by {order.dealer_id} to the account network within "
                            f"{config.CALL_LOOKBACK_MIN} min before the order: " + "; ".join(parts))


def _cue_link(candidate: Candidate, calls: list[Call], cues: list[LeakCue]) -> ChainLink:
    call_ids = {c.call_id for c in calls}
    hits = [c for c in cues if c.scrip == candidate.scrip and c.call_id in call_ids]
    if not hits:
        why = "no grounded cue names" if calls else "no call in the window to search for"
        return ChainLink(key="leak_cue", ok=False, evidence_ids=[], detail=f"Leak cue missing: {why} {candidate.scrip}")
    ids: list[str] = []
    for cue in hits:
        ids += [f"u:{u}" for u in cue.utterance_ids] + [f"c:{cue.call_id}"]
    first = hits[0]
    quote = first.quote if len(first.quote) <= QUOTE_DETAIL_CHARS else first.quote[:QUOTE_DETAIL_CHARS] + "..."
    return ChainLink(key="leak_cue", ok=True, evidence_ids=list(dict.fromkeys(ids)),
                     detail=f"{len(hits)} grounded cue(s) naming {candidate.scrip}; e.g. \"{quote}\" "
                            f"({', '.join(first.utterance_ids)}, {first.extractor})")


def _clause_link(clauses: Mapping[str, Clause]) -> ChainLink:
    found = [cid for cid in config.FRONT_RUNNING_CLAUSES if cid in clauses]
    missing = [cid for cid in config.FRONT_RUNNING_CLAUSES if cid not in clauses]
    detail = "; ".join(f"{cid}: {clauses[cid].title}" for cid in found)
    if missing:
        detail = (detail + "; " if detail else "") + "missing from clause table: " + ", ".join(missing)
    return ChainLink(key="clause", ok=not missing, evidence_ids=[f"l:{cid}" for cid in found], detail=detail)


def build_chain(candidate: Candidate, order: FundOrder, trades: Mapping[str, Trade], path: list[Link],
                calls: list[Call], cues: list[LeakCue], clauses: Mapping[str, Clause]) -> list[ChainLink]:
    """The 9 chain links in CHAIN_KEYS order, each re-derived from the raw evidence.

    `calls` are the gathered network calls; only those inside the lookback window count."""
    pre = [trades[i] for i in candidate.pre_trade_ids if i in trades]
    post = [trades[i] for i in candidate.post_trade_ids if i in trades]
    calls = _window_calls(order, calls)
    return [
        _order_link(candidate, order),
        _pre_link(candidate, order, pre),
        _post_link(candidate, order, post),
        _profit_link(order, pre, post),
        _pattern_link(candidate, pre),
        _path_link(candidate, order, path),
        _call_link(order, calls),
        _cue_link(candidate, calls, cues),
        _clause_link(clauses),
    ]


def recommend(chain: list[ChainLink]) -> Recommendation:
    """ESCALATE iff all 9 ok; REVIEW if core ok and (link_path or leak_cue or pattern); else DISMISS."""
    ok = {link.key: link.ok for link in chain}
    if tuple(link.key for link in chain) == CHAIN_KEYS and all(ok.values()):
        return Recommendation.ESCALATE
    if all(ok.get(k, False) for k in CORE_KEYS) and any(ok.get(k) for k in REVIEW_ANY_KEYS):
        return Recommendation.REVIEW
    return Recommendation.DISMISS
