# DealerWatch (rehearsal)

Front-running investigator for fund houses. Synthetic data only. See `SUBMISSION.md` for the pitch and `HANDOFF.md` for current state.

## Setup
macOS / Linux:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # if uv is missing
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```
Windows: same with `.venv\Scripts\activate`.

## Run
```bash
python -m dealerwatch.data.synth --seed 7 --out data/generated     # synthetic universe
python -m pytest -q                                                 # tests (637 at handoff)
python -m dealerwatch.eval.harness --data data/generated --runtime runtime   # writes EVAL.md
python -m uvicorn dealerwatch.api:app --port 8077                   # UI at http://localhost:8077
```

## Modes
`DW_LLM` = mock (default) | ollama | openai | anthropic. `DW_LLM_MODEL` overrides the model. `DW_ASR` = replay (default) | sarvam (needs `SARVAM_API_KEY`). Local model: `ollama pull gemma4:e2b`.
