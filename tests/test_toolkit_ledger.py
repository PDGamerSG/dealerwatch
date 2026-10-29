from __future__ import annotations

import sqlite3
import threading

import pytest

from toolkit.ledger import GENESIS, Ledger, canonical_json, entry_hash, sha256_hex


@pytest.fixture
def ledger(tmp_path):
    led = Ledger(str(tmp_path / "sub" / "ledger.db"))
    yield led
    led.close()


def test_append_builds_hash_chain(ledger):
    first = ledger.append("system", "run.start", {"seed": 7})
    second = ledger.append("pipeline", "detect.candidates", {"count": 3, "ids": ["X-1", "X-2"]})
    assert set(first) == {"seq", "ts", "actor", "action", "payload", "payload_hash", "prev_hash", "hash"}
    assert (first["seq"], second["seq"]) == (1, 2)
    assert first["prev_hash"] == GENESIS == "0" * 64
    assert second["prev_hash"] == first["hash"]
    assert first["payload"] == {"seed": 7}
    assert first["payload_hash"] == sha256_hex(canonical_json({"seed": 7}))
    assert first["hash"] == entry_hash(1, first["ts"], "system", "run.start", first["payload_hash"], GENESIS)
    assert ledger.head() == second["hash"]
    assert ledger.count() == 2


def test_verify_ok_and_empty(ledger):
    assert ledger.verify() == {"ok": True, "checked": 0, "first_bad_seq": None, "reason": None}
    assert ledger.head() == GENESIS
    for i in range(5):
        ledger.append("a", "step", {"i": i})
    assert ledger.verify() == {"ok": True, "checked": 5, "first_bad_seq": None, "reason": None}


def test_tamper_detected_at_seq(ledger):
    for i in range(6):
        ledger.append("a", "step", {"i": i})
    ledger.tamper_for_demo(4, {"i": 999})
    result = ledger.verify()
    assert result["ok"] is False
    assert result["first_bad_seq"] == 4
    assert result["checked"] == 4
    assert "payload" in result["reason"]
    assert ledger.entries()[3]["payload"] == {"i": 999}


def test_tamper_unknown_seq_raises(ledger):
    ledger.append("a", "step", {})
    with pytest.raises(ValueError):
        ledger.tamper_for_demo(42, {"x": 1})


def test_deleted_row_breaks_chain(tmp_path):
    path = str(tmp_path / "l.db")
    led = Ledger(path)
    for i in range(4):
        led.append("a", "step", {"i": i})
    raw = sqlite3.connect(path)
    raw.execute("DELETE FROM ledger WHERE seq = 2")
    raw.commit()
    raw.close()
    result = led.verify()
    assert result["ok"] is False and result["first_bad_seq"] == 3
    led.close()


def test_reset_restarts_at_genesis(ledger):
    for i in range(3):
        ledger.append("a", "step", {"i": i})
    ledger.reset()
    assert ledger.count() == 0 and ledger.head() == GENESIS and ledger.entries() == []
    entry = ledger.append("a", "again", {})
    assert entry["seq"] == 1 and entry["prev_hash"] == GENESIS
    assert ledger.verify()["ok"]


def test_entries_limit_offset_and_persistence(tmp_path):
    path = str(tmp_path / "l.db")
    led = Ledger(path)
    for i in range(10):
        led.append("a", "step", {"i": i})
    assert [e["seq"] for e in led.entries(limit=3, offset=2)] == [3, 4, 5]
    assert len(led.entries()) == 10
    head = led.head()
    led.close()
    reopened = Ledger(path)
    assert reopened.count() == 10 and reopened.head() == head and reopened.verify()["ok"]
    reopened.close()


def test_concurrent_appends_from_threads(ledger):
    errors: list[BaseException] = []

    def worker(n: int) -> None:
        try:
            for i in range(25):
                ledger.append(f"t{n}", "step", {"n": n, "i": i})
        except BaseException as exc:  # pragma: no cover - surfaced by the assert below
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    assert ledger.count() == 200
    assert [e["seq"] for e in ledger.entries()] == list(range(1, 201))
    assert ledger.verify()["ok"]


def test_concurrent_appends_from_two_connections(tmp_path):
    path = str(tmp_path / "shared.db")
    a, b = Ledger(path), Ledger(path)

    def worker(led: Ledger, tag: str) -> None:
        for i in range(20):
            led.append(tag, "step", {"i": i})

    threads = [threading.Thread(target=worker, args=(a, "a")), threading.Thread(target=worker, args=(b, "b"))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert a.count() == 40 and a.verify()["ok"] and b.verify()["ok"]
    a.close()
    b.close()


def test_canonical_hashing_is_stable():
    assert canonical_json({"b": 1, "a": [1, 2], "c": {"z": None, "y": "₹"}}) == '{"a":[1,2],"b":1,"c":{"y":"₹","z":null}}'
    assert sha256_hex(canonical_json({"b": 1, "a": 2})) == sha256_hex(canonical_json({"a": 2, "b": 1}))
    # a fixed vector guards against accidental changes to the canonical form
    assert sha256_hex(canonical_json({"seq": 1, "action": "run.start"})) == (
        "55e1e1e83d628ebce9118e6f06e7ea3414ba656dc8a931567af6fbf95705a36d")


def test_payload_with_non_string_keys_and_models_verifies(ledger):
    class Model:
        def model_dump(self, mode: str = "python") -> dict:
            return {"x": 1, "mode": mode}

    ledger.append("a", "odd", {10: "ten", 9: "nine", "obj": Model(), "tags": {"b", "a"}})
    entry = ledger.entries()[0]
    assert entry["payload"]["obj"] == {"x": 1, "mode": "json"}
    assert entry["payload"]["tags"] == ["a", "b"]
    assert ledger.verify()["ok"]
