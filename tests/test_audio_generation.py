"""Native rendering boundaries and real PCM stitching without platform speech dependencies."""
from __future__ import annotations

import array
import copy
import json
import subprocess
import sys
import wave
from pathlib import Path

import pytest

from scripts import make_audio as audio


def write_wav(path: Path, samples: list[int], rate: int = 16000) -> None:
    data = array.array("h", samples)
    if sys.byteorder == "big":
        data.byteswap()
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(data.tobytes())


@pytest.fixture
def call_path(tmp_path: Path) -> Path:
    path = tmp_path / "calls" / "C-001.json"
    path.parent.mkdir()
    path.write_text(json.dumps({
        "call_id": "C-001", "dealer_id": "D1", "counterparty_number": "+919123456789",
        "start_time": "2026-09-01T10:00:00", "duration_s": 12, "audio_file": None,
        "utterances": [
            {"id": "C-001-u01", "speaker": "D1", "start_ms": 200, "end_ms": 5000,
             "text": "Buy INFY; $(touch should-never-exist) `hello`"},
            {"id": "C-001-u02", "speaker": "P-001", "start_ms": 5500, "end_ms": 11000,
             "text": "--voice=unsafe TCS and LT too?"},
        ],
    }), encoding="utf-8")
    return path


@pytest.mark.parametrize("installed, expected", [
    ("Rishi    en_IN # Hello\nVeena    hi_IN # Namaste\nSamantha en_US # Hello", ("Rishi", "Veena")),
    ("Samantha en_US # Hello\nLekha    hi_IN # Namaste", ("Samantha", "Lekha")),
    ("Alex     en_US # Hello", ("Alex", "Alex")),
    ("Unknown Voice en_GB # Hello\nAnother Voice en_US # Hi", ("Unknown Voice", "Another Voice")),
    ("Albert en_US # Hello\nRishi (English (India)) en_IN # Hello\nLekha (Hindi (India)) hi_IN # Namaste",
     ("Rishi (English (India))", "Lekha (Hindi (India))")),
])
def test_macos_renders_with_installed_voice_fallbacks_and_safe_text(monkeypatch, call_path, installed, expected) -> None:
    monkeypatch.setattr(audio.sys, "platform", "darwin")
    commands = []
    spoken_text = []

    def native_run(arguments, **kwargs):
        assert isinstance(arguments, list) and not kwargs.get("shell")
        commands.append(arguments)
        if arguments == ["say", "-v", "?"]:
            return subprocess.CompletedProcess(arguments, 0, stdout=installed, stderr="")
        if arguments[0] == "say":
            assert "-f" in arguments, "transcript must be file input, never command arguments"
            spoken_text.append(Path(arguments[arguments.index("-f") + 1]).read_text(encoding="utf-8"))
            Path(arguments[arguments.index("-o") + 1]).write_bytes(b"synthetic AIFF placeholder")
        elif arguments[0] == "afconvert":
            assert arguments[1:6] == ["-f", "WAVE", "-d", "LEI16@16000", "-c"]
            assert arguments[6] == "1"
            write_wav(Path(arguments[-1]), [2000] * 1600)
        else:
            pytest.fail(f"unexpected native command: {arguments}")
        return subprocess.CompletedProcess(arguments, 0, stdout="", stderr="")

    monkeypatch.setattr(audio.subprocess, "run", native_run)
    before = json.loads(call_path.read_text())
    report = audio.render_call(call_path, call_path.parent.parent)
    after = json.loads(call_path.read_text())
    used_voices = [args[args.index("-v") + 1] for args in commands if args[0] == "say" and "-o" in args]
    assert used_voices == list(expected)
    assert spoken_text == ["Buy Infy; $(touch should-never-exist) `hello`", "--voice=unsafe T C S and L and T too?"]
    assert [u["text"] for u in after["utterances"]] == [u["text"] for u in before["utterances"]]
    assert after["audio_file"] == "audio/C-001.wav" and after["duration_s"] == 2
    assert [(u["start_ms"], u["end_ms"]) for u in after["utterances"]] == [(300, 400), (750, 850)]
    assert report["wav_ms"] == 1350 and report["last_end_ms"] == 850


