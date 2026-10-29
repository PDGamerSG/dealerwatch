from __future__ import annotations

import json

import httpx
import pytest

from toolkit.llm import LLM, get_llm, matches_schema, parse_json_object

SCHEMA = {
    "type": "object",
    "required": ["cues"],
    "properties": {"cues": {"type": "array", "items": {"type": "object", "required": ["utterance_id", "quote"]}}},
}
GOOD = {"cues": [{"utterance_id": "C-001-u02", "quote": "INFY mein bada order"}]}
FALLBACK = {"cues": [], "source": "fallback"}


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for name in ("DW_LLM", "DW_LLM_MODEL", "DW_LLM_CACHE_ON", "DW_OLLAMA_URL", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DW_LLM_CACHE", str(tmp_path / "cache"))


def ollama_llm(content: str | list[str], status: int = 200, seen: list | None = None) -> LLM:
    replies = [content] if isinstance(content, str) else list(content)

    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(json.loads(request.content))
        text = replies.pop(0) if len(replies) > 1 else replies[0]
        return httpx.Response(status, json={"message": {"role": "assistant", "content": text}})

    return LLM("ollama", transport=httpx.MockTransport(handler))


def test_get_llm_defaults_to_mock_and_reads_env(monkeypatch):
    assert get_llm().provider == "mock"
    monkeypatch.setenv("DW_LLM", "ollama")
    llm = get_llm()
    assert (llm.provider, llm.model) == ("ollama", "gemma4:e2b")
    monkeypatch.setenv("DW_LLM_MODEL", "custom:1b")
    assert get_llm().model == "custom:1b"
    assert get_llm("openai").model == "gpt-4.1-mini"  # DW_LLM_MODEL belongs to the env provider only
    assert get_llm("anthropic").model == "claude-haiku-5-5"
    with pytest.raises(ValueError):
        get_llm("gpt")


def test_mock_returns_fallback():
    llm = get_llm("mock")
    assert llm.complete_json("s", "u", SCHEMA, lambda: FALLBACK) == FALLBACK
    assert llm.complete_text("s", "u", lambda: "template") == "template"
    assert llm.stats["calls"] == 2 and llm.stats["fallbacks"] == 0
    assert set(llm.stats) >= {"provider", "model", "calls", "fallbacks", "total_ms", "last_error"}


def test_ollama_json_request_shape_and_fenced_reply():
    seen: list = []
    llm = ollama_llm("```json\n" + json.dumps(GOOD) + "\n```", seen=seen)
    assert llm.complete_json("system", "user", SCHEMA, lambda: FALLBACK) == GOOD
    body = seen[0]
    assert body["model"] == "gemma4:e2b" and body["format"] == "json" and body["stream"] is False
    assert body["options"]["temperature"] == 0
    assert body["messages"][0]["role"] == "system" and "JSON" in body["messages"][0]["content"]
    assert llm.stats["fallbacks"] == 0 and llm.stats["calls"] == 1


def test_cache_hit_skips_transport():
    seen: list = []
    llm = ollama_llm(json.dumps(GOOD), seen=seen)
    first = llm.complete_json("s", "u", SCHEMA, lambda: FALLBACK)
    again = ollama_llm(json.dumps({"cues": []}), seen=seen)  # fresh client, same disk cache
    second = again.complete_json("s", "u", SCHEMA, lambda: FALLBACK)
    assert first == second == GOOD
    assert len(seen) == 1
    assert again.stats["cache_hits"] == 1 and again.stats["calls"] == 1


def test_cache_off_calls_every_time(monkeypatch):
    monkeypatch.setenv("DW_LLM_CACHE_ON", "0")
    seen: list = []
    llm = ollama_llm(json.dumps(GOOD), seen=seen)
    llm.complete_json("s", "u", SCHEMA, lambda: FALLBACK)
    llm.complete_json("s", "u", SCHEMA, lambda: FALLBACK)
    assert len(seen) == 2 and llm.stats["cache_hits"] == 0


def test_invalid_json_uses_fallback_and_is_not_cached():
    llm = ollama_llm("sure! here you go: not json at all")
    assert llm.complete_json("s", "u", SCHEMA, lambda: FALLBACK) == FALLBACK
    assert llm.stats["fallbacks"] == 1 and "JSON" in llm.stats["last_error"]
    assert not llm.cache_dir.exists() or not list(llm.cache_dir.glob("*.json"))


def test_schema_mismatch_uses_fallback():
    llm = ollama_llm(json.dumps({"cues": [{"quote": "missing utterance id"}]}))
    assert llm.complete_json("s", "u", SCHEMA, lambda: FALLBACK) == FALLBACK
    assert llm.stats["fallbacks"] == 1


def test_http_error_uses_fallback():
    llm = ollama_llm("{}", status=500)
    assert llm.complete_text("s", "u", lambda: "template") == "template"
    assert llm.stats["fallbacks"] == 1 and "500" in llm.stats["last_error"]


def test_provider_exception_falls_back_and_redacts_key(monkeypatch):
    secret = "sk-test-SECRETSECRETSECRET123"
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    llm = LLM("openai")

    def boom(*args, **kwargs):
        raise TimeoutError(f"timed out talking with key {secret}")

    monkeypatch.setattr(llm, "_send", boom)
    assert llm.complete_json("s", "u", SCHEMA, lambda: FALLBACK) == FALLBACK
    assert llm.stats["fallbacks"] == 1
    assert "TimeoutError" in llm.stats["last_error"] and secret not in llm.stats["last_error"]
    assert llm.stats["total_ms"] >= 0


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_missing_key_falls_back_without_network(provider):
    llm = get_llm(provider)
    assert llm.complete_text("s", "u", lambda: "template") == "template"
    assert llm.stats["fallbacks"] == 1 and "API_KEY is not set" in llm.stats["last_error"]


def test_complete_text_empty_reply_falls_back():
    assert ollama_llm("   ").complete_text("s", "u", lambda: "template") == "template"
    assert ollama_llm(" A grounded line. ").complete_text("s", "u", lambda: "template") == "A grounded line."


def test_stats_accumulate():
    llm = ollama_llm(["not json", json.dumps(GOOD)])
    assert llm.complete_json("s", "u1", SCHEMA, lambda: FALLBACK) == FALLBACK
    assert llm.complete_json("s", "u2", SCHEMA, lambda: FALLBACK) == GOOD
    assert llm.stats["calls"] == 2 and llm.stats["fallbacks"] == 1
    assert isinstance(llm.stats["total_ms"], int) and llm.stats["total_ms"] >= 0
    assert llm.stats["provider"] == "ollama" and llm.stats["model"] == "gemma4:e2b"


def test_parse_json_object_tolerance():
    assert parse_json_object('```\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_object('Here: {"a": {"b": [1, 2]}} done') == {"a": {"b": [1, 2]}}
    assert parse_json_object("[1, 2]") is None
    assert parse_json_object("nothing") is None


def test_matches_schema_loose():
    assert matches_schema(GOOD, SCHEMA)
    assert not matches_schema({}, SCHEMA)
    assert not matches_schema({"cues": "x"}, SCHEMA)
    assert matches_schema({"cues": [], "extra": 1}, SCHEMA)
    assert matches_schema({"n": "5"}, {"type": "object", "required": ["n"], "properties": {"n": {"type": "integer"}}})
