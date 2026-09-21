# 02: Offline test suite

**What to build:** A test suite that runs with no API key and no network, covering corpus parsing, all six perturbations, and the metrics maths.

This exists because of one specific failure mode: a perturbation that silently no-ops would make the benchmark report a clean, confident result for entirely the wrong reason. A benchmark whose own instrument is untested has no standing to measure anything else.

**Blocked by:** None (can start immediately)

**Status:** ready-for-human

- [x] Fact-marker parsing is tested, including markers spanning a line break and answers with no markers
- [x] Each of the six perturbations has a test asserting it changes what it should and leaves the rest alone
- [x] The control perturbation is tested to assert it changes wording only and no claims
- [x] Perturbations that cannot apply (too few paragraphs, no facts) return nothing rather than raising
- [x] Metrics are tested against hand-computed fixtures: known spread, known effect size, known rank inversions
- [x] Monotonicity is tested on a deliberately inverted set to confirm it reports the inversion
- [x] The whole suite runs in under ten seconds with no API key present

## Comments

31 tests, 1.3 seconds, no API key. Two agreed seams: `apply_all` / `find_no_ops` over
an `Answer`, and the four metric functions over `list[Grading]`.

**Not strictly TDD**, and worth being honest about. The code already existed, so most
of these are characterization tests confirming current behaviour rather than driving
new behaviour. One genuine red-green cycle occurred, below.

**Bug found: the control introduced a capitalisation error.** Matching is
case-insensitive, so "However" at the start of a sentence was rewritten to lowercase
"nevertheless". A grader could reasonably penalise that as a language error, which
would make the control register an effect that is really a defect in the control —
the same class of failure that got the `yet` substitution removed. Substitution now
preserves the original word's case. Control drift on the stub run is 0.0033.

Expected values in the metrics tests are hand-worked literals, never recomputed with
the code under test. `test_a_control_that_moves_the_score_fails` is the one to keep
sacred: it asserts the harness notices a drifting control, and every other number the
benchmark reports depends on that check working.

Status is `ready-for-human`: the suite is complete for the two agreed seams, but a
third seam (corpus loading, malformed front matter) was deliberately excluded and may
be worth revisiting once the corpus grows in ticket 03.
