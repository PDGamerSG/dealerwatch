"""Read-only evidence gathering: the dealer's calls into the account's link network before the order."""
from __future__ import annotations

from datetime import timedelta

from toolkit import asr

from dealerwatch import config
from dealerwatch.detect.links import normalize_phone
from dealerwatch.io import parse_ts
from dealerwatch.models import Call, FundOrder, Utterance

TranscriptCache = dict[str, tuple[Call, str]]


def calls_in_window(order: FundOrder, calls: list[Call], numbers: set[str]) -> list[Call]:
    """Calls by order.dealer_id starting in [order_time - lookback, order_time] to a network number."""
    t0 = parse_ts(order.order_time)
    start = t0 - timedelta(minutes=config.CALL_LOOKBACK_MIN)
    wanted = {normalize_phone(n) for n in numbers}
    hits = [c for c in calls
            if c.dealer_id == order.dealer_id
            and start <= parse_ts(c.start_time) <= t0
            and normalize_phone(c.counterparty_number) in wanted]
    return sorted(hits, key=lambda c: (c.start_time, c.call_id))


def transcribe_call(call: Call, data_dir: str, cache: TranscriptCache | None = None) -> tuple[Call, str]:
    """Return a copy of the call whose utterances come from toolkit.asr, plus the provider used."""
    if cache is not None and call.call_id in cache:
        return cache[call.call_id]
    raw, provider = asr.transcribe(call.model_dump(mode="json"), data_dir)
    result = (call.model_copy(update={"utterances": [Utterance.model_validate(u) for u in raw]}), provider)
    if cache is not None:
        cache[call.call_id] = result
    return result


def gather_calls(order: FundOrder, calls: list[Call], numbers: set[str], data_dir: str,
                 cache: TranscriptCache | None = None) -> tuple[list[Call], set[str]]:
    """Transcribed calls in the window touching the network, and the set of ASR providers used."""
    out: list[Call] = []
    providers: set[str] = set()
    for call in calls_in_window(order, calls, numbers):
        transcribed, provider = transcribe_call(call, data_dir, cache)
        out.append(transcribed)
        providers.add(provider)
    return out, providers
