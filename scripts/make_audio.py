"""Render fictional DealerWatch calls to 16 kHz mono WAV with macOS speech or Windows SAPI.

Usage (from the repo root; scripts/make_audio.ps1 forwards here):
    python scripts/make_audio.py [--data-dir data/generated] [--all]

On Windows, make_audio.ps1 renders utterances with Microsoft David / Microsoft Zira. On macOS,
say uses Rishi / Veena or Lekha when installed, falling back to available voices; afconvert makes PCM.
This script stitches the temporary utterances with
short pauses into audio/C-xxx.wav and rewrites the call JSON with the real utterance offsets
(start_ms/end_ms), duration_s and audio_file. The JSON is only rewritten when the WAV was created.
By default it renders the calls inside planted lookback windows (leak, injection, small talk) plus three
innocent calls; --all renders every call. All audio is synthetic speech of fictional transcripts.
"""
from __future__ import annotations

import argparse
import array
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from datetime import datetime, timedelta
from pathlib import Path

RATE = 16000
SAMPLE_WIDTH = 2
LEAD_MS, GAP_MS, TAIL_MS = 300, 350, 500
TRIM_THRESHOLD, TRIM_MARGIN_MS = 300, 40
DEALER_VOICE, OTHER_VOICE = "Microsoft David", "Microsoft Zira"
LOOKBACK_MIN = 180
WINDOW_LABELS = ("TRUE_FR", "INJECTION_FR", "CALL_NO_CUE")
N_INNOCENT = 3
SPOKEN = {"BAJFINANCE": "Bajaj Finance", "HDFCBANK": "H D F C Bank", "RELIANCE": "Reliance", "INFY": "Infy",
          "SBIN": "S B I", "TCS": "T C S", "ITC": "I T C", "LT": "L and T"}
REPO = Path(__file__).resolve().parents[1]
PS1 = Path(__file__).with_name("make_audio.ps1")


def spoken(text: str) -> str:
    """Make tickers pronounceable for the TTS voice; the JSON transcript keeps the original text."""
    return re.sub(r"\b(" + "|".join(SPOKEN) + r")\b", lambda m: SPOKEN[m.group(1)], text)


def voice_for(speaker: str, voices: tuple[str, str] = (DEALER_VOICE, OTHER_VOICE)) -> str:
    """Use a distinct voice for the dealer and counterparty when available."""
    return voices[0] if re.fullmatch(r"D\d+", speaker) else voices[1]


def _mac_voices() -> tuple[str, str]:
    """Prefer Indian voices, then available English/Hindi voices, without downloading any."""
    result = subprocess.run(["say", "-v", "?"], check=True, capture_output=True, text=True, timeout=30)
    available = []
    for line in result.stdout.splitlines():
        match = re.match(r"^(.+?)\s+([a-z]{2,3}_[A-Za-z0-9_]+)\s+#", line)
        if match:
            available.append((match[1].strip(), match[2]))
    if not available:
        raise ValueError("macOS say reported no installed voices")
    names = [name for name, language in available if language.startswith(("en_", "hi_"))]
    names = names or [name for name, _ in available]

    def preferred(choices: tuple[str, ...], excluded: str = "") -> str:
        # Newer macOS versions append a language description to the voice name.
        return next((name for choice in choices for name in names if name != excluded
                     and (name == choice or name.startswith(choice + " ("))),
                    next((name for name in names if name != excluded), names[0]))

    dealer = preferred(("Rishi", "Alex", "Daniel", "Samantha"))
    other = preferred(("Veena", "Lekha", "Samantha", "Karen", "Moira"), dealer)
    return dealer, other


def select_calls(data_dir: Path, render_all: bool = False) -> list[Path]:
    """Call files to render: those in a planted case's lookback window plus the first innocent ones."""
    paths = sorted((data_dir / "calls").glob("C-*.json"))
    if render_all:
        return paths
    orders = {o["order_id"]: o for o in json.loads((data_dir / "orders.json").read_text(encoding="utf-8"))}
    windows = []
    for case in json.loads((data_dir / "truth.json").read_text(encoding="utf-8"))["cases"]:
        if case["label"] in WINDOW_LABELS:
            order = orders[case["order_id"]]
            t0 = datetime.fromisoformat(order["order_time"])
            windows.append((order["dealer_id"], t0 - timedelta(minutes=LOOKBACK_MIN), t0))
    picked, innocent = [], []
    for path in paths:
        call = json.loads(path.read_text(encoding="utf-8"))
        start = datetime.fromisoformat(call["start_time"])
        if any(call["dealer_id"] == d and lo <= start <= hi for d, lo, hi in windows):
            picked.append(path)
        elif len(innocent) < N_INNOCENT:
            innocent.append(path)
    return sorted(picked + innocent)


def _trim(data: bytes) -> bytes:
    """Drop leading/trailing near-silence from 16-bit mono PCM, keeping a small margin."""
    samples = array.array("h")
    samples.frombytes(data)
    if sys.byteorder == "big":
        samples.byteswap()
    first = next((i for i, s in enumerate(samples) if abs(s) > TRIM_THRESHOLD), None)
    if first is None:
        return data
    last = next(i for i in range(len(samples) - 1, -1, -1) if abs(samples[i]) > TRIM_THRESHOLD)
    margin = RATE * TRIM_MARGIN_MS // 1000
    lo, hi = max(0, first - margin), min(len(samples), last + margin + 1)
    return data[lo * SAMPLE_WIDTH:hi * SAMPLE_WIDTH]


def _ms(n_bytes: int) -> int:
    return n_bytes // SAMPLE_WIDTH * 1000 // RATE


