"""The six perturbations.

Each returns perturbed answer text plus the direction the score is expected to move
on a named criterion. ``synonym_rewrite`` is the control: if a grader's scores move
when only wording changes, the harness is measuring noise, and that is a finding in
itself rather than something to hide.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Callable

from .corpus import Answer, render

# Deliberately bland filler. It adds length and zero substance, which is the point.
FILLER_SENTENCES = [
    "This dimension of the issue has been widely discussed in policy circles.",
    "It is important to note that the matter has several aspects worth considering.",
    "Various stakeholders have expressed differing views on this question over time.",
    "The broader context of this issue continues to remain relevant to the debate.",
]

# Wording-only substitutions. Nothing here changes a claim, a fact, or an argument.
#
# Connectives and intensifiers only. Domain nouns are deliberately absent: "essential
# features" and "basic structure" are terms of art in constitutional law, and swapping
# them would change meaning, which is the one thing the control must never do.
_SYNONYMS = {
    r"\bimportant\b": "significant",
    r"\bshows\b": "demonstrates",
    r"\bbecause\b": "since",
    r"\bhowever\b": "nevertheless",
    r"\bmany\b": "numerous",
    r"\balso\b": "additionally",
    r"\bhelp\b": "assist",
    r"\bbig\b": "substantial",
    # "yet" is deliberately absent: adverbial "yet" ("not yet settled") becomes
    # "not nevertheless settled", which is ungrammatical. A grader would rightly
    # mark that down, and the control would register sensitivity that is really a
    # defect in the control itself.
    r"\btherefore\b": "consequently",
    r"\bthus\b": "hence",
    r"\brather than\b": "instead of",
    r"\bsuch as\b": "including",
    r"\boften\b": "frequently",
    r"\bseveral\b": "multiple",
    r"\bfor example\b": "for instance",
    r"\bin addition\b": "additionally",
    r"\bvery\b": "highly",
}

# The bare words the control rewrites. Anything measuring answer quality must avoid
# these, or it will register an effect from the control and mark its own homework.
SYNONYM_TARGETS = frozenset(
    p.replace(r"\b", "").replace("\\", "") for p in _SYNONYMS
) | frozenset(_SYNONYMS.values())


@dataclass(frozen=True)
class Perturbation:
    name: str
    criterion: str
    direction: int  # -1 expect a fall, 0 expect no change, +1 expect a rise
    text: str
    note: str = ""


def _matching_case(replacement: str) -> Callable[[re.Match], str]:
    """Substitute without changing capitalisation.

    Matching is case-insensitive, so "However" at the start of a sentence would
    otherwise become lowercase "nevertheless". That is a mechanical error a grader
    could reasonably penalise, which would make the control register an effect that
    is really a defect in the control itself.
    """

    def substitute(match: re.Match) -> str:
        if match.group(0)[:1].isupper():
            return replacement[:1].upper() + replacement[1:]
        return replacement

    return substitute


def _rng(answer: Answer, salt: str) -> random.Random:
    """Deterministic per (answer, perturbation) so runs are reproducible."""
    return random.Random(f"{answer.answer_id}:{salt}")


def delete_fact(answer: Answer) -> Perturbation | None:
    facts = answer.facts
    if not facts:
        return None
    victim = _rng(answer, "delete").choice(facts)
    body = answer.body[: victim.start] + answer.body[victim.end :]
    body = re.sub(r"\s{2,}", " ", body)
    return Perturbation(
        "delete_fact",
        "factual_accuracy",
        -1,
        render(body),
        f"removed: {victim.correct}",
    )


def corrupt_fact(answer: Answer) -> Perturbation | None:
    """Wrong information should be penalised harder than missing information."""
    facts = answer.facts
    if not facts:
        return None
    victim = _rng(answer, "corrupt").choice(facts)
    body = answer.body[: victim.start] + victim.corrupted + answer.body[victim.end :]
    return Perturbation(
        "corrupt_fact",
        "factual_accuracy",
        -1,
        render(body),
        f"{victim.correct} -> {victim.corrupted}",
    )


def scramble_structure(answer: Answer) -> Perturbation | None:
    paras = answer.paragraphs
    if len(paras) < 3:
        return None
    shuffled = paras[:]
    rng = _rng(answer, "scramble")
    for _ in range(20):
        rng.shuffle(shuffled)
        if shuffled != paras:
            break
    else:
        return None
    return Perturbation(
        "scramble_structure", "structure", -1, render("\n\n".join(shuffled))
    )


def pad_verbosity(answer: Answer) -> Perturbation:
    """More words, no more content. No criterion should reward this."""
    rng = _rng(answer, "pad")
    paras = answer.paragraphs
    padded = [f"{p} {rng.choice(FILLER_SENTENCES)}" for p in paras]
    return Perturbation(
        "pad_verbosity", "structure", 0, render("\n\n".join(padded)),
        "length inflated without new content",
    )


def remove_conclusion(answer: Answer) -> Perturbation | None:
    paras = answer.paragraphs
    if len(paras) < 3:
        return None
    return Perturbation(
        "remove_conclusion", "structure", -1, render("\n\n".join(paras[:-1]))
    )


def synonym_rewrite(answer: Answer) -> Perturbation | None:
    """THE CONTROL. Wording changes only. Expected direction is zero.

    Returns None when no substitution applies. Returning unchanged text instead would
    be worse than useless: the grader would correctly report no change, and the
    benchmark would record a passing control that tested nothing.
    """
    body = answer.body
    for pattern, replacement in _SYNONYMS.items():
        body = re.sub(pattern, _matching_case(replacement), body, flags=re.IGNORECASE)
    if render(body) == answer.rendered():
        return None
    return Perturbation(
        "synonym_rewrite", "overall", 0, render(body), "control: wording only"
    )


ALL: list[Callable[[Answer], Perturbation | None]] = [
    delete_fact,
    corrupt_fact,
    scramble_structure,
    pad_verbosity,
    remove_conclusion,
    synonym_rewrite,
]

CONTROL = "synonym_rewrite"


def apply_all(answer: Answer) -> list[Perturbation]:
    """Every perturbation that genuinely changes this answer.

    No-ops are filtered here rather than at the call sites, so there is one
    definition of "this perturbation did nothing". Grading a no-op would cost money
    to learn that unchanged text scores the same.
    """
    original = answer.rendered()
    out = []
    for fn in ALL:
        result = fn(answer)
        if result is not None and result.text != original:
            out.append(result)
    return out


def find_no_ops(answer: Answer) -> list[str]:
    """Names of perturbations that produced no change, for `validate` to report.

    A perturbation that leaves the text untouched is a silent no-op: the grader
    correctly reports no change, and the benchmark records a clean result for
    entirely the wrong reason. The author needs to know, so the answer can be fixed.
    """
    original = answer.rendered()
    names = []
    for fn in ALL:
        result = fn(answer)
        if result is None or result.text == original:
            names.append(fn.__name__)
    return names
