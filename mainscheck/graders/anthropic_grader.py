"""Anthropic-backed grader.

Scores come back as JSON so they are machine-comparable. The model is asked for a
rationale too, because a score with no reasoning cannot be audited — and auditing
is the entire point of this project.
"""

from __future__ import annotations

import json
import os
import re

from anthropic import AsyncAnthropic

from .base import Cache, Grader

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


class AnthropicGrader(Grader):
    def __init__(
        self,
        model: str,
        rubric: dict,
        cache: Cache,
        *,
        max_tokens: int = 1024,
        client: AsyncAnthropic | None = None,
    ) -> None:
        super().__init__(model, rubric, cache)
        self.max_tokens = max_tokens
        if client is not None:
            self.client = client
        else:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                raise RuntimeError(
                    "ANTHROPIC_API_KEY is not set. Export it before running."
                )
            self.client = AsyncAnthropic()

    async def _call(self, prompt: str, temperature: float, answer_text: str):
        # answer_text is unused here: the prompt already carries it.
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            block.text for block in response.content if block.type == "text"
        )
        scores, rationale = self._parse(text)
        return (
            scores,
            rationale,
            response.usage.input_tokens,
            response.usage.output_tokens,
        )

    def _parse(self, text: str) -> tuple[dict[str, float], str]:
        match = _JSON_BLOCK.search(text)
        if not match:
            raise ValueError(f"no JSON object in response: {text[:200]!r}")
        payload = json.loads(match.group(0))

        raw = payload.get("scores", payload)
        scores: dict[str, float] = {}
        for criterion in self.criteria:
            if criterion not in raw:
                raise ValueError(f"response missing criterion {criterion!r}")
            scores[criterion] = float(raw[criterion])

        return scores, str(payload.get("rationale", ""))
