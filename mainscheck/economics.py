"""Cost and latency per evaluation.

Prices are NOT hardcoded here. They change, and a benchmark that quietly reports
stale pricing is worse than one that reports none. Fill in config/pricing.yaml from
the current published price list and cite the date you checked in your README.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

import yaml

from .graders.base import Grading


@dataclass
class Economics:
    model: str
    rubric_id: str
    evaluations: int
    mean_input_tokens: float
    mean_output_tokens: float
    mean_latency_s: float
    cost_per_eval_usd: float | None
    cost_per_1k_evals_usd: float | None

    @property
    def priced(self) -> bool:
        return self.cost_per_eval_usd is not None


def load_pricing(path: Path) -> dict[str, dict[str, float]]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {
        model: {
            "input": float(rates["input_per_mtok"]),
            "output": float(rates["output_per_mtok"]),
        }
        for model, rates in data.get("models", {}).items()
        if rates.get("input_per_mtok") is not None
    }


def summarise(
    gradings: list[Grading], pricing: dict[str, dict[str, float]]
) -> list[Economics]:
    groups: dict[tuple[str, str], list[Grading]] = defaultdict(list)
    for g in gradings:
        if not g.error:
            groups[(g.model, g.rubric_id)].append(g)

    out: list[Economics] = []
    for (model, rubric_id), items in sorted(groups.items()):
        tin = mean(g.input_tokens for g in items)
        tout = mean(g.output_tokens for g in items)
        rates = pricing.get(model)
        if rates:
            cost = (tin / 1_000_000) * rates["input"] + (tout / 1_000_000) * rates["output"]
        else:
            cost = None
        out.append(
            Economics(
                model=model,
                rubric_id=rubric_id,
                evaluations=len(items),
                mean_input_tokens=tin,
                mean_output_tokens=tout,
                mean_latency_s=mean(g.latency_s for g in items),
                cost_per_eval_usd=cost,
                cost_per_1k_evals_usd=cost * 1000 if cost is not None else None,
            )
        )
    return out


def routing_saving(
    full: Economics, cheap: Economics, cheap_share: float
) -> float | None:
    """Saving from sending ``cheap_share`` of evaluations to the cheaper config.

    The argument this supports: if structure checking can go to a small model and
    only factual accuracy needs a large one, what does the blended cost become?
    """
    if not (full.priced and cheap.priced):
        return None
    if not 0.0 <= cheap_share <= 1.0:
        raise ValueError("cheap_share must be between 0 and 1")
    blended = (
        cheap_share * cheap.cost_per_eval_usd
        + (1 - cheap_share) * full.cost_per_eval_usd
    )
    return 1 - (blended / full.cost_per_eval_usd)
