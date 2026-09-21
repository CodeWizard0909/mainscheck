"""Grader backed by a locally hosted model through Ollama.

This is the default grader for the published results. Everything it measures can be
reproduced by anyone with `ollama pull` and this repository - no API key, no billing
account, no rate limit. A benchmark that a reader cannot re-run is a claim, not a
measurement.

Unlike the current hosted models, Ollama still accepts `temperature`, so the
temperature axis is meaningful here and worth using.
"""

from __future__ import annotations

import os

import httpx2 as httpx

from .base import Cache, Grader, parse_scores

DEFAULT_HOST = "http://127.0.0.1:11434"


class OllamaGrader(Grader):
    def __init__(
        self,
        model: str,
        rubric: dict,
        cache: Cache,
        *,
        host: str | None = None,
        timeout: float = 600.0,
        num_predict: int = 512,
    ) -> None:
        super().__init__(model, rubric, cache)
        self.host = (host or os.environ.get("OLLAMA_HOST") or DEFAULT_HOST).rstrip("/")
        # Generous by design: a 7B model on CPU can take minutes for one grading, and
        # a timeout mid-corpus wastes the compute already spent.
        self.timeout = timeout
        self.num_predict = num_predict

    async def _call(self, prompt: str, temperature: float, answer_text: str):
        # answer_text is unused: the prompt already carries it.
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            # Ollama constrains decoding to valid JSON. The rubric still has to ask
            # for the right keys, but this removes prose-around-the-JSON failures,
            # which are the dominant parse error for small models.
            "format": "json",
            "options": {
                "temperature": temperature,
                "num_predict": self.num_predict,
            },
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.host}/api/chat", json=payload)
            if response.status_code == 404:
                raise RuntimeError(
                    f"model {self.model!r} is not pulled. Run: ollama pull {self.model}"
                )
            response.raise_for_status()
            body = response.json()

        text = body.get("message", {}).get("content", "")
        scores, rationale = parse_scores(text, self.criteria)

        # Ollama reports real token counts, so the economics section works unchanged.
        return (
            scores,
            rationale,
            int(body.get("prompt_eval_count", 0)),
            int(body.get("eval_count", 0)),
        )


async def is_running(host: str | None = None) -> str | None:
    """Return the host if an Ollama server answers there, else None."""
    base = (host or os.environ.get("OLLAMA_HOST") or DEFAULT_HOST).rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{base}/api/tags")
            response.raise_for_status()
    except Exception:
        return None
    return base
