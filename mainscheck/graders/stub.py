"""A deterministic stub grader, for exercising the pipeline without an API.

**This is not a grader.** It scores text by counting surface features, which is
precisely the kind of evaluation this project exists to discredit. It exists so the
runner, the metrics and the report can be verified end to end without spending money,
and so tests have something to run against.

Results produced by it are written to a separate directory and never mix with real
ones. Nothing it produces belongs in a published report.
"""

from __future__ import annotations

import hashlib
import re

from .base import Cache, Grader

# Words that signal an argument is being weighed rather than listed.
_ANALYTICAL = re.compile(
    r"\b(however|whereas|although|critics|conversely|yet|nevertheless|"
    r"defended|criticised|tension|trade-?off)\b",
    re.IGNORECASE,
)
# Filler that adds length without content. The padding perturbation inserts these.
_FILLER = re.compile(
    r"\b(widely discussed|important to note|various stakeholders|broader context)\b",
    re.IGNORECASE,
)
# Dates, Article numbers and case years - a crude proxy for factual density.
_FACTUAL = re.compile(r"\b(Article\s+\d+|\d{4})\b")


class StubGrader(Grader):
    """Scores from text features, deterministically.

    Being deterministic, it reports a self-consistency of exactly 0.0 within a
    temperature - which is correct for it, and not a bug to engineer around. The
    metrics that verify the pipeline here are sensitivity and monotonicity, which do
    vary, because the text varies. Consistency is exercised properly in the tests
    against hand-built fixtures.
    """

    def __init__(
        self, model: str, rubric: dict, cache: Cache, *, jitter: float = 0.3
    ) -> None:
        super().__init__(model, rubric, cache)
        self.jitter = jitter

    async def _call(self, prompt: str, temperature: float):
        answer = self._answer_from(prompt)
        words = max(1, len(answer.split()))

        paragraphs = len([p for p in answer.split("\n\n") if p.strip()])
        analytical = len(_ANALYTICAL.findall(answer))
        factual = len(_FACTUAL.findall(answer))
        filler = len(_FILLER.findall(answer))

        base = {
            "comprehension": 5.0 + min(2.5, analytical * 0.6),
            "structure": 3.0 + min(4.0, paragraphs * 0.9) - min(2.0, filler * 0.5),
            "factual_accuracy": 4.0 + min(4.0, factual * 0.7),
            "analytical_depth": 3.5 + min(4.0, analytical * 0.9) - (words > 600) * 0.5,
            "overall": 4.0 + min(3.0, analytical * 0.5) + min(2.0, factual * 0.3),
        }

        scores = {}
        for criterion in self.criteria:
            value = base.get(criterion, 5.0) + self._jitter_for(answer, criterion, temperature)
            scores[criterion] = round(max(0.0, min(10.0, value)), 2)

        rationale = (
            f"Stub: {paragraphs} paragraphs, {factual} factual markers, "
            f"{analytical} analytical signals, {filler} filler phrases."
        )
        return scores, rationale, words + 120, 60

    def _jitter_for(self, answer: str, criterion: str, temperature: float) -> float:
        """Deterministic pseudo-noise. Same inputs give the same value, always."""
        if self.jitter <= 0:
            return 0.0
        seed = f"{answer}:{criterion}:{temperature}:{self.model}"
        digest = hashlib.sha256(seed.encode("utf-8")).digest()
        unit = int.from_bytes(digest[:4], "big") / 0xFFFFFFFF  # 0.0 to 1.0
        spread = self.jitter * (1.0 + temperature)
        return (unit - 0.5) * 2 * spread

    @staticmethod
    def _answer_from(prompt: str) -> str:
        """Pull the answer back out of the rendered prompt."""
        for marker in ("CANDIDATE ANSWER:", "ANSWER:"):
            if marker in prompt:
                tail = prompt.split(marker, 1)[1]
                # Stop at the next all-caps section header, if any.
                stop = re.search(r"\n[A-Z][A-Z ]{3,}:", tail)
                return (tail[: stop.start()] if stop else tail).strip()
        return prompt