def stitch(parts: list[Path], out: Path) -> tuple[list[tuple[int, int]], int]:
    """Concatenate 16 kHz mono 16-bit WAVs with pauses; returns each part's (start_ms, end_ms) and total ms."""
    def silence(ms: int) -> bytes:
        return b"\x00" * (RATE * ms // 1000 * SAMPLE_WIDTH)

    frames = bytearray(silence(LEAD_MS))
    spans: list[tuple[int, int]] = []
    for i, part in enumerate(parts):
        with wave.open(str(part), "rb") as w:
            if (w.getnchannels(), w.getsampwidth(), w.getframerate()) != (1, SAMPLE_WIDTH, RATE):
                raise ValueError(f"{part.name}: expected 16 kHz mono 16-bit PCM, got {w.getparams()}")
            data = _trim(w.readframes(w.getnframes()))
        start = _ms(len(frames))
        frames += data
        spans.append((start, _ms(len(frames))))
        frames += silence(GAP_MS if i < len(parts) - 1 else TAIL_MS)
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(SAMPLE_WIDTH)
        w.setframerate(RATE)
        w.writeframes(bytes(frames))
    return spans, _ms(len(frames))


def wav_ms(path: Path) -> int:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() * 1000 // w.getframerate()


def apply_timings(call: dict, spans: list[tuple[int, int]], total_ms: int, audio_rel: str) -> dict:
    """Return the call with real utterance offsets, duration and audio_file."""
    if len(spans) != len(call["utterances"]):
        raise ValueError(f"{call['call_id']}: {len(spans)} rendered parts for {len(call['utterances'])} utterances")
    utterances = [{**u, "start_ms": a, "end_ms": b} for u, (a, b) in zip(call["utterances"], spans)]
    return {**call, "utterances": utterances, "duration_s": math.ceil(total_ms / 1000), "audio_file": audio_rel}


def _render_parts(call: dict, workdir: Path) -> list[Path]:
    """Invoke native speech tools with argument arrays and text supplied through files."""
    if sys.platform == "darwin":
        voices = _mac_voices()
        parts = []
        for i, utterance in enumerate(call["utterances"]):
            text_path, aiff, wav = (workdir / f"part-{i:04d}.{suffix}" for suffix in ("txt", "aiff", "wav"))
            text_path.write_text(spoken(utterance["text"]), encoding="utf-8")
            subprocess.run(["say", "-v", voice_for(utterance["speaker"], voices), "-r", "165", "-o", str(aiff),
                            "-f", str(text_path)], check=True, capture_output=True, text=True, timeout=120)
            subprocess.run(["afconvert", "-f", "WAVE", "-d", f"LEI16@{RATE}", "-c", "1", str(aiff), str(wav)],
                           check=True, capture_output=True, text=True, timeout=30)
            parts.append(wav)
        return parts
    if sys.platform != "win32":
        raise ValueError("native speech rendering requires macOS or Windows")
    manifest = [{"text": spoken(u["text"]), "voice": voice_for(u["speaker"]),
                 "out": str(workdir / f"part-{i:04d}.wav")} for i, u in enumerate(call["utterances"])]
    manifest_path = workdir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(PS1),
                    "-Manifest", str(manifest_path)], check=True, capture_output=True, text=True, timeout=300)
    return [Path(m["out"]) for m in manifest]


def render_call(call_path: Path, data_dir: Path) -> dict:
    """Render one call to audio/<call_id>.wav and rewrite its JSON; returns a short report."""
    call = json.loads(call_path.read_text(encoding="utf-8"))
    if not isinstance(call.get("call_id"), str) or not re.fullmatch(r"[A-Za-z0-9_-]+", call["call_id"]):
        raise ValueError("call_id must be a safe filename identifier")
    if not call.get("utterances"):
        raise ValueError(f"{call['call_id']}: at least one utterance is required")
    audio_rel = f"audio/{call['call_id']}.wav"
    workdir = Path(tempfile.mkdtemp(prefix=f"dw_{call['call_id']}_"))
    try:
        spans, total_ms = stitch(_render_parts(call, workdir), data_dir / audio_rel)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    updated = apply_timings(call, spans, total_ms, audio_rel)
    with open(call_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(updated, sort_keys=True, indent=2, ensure_ascii=False) + "\n")
    return {"call_id": call["call_id"], "utterances": len(spans), "wav_ms": wav_ms(data_dir / audio_rel),
            "last_end_ms": spans[-1][1], "duration_s": updated["duration_s"]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render DealerWatch calls to WAV with macOS speech or Windows SAPI.")
    ap.add_argument("--data-dir", default=str(REPO / "data" / "generated"))
    ap.add_argument("--all", action="store_true", help="render every call, not just the planted-window ones")
    args = ap.parse_args(argv)
    required = {"darwin": ("say", "afconvert"), "win32": ("powershell",)}.get(sys.platform)
    if required is None or any(shutil.which(command) is None for command in required):
        print("make_audio: macOS say/afconvert or Windows PowerShell with System.Speech is required; no audio rendered.")
        return 1
    data_dir = Path(args.data_dir)
    selected = select_calls(data_dir, args.all)
    failures = 0
    for path in selected:
        try:
            r = render_call(path, data_dir)
        except (subprocess.SubprocessError, ValueError, OSError, wave.Error) as exc:
            failures += 1
            detail = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) and exc.stderr else exc
            print(f"  {path.stem}: FAILED ({detail})")
            continue
        print(f"  {r['call_id']}: {r['utterances']} utterances, wav {r['wav_ms'] / 1000:.1f}s, "
              f"last utterance ends {r['last_end_ms'] / 1000:.1f}s, duration_s {r['duration_s']}")
    print(f"make_audio: rendered {len(selected) - failures}/{len(selected)} calls into {data_dir / 'audio'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
