# 04: Reliability metrics

**What to build:** The four reliability measurements over the full corpus, reported per configuration: self-consistency, perturbation sensitivity, rank monotonicity, and length and position bias.

Two gates live in this ticket, and they are the reason it is one ticket rather than four.

**The control gate.** If `synonym_rewrite` — which changes wording only — moves overall scores by more than 0.2 points, the harness is measuring sampling noise rather than answer quality. That result is reported on the front page of the report, not buried or worked around.

**The day-9 decision.** Once self-consistency is measured, inspect the spread before going further. If the grader is already highly stable, there is no reliability story, and the headline pivots to the cost-and-latency frontier instead. Making this call here is the whole point; discovering it in the final week is the failure mode this ticket exists to prevent.

**Blocked by:** 02, 03

**Status:** ready-for-human

- [x] Self-consistency run: every answer graded five times at temperature 0 and at 0.7
- [x] Standard deviation reported per criterion, plus the largest spread seen on any single answer
- [x] Sensitivity reported as mean score change per perturbation, with effect sizes
- [x] `corrupt_fact` penalised at least as heavily as `delete_fact`, or the discrepancy is written up
- [x] Planted factual errors land on the factual-accuracy criterion, not spread across all four
- [x] Monotonicity reported as Spearman's rho and pairwise inversion rate against quality labels
- [x] Length bias reported from the padding perturbation; position bias from batch order
- [x] Control gate evaluated and its verdict stated explicitly in the report
- [x] Day-9 decision recorded in writing: reliability headline, or pivot to economics

## Comments

**Observation from ticket 01, not a change to the ask above.** `consistency` currently
groups every original grading for an answer together regardless of temperature, so the
reported spread blends sampling noise at one temperature with the difference between
temperature settings. Those are two different things and a headline number should not
mix them. Worth deciding here whether to report per-temperature or keep the blend and
label it.

This got more pressing with the move to local grading. The current hosted models
reject sampling parameters, so the two temperature groups would have been identical
requests and the blend would have been harmless. Ollama accepts them, so the blend now
mixes two genuinely different quantities, and collapsing them into one number would
hide the more interesting of the two.

**Resolved: report per temperature.** `consistency` now groups by (answer,
temperature) so a spread can never straddle two settings, and
`consistency_by_temperature` reports each separately. The blended figure had claimed
"varies by up to 3.0 points" for a grader that is deterministic on 27 of 30 answers.

## Results — llama3.2:3b, structured rubric, 480 gradings

**Consistency**

| Temperature | Mean spread | Worst | Identical across 5 repeats |
| --- | --- | --- | --- |
| 0.0 | 0.09 | 1.25 | 27/30 |
| 0.7 | 0.88 | 2.75 | 1/30 |

**Quality separation is good.** weak 5.83, middling 7.59, strong 8.50, with 1 inversion
in 30 within-question pairs. The grader can tell a bad answer from a good one.

**Sensitivity is the finding: it cannot tell a true fact from a false one.**

| Perturbation | Mean effect | No change at all |
| --- | --- | --- |
| `corrupt_fact` | −0.04 | 26/30 |
| `delete_fact` | **+0.09** | 20/30 |
| `scramble_structure` | −0.07 | 21/30 |
| `pad_verbosity` | −0.05 | 18/30 |
| `remove_conclusion` | −0.25 | 16/30 |

Every median is exactly 0.000.

**`corrupt_fact` vs `delete_fact`, as the criterion above asks.** Corruption should be
punished harder than omission; it is not. Corruption moves the overall score −0.04
while deletion moves it **+0.09 — the wrong direction entirely.** Deleting a true fact
made answers score marginally better. Neither effect is meaningfully distinguishable
from zero, which is the real point: the grader is not reading the facts.

**Attribution is weakly correct.** Narrowed to the `factual_accuracy` criterion alone,
`corrupt_fact` moves −0.18 and `delete_fact` −0.11, both larger than their effect on
the overall score. So the penalty, such as it is, does land on the right criterion —
it is simply far too small to matter, and absent entirely on 25 of 30 answers.

**The control fails, and only in one band.**

| Band | Mean | Largest |
| --- | --- | --- |
| weak | **+0.54** | +2.00 |
| middling | −0.07 | +0.50 |
| strong | **0.00** | 0.00 |

Aggregate drift is +0.158, which *passes* the 0.2 gate. The failure is invisible until
split by quality. `effect_by_quality` now does that split, and the CLI prints the
failing bands in red.

**Headline:** a weak answer gains more from being reworded (+0.54) than it loses from
having its facts corrupted (−0.18). Measured on the same answers in the same run.

**Day-9 decision: reliability is the headline, not economics.** The original fallback
was to pivot to cost if the grader turned out to be stable and uninteresting. It is
stable — and that made the result sharper rather than duller, because a deterministic
grader means the control drift cannot be dismissed as sampling noise.

**Caveats for whoever writes this up.** One model, one rubric, ten answers per quality
band. The +0.54 has a maximum of +2.00, so a few answers carry it. The corpus is
LLM-drafted (`corpus/PROVENANCE.md`). None of this describes a commercial grader.
