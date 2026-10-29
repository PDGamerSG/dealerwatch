"""Evaluation on a labelled synthetic universe: DealerWatch vs a rules-only sandwich-score baseline.

Population = every detector candidate plus every planted (truth) pair. Planted pairs carry their
expected recommendation; every other candidate is background and counts as a negative. A planted
pair with no candidate is a produced DISMISS. Baseline escalates iff candidate score >= 0.5.

CLI: python -m dealerwatch.eval.harness --data data/generated --runtime runtime [--md EVAL.md]
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

from dealerwatch import config
from dealerwatch.io import load_universe
from dealerwatch.models import Recommendation
from dealerwatch.pipeline import run
from dealerwatch.store import Store

LABELS = ("TRUE_FR", "INJECTION_FR", "LINKED_NO_CALL", "CALL_NO_CUE", "COINCIDENCE")
RECS = tuple(r.value for r in Recommendation)


def _ratio(num: int, den: int) -> float:
    return round(num / den, 4) if den else 0.0


def prf(pairs: list[tuple[bool, bool]]) -> dict[str, Any]:
    """Confusion counts, precision, recall and F1 from (gold, predicted) booleans."""
    tp = sum(g and p for g, p in pairs)
    fp = sum(p and not g for g, p in pairs)
    fn = sum(g and not p for g, p in pairs)
    tn = sum(not g and not p for g, p in pairs)
    precision, recall = _ratio(tp, tp + fp), _ratio(tp, tp + fn)
    f1 = round(2 * precision * recall / (precision + recall), 4) if precision + recall else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": precision, "recall": recall, "f1": f1}


def percentile(values: list[int], q: float) -> int:
    """Nearest-rank percentile (0 for an empty list)."""
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(q / 100 * len(ordered)) - 1)]


def evaluate(data_dir: str, runtime_dir: str, llm: Any = None) -> dict[str, Any]:
    """Run the pipeline on `data_dir` and score it against truth.json."""
    stats = run(data_dir, runtime_dir, llm=llm)
    cases = Store(Path(runtime_dir) / config.DB_FILE).list_cases()
    truth = load_universe(data_dir).truth.get("cases", [])
    by_pair = {(c.order.order_id, c.account.account_id): c for c in cases}
    planted = {(t["order_id"], t["account_id"]): t for t in truth}

    rows = []
    for pair in sorted(set(by_pair) | set(planted)):
        case, gold = by_pair.get(pair), planted.get(pair)
        rows.append({
            "order_id": pair[0], "account_id": pair[1],
            "label": gold["label"] if gold else None,
            "expected": gold["expected"] if gold else None,
            "case_id": case.case_id if case else None,
            "score": case.candidate.score if case else None,
            "produced": case.recommendation.value if case else Recommendation.DISMISS.value,
            "baseline": Recommendation.ESCALATE.value
            if case and case.candidate.score >= config.BASELINE_ESCALATE_SCORE else Recommendation.DISMISS.value,
        })

    esc = Recommendation.ESCALATE.value
    dw = prf([(r["expected"] == esc, r["produced"] == esc) for r in rows])
    base = prf([(r["expected"] == esc, r["baseline"] == esc) for r in rows])

    labels = [lb for lb in LABELS if any(r["label"] == lb for r in rows)]
    labels += sorted({r["label"] for r in rows if r["label"] and r["label"] not in LABELS})
    per_label = []
    for lb in labels:
        sub = [r for r in rows if r["label"] == lb]
        per_label.append({
            "label": lb, "n": len(sub),
            "expected": sorted({r["expected"] for r in sub}),
            "dealerwatch": {rec: sum(r["produced"] == rec for r in sub) for rec in RECS},
            "dealerwatch_correct": sum(r["produced"] == r["expected"] for r in sub),
            "baseline_escalate": sum(r["baseline"] == esc for r in sub),
            "baseline_correct": sum(r["baseline"] == r["expected"] for r in sub),
        })

    planted_rows = [r for r in rows if r["label"]]
    background = [r for r in rows if not r["label"]]
    latencies = [c.latency_ms for c in cases]
    review = Recommendation.REVIEW.value
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "data_dir": str(data_dir),
        "run": stats.model_dump(mode="json"),
        "population": len(rows),
        "candidates": len(cases),
        "planted": len(planted_rows),
        "planted_without_candidate": sum(1 for r in planted_rows if r["case_id"] is None),
        "escalate": {"dealerwatch": dw, "baseline": base},
        "accuracy_planted": {
            "dealerwatch": _ratio(sum(r["produced"] == r["expected"] for r in planted_rows), len(planted_rows)),
            "baseline": _ratio(sum(r["baseline"] == r["expected"] for r in planted_rows), len(planted_rows)),
        },
        "per_label": per_label,
        "review_rate": _ratio(sum(c.recommendation.value == review for c in cases), len(cases)),
        "review_rate_planted": _ratio(sum(r["produced"] == review for r in planted_rows), len(planted_rows)),
        "false_alarms": {
            "non_planted_candidates": len(background),
            "dealerwatch_escalate": sum(r["produced"] == esc for r in background),
            "dealerwatch_review": sum(r["produced"] == review for r in background),
            "baseline_escalate": sum(r["baseline"] == esc for r in background),
        },
        "latency_ms": {"p50": percentile(latencies, 50), "p95": percentile(latencies, 95),
                       "max": max(latencies, default=0), "n": len(latencies)},
        "rows": rows,
    }


def to_markdown(result: dict[str, Any]) -> str:
    """EVAL.md: metric tables for the run."""
    dw, base = result["escalate"]["dealerwatch"], result["escalate"]["baseline"]
    run_s, fa, lat = result["run"], result["false_alarms"], result["latency_ms"]
    lines = [
        "# DealerWatch evaluation",
        "",
        f"Generated {result['generated_at']} on `{result['data_dir']}` (synthetic, seed-labelled). "
        f"LLM: {run_s['llm_provider']} ({run_s['llm_calls']} calls, {run_s['llm_fallbacks']} fallbacks); "
        f"ASR: {run_s['asr_provider']}.",
        "",
        f"Population: {result['population']} (order, account) pairs = {result['candidates']} detector candidates "
        f"plus {result['planted_without_candidate']} planted pairs without a candidate; {result['planted']} planted. "
        "Background candidates count as negatives. Baseline: escalate iff sandwich score >= "
        f"{config.BASELINE_ESCALATE_SCORE}.",
        "",
        "## ESCALATE",
        "",
        "| System | TP | FP | FN | TN | Precision | Recall | F1 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name, m in (("DealerWatch", dw), ("Rules-only baseline", base)):
        lines.append(f"| {name} | {m['tp']} | {m['fp']} | {m['fn']} | {m['tn']} | {m['precision']:.3f} | "
                     f"{m['recall']:.3f} | {m['f1']:.3f} |")
    lines += [
        "",
        "## Per label (planted cases)",
        "",
        "| Label | n | Expected | DW ESCALATE | DW REVIEW | DW DISMISS | DW correct | Baseline ESCALATE | Baseline correct |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row in result["per_label"]:
        d = row["dealerwatch"]
        lines.append(f"| {row['label']} | {row['n']} | {'/'.join(row['expected'])} | {d['ESCALATE']} | {d['REVIEW']} | "
                     f"{d['DISMISS']} | {row['dealerwatch_correct']}/{row['n']} | {row['baseline_escalate']} | "
                     f"{row['baseline_correct']}/{row['n']} |")
    acc = result["accuracy_planted"]
    lines += [
        "",
        "## Abstain, false alarms, latency",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Planted-case accuracy (DealerWatch / baseline) | {acc['dealerwatch']:.3f} / {acc['baseline']:.3f} |",
        f"| REVIEW (abstain) rate, all candidates | {result['review_rate']:.3f} |",
        f"| REVIEW rate, planted cases | {result['review_rate_planted']:.3f} |",
        f"| Non-planted candidates | {fa['non_planted_candidates']} |",
        f"| False alarms: DealerWatch ESCALATE / REVIEW | {fa['dealerwatch_escalate']} / {fa['dealerwatch_review']} |",
        f"| False alarms: baseline ESCALATE | {fa['baseline_escalate']} |",
        f"| Case latency p50 / p95 / max (ms) | {lat['p50']} / {lat['p95']} / {lat['max']} |",
        f"| Pipeline total (ms) | {run_s['total_ms']} |",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate DealerWatch on a labelled data directory.")
    parser.add_argument("--data", default="data/generated")
    parser.add_argument("--runtime", default="runtime")
    parser.add_argument("--md", default="EVAL.md", help="markdown report path")
    args = parser.parse_args(argv)
    result = evaluate(args.data, args.runtime)
    out = Path(args.runtime) / "eval.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    Path(args.md).write_text(to_markdown(result), encoding="utf-8")
    dw, base = result["escalate"]["dealerwatch"], result["escalate"]["baseline"]
    print(f"ESCALATE F1 DealerWatch {dw['f1']:.3f} (P {dw['precision']:.3f} R {dw['recall']:.3f}) | "
          f"baseline {base['f1']:.3f} (P {base['precision']:.3f} R {base['recall']:.3f}) | "
          f"review rate {result['review_rate']:.3f} | p50 {result['latency_ms']['p50']} ms -> {out}, {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
