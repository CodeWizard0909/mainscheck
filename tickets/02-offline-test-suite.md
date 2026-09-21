# 02: Offline test suite

**What to build:** A test suite that runs with no API key and no network, covering corpus parsing, all six perturbations, and the metrics maths.

This exists because of one specific failure mode: a perturbation that silently no-ops would make the benchmark report a clean, confident result for entirely the wrong reason. A benchmark whose own instrument is untested has no standing to measure anything else.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Fact-marker parsing is tested, including markers spanning a line break and answers with no markers
- [ ] Each of the six perturbations has a test asserting it changes what it should and leaves the rest alone
- [ ] The control perturbation is tested to assert it changes wording only and no claims
- [ ] Perturbations that cannot apply (too few paragraphs, no facts) return nothing rather than raising
- [ ] Metrics are tested against hand-computed fixtures: known spread, known effect size, known rank inversions
- [ ] Monotonicity is tested on a deliberately inverted set to confirm it reports the inversion
- [ ] The whole suite runs in under ten seconds with no API key present
