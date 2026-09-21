"""The four reliability metrics.

Every one of these is computed per (model, rubric) configuration so that
configurations can be compared on a like-for-like basis.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from statistics import mean, pstdev

from scipy.stats import spearmanr

from .corpus import QUALITY_ORDER
from .graders.base import Grading
from .perturb import CONTROL


@dataclass
class ConsistencyResult:
    per_criterion_sd: dict[str, float]
    worst_criterion: str
    worst_sd: float
    max_spread: float  # largest (max - min) overall score seen on a single answer

    @property
    def headline(self) -> str:
        return (
            f"same answer varies by up to {self.max_spread:.1f} points; "
            f"worst criterion '{self.worst_criterion}' SD={self.worst_sd:.2f}"
        )


def consistency(gradings: list[Grading]) -> ConsistencyResult:
    """Same answer, same config, repeated runs. How much does the score wander?"""
    originals = [g for g in gradings if g.variant == "original" and not g.error]
    by_answer: dict[str, list[Grading]] = defaultdict(list)
    for g in originals:
        by_answer[g.answer_id].append(g)

    per_criterion: dict[str, list[float]] = defaultdict(list)
    spreads: list[float] = []

    for runs in by_answer.values():
        if len(runs) < 2:
            continue
        overalls = [g.overall for g in runs if g.overall is not None]
        if len(overalls) >= 2:
            spreads.append(max(overalls) - min(overalls))
        for criterion in runs[0].scores:
            values = [g.scores[criterion] for g in runs if criterion in g.scores]
            if len(values) >= 2:
                per_criterion[criterion].append(pstdev(values))

    sds = {c: mean(v) for c, v in per_criterion.items() if v}
    if not sds:
        return ConsistencyResult({}, "n/a", 0.0, 0.0)
    worst = max(sds, key=lambda c: sds[c])
    return ConsistencyResult(sds, worst, sds[worst], max(spreads) if spreads else 0.0)


@dataclass
class SensitivityResult:
    per_perturbation: dict[str, float] = field(default_factory=dict)
    expected_direction: dict[str, int] = field(default_factory=dict)
    control_drift: float = 0.0

    def passed(self, name: str) -> bool:
        """Did the score move the way it should have?"""
        delta = self.per_perturbation.get(name, 0.0)
        direction = self.expected_direction.get(name, 0)
        if direction == 0:
            return abs(delta) <= 0.2
        return delta * direction > 0


def sensitivity(
    gradings: list[Grading], directions: dict[str, int]
) -> SensitivityResult:
    """Mean change in overall score, per perturbation, against the original."""
    baseline: dict[str, float] = {}
    for g in gradings:
        if g.variant == "original" and not g.error and g.overall is not None:
            baseline.setdefault(g.answer_id, g.overall)

    deltas: dict[str, list[float]] = defaultdict(list)
    for g in gradings:
        if g.variant == "original" or g.error or g.overall is None:
            continue
        if g.answer_id in baseline:
            deltas[g.variant].append(g.overall - baseline[g.answer_id])

    per = {name: mean(values) for name, values in deltas.items() if values}
    return SensitivityResult(per, directions, abs(per.get(CONTROL, 0.0)))


@dataclass
class MonotonicityResult:
    spearman_rho: float
    p_value: float
    inversion_rate: float


def monotonicity(
    gradings: list[Grading], quality_by_answer: dict[str, str]
) -> MonotonicityResult:
    """Do weak < middling < strong answers actually rank in that order?"""
    scored: dict[str, list[float]] = defaultdict(list)
    for g in gradings:
        if g.variant == "original" and not g.error and g.overall is not None:
            scored[g.answer_id].append(g.overall)

    pairs = [
        (QUALITY_ORDER[quality_by_answer[aid]], mean(vals))
        for aid, vals in scored.items()
        if aid in quality_by_answer
    ]
    if len(pairs) < 3:
        return MonotonicityResult(0.0, 1.0, 0.0)

    ranks, scores = zip(*pairs)
    rho, p = spearmanr(ranks, scores)

    inversions = total = 0
    for i in range(len(pairs)):
        for j in range(i + 1, len(pairs)):
            if ranks[i] == ranks[j]:
                continue
            total += 1
            expected_higher = i if ranks[i] > ranks[j] else j
            other = j if expected_higher == i else i
            if scores[expected_higher] <= scores[other]:
                inversions += 1

    return MonotonicityResult(
        float(rho), float(p), inversions / total if total else 0.0
    )


@dataclass
class BiasResult:
    length_bias: float  # score change per 100 added characters, from pad_verbosity
    position_bias: float  # first-in-batch vs last-in-batch mean difference


def bias(gradings: list[Grading], lengths: dict[tuple[str, str], int]) -> BiasResult:
    """Length bias uses the padding perturbation; padding adds words, not substance."""
    baseline: dict[str, float] = {}
    for g in gradings:
        if g.variant == "original" and not g.error and g.overall is not None:
            baseline.setdefault(g.answer_id, g.overall)

    per_100: list[float] = []
    for g in gradings:
        if g.variant != "pad_verbosity" or g.error or g.overall is None:
            continue
        original_len = lengths.get((g.answer_id, "original"))
        padded_len = lengths.get((g.answer_id, "pad_verbosity"))
        if not original_len or not padded_len or padded_len <= original_len:
            continue
        added = (padded_len - original_len) / 100
        if g.answer_id in baseline and added > 0:
            per_100.append((g.overall - baseline[g.answer_id]) / added)

    ordered = [
        g for g in gradings
        if g.variant == "original" and not g.error and g.overall is not None
    ]
    if len(ordered) >= 4:
        quarter = max(1, len(ordered) // 4)
        first = mean(g.overall for g in ordered[:quarter])
        last = mean(g.overall for g in ordered[-quarter:])
        position = first - last
    else:
        position = 0.0

    return BiasResult(mean(per_100) if per_100 else 0.0, position)
