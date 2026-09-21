# 04: Reliability metrics

**What to build:** The four reliability measurements over the full corpus, reported per configuration: self-consistency, perturbation sensitivity, rank monotonicity, and length and position bias.

Two gates live in this ticket, and they are the reason it is one ticket rather than four.

**The control gate.** If `synonym_rewrite` — which changes wording only — moves overall scores by more than 0.2 points, the harness is measuring sampling noise rather than answer quality. That result is reported on the front page of the report, not buried or worked around.

**The day-9 decision.** Once self-consistency is measured, inspect the spread before going further. If the grader is already highly stable, there is no reliability story, and the headline pivots to the cost-and-latency frontier instead. Making this call here is the whole point; discovering it in the final week is the failure mode this ticket exists to prevent.

**Blocked by:** 02, 03

**Status:** ready-for-agent

- [ ] Self-consistency run: every answer graded five times at temperature 0 and at 0.7
- [ ] Standard deviation reported per criterion, plus the largest spread seen on any single answer
- [ ] Sensitivity reported as mean score change per perturbation, with effect sizes
- [ ] `corrupt_fact` penalised at least as heavily as `delete_fact`, or the discrepancy is written up
- [ ] Planted factual errors land on the factual-accuracy criterion, not spread across all four
- [ ] Monotonicity reported as Spearman's rho and pairwise inversion rate against quality labels
- [ ] Length bias reported from the padding perturbation; position bias from batch order
- [ ] Control gate evaluated and its verdict stated explicitly in the report
- [ ] Day-9 decision recorded in writing: reliability headline, or pivot to economics

## Comments

**Observation from ticket 01, not a change to the ask above.** `consistency` currently
groups every original grading for an answer together regardless of temperature, so the
reported spread blends sampling noise at one temperature with the difference between
temperature settings. Those are two different things and a headline number should not
mix them. Worth deciding here whether to report per-temperature or keep the blend and
label it.
