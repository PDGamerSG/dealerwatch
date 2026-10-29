# Synthetic data and detector measurements

Run from the repository root with the environment's Python:

```sh
python -m dealerwatch.data.synth --seed 7 --out data/generated
python scripts/make_audio.py --data-dir data/generated
```

All entities, trades, orders, calls, and prices are fictional. Seed 7 produces 40 fund orders,
2,558 trades (2,500 background and 58 planted), 60 accounts, 25 calls, and 60,000 minute bars
over 20 weekdays. JSON models and filenames follow `CONTRACT.md`.

| Truth label | Pairs | Expected recommendation |
|---|---:|---|
| TRUE_FR | 5 | ESCALATE |
| INJECTION_FR | 1 | ESCALATE |
| LINKED_NO_CALL | 2 | REVIEW |
| CALL_NO_CUE | 2 | REVIEW |
| UNLINKED_PATTERN | 6 | REVIEW |
| COINCIDENCE | 3 | DISMISS |

The six unlinked pattern pairs use three separate unlinked accounts, with two fund orders per
account. Their repeated, profitable sandwiches score at least 0.5, so the rules-only baseline
falsely escalates them. DealerWatch retains REVIEW because dealer links and leak calls are missing.
The original 13 labelled cases retain their evidence requirements. Generator tests cover seeds
0, 7, and 42, exact file reproducibility, references, price bars, windows, and injection content.
A local audit of seeds 0–49 also matched all 950 truth recommendations and verified all 300
decoys exceeded the baseline threshold.

The generator deliberately resamples background trades to remove accidental sandwiches. These
labelled cases check the application rules; their accuracy is not an estimate of performance on
real market data.

Audio uses installed native voices: macOS `say` plus `afconvert`, or Windows PowerShell SAPI.
macOS prefers Rishi for dealers and Veena or Lekha for counterparties, then falls back to other
installed voices. No voices are downloaded. Default selection renders seven planted-window
calls and three innocent ones; `--all` renders all 25. WAV files are 16 kHz, mono, 16-bit PCM.
Only successfully rendered calls receive real utterance timings and an `audio_file` reference.
Regenerating the dataset replaces call JSON and removes those audio references; rerun audio
generation afterwards. Replay transcripts work without native audio tooling on Linux.

The detector indexes trades by scrip and timestamp, then slices each order's window with binary
search. The pre window remains `[t0 - 60 min, t0)` and the post window `(t0, t0 + 90 min]`.
Tests compare every candidate field against an independent scan and exercise microsecond
boundaries, BUY/SELL symmetry, duplicate timestamps, and historical trades outside the window.

Reproduce the performance measurement without reading or writing application datasets/databases:

```sh
python scripts/benchmark.py --orders 1000 --trades 100000 --repeat 3 --seed 7
```

The benchmark creates independent unique records in memory: 1,000 orders, 100,000 trades,
600 accounts, eight scrips, and 20 sessions. One untimed warmup precedes three runs of each
algorithm. Timings include timestamp parsing and indexing, and exclude generation, file IO,
and the investigation pipeline. All 7,107 candidate outputs match the prior full-scrip scan.
The report includes input/output SHA-256 digests, per-run timings, and environment details.
`--output <path>` optionally saves only the JSON report.

Measured on 30 October 2026 with Python 3.12.14, macOS 27.0.1, Apple M1 Max, arm64, 10 logical CPUs:

| Algorithm | Runs (ms) | Median (ms) |
|---|---|---:|
| Indexed detector | 399.725, 447.464, 411.871 | 411.871 |
| Previous full-scrip scan | 6402.389, 6252.420, 6270.977 | 6270.977 |

The observed median ratio was 15.23× on this synthetic workload. It is a local measurement,
not a throughput guarantee for other data distributions or machines.
