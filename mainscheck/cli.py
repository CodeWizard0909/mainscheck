"""Command line interface.

    uv run mainscheck run --rubric structured --model <model-id> --repeats 5
    uv run mainscheck report --open
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click
import yaml

from .corpus import load_corpus, load_questions
from .economics import load_pricing, summarise
from .graders.anthropic_grader import AnthropicGrader
from .graders.base import Cache
from .metrics import bias, consistency, monotonicity, sensitivity
from .perturb import CONTROL, apply_all
from .report import build_report
from .runner import build_tasks, load_all, run, save

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus" / "answers"
QUESTIONS = ROOT / "corpus" / "questions.yaml"
RUBRICS = ROOT / "rubrics"
RESULTS = ROOT / "results"
CACHE = ROOT / ".cache"
PRICING = ROOT / "config" / "pricing.yaml"


@click.group()
def cli() -> None:
    """An open reliability test for AI grading of UPSC Mains answers."""


@cli.command("run")
@click.option("--rubric", default="structured", help="Rubric id in rubrics/.")
@click.option("--model", required=True, help="Model id to grade with.")
@click.option("--repeats", default=5, show_default=True,
              help="Repeat runs per answer, for self-consistency.")
@click.option("--temperatures", default="0.0,0.7", show_default=True)
@click.option("--concurrency", default=8, show_default=True)
@click.option("--no-perturbations", is_flag=True, help="Consistency only.")
@click.option("--limit", default=0, help="Use only the first N answers (a smoke test).")
def run_cmd(rubric, model, repeats, temperatures, concurrency, no_perturbations, limit):
    """Grade the corpus and save results."""
    rubric_path = RUBRICS / f"{rubric}.yaml"
    if not rubric_path.exists():
        raise click.ClickException(f"no rubric at {rubric_path}")
    rubric_cfg = yaml.safe_load(rubric_path.read_text(encoding="utf-8"))

    answers = load_corpus(CORPUS)
    if limit:
        answers = answers[:limit]
    questions = load_questions(QUESTIONS)

    temps = [float(t) for t in temperatures.split(",") if t.strip()]
    tasks = build_tasks(
        answers, questions,
        repeats=repeats,
        temperatures=temps,
        include_perturbations=not no_perturbations,
    )

    cache = Cache(CACHE)
    grader = AnthropicGrader(model, rubric_cfg, cache)

    click.echo(f"{len(answers)} answers -> {len(tasks)} gradings "
               f"({model}, rubric={rubric})")

    done = 0
    def tick(_):
        nonlocal done
        done += 1
        if done % 25 == 0 or done == len(tasks):
            click.echo(f"  {done}/{len(tasks)}  cache hits={cache.hits}", err=True)

    gradings = asyncio.run(run(grader, tasks, concurrency=concurrency, progress=tick))

    failed = [g for g in gradings if g.error]
    if failed:
        click.secho(f"{len(failed)} gradings failed; first: {failed[0].error}",
                    fg="yellow", err=True)

    out = RESULTS / f"{model}__{rubric}.json"
    save(gradings, out)
    click.secho(f"wrote {out.relative_to(ROOT)}", fg="green")
    click.echo(f"cache: {cache.hits} hits, {cache.misses} misses")


@cli.command("report")
@click.option("--open", "open_", is_flag=True, help="Open the report when built.")
def report_cmd(open_):
    """Compute metrics across every saved run and build the HTML report."""
    if not RESULTS.exists() or not any(RESULTS.glob("*.json")):
        raise click.ClickException("no results yet - run `mainscheck run` first")

    gradings = load_all(RESULTS)
    answers = {a.answer_id: a for a in load_corpus(CORPUS)}
    quality = {aid: a.quality for aid, a in answers.items()}

    directions = {}
    lengths: dict[tuple[str, str], int] = {}
    for answer in answers.values():
        lengths[(answer.answer_id, "original")] = len(answer.rendered())
        for perturbation in apply_all(answer):
            directions[perturbation.name] = perturbation.direction
            lengths[(answer.answer_id, perturbation.name)] = len(perturbation.text)

    configs = sorted({(g.model, g.rubric_id) for g in gradings})
    blocks = []
    for model, rubric_id in configs:
        subset = [g for g in gradings if g.model == model and g.rubric_id == rubric_id]
        blocks.append({
            "model": model,
            "rubric": rubric_id,
            "consistency": consistency(subset),
            "sensitivity": sensitivity(subset, directions),
            "monotonicity": monotonicity(subset, quality),
            "bias": bias(subset, lengths),
        })

    economics = summarise(gradings, load_pricing(PRICING))
    path = build_report(blocks, economics, ROOT / "report" / "index.html")
    click.secho(f"wrote {path.relative_to(ROOT)}", fg="green")

    for block in blocks:
        control_drift = block["sensitivity"].control_drift
        flag = "OK" if control_drift <= 0.2 else "CONTROL DRIFT"
        click.echo(
            f"  {block['model']} / {block['rubric']}: "
            f"{block['consistency'].headline}  [{flag}]"
        )

    if not any(e.priced for e in economics):
        click.secho(
            "note: config/pricing.yaml has no prices, so cost columns are blank. "
            "Fill it from the current published price list.",
            fg="yellow",
        )

    if open_:
        import webbrowser
        webbrowser.open(path.as_uri())


@cli.command("validate")
def validate_cmd():
    """Check the corpus loads and every perturbation applies. No API calls."""
    answers = load_corpus(CORPUS)
    questions = load_questions(QUESTIONS)
    problems = []

    for answer in answers:
        if answer.question_id not in questions:
            problems.append(f"{answer.answer_id}: unknown question_id")
        if not answer.facts:
            problems.append(f"{answer.answer_id}: no {{{{f:...}}}} fact markers")
        if len(answer.paragraphs) < 3:
            problems.append(f"{answer.answer_id}: fewer than 3 paragraphs")
        names = {p.name for p in apply_all(answer)}
        if CONTROL not in names:
            problems.append(f"{answer.answer_id}: control perturbation did not apply")

    by_quality = {}
    for answer in answers:
        by_quality[answer.quality] = by_quality.get(answer.quality, 0) + 1

    click.echo(f"{len(answers)} answers: {by_quality}")
    for problem in problems:
        click.secho(f"  {problem}", fg="yellow")
    if problems:
        sys.exit(1)
    click.secho("corpus OK", fg="green")
