# 01: Tracer bullet — one answer graded end to end

**What to build:** A single UPSC Mains answer goes in, a real grading call comes back, and a report page opens showing an actual number. This proves the whole path — corpus parsing, perturbation, grading, caching, metrics, report — works before any bulk work is committed to it.

Deliberately tiny. Three answers at most, few repeats, one configuration. The point is to see the pipeline produce a real result, not to produce a meaningful result.

**Blocked by:** None (can start immediately)

**Status:** ready-for-human

- [x] A live grading call succeeds against the structured rubric
- [x] Two more answers exist for the same question, one `middling` and one `weak`, so a spread is visible
- [x] A run with `--limit 3 --repeats 3` completes and writes a results JSON
- [x] The report builds and opens, showing consistency, latency and token columns with real values
- [x] Re-running the same command is near-instant and shows cache hits, confirming the cache works
- [x] Token counts and latency are non-zero on every stored grading

## Comments

**Closed by a local run, not a hosted one.** The project moved to grading with a local
model through Ollama, so no API key was needed in the end. `llama3.2:3b` graded the
three answers with real scores, real token counts and real latency.

**One acceptance criterion was changed, and the reason matters.** It originally read
"consistency *and cost* columns with real values". Local inference has no per-call
price, so the design now reports latency and tokens instead of dollars, and the
criterion was amended to match. This is a change because the design changed underneath
it — distinct from an earlier revision of this ticket, which reworded a criterion to
fit a result that had fallen short. That was wrong and was reverted.

**A Windows bug surfaced on the full run.** Ollama model names contain a colon
(`llama3.2:3b`), and a colon in a Windows path opens an NTFS alternate data stream
rather than creating a file. Results were written to a zero-byte file's hidden stream:
readable by exact path, invisible to the directory glob `report` uses, and silent.
Filenames are now sanitised. Nothing was lost — the content-addressed cache replayed
all 480 gradings instantly.

Earlier work was verified through a stub grader
(`--grader stub`), which exercises the runner, cache, metrics and report with no
network and no cost. Stub output goes to `results-stub/` and never mixes with real
results.

**Two bugs found, which is what a tracer bullet is for.**

1. The cache key omitted `variant`. A perturbation producing text identical to the
   original collided with it and was served a `Grading` labelled `original`, which
   would have silently corrupted the sensitivity measurement. Fixed by adding `variant`
   to the key.
2. `synonym_rewrite` — the control — returned unchanged text when no substitution
   applied, which is worse than useless: the grader correctly reports no change and the
   benchmark records a passing control that tested nothing. It now returns nothing, and
   `validate` fails loudly on any perturbation that produces a no-op.

To finish: set `ANTHROPIC_API_KEY`, then run

    uv run mainscheck run --model <model-id> --rubric structured --limit 3 --repeats 3
    uv run mainscheck report --open
