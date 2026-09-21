"""Answer corpus: loading, fact markers, and structure.

An answer file is markdown with YAML front matter:

    ---
    question_id: gs2-2023-q5
    paper: GS2
    quality: strong          # strong | middling | weak
    ---

    Paragraph one, containing {{f:the Right to Education Act, 2009|the Right to
    Education Act, 2011}} as a marked fact.

    Paragraph two.

    Paragraph three, which is the conclusion.

A marked fact is ``{{f:correct|corrupted}}``. The correct form is what the grader
sees; the corrupted form is only used by the ``corrupt_fact`` perturbation. Keeping
both inline means a fact and its plausible-but-wrong twin never drift apart.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

QUALITY_ORDER = {"weak": 0, "middling": 1, "strong": 2}

_FACT = re.compile(r"\{\{f:(?P<correct>[^|{}]+)\|(?P<corrupted>[^|{}]+)\}\}")
_FRONT_MATTER = re.compile(r"\A---\n(?P<meta>.*?)\n---\n(?P<body>.*)\Z", re.DOTALL)


@dataclass(frozen=True)
class Fact:
    correct: str
    corrupted: str
    start: int
    end: int


@dataclass(frozen=True)
class Answer:
    answer_id: str
    question_id: str
    paper: str
    quality: str
    body: str

    @property
    def facts(self) -> list[Fact]:
        return [
            Fact(m.group("correct"), m.group("corrupted"), m.start(), m.end())
            for m in _FACT.finditer(self.body)
        ]

    @property
    def paragraphs(self) -> list[str]:
        return [p.strip() for p in re.split(r"\n\s*\n", self.body) if p.strip()]

    def rendered(self) -> str:
        """The text a grader actually sees: markers resolved to their correct form."""
        return render(self.body)


def render(body: str) -> str:
    return _FACT.sub(lambda m: m.group("correct"), body).strip()


def load_answer(path: Path) -> Answer:
    raw = path.read_text(encoding="utf-8")
    match = _FRONT_MATTER.match(raw)
    if not match:
        raise ValueError(f"{path.name}: missing YAML front matter")
    meta = yaml.safe_load(match.group("meta")) or {}

    for key in ("question_id", "paper", "quality"):
        if key not in meta:
            raise ValueError(f"{path.name}: front matter missing '{key}'")
    if meta["quality"] not in QUALITY_ORDER:
        raise ValueError(
            f"{path.name}: quality must be one of {sorted(QUALITY_ORDER)}, "
            f"got {meta['quality']!r}"
        )

    return Answer(
        answer_id=path.stem,
        question_id=str(meta["question_id"]),
        paper=str(meta["paper"]),
        quality=str(meta["quality"]),
        body=match.group("body").strip(),
    )


def load_corpus(directory: Path) -> list[Answer]:
    answers = [load_answer(p) for p in sorted(directory.glob("*.md"))]
    if not answers:
        raise ValueError(f"no answers found in {directory}")
    return answers


def load_questions(path: Path) -> dict[str, str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {str(k): str(v) for k, v in data.items()}
