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
from .env import load_dotenv
from .graders.anthropic_grader import AnthropicGrader
from .graders.base import Cache
from .graders.ollama import DEFAULT_HOST as OLLAMA_DEFAULT_HOST
from .graders.ollama import OllamaGrader, is_running
from .graders.stub import StubGrader
from .metrics import (
    bias,
    consistency,
    consistency_by_temperature,
    effect_by_quality,
    monotonicity,
    sensitivity,
)
from .perturb import CONTROL, apply_all, find_no_ops
from .report import build_report
from .runner import build_tasks, load_all, run, safe_filename, save

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus" / "answers"
QUESTIONS = ROOT / "corpus" / "questions.yaml"
RUBRICS = ROOT / "rubrics"
CACHE = ROOT / ".cache"
PRICING = ROOT / "config" / "pricing.yaml"

# Real runs and stub runs are kept apart so stub output can never reach a published
# report. Each results directory gets its own report file.
REAL_RESULTS = "results"
STUB_RESULTS = "results-stub"


def report_path_for(results_dir: str) -> Path:
    name = "index.html" if results_dir == REAL_RESULTS else f"{results_dir}.html"
    return ROOT / "report" / name


@click.group()
def cli() -> None:
    """An open reliability test for AI grading of UPSC Mains answers."""
    # Names only. The values are secrets and are never printed.
    for name in load_dotenv(ROOT / ".env"):
        click.echo(f"loaded {name} from .env", err=True)


@cli.command("run")
@click.option("--rubric", default="structured", help="Rubric id in rubrics/.")
@click.option("--model", required=True, help="Model id to grade with.")
@click.option("--repeats", default=5, show_default=True,
              help="Repeat runs per answer, for self-consistency.")
@click.option("--temperatures", default="0.0,0.7", show_default=True,
              help="Local models accept sampling parameters, so this axis is real. "
                   "Current hosted models reject them, and the value is then only "
                   "recorded as cache-key metadata - there, repeats alone measure "
                   "consistency.")
@click.option("--concurrency", default=8, show_default=True)
@click.option("--no-perturbations", is_flag=True, help="Consistency only.")
@click.option("--limit", default=0, help="Use only the first N answers (a smoke test).")
@click.option("--grader", type=click.Choice(["ollama", "anthropic", "stub"]),
              default="ollama", show_default=True,
              help="'ollama' runs a local model - free, no key. 'stub' exercises "
                   "the pipeline with no model at all.")
@click.option("--results-dir", default=None,
              help="Where to write results. Defaults to results/, or results-stub/ "
                   "for the stub grader so the two never mix.")
def run_cmd(rubric, model, repeats, temperatures, concurrency, no_perturbations, limit,
            grader, results_dir):
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

    if grader == "stub":
        cache = Cache(CACHE / "stub")
        grader_impl = StubGrader(model, rubric_cfg, cache)
        out_dir = ROOT / (results_dir or STUB_RESULTS)
        click.secho("stub grader: no API calls, and these results are not real",
                    fg="yellow", err=True)
    elif grader == "ollama":
        host = asyncio.run(is_running())
        if host is None:
            raise click.ClickException(
                f"no Ollama server at {OLLAMA_DEFAULT_HOST}. Start it with `ollama "
                "serve`, or install it from https://ollama.com/download"
            )
        cache = Cache(CACHE)
        grader_impl = OllamaGrader(model, rubric_cfg, cache, host=host)
        out_dir = ROOT / (results_dir or REAL_RESULTS)
        # Local inference is compute-bound, so parallel requests queue rather than
        # overlap. More than a couple just adds memory pressure.
        concurrency = min(concurrency, 2)
        click.echo(f"ollama at {host}, concurrency capped to {concurrency}", err=True)
    else:
        cache = Cache(CACHE)
        grader_impl = AnthropicGrader(model, rubric_cfg, cache)
        out_dir = ROOT / (results_dir or REAL_RESULTS)

    click.echo(f"{len(answers)} answers -> {len(tasks)} gradings "
               f"({model}, rubric={rubric})")

    done = 0
    def tick(_):
        nonlocal done
        done += 1
        if done % 25 == 0 or done == len(tasks):
            click.echo(f"  {done}/{len(tasks)}  cache hits={cache.hits}", err=True)

    gradings = asyncio.run(run(grader_impl, tasks, concurrency=concurrency, progress=tick))

    failed = [g for g in gradings if g.error]
    if failed:
        click.secho(f"{len(failed)} gradings failed; first: {failed[0].error}",
                    fg="yellow", err=True)

    # Writing a results file of nothing but errors poisons the directory: `report`
    # would load it and compute metrics over an empty set.
    if len(failed) == len(gradings):
        raise click.ClickException(
            "every grading failed - nothing written. Fix the error above and re-run."
        )

    out = out_dir / f"{safe_filename(model)}__{rubric}.json"
    save(gradings, out)
    click.secho(f"wrote {out.relative_to(ROOT)}", fg="green")
    click.echo(f"cache: {cache.hits} hits, {cache.misses} misses")


@cli.command("report")
@click.option("--open", "open_", is_flag=True, help="Open the report when built.")
@click.option("--results-dir", default=REAL_RESULTS, show_default=True,
              help="Pass results-stub to inspect a stub run.")
def report_cmd(open_, results_dir):
    """Compute metrics across every saved run and build the HTML report."""
    source = ROOT / results_dir
    if not source.exists() or not any(source.glob("*.json")):
        raise click.ClickException(f"no results in {results_dir}/ - run `mainscheck run` first")

    gradings = load_all(source)
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
        by_temperature = consistency_by_temperature(subset)
        # Pin the banded control to the lowest temperature present: where the model
        # is deterministic, a measured change is a real effect rather than noise.
        coldest = min(by_temperature) if by_temperature else None
        blocks.append({
            "model": model,
            "rubric": rubric_id,
            "consistency": consistency(subset),
            "by_temperature": by_temperature,
            "sensitivity": sensitivity(subset, directions),
            "monotonicity": monotonicity(subset, quality),
            "bias": bias(subset, lengths),
            "control_by_band": effect_by_quality(
                subset, quality, CONTROL, temperature=coldest
            ),
        })

    economics = summarise(gradings, load_pricing(PRICING))
    path = build_report(blocks, economics, report_path_for(results_dir))
    click.secho(f"wrote {path.relative_to(ROOT)}", fg="green")

    for block in blocks:
        click.echo(f"  {block['model']} / {block['rubric']}")
        for temp, c in sorted(block["by_temperature"].items()):
            if c.answers:
                click.echo(f"    t={temp:.1f}  {c.headline}")

        banded = block["control_by_band"]
        failing = {b: v for b, v in banded.per_band.items() if abs(v) > 0.2}
        if failing:
            detail = ", ".join(f"{b} {v:+.2f}" for b, v in sorted(failing.items()))
            click.secho(f"    CONTROL DRIFT by band: {detail}", fg="red")
        elif banded.per_band:
            click.echo("    control flat across every quality band")

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
        for name in find_no_ops(answer):
            problems.append(
                f"{answer.answer_id}: {name} produced no change "
                f"(the answer lacks anything for it to act on)"
            )

    by_quality = {}
    for answer in answers:
        by_quality[answer.quality] = by_quality.get(answer.quality, 0) + 1

    click.echo(f"{len(answers)} answers: {by_quality}")
    for problem in problems:
        click.secho(f"  {problem}", fg="yellow")
    if problems:
        sys.exit(1)
    click.secho("corpus OK", fg="green")
