"""
inference_provider.py
=====================
Formal InferenceProvider abstraction.

All language-model integrations (OpenAI, Ollama, future providers) implement
this interface so that the Executive Brain and Orchestrator do not depend on
any specific provider SDK.  New providers can be added by subclassing
InferenceProvider without touching the Executive Core or the /ask contract.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Optional


class InferenceProvider(ABC):
    """Abstract base class for all inference providers."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the provider is configured and reachable."""

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """
        Send a chat completion request.

        Returns the model reply as a plain string, or None if the provider
        is unavailable or the request fails.
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name for logging."""


class OpenAIProvider(InferenceProvider):
    """Adapter for the OpenAI chat completions API."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self._api_key = api_key
        self._model = model
        self._client = None
        if api_key:
            try:
                from openai import OpenAI  # type: ignore[import]
                self._client = OpenAI(api_key=api_key)
            except Exception:
                self._client = None

    @property
    def name(self) -> str:
        return f"openai/{self._model}"

    def is_available(self) -> bool:
        return self._client is not None

    def complete(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        if not self._client:
            return None
        try:
            completion = self._client.chat.completions.create(
                model=self._model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = (
                getattr(completion.choices[0].message, "content", None) or ""
            ).strip()
            return content or None
        except Exception:
            return None


class OllamaProvider(InferenceProvider):
    """Adapter for a local Ollama inference server."""

    def __init__(self, host: str = "http://127.0.0.1:11434", model: str = "smollm:135m") -> None:
        self._host = host.rstrip("/")
        self._model = model

    @property
    def name(self) -> str:
        return f"ollama/{self._model}"

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(f"{self._host}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=2):
                return True
        except Exception:
            return False

    def complete(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        try:
            payload = json.dumps(
                {
                    "model": self._model,
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                }
            ).encode("utf-8")
            req = urllib.request.Request(
                f"{self._host}/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode("utf-8"))
                message = data.get("message") or {}
                content = message.get("content") or ""
                return content.strip() or None
        except Exception:
            return None
