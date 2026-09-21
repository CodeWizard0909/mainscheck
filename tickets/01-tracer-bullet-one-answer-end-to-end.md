# 01: Tracer bullet — one answer graded end to end

**What to build:** A single UPSC Mains answer goes in, a real grading call comes back, and a report page opens showing an actual number. This proves the whole path — corpus parsing, perturbation, grading, caching, metrics, report — works before any bulk work is committed to it.

Deliberately tiny. Three answers at most, few repeats, one configuration. The point is to see the pipeline produce a real result, not to produce a meaningful result.

**Blocked by:** None (can start immediately)

**Status:** needs-info

- [ ] `ANTHROPIC_API_KEY` set and a live grading call succeeds against the structured rubric
- [x] Two more answers exist for the same question, one `middling` and one `weak`, so a spread is visible
- [x] A run with `--limit 3 --repeats 3` completes and writes a results JSON
- [ ] The report builds and opens, showing consistency and cost columns with real values
- [x] Re-running the same command is near-instant and shows cache hits, confirming the cache works
- [ ] Token counts and latency are non-zero on every stored grading

## Comments

**Status is `needs-info`:** waiting on an `ANTHROPIC_API_KEY`. Three criteria stay
unticked until one is available, and none of them should be reworded to match what the
stub can reach — the earlier revision of this ticket did exactly that and it was wrong.

- The **live grading call** cannot happen at all.
- The **report criterion** asks for consistency *and cost* with real values. Cost is
  blank until `config/pricing.yaml` is filled, and the consistency the stub produces is
  0.0 by construction, which is not a real value.
- **Tokens and latency** are non-zero in stub output, but the token counts are
  fabricated rather than reported by a model, so the criterion is not met.

Everything else is done and verified through a stub grader
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
