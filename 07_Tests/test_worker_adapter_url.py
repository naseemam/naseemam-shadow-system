import os

from kernel import worker_adapters


def test_api_base_adds_scheme_and_strips_endpoint(monkeypatch):
    monkeypatch.setenv("AMEER_LLM_API_BASE", "api.example.test/v1/chat/completions")
    assert worker_adapters._api_base() == "https://api.example.test/v1"


def test_api_base_preserves_v1_base(monkeypatch):
    monkeypatch.setenv("AMEER_LLM_API_BASE", "https://api.example.test/v1")
    assert worker_adapters._api_base() == "https://api.example.test/v1"


def test_api_base_prefers_ameer_override(monkeypatch):
    monkeypatch.setenv("AMEER_LLM_API_BASE", "https://ameer.example.test/v1")
    monkeypatch.setenv("OPENAI_API_BASE", "https://openai.example.test/v1")
    assert worker_adapters._api_base() == "https://ameer.example.test/v1"
