# MainsCheck

An open test for whether an AI examiner is **consistent**, and whether it reacts to
the things that should change a mark.

Several Indian exam-prep products now advertise AI evaluation of UPSC Mains answers.
None of them publishes evidence that the scores are stable. This measures that.

> **Status: scaffold.** The harness runs; the corpus is one example answer. Headline
> numbers appear here once the corpus is written and the first full run completes.

---

## What it measures

| Metric | Question it answers |
|---|---|
| **Self-consistency** | Grade the same answer five times. How far do the scores wander? |
| **Sensitivity** | Delete a fact from a correct answer. Does the mark actually fall? |
| **Monotonicity** | Do weak, middling and strong answers rank in that order? |
| **Bias** | Does padding an answer with filler raise its score? Does grading position matter? |

### Why not compare against human examiners?

That was the first design. It does not work. UPSC does not publish evaluated answer
copies with per-answer marks; what circulates is toppers' copies hosted by coaching
institutes, as scanned handwriting, under their copyright. Building on that would mean
a handwriting-OCR project and redistributing material that is not mine.

So the benchmark is inverted: instead of asking whether the grader agrees with a
human, it asks whether the grader agrees **with itself**, and whether it responds to
edits that objectively change answer quality. No ground truth, no OCR, no borrowed
data — and arguably the harsher test. A grader that scores the same answer 5 on
Tuesday and 8 on Wednesday is not useful, however well it correlates on average.

---

## The six perturbations

| Perturbation | Expected effect |
|---|---|
| `delete_fact` | factual accuracy falls |
| `corrupt_fact` | factual accuracy falls **further** — wrong is worse than missing |
| `scramble_structure` | structure falls |
| `pad_verbosity` | nothing rises |
| `remove_conclusion` | structure falls |
| `synonym_rewrite` | **nothing moves — this is the control** |

The control carries the weight. If wording-only changes shift the score, the harness
is measuring sampling noise rather than answer quality, and the report says so on its
front page instead of hiding it.

---

## Run it

```bash
uv sync
uv run mainscheck validate
```

`validate` needs no API key. It checks that every answer parses, carries fact markers,
has at least three paragraphs, and that all six perturbations apply.

```bash
export ANTHROPIC_API_KEY=...
uv run mainscheck run --rubric structured --model <model-id> --repeats 5 --limit 3
uv run mainscheck report --open
```

Start with `--limit 3`. The full matrix is answers x repeats x temperatures x
perturbations x configurations, which runs to tens of thousands of calls — extrapolate
the cost from a small run before committing to a large one. Every response is cached
to `.cache/` by content hash, so re-runs are nearly free.

Cost and latency are recorded on every call. Fill in `config/pricing.yaml` with
current published rates to populate the cost columns, and note the date you checked.

---

## Corpus format

Answers live in `corpus/answers/*.md` with YAML front matter:

```markdown
---
question_id: gs2-2023-q5
paper: GS2
quality: strong        # strong | middling | weak
---

Body text with {{f:the correct fact|a plausible wrong version}} marked inline.
```

Facts are marked `{{f:correct|corrupted}}`. The grader only ever sees the correct
form; the corrupted twin exists so `corrupt_fact` can swap in something wrong but
believable. Keeping both inline stops them drifting apart.

Questions come from public previous-year papers, verbatim including the directive
word, since comprehension is one of the scored criteria.

---

## Adding your own grader

Subclass `Grader` in `mainscheck/graders/base.py`, implement `_call`, and it slots
into the same metrics and report as everything else.

---

## Limitations

Written here first, deliberately.

- **All 30 answers were LLM-drafted and author-reviewed.** None was written by a UPSC
  aspirant or under examination conditions. An LLM-written corpus graded by an LLM has
  a circularity problem, and it is the most serious limitation here. It affects the
  monotonicity result in particular, since the quality labels encode the author's
  judgement rather than an examiner's. See [corpus/PROVENANCE.md](corpus/PROVENANCE.md)
  for what it does and does not undermine.
- **Nine of the ten questions are verbatim UPSC Mains 2023; one is author-written** and
  labelled `authored` so it is never cited as a real paper.
- **Consistency is not accuracy.** A grader could be perfectly stable and perfectly
  wrong. This measures reliability, which is necessary but not sufficient.
- **Effect sizes are means over a small corpus.** Treat them as directional.
- **No competitor products are tested.** Grading through someone's paid app would
  breach its terms. Only configurations — model plus rubric plus prompt — are compared.
- **Prices are user-supplied.** See `config/pricing.yaml`.

---

## Licence

Code: MIT. Corpus and results: CC BY 4.0. Questions are public UPSC material.
