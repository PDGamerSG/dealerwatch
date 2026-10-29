"""Provider-switchable LLM client with deterministic fallbacks.

`get_llm()` picks the provider from env `DW_LLM` (mock | ollama | openai | anthropic, default mock)
and the model from `DW_LLM_MODEL`. Every call takes a `fallback` callable: the mock provider always
returns it, and real providers return it on any error, timeout, empty output, invalid JSON or JSON
missing the schema's required keys (counted in `stats["fallbacks"]`). Successful responses are cached
on disk under `DW_LLM_CACHE` (default `.llm_cache/`) unless `DW_LLM_CACHE_ON=0`.

API keys are read from the environment at call time and are never logged, cached or stored in stats.
Generic: no project imports.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

log = logging.getLogger("toolkit.llm")

PROVIDERS = ("mock", "ollama", "openai", "anthropic")
DEFAULT_MODELS = {"mock": "mock", "ollama": "gemma4:e2b", "openai": "gpt-4.1-mini", "anthropic": "claude-haiku-5-5"}
DEFAULT_OLLAMA_URL = "http://localhost:11434"
_KEY_ENVS = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "SARVAM_API_KEY")
_KEY_PATTERN = re.compile(r"\bsk-[A-Za-z0-9_\-]{8,}")
_FENCE = re.compile(r"^```[a-zA-Z0-9_-]*\s*\n?(.*?)\n?```\s*$", re.DOTALL)
_JSON_INSTRUCTION = (
    "\n\nRespond with a single JSON object and nothing else: no prose, no markdown, no code fences. "
    "The object must conform to this JSON schema:\n"
)


class LLMError(RuntimeError):
    """A provider call failed or returned an unusable response."""


# ---------- helpers ----------


def redact(text: str) -> str:
    """Remove any configured API key value (and anything shaped like `sk-...`) from a message."""
    for name in _KEY_ENVS:
        value = os.environ.get(name)
        if value and len(value) >= 6:
            text = text.replace(value, "***")
    return _KEY_PATTERN.sub("sk-***", text)


def parse_json_object(text: str) -> dict | None:
    """Parse a JSON object from model output, tolerating code fences and surrounding prose."""
    if not isinstance(text, str):
        return None
    body = text.strip().lstrip("﻿")
    fenced = _FENCE.match(body)
    if fenced:
        body = fenced.group(1).strip()
    try:
        obj = json.loads(body)
    except ValueError:
        obj = None
        start = body.find("{")
        if start >= 0:
            try:
                obj, _ = json.JSONDecoder().raw_decode(body[start:])
            except ValueError:
                end = body.rfind("}")
                try:
                    obj = json.loads(body[start:end + 1]) if end > start else None
                except ValueError:
                    obj = None
    return obj if isinstance(obj, dict) else None


def matches_schema(obj: Any, schema: dict) -> bool:
    """Loose check: required keys present (recursively through object properties and array items)
    and declared object/array containers have the right shape. Scalar types are not enforced."""
    if not isinstance(schema, dict):
        return True
    declared = schema.get("type")
    types = set(declared) if isinstance(declared, list) else {declared} if declared else set()
    if obj is None and "null" in types:
        return True
    if "object" in types or (not types and ("properties" in schema or "required" in schema)):
        if not isinstance(obj, dict):
            return False
        if any(key not in obj for key in schema.get("required") or []):
            return False
        props = schema.get("properties") or {}
        return all(matches_schema(obj[k], sub) for k, sub in props.items() if k in obj)
    if "array" in types:
        if not isinstance(obj, list):
            return False
        items = schema.get("items")
        return all(matches_schema(item, items) for item in obj) if isinstance(items, dict) else True
    return True


def _env_flag(name: str, default: str = "1") -> bool:
    return os.environ.get(name, default).strip().lower() not in ("0", "false", "no", "off", "")


# ---------- client ----------


class LLM:
    """One provider + model. `complete_json` / `complete_text` never raise for provider failures."""

    def __init__(self, provider: str = "mock", model: str | None = None, *,
                 cache_dir: str | None = None, cache_on: bool | None = None,
                 transport: httpx.BaseTransport | None = None):
        provider = (provider or "mock").strip().lower()
        if provider not in PROVIDERS:
            raise ValueError(f"unknown LLM provider {provider!r}; expected one of {', '.join(PROVIDERS)}")
        self.provider = provider
        self.model = model or DEFAULT_MODELS[provider]
        self.cache_dir = Path(cache_dir or os.environ.get("DW_LLM_CACHE") or ".llm_cache")
        self.cache_on = _env_flag("DW_LLM_CACHE_ON") if cache_on is None else cache_on
        self._transport = transport  # httpx transport for the ollama path (tests inject MockTransport)
        self._lock = threading.Lock()
        self.stats: dict[str, Any] = {"provider": self.provider, "model": self.model, "calls": 0,
                                      "fallbacks": 0, "cache_hits": 0, "total_ms": 0, "last_error": None}

    # -- public API -----------------------------------------------------------------------------
    def complete_json(self, system: str, user: str, schema: dict, fallback: Callable[[], dict], *,
                      max_tokens: int = 800, timeout_s: float = 30) -> dict:
        """JSON object conforming (loosely) to `schema`, or `fallback()`."""
        full_system = system + _JSON_INSTRUCTION + json.dumps(schema, sort_keys=True, ensure_ascii=False)

        def accept(raw: str) -> dict | None:
            obj = parse_json_object(raw)
            return obj if obj is not None and matches_schema(obj, schema) else None

        return self._complete(full_system, user, fallback, accept, json_mode=True,
                              max_tokens=max_tokens, timeout_s=timeout_s, invalid="invalid or non-conforming JSON")

    def complete_text(self, system: str, user: str, fallback: Callable[[], str], *,
                      max_tokens: int = 600, timeout_s: float = 30) -> str:
        """Plain text completion, or `fallback()`."""

        def accept(raw: str) -> str | None:
            text = raw.strip() if isinstance(raw, str) else ""
            return text or None

        return self._complete(system, user, fallback, accept, json_mode=False,
                              max_tokens=max_tokens, timeout_s=timeout_s, invalid="empty response")

    # -- core -----------------------------------------------------------------------------------
    def _complete(self, system: str, user: str, fallback: Callable[[], Any], accept: Callable[[str], Any], *,
                  json_mode: bool, max_tokens: int, timeout_s: float, invalid: str) -> Any:
        with self._lock:
            self.stats["calls"] += 1
        if self.provider == "mock":
            return fallback()
        started = time.perf_counter()
        key = self.cache_key(system, user)
        try:
            cached = self._cache_get(key)
            if cached is not None:
                value = accept(cached)
                if value is not None:
                    with self._lock:
                        self.stats["cache_hits"] += 1
                    return value
            raw = self._send(system, user, json_mode=json_mode, max_tokens=int(max_tokens), timeout_s=float(timeout_s))
            value = accept(raw)
            if value is None:
                raise LLMError(invalid)
            self._cache_put(key, raw)
            return value
        except Exception as exc:  # noqa: BLE001 - every provider failure degrades to the fallback
            reason = redact(f"{type(exc).__name__}: {exc}")[:300]
            with self._lock:
                self.stats["fallbacks"] += 1
                self.stats["last_error"] = reason
            log.warning("LLM %s/%s fell back: %s", self.provider, self.model, reason)
            return fallback()
        finally:
            with self._lock:
                self.stats["total_ms"] += int(round((time.perf_counter() - started) * 1000))

    def _send(self, system: str, user: str, *, json_mode: bool, max_tokens: int, timeout_s: float) -> str:
        """Raw completion text from the configured provider (raises on any failure)."""
        if self.provider == "ollama":
            return self._send_ollama(system, user, json_mode=json_mode, max_tokens=max_tokens, timeout_s=timeout_s)
        if self.provider == "openai":
            return self._send_openai(system, user, json_mode=json_mode, max_tokens=max_tokens, timeout_s=timeout_s)
        if self.provider == "anthropic":
            return self._send_anthropic(system, user, max_tokens=max_tokens, timeout_s=timeout_s)
        raise LLMError(f"provider {self.provider} has no transport")

    def _send_ollama(self, system: str, user: str, *, json_mode: bool, max_tokens: int, timeout_s: float) -> str:
        base = (os.environ.get("DW_OLLAMA_URL") or DEFAULT_OLLAMA_URL).rstrip("/")
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "stream": False,
            "options": {"temperature": 0, "num_predict": max_tokens},
        }
        if json_mode:
            body["format"] = "json"
        with httpx.Client(transport=self._transport, timeout=timeout_s) as http:
            response = http.post(f"{base}/api/chat", json=body)
        if response.status_code >= 400:
            raise LLMError(f"ollama returned HTTP {response.status_code}: {response.text[:200]}")
        content = ((response.json() or {}).get("message") or {}).get("content")
        if not isinstance(content, str):
            raise LLMError("ollama response has no message content")
        return content

    def _send_openai(self, system: str, user: str, *, json_mode: bool, max_tokens: int, timeout_s: float) -> str:
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise LLMError("OPENAI_API_KEY is not set")
        from openai import OpenAI

        client = OpenAI(api_key=api_key, timeout=timeout_s, max_retries=1)
        kwargs: dict[str, Any] = {}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0,
            max_tokens=max_tokens,
            **kwargs,
        )
        content = resp.choices[0].message.content if resp.choices else None
        if not isinstance(content, str):
            raise LLMError("openai response has no message content")
        return content

    def _send_anthropic(self, system: str, user: str, *, max_tokens: int, timeout_s: float) -> str:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            raise LLMError("ANTHROPIC_API_KEY is not set")
        import anthropic

        client = anthropic.Anthropic(api_key=api_key, timeout=timeout_s, max_retries=1)
        # Claude Haiku 5.5 accepts only default sampling parameters, so temperature is not sent;
        # determinism comes from the prompt, low effort and the response cache. Adaptive thinking
        # is on by default and counts toward max_tokens, hence the headroom.
        resp = client.messages.create(
            model=self.model,
            max_tokens=max_tokens + 1024,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"effort": "low"},
        )
        if resp.stop_reason == "refusal":
            raise LLMError("anthropic declined the request (stop_reason=refusal)")
        text = "".join(block.text for block in resp.content if block.type == "text")
        if not text.strip():
            raise LLMError(f"anthropic response has no text (stop_reason={resp.stop_reason})")
        return text

    # -- cache ----------------------------------------------------------------------------------
    def cache_key(self, system: str, user: str) -> str:
        return hashlib.sha256(f"{self.provider}|{self.model}|{system}|{user}".encode("utf-8")).hexdigest()

    def _cache_get(self, key: str) -> str | None:
        if not self.cache_on:
            return None
        path = self.cache_dir / f"{key}.json"
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        raw = doc.get("response") if isinstance(doc, dict) else None
        return raw if isinstance(raw, str) else None

    def _cache_put(self, key: str, raw: str) -> None:
        if not self.cache_on:
            return
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            tmp = self.cache_dir / f"{key}.{os.getpid()}.{threading.get_ident()}.tmp"
            tmp.write_text(json.dumps({"provider": self.provider, "model": self.model, "response": raw},
                                      ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self.cache_dir / f"{key}.json")
        except OSError as exc:
            log.warning("LLM cache write failed: %s", type(exc).__name__)


def get_llm(provider: str | None = None, model: str | None = None) -> LLM:
    """LLM for `provider` (default env `DW_LLM`, else mock). `DW_LLM_MODEL` overrides the default model
    when it applies to the chosen provider (i.e. the provider is the one named by `DW_LLM`)."""
    env_provider = (os.environ.get("DW_LLM") or "mock").strip().lower()
    chosen = (provider or env_provider).strip().lower()
    if model is None and chosen == env_provider:
        model = (os.environ.get("DW_LLM_MODEL") or "").strip() or None
    return LLM(chosen, model)
