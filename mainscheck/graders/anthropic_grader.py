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

# Sampling parameters were removed from the current generation: sending `temperature`
# to Opus 5, Sonnet 5 or Opus 4.7/4.8 returns a 400. Only older models still accept it.
#
# This matters to the benchmark's design, not just its plumbing. Self-consistency here
# measures ordinary sampling variance across repeated identical requests, because
# temperature is no longer a dial the caller controls. The temperature recorded on each
# Grading is kept as cache-key metadata only; for these models it is never sent.
_MODELS_ACCEPTING_TEMPERATURE = frozenset(
    {"claude-haiku-4-5", "claude-sonnet-4-5", "claude-haiku-3-5"}
)


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
                    "ANTHROPIC_API_KEY is not set. Put it in .env or export it."
                )
            # An API key that is not scoped to a workspace must name one per request.
            # Set ANTHROPIC_WORKSPACE_ID, or use a workspace-scoped key instead.
            workspace = os.environ.get("ANTHROPIC_WORKSPACE_ID")
            headers = {"anthropic-workspace-id": workspace} if workspace else None
            self.client = AsyncAnthropic(default_headers=headers)

    async def _call(self, prompt: str, temperature: float, answer_text: str):
        # answer_text is unused here: the prompt already carries it.
        request: dict = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if self.model in _MODELS_ACCEPTING_TEMPERATURE:
            request["temperature"] = temperature

        response = await self.client.messages.create(**request)
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