def test_windows_keeps_manifest_rendering_and_updates_real_timings(monkeypatch, call_path) -> None:
    monkeypatch.setattr(audio.sys, "platform", "win32")

    def native_run(arguments, **kwargs):
        assert arguments[:4] == ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass"]
        assert not kwargs.get("shell")
        manifest = json.loads(Path(arguments[arguments.index("-Manifest") + 1]).read_text())
        assert [row["voice"] for row in manifest] == ["Microsoft David", "Microsoft Zira"]
        for row in manifest:
            write_wav(Path(row["out"]), [2000] * 3200)
        return subprocess.CompletedProcess(arguments, 0, stdout="", stderr="")

    monkeypatch.setattr(audio.subprocess, "run", native_run)
    report = audio.render_call(call_path, call_path.parent.parent)
    after = json.loads(call_path.read_text())
    assert after["audio_file"] == "audio/C-001.wav"
    assert report["wav_ms"] == 1550
    assert [(u["start_ms"], u["end_ms"]) for u in after["utterances"]] == [(300, 500), (850, 1050)]


def test_failed_native_renderer_leaves_call_and_previous_audio_unchanged(monkeypatch, call_path) -> None:
    monkeypatch.setattr(audio.sys, "platform", "darwin")
    old_json = call_path.read_bytes()
    target = call_path.parent.parent / "audio" / "C-001.wav"
    target.parent.mkdir()
    target.write_bytes(b"previous audio")

    def native_run(arguments, **kwargs):
        if arguments == ["say", "-v", "?"]:
            return subprocess.CompletedProcess(arguments, 0, stdout="Alex en_US # Hello", stderr="")
        raise subprocess.CalledProcessError(1, arguments, stderr="speech unavailable")

    monkeypatch.setattr(audio.subprocess, "run", native_run)
    with pytest.raises(subprocess.CalledProcessError):
        audio.render_call(call_path, call_path.parent.parent)
    assert call_path.read_bytes() == old_json and target.read_bytes() == b"previous audio"


@pytest.mark.parametrize("bad_id", ["../escape", "/absolute", "C/../../escape"])
def test_call_identifier_cannot_escape_audio_directory(call_path, bad_id) -> None:
    call = json.loads(call_path.read_text())
    call["call_id"] = bad_id
    call_path.write_text(json.dumps(call))
    with pytest.raises(ValueError, match="call_id"):
        audio.render_call(call_path, call_path.parent.parent)


def test_empty_call_is_rejected_before_rendering(call_path) -> None:
    call = json.loads(call_path.read_text())
    call["utterances"] = []
    call_path.write_text(json.dumps(call))
    with pytest.raises(ValueError, match="utterance"):
        audio.render_call(call_path, call_path.parent.parent)


def test_stitch_trims_pcm_and_keeps_offsets_inside_audio(tmp_path: Path) -> None:
    parts = [tmp_path / "first.wav", tmp_path / "second.wav"]
    for part in parts:
        write_wav(part, [0] * 1600 + [2000] * 1600 + [0] * 1600)
    target = tmp_path / "audio" / "combined.wav"
    spans, total = audio.stitch(parts, target)
    assert spans == [(300, 480), (830, 1010)]
    assert total == audio.wav_ms(target) == 1510
    with wave.open(str(target), "rb") as output:
        assert (output.getnchannels(), output.getsampwidth(), output.getframerate()) == (1, 2, 16000)


def test_invalid_audio_format_does_not_replace_output(tmp_path: Path) -> None:
    part, target = tmp_path / "wrong-rate.wav", tmp_path / "combined.wav"
    write_wav(part, [2000] * 800, rate=8000)
    target.write_bytes(b"previous")
    with pytest.raises(ValueError, match="16 kHz mono"):
        audio.stitch([part], target)
    assert target.read_bytes() == b"previous"


def test_apply_timings_does_not_mutate_input_and_rejects_missing_parts(call_path) -> None:
    call = json.loads(call_path.read_text())
    saved = copy.deepcopy(call)
    updated = audio.apply_timings(call, [(300, 480), (830, 1010)], 1510, "audio/C-001.wav")
    assert call == saved and updated["duration_s"] == 2
    with pytest.raises(ValueError, match="rendered parts"):
        audio.apply_timings(call, [(300, 480)], 1510, "audio/C-001.wav")


def test_select_calls_covers_every_planted_call_and_three_innocent(tmp_path: Path) -> None:
    from dealerwatch.data.synth import generate

    generate(7, str(tmp_path))
    paths = audio.select_calls(tmp_path)
    assert len(paths) == 10  # five leak/injection calls, two small-talk calls, three innocent calls
    assert len(set(paths)) == len(paths)
    assert len(audio.select_calls(tmp_path, render_all=True)) == 25


@pytest.mark.parametrize("platform", ["darwin", "win32", "linux"])
def test_main_reports_missing_native_tools_without_rendering(monkeypatch, tmp_path, platform, capsys) -> None:
    monkeypatch.setattr(audio.sys, "platform", platform)
    monkeypatch.setattr(audio.shutil, "which", lambda executable: None)
    assert audio.main(["--data-dir", str(tmp_path)]) == 1
    assert "no audio rendered" in capsys.readouterr().out
