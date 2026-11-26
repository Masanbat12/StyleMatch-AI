"""Provider-neutral chat client for free LLMs.

Every supported provider speaks the OpenAI-compatible ``/chat/completions`` protocol, so one
small streaming client covers all of them. The default is a local Ollama model: free, no
account, no key, no rate limits. Switching provider is configuration only (env vars or
``.streamlit/secrets.toml``), never a code change:

    [llm]
    provider = "ollama"          # ollama | groq | gemini | openrouter | custom
    model = "qwen2.5:3b"         # optional, each provider has a default
    api_key = ""                 # not needed for ollama
    base_url = ""                # only for provider = "custom"

Env vars override secrets: LLM_PROVIDER, LLM_MODEL, LLM_API_KEY, LLM_BASE_URL.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Iterator

import httpx

PROVIDERS: dict[str, dict[str, str]] = {
    "ollama": {"base_url": "http://localhost:11434/v1", "model": "qwen2.5:3b", "label": "Ollama (local)"},
    "groq": {"base_url": "https://api.groq.com/openai/v1", "model": "llama-3.3-70b-versatile", "label": "Groq"},
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-2.0-flash",
        "label": "Google Gemini",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "label": "OpenRouter",
    },
    "custom": {"base_url": "", "model": "", "label": "Custom endpoint"},
}

# Local CPU inference is slow to produce the first token; remote APIs are fast.
CONNECT_TIMEOUT_S = 3.0
READ_TIMEOUT_S = 180.0


class LLMUnavailableError(RuntimeError):
    """Raised when the configured LLM cannot be reached or returns an error."""


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    base_url: str
    model: str
    api_key: str | None

    @property
    def label(self) -> str:
        return f"{PROVIDERS.get(self.provider, PROVIDERS['custom'])['label']} · {self.model}"

    @property
    def is_local(self) -> bool:
        return self.provider == "ollama"


def _setting(name: str) -> str | None:
    env_value = os.getenv(f"LLM_{name.upper()}")
    if env_value:
        return env_value.strip()
    try:
        import streamlit as st

        section = st.secrets.get("llm")
        if section and section.get(name):
            return str(section.get(name)).strip()
    except Exception:  # no secrets file, or not running under Streamlit
        pass
    return None


def load_config() -> LLMConfig:
    provider = (_setting("provider") or "ollama").lower()
    preset = PROVIDERS.get(provider, PROVIDERS["custom"])
    base_url = (_setting("base_url") or preset["base_url"]).rstrip("/")
    model = _setting("model") or preset["model"]
    return LLMConfig(provider=provider, base_url=base_url, model=model, api_key=_setting("api_key"))


def _headers(config: LLMConfig) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    return headers


def check_available(config: LLMConfig | None = None) -> tuple[bool, str]:
    """Cheap readiness probe. Returns (ok, human-readable status)."""
    config = config or load_config()
    if not config.base_url or not config.model:
        return False, "LLM is not configured (missing base_url or model)."
    if not config.is_local and not config.api_key:
        return False, f"{PROVIDERS.get(config.provider, PROVIDERS['custom'])['label']} needs an api_key in secrets."

    if config.is_local:
        root = config.base_url.removesuffix("/v1")
        try:
            response = httpx.get(f"{root}/api/tags", timeout=CONNECT_TIMEOUT_S)
            response.raise_for_status()
        except httpx.HTTPError:
            return False, "Ollama is not running. Start it, then run: ollama pull " + config.model
        names = {m.get("name", "") for m in response.json().get("models", [])}
        wanted = config.model if ":" in config.model else f"{config.model}:latest"
        if wanted not in names:
            return False, f"Model {config.model} is not downloaded. Run: ollama pull {config.model}"
    return True, f"Connected to {config.label}"


def stream_chat(
    messages: list[dict[str, str]],
    *,
    config: LLMConfig | None = None,
    temperature: float = 0.4,
    max_tokens: int = 700,
) -> Iterator[str]:
    """Yield the reply text incrementally (OpenAI-compatible SSE streaming)."""
    config = config or load_config()
    payload = {
        "model": config.model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    timeout = httpx.Timeout(READ_TIMEOUT_S, connect=CONNECT_TIMEOUT_S)
    try:
        with httpx.stream(
            "POST",
            f"{config.base_url}/chat/completions",
            headers=_headers(config),
            json=payload,
            timeout=timeout,
        ) as response:
            if response.status_code >= 400:
                detail = response.read().decode("utf-8", "replace")[:300]
                raise LLMUnavailableError(f"{config.label} returned HTTP {response.status_code}: {detail}")
            for line in response.iter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                text = (choices[0].get("delta") or {}).get("content")
                if text:
                    yield text
    except httpx.HTTPError as exc:
        raise LLMUnavailableError(f"Could not reach {config.label}: {exc}") from exc
