"""Orchestration: build the work list, run it with bounded concurrency, save results."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path

from .corpus import Answer
from .graders.base import Grader, Grading
from .perturb import apply_all


@dataclass(frozen=True)
class Task:
    answer: Answer
    question: str
    variant: str
    text: str
    run_index: int
    temperature: float


def build_tasks(
    answers: list[Answer],
    questions: dict[str, str],
    *,
    repeats: int,
    temperatures: list[float],
    include_perturbations: bool,
) -> list[Task]:
    tasks: list[Task] = []
    for answer in answers:
        question = questions.get(answer.question_id)
        if question is None:
            raise ValueError(
                f"{answer.answer_id}: question_id {answer.question_id!r} "
                "not found in questions.yaml"
            )

        for temperature in temperatures:
            for run_index in range(repeats):
                tasks.append(
                    Task(answer, question, "original", answer.rendered(),
                         run_index, temperature)
                )

        if include_perturbations:
            # Perturbations run once, at temperature 0 — we are measuring the effect
            # of the edit, not of sampling noise.
            for perturbation in apply_all(answer):
                tasks.append(
                    Task(answer, question, perturbation.name, perturbation.text, 0, 0.0)
                )
    return tasks


async def run(
    grader: Grader, tasks: list[Task], *, concurrency: int = 8, progress=None
) -> list[Grading]:
    semaphore = asyncio.Semaphore(concurrency)

    async def one(task: Task) -> Grading:
        async with semaphore:
            result = await grader.grade(
                answer_id=task.answer.answer_id,
                question_id=task.answer.question_id,
                question=task.question,
                answer_text=task.text,
                variant=task.variant,
                run_index=task.run_index,
                temperature=task.temperature,
            )
            if progress is not None:
                progress(result)
            return result

    return await asyncio.gather(*(one(t) for t in tasks))


_ILLEGAL_IN_FILENAMES = str.maketrans({c: "-" for c in '<>:"/\\|?*'})


def safe_filename(name: str) -> str:
    """Make a model name usable as a filename.

    Ollama names contain a colon (``llama3.2:3b``). On Windows a colon in a path
    opens an NTFS alternate data stream instead of creating a file, so the results
    land on a zero-byte file, stay readable by exact path, and are invisible to the
    directory glob the report uses. Silent, and very confusing to diagnose.
    """
    return name.translate(_ILLEGAL_IN_FILENAMES)


def save(gradings: list[Grading], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([g.model_dump() for g in gradings], indent=2), encoding="utf-8"
    )


def load(path: Path) -> list[Grading]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [Grading.model_validate(item) for item in raw]


def load_all(directory: Path) -> list[Grading]:
    out: list[Grading] = []
    for path in sorted(directory.glob("*.json")):
        out.extend(load(path))
    return out
