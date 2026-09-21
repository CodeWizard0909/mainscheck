"""Grader interface, result schema, and the disk cache.

Token counts and latency are recorded on every call from the start. Retrofitting
cost accounting once thousands of results exist is miserable, and the economics half
of this project depends on it.
"""

from __future__ import annotations

import hashlib
import json
import time
from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel, Field


class Grading(BaseModel):
    """One grading of one piece of text by one configuration."""

    answer_id: str
    question_id: str
    variant: str = "original"  # "original" or a perturbation name
    run_index: int = 0

    model: str
    rubric_id: str
    temperature: float

    scores: dict[str, float] = Field(default_factory=dict)
    rationale: str = ""

    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0

    error: str | None = None

    @property
    def overall(self) -> float | None:
        if not self.scores:
            return None
        return sum(self.scores.values()) / len(self.scores)


class Cache:
    """Content-addressed disk cache.

    ``run_index`` is part of the key on purpose. Self-consistency measurement needs
    N genuinely separate calls; a cache that collapsed them would silently report
    perfect consistency.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.hits = 0
        self.misses = 0

    def key(self, **parts: object) -> str:
        blob = json.dumps(parts, sort_keys=True, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]

    def get(self, key: str) -> Grading | None:
        path = self.root / f"{key}.json"
        if not path.exists():
            self.misses += 1
            return None
        self.hits += 1
        return Grading.model_validate_json(path.read_text(encoding="utf-8"))

    def put(self, key: str, grading: Grading) -> None:
        path = self.root / f"{key}.json"
        path.write_text(grading.model_dump_json(indent=2), encoding="utf-8")


class Grader(ABC):
    """Implement this to plug in your own evaluator and compare it against the rest."""

    def __init__(self, model: str, rubric: dict, cache: Cache) -> None:
        self.model = model
        self.rubric = rubric
        self.rubric_id = rubric["id"]
        self.criteria = list(rubric["criteria"])
        self.cache = cache

    @abstractmethod
    async def _call(
        self, prompt: str, temperature: float, answer_text: str
    ) -> tuple[dict, str, int, int]:
        """Return (scores, rationale, input_tokens, output_tokens).

        ``answer_text`` is the raw answer, passed through so an implementation never
        has to parse it back out of the rendered prompt.
        """

    def build_prompt(self, question: str, answer_text: str) -> str:
        criteria_block = "\n".join(
            f"- {name}: {desc}" for name, desc in self.rubric["criteria"].items()
        )
        return self.rubric["template"].format(
            question=question,
            answer=answer_text,
            criteria=criteria_block,
            scale=self.rubric.get("scale", "0 to 10"),
        )

    async def grade(
        self,
        *,
        answer_id: str,
        question_id: str,
        question: str,
        answer_text: str,
        variant: str = "original",
        run_index: int = 0,
        temperature: float = 0.0,
    ) -> Grading:
        key = self.cache.key(
            model=self.model,
            rubric=self.rubric_id,
            question=question,
            answer=answer_text,
            temperature=temperature,
            run_index=run_index,
            # Variant belongs in the key even though it does not change the prompt.
            # A perturbation that happens to produce text identical to the original
            # would otherwise collide with it and be served a Grading labelled
            # "original", silently corrupting the sensitivity measurement.
            variant=variant,
        )
        cached = self.cache.get(key)
        if cached is not None:
            return cached

        prompt = self.build_prompt(question, answer_text)
        started = time.perf_counter()
        try:
            scores, rationale, tin, tout = await self._call(
                prompt, temperature, answer_text
            )
            error = None
        except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
            scores, rationale, tin, tout = {}, "", 0, 0
            error = f"{type(exc).__name__}: {exc}"

        grading = Grading(
            answer_id=answer_id,
            question_id=question_id,
            variant=variant,
            run_index=run_index,
            model=self.model,
            rubric_id=self.rubric_id,
            temperature=temperature,
            scores=scores,
            rationale=rationale,
            input_tokens=tin,
            output_tokens=tout,
            latency_s=time.perf_counter() - started,
            error=error,
        )
        if error is None:
            self.cache.put(key, grading)
        return grading
