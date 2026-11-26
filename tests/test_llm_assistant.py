from __future__ import annotations

import contextlib

import pytest

import llm_client
from style_assistant import MAX_QUESTION_CHARS, build_llm_messages, build_style_facts


def _facts(**overrides):
    params = dict(skin_tone="medium", undertone="warm", style="elegant", occasion="work")
    params.update(overrides)
    return build_style_facts(**params)


def test_facts_contain_profile_palette_and_engine_looks():
    facts = _facts()
    assert "Skin tone: Medium; undertone: Warm" in facts
    assert "Recommended palette:" in facts
    assert "ENGINE TOP-RANKED LOOKS" in facts
    assert "score" in facts and "/100" in facts


def test_facts_use_dress_garment_names():
    facts = _facts(top_label="Dress", is_dress=True)
    assert "one-piece dress" in facts
    assert "pants" not in facts.split("ENGINE TOP-RANKED LOOKS")[1].lower()


def test_facts_include_current_outfit_score_verbatim():
    outfit = {"shirt_color": "white", "pants_color": "navy", "shoes_color": "brown", "score": 73, "reasons": ["x"]}
    facts = _facts(current_outfit=outfit)
    assert "CURRENT OUTFIT IN THE BUILDER" in facts
    assert "Engine score: 73/100" in facts


def test_messages_are_grounded_and_question_is_capped():
    messages = build_llm_messages("a" * 5000, "FACTS")
    assert messages[0]["role"] == "system"
    assert "never invent" in messages[0]["content"]
    assert messages[1]["content"].startswith("STYLE FACTS\nFACTS")
    assert messages[1]["content"].count("a") <= MAX_QUESTION_CHARS + 10


def test_empty_question_gets_default():
    assert "What should I wear" in build_llm_messages("   ", "F")[1]["content"]


def test_default_provider_is_free_local_ollama(monkeypatch):
    for name in ("PROVIDER", "MODEL", "API_KEY", "BASE_URL"):
        monkeypatch.delenv(f"LLM_{name}", raising=False)
    monkeypatch.setattr(llm_client, "_setting", lambda name: None)
    config = llm_client.load_config()
    assert config.provider == "ollama"
    assert config.is_local
    assert config.base_url == "http://localhost:11434/v1"


def test_remote_provider_without_key_is_unavailable(monkeypatch):
    monkeypatch.setattr(llm_client, "_setting", lambda name: {"provider": "groq"}.get(name))
    ok, message = llm_client.check_available()
    assert not ok
    assert "api_key" in message


class _FakeResponse:
    def __init__(self, lines, status_code=200):
        self._lines = lines
        self.status_code = status_code

    def iter_lines(self):
        yield from self._lines

    def read(self):
        return b"boom"


def test_stream_chat_parses_openai_sse(monkeypatch):
    lines = [
        'data: {"choices":[{"delta":{"role":"assistant"}}]}',
        'data: {"choices":[{"delta":{"content":"Navy "}}]}',
        ": keep-alive",
        'data: {"choices":[{"delta":{"content":"suits you."}}]}',
        "data: [DONE]",
    ]
    monkeypatch.setattr(llm_client.httpx, "stream", lambda *a, **k: contextlib.nullcontext(_FakeResponse(lines)))
    config = llm_client.LLMConfig("ollama", "http://x/v1", "m", None)
    assert "".join(llm_client.stream_chat([{"role": "user", "content": "hi"}], config=config)) == "Navy suits you."


def test_stream_chat_http_error_raises(monkeypatch):
    monkeypatch.setattr(llm_client.httpx, "stream", lambda *a, **k: contextlib.nullcontext(_FakeResponse([], 401)))
    config = llm_client.LLMConfig("groq", "http://x/v1", "m", "k")
    with pytest.raises(llm_client.LLMUnavailableError):
        list(llm_client.stream_chat([], config=config))
