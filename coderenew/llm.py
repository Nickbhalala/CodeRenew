"""LLM clients. The chain only needs `complete(system, user) -> str`."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol


class LLMClient(Protocol):
    def complete(self, system: str, user: str) -> str: ...


class OpenAIClient:
    def __init__(self, model: str = "gpt-4o", api_key: str | None = None) -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self.model = model

    def complete(self, system: str, user: str) -> str:
        resp = self._client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        return resp.choices[0].message.content or ""


@dataclass
class ScriptedLLM:
    """Returns canned responses in order; records prompts. Used in tests."""

    responses: list[str | Callable[[str, str], str]]
    calls: list[tuple[str, str]] = field(default_factory=list)

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        if not self.responses:
            raise RuntimeError("ScriptedLLM ran out of responses")
        nxt = self.responses.pop(0)
        return nxt(system, user) if callable(nxt) else nxt
