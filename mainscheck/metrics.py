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
    mean_spread: float = 0.0
    deterministic: int = 0  # answers whose repeats agreed exactly
    answers: int = 0

    @property
    def headline(self) -> str:
        if not self.answers:
            return "no repeated runs to compare"
        return (
            f"mean spread {self.mean_spread:.2f}, worst {self.max_spread:.2f}; "
            f"{self.deterministic}/{self.answers} answers identical across repeats"
        )


def consistency(gradings: list[Grading]) -> ConsistencyResult:
    """Same answer, same config, same temperature, repeated runs.

    Runs are grouped by (answer, temperature) rather than by answer alone. Mixing
    temperatures would blend two different quantities - sampling variance at one
    temperature, and the difference between temperature settings - into a single
    number that describes neither. On a deterministic model the blended figure looks
    like instability that is not there.
    """
    runs_by_group: dict[tuple[str, float], list[Grading]] = defaultdict(list)
    for g in gradings:
        if g.variant == "original" and not g.error:
            runs_by_group[(g.answer_id, g.temperature)].append(g)

    per_criterion: dict[str, list[float]] = defaultdict(list)
    spreads: list[float] = []

    for runs in runs_by_group.values():
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
    return ConsistencyResult(
        per_criterion_sd=sds,
        worst_criterion=worst,
        worst_sd=sds[worst],
        max_spread=max(spreads) if spreads else 0.0,
        mean_spread=mean(spreads) if spreads else 0.0,
        deterministic=sum(1 for s in spreads if s == 0.0),
        answers=len(spreads),
    )


def consistency_by_temperature(
    gradings: list[Grading],
) -> dict[float, ConsistencyResult]:
    """Consistency reported separately per temperature.

    This is the headline split: a model can be perfectly deterministic at 0 and wander
    at 0.7, and a single blended figure hides both facts.
    """
    by_temp: dict[float, list[Grading]] = defaultdict(list)
    for g in gradings:
        by_temp[g.temperature].append(g)
    return {t: consistency(rows) for t, rows in sorted(by_temp.items())}


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
class BandedEffect:
    """One perturbation's effect, split by the quality band of the answer.

    An aggregate mean can pass a gate while hiding the whole finding. A control that
    is flat on strong answers and moves weak ones by half a point averages to
    something unremarkable, and the average is the least interesting number in it.
    """

    per_band: dict[str, float]
    max_per_band: dict[str, float]
    counts: dict[str, int]

    @property
    def worst_band(self) -> str | None:
        if not self.per_band:
            return None
        return max(self.per_band, key=lambda b: abs(self.per_band[b]))


def effect_by_quality(
    gradings: list[Grading],
    quality_by_answer: dict[str, str],
    variant: str,
    *,
    temperature: float | None = None,
) -> BandedEffect:
    """Mean and worst change for one perturbation, per quality band.

    Pin ``temperature`` to the deterministic setting where the model has one: at a
    sampling temperature the measured change is partly noise, and the point here is
    to attribute a real effect to a band.
    """
    rows = [g for g in gradings if not g.error and g.overall is not None]
    if temperature is not None:
        rows = [g for g in rows if g.temperature == temperature]

    baseline: dict[str, list[float]] = defaultdict(list)
    for g in rows:
        if g.variant == "original":
            baseline[g.answer_id].append(g.overall)
    base = {aid: mean(vals) for aid, vals in baseline.items()}

    per_band: dict[str, list[float]] = defaultdict(list)
    for g in rows:
        if g.variant != variant or g.answer_id not in base:
            continue
        band = quality_by_answer.get(g.answer_id)
        if band:
            per_band[band].append(g.overall - base[g.answer_id])

    return BandedEffect(
        per_band={b: mean(v) for b, v in per_band.items()},
        max_per_band={b: max(v, key=abs) for b, v in per_band.items()},
        counts={b: len(v) for b, v in per_band.items()},
    )


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
