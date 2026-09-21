# MainsCheck

An open reliability test for AI grading of UPSC Mains answers. It measures whether a
grading configuration is consistent with itself and whether it responds to edits that
should change a mark — not whether it agrees with human examiners, which no public data
supports.

## Agent skills

### Issue tracker

Issues are tracked markdown files in `tickets/`, numbered in dependency order; the
product spec is a Claude doc, not a file in this repo. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical roles, unchanged, written as a `**Status:**` line in each ticket
file. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context. `CONTEXT.md` and `docs/adr/` do not exist yet and are created lazily.
See `docs/agents/domain.md`.

## Working on this repo

- Run things through `uv`: `uv run mainscheck validate` needs no model at all and
  checks the corpus parses, has fact markers, and that all six perturbations apply.
- **Grading runs on a local model through Ollama by default, and must stay free to
  run.** Do not introduce a paid API on the default path. `--grader anthropic` exists
  for anyone who wants it and is never the default.
- Local inference is compute-bound: concurrency is capped at 2, and a full
  configuration takes hours on CPU rather than minutes. Always try `--limit 3` first.
  Responses cache by content hash, so an interrupted run resumes for free.
- The control perturbation (`synonym_rewrite`) must leave scores flat. If it doesn't,
  report that rather than working around it — it means the harness is measuring
  sampling noise.
- Never add scraped or redistributed coaching-institute material to the corpus. Answers
  are self-authored; published toppers' copies may be read for calibration only.
- Prices are never hardcoded. They live in `config/pricing.yaml`, user-supplied and
  dated.
