# AI tools and models used

| Where | Tool / model | Role |
|---|---|---|
| Building the code | Claude Code (Anthropic Claude models) | Coding assistant for this rehearsal build |
| Leak-cue extraction (optional) | Local `gemma4:e2b` via Ollama, or OpenAI / Anthropic models via `DW_LLM` | Schema-constrained extraction; output grounded and checked |
| Case narrative (optional) | Same provider as above | Short summary; rejected and replaced by a template if it cites anything not in the evidence |
| Speech-to-text (optional) | Sarvam Saaras speech-to-text with diarization via `DW_ASR=sarvam` | Transcribes dealer-desk call recordings; offline replay by default |
| Default mode | No model (`DW_LLM=mock`, `DW_ASR=replay`) | Deterministic rules and replayed transcripts so the demo runs without network |

Decisions are made by deterministic code and by the human reviewer, never by a model.

## Declared reusable components
See `DECLARED_COMPONENTS.md`.

## 30 October end-to-end implementation

Codex coordinated repository inspection, architecture, implementation, independent code review and automated verification. Parallel agents handled durable persistence, synthetic scenarios/performance, the basic frontend and a read-only integration review. Python/Chromium regression tests and reproducible measurements were run locally. No external model output determines an escalation; reviewer actions remain explicit.
