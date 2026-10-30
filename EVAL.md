# DealerWatch evaluation

Generated 2026-10-30T17:15:27 on `data/generated` (synthetic, seed-labelled). LLM: mock (26 calls, 0 fallbacks); ASR: replay.

Population: 19 (order, account) pairs = 19 detector candidates plus 0 planted pairs without a candidate; 19 planted. Background candidates count as negatives. Baseline: escalate iff sandwich score >= 0.5.

## ESCALATE

| System | TP | FP | FN | TN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| DealerWatch | 6 | 0 | 0 | 13 | 1.000 | 1.000 | 1.000 |
| Rules-only baseline | 6 | 6 | 0 | 7 | 0.500 | 1.000 | 0.667 |

## Per label (planted cases)

| Label | n | Expected | DW ESCALATE | DW REVIEW | DW DISMISS | DW correct | Baseline ESCALATE | Baseline correct |
|---|---|---|---|---|---|---|---|---|
| TRUE_FR | 5 | ESCALATE | 5 | 0 | 0 | 5/5 | 5 | 5/5 |
| INJECTION_FR | 1 | ESCALATE | 1 | 0 | 0 | 1/1 | 1 | 1/1 |
| LINKED_NO_CALL | 2 | REVIEW | 0 | 2 | 0 | 2/2 | 0 | 0/2 |
| CALL_NO_CUE | 2 | REVIEW | 0 | 2 | 0 | 2/2 | 0 | 0/2 |
| UNLINKED_PATTERN | 6 | REVIEW | 0 | 6 | 0 | 6/6 | 6 | 0/6 |
| COINCIDENCE | 3 | DISMISS | 0 | 0 | 3 | 3/3 | 0 | 3/3 |

## Abstain, false alarms, latency

| Metric | Value |
|---|---|
| Planted-case accuracy (DealerWatch / baseline) | 1.000 / 0.474 |
| REVIEW (abstain) rate, all candidates | 0.526 |
| REVIEW rate, planted cases | 0.526 |
| Non-planted candidates | 0 |
| False alarms: DealerWatch ESCALATE / REVIEW | 0 / 0 |
| False alarms: baseline ESCALATE | 0 |
| Case latency p50 / p95 / max (ms) | 1 / 4 / 4 |
| Pipeline total (ms) | 440 |
