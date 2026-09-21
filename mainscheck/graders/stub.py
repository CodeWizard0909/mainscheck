"""A deterministic stub grader, for exercising the pipeline without an API.

**This is not a grader.** It scores text by counting surface features, which is
precisely the kind of evaluation this project exists to discredit. It exists so the
runner, the metrics and the report can be verified end to end without spending money.
Tests do not depend on it; they build their own fixtures.

Results produced by it are written to a separate directory and never mix with real
ones. Nothing it produces belongs in a published report.

Known blind spots, left in place rather than tuned away: it counts date-like and
Article-like tokens, so ``corrupt_fact`` (1980 -> 1985) leaves its factual score
unchanged, and it counts paragraphs, so ``scramble_structure`` leaves its structure
score unchanged. Both register near zero. A real grader would react to either. Tuning
the stub until those moved would be fitting a fake evaluator to a desired result, which
is the practice this whole project exists to expose.
"""

from __future__ import annotations

import hashlib
import re

from ..perturb import FILLER_SENTENCES, SYNONYM_TARGETS
from .base import Cache, Grader

# Words that signal an argument is being weighed rather than listed.
#
# Anything the control perturbation rewrites is excluded. If the stub rewarded a word
# that synonym_rewrite substitutes, the stub would report the control as having an
# effect - it would be marking its own homework, and the pipeline check would pass
# while demonstrating the exact bug the control exists to catch.
_ANALYTICAL = re.compile(
    r"\b("
    + "|".join(
        w for w in
        ["whereas", "although", "critics", "conversely", "defended", "criticised",
         "tension", "trade-?off"]
        if w not in SYNONYM_TARGETS
    )
    + r")\b",
    re.IGNORECASE,
)
# Filler the padding perturbation inserts, taken from its own list so the two
# cannot drift apart.
_FILLER = re.compile(
    "|".join(re.escape(s.rstrip(".")) for s in FILLER_SENTENCES), re.IGNORECASE
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

    JITTER = 0.3

    async def _call(self, prompt: str, temperature: float, answer_text: str):
        answer = answer_text
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
            value = base.get(criterion, 5.0) + self._jitter_for(
                answer, criterion, temperature
            )
            scores[criterion] = round(max(0.0, min(10.0, value)), 2)

        rationale = (
            f"Stub: {paragraphs} paragraphs, {factual} factual markers, "
            f"{analytical} analytical signals, {filler} filler phrases."
        )
        return scores, rationale, words + 120, 60

    def _jitter_for(self, answer: str, criterion: str, temperature: float) -> float:
        """Deterministic pseudo-noise. Same inputs give the same value, always."""
        seed = f"{answer}:{criterion}:{temperature}:{self.model}"
        digest = hashlib.sha256(seed.encode("utf-8")).digest()
        unit = int.from_bytes(digest[:4], "big") / 0xFFFFFFFF  # 0.0 to 1.0
        spread = self.JITTER * (1.0 + temperature)
        return (unit - 0.5) * 2 * spread
