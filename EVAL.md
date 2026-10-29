# DealerWatch evaluation

Generated 2026-10-29T10:12:27 on `data/generated` (synthetic, seed-labelled). LLM: mock (20 calls, 0 fallbacks); ASR: replay.

Population: 13 (order, account) pairs = 13 detector candidates plus 0 planted pairs without a candidate; 13 planted. Background candidates count as negatives. Baseline: escalate iff sandwich score >= 0.5.

## ESCALATE

| System | TP | FP | FN | TN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| DealerWatch | 6 | 0 | 0 | 7 | 1.000 | 1.000 | 1.000 |
| Rules-only baseline | 6 | 0 | 0 | 7 | 1.000 | 1.000 | 1.000 |

## Per label (planted cases)

| Label | n | Expected | DW ESCALATE | DW REVIEW | DW DISMISS | DW correct | Baseline ESCALATE | Baseline correct |
|---|---|---|---|---|---|---|---|---|
| TRUE_FR | 5 | ESCALATE | 5 | 0 | 0 | 5/5 | 5 | 5/5 |
| INJECTION_FR | 1 | ESCALATE | 1 | 0 | 0 | 1/1 | 1 | 1/1 |
| LINKED_NO_CALL | 2 | REVIEW | 0 | 2 | 0 | 2/2 | 0 | 0/2 |
| CALL_NO_CUE | 2 | REVIEW | 0 | 2 | 0 | 2/2 | 0 | 0/2 |
| COINCIDENCE | 3 | DISMISS | 0 | 0 | 3 | 3/3 | 0 | 3/3 |

## Abstain, false alarms, latency

| Metric | Value |
|---|---|
| Planted-case accuracy (DealerWatch / baseline) | 1.000 / 0.692 |
| REVIEW (abstain) rate, all candidates | 0.308 |
| REVIEW rate, planted cases | 0.308 |
| Non-planted candidates | 0 |
| False alarms: DealerWatch ESCALATE / REVIEW | 0 / 0 |
| False alarms: baseline ESCALATE | 0 |
| Case latency p50 / p95 / max (ms) | 12 / 15 / 15 |
| Pipeline total (ms) | 368 |
