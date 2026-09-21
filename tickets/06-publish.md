# 06: Publish

**What to build:** The repository becomes something a stranger can judge in sixty seconds without the author present — a hardened report, an honest README, real licence files, a public URL, and a short walkthrough.

The limitations section is written by the author, first, before a reviewer writes it for them. Consistency is not accuracy; the corpus is not real examination scripts; effect sizes are means over a small corpus; findings are specific to the configurations tested on the date tested. A visible limitations section is what separates a benchmark from marketing, and it is the only thing protecting the credibility this artefact runs on.

**Blocked by:** 05

**Status:** ready-for-human

- [x] Cost-versus-reliability chart sits above the fold on the report page
- [x] README headline table shows the real numbers, replacing the scaffold notice
- [x] Three copy-pasteable commands in the README work from a clean clone
- [x] Limitations section written honestly, including how the corpus was drafted
- [x] `LICENSE` (MIT) and `LICENSE-CORPUS` (CC BY 4.0) files exist, matching what the README claims
- [x] Public GitHub repository created and pushed
- [x] Report published to a URL that opens on a phone
- [ ] 90-second walkthrough recorded, ending on the perturbation result rather than on the author

## Comments

Repository: https://github.com/CodeWizard0909/mainscheck
Report: https://codewizard0909.github.io/mainscheck/

**Published safely.** Before the repository was made public, the full history was
scanned for key material (`sk-ant-`, `gho_`, `wrkspc_`) and came back clean, and
`research/`, `.env`, `.scratch/` and `results-stub/` were confirmed untracked. 74 files
published. The one apparent hit was a docstring in `env.py` containing the literal
text `ANTHROPIC_API_KEY=...`, not a key.

**The page leads with a stat, not a chart**, because the headline is a single number:
0 of 4 configurations detected a corrupted fact. The chart beneath it plots latency
against control drift, two series by model size, four directly-labelled marks, the 0.2
gate drawn, hover on each mark, validated palette with real dark-mode steps.

**The built report is committed to `docs/`** and served by Pages, so the published
numbers can always be traced to the commit that produced them. Stub and scratch
reports stay in the ignored `report/` directory where they cannot be confused with it.

**Verified from a clean clone:** `uv sync`, `mainscheck validate` and 36 tests pass
with no model, no key and no network.

**The walkthrough is the one criterion left, and it is a human task.** The script is
in the build spec. The beat that matters is at 0:45 — corrupt a fact in a correct
answer, show the score not moving.
