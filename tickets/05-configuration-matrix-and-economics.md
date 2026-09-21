# 05: Configuration matrix and economics

**What to build:** The same corpus graded by three models crossed with two rubrics, and the cost of each configuration reported beside its reliability.

The comparison that matters is the structured rubric against the naive "score this out of 10" baseline. If structured grading does not beat naive grading on consistency, that is the finding and it gets published as such.

The economics half answers a question the reliability half cannot: what does a trustworthy evaluation actually cost to run?

**Cost here means compute, not dollars.** Grading runs on locally hosted models, so there is no per-call price. The measure is tokens and wall-clock latency per evaluation, and the practical question becomes what a team could self-host: a product that can grade acceptably on a 3B model running on its own hardware has a completely different margin from one paying per call at scale. The routing argument survives intact — send structure checks to the smallest model that stays reliable, reserve the larger one for factual accuracy and Essay — but it is measured in seconds and tokens rather than in currency.

**Two model sizes, not three.** Originally three — a 3B, a 7B and a 9B — so the frontier being drawn was reliability against model size. Revised down after measuring the real per-grading cost on the target hardware: a 7B is roughly 2.2× slower than a 3B on CPU with no usable GPU acceleration, which put the six-configuration sweep at about sixteen hours.

Two sizes answer the question that matters: is fact-insensitivity a property of small models in general, or of this particular model? A third size refines a curve that two points have not yet established. If the 3B and the 7B disagree in an interesting way, a third earns its nine hours and can be added then.

Sizes are local models, not vendors, so the axis stays model capacity rather than provider.

The risk here is time rather than money. A configuration takes hours on CPU, so run a small subset first and extrapolate the wall-clock before committing a night to it. Responses cache by content hash, so an interrupted run resumes without repeating work.

**Blocked by:** 04

**Status:** ready-for-human

- [x] Two local model sizes × two rubrics run over the full corpus on identical inputs
- [x] Wall-clock extrapolated from a subset run before the full sweep is launched
- [x] Mean latency and mean tokens per evaluation reported for every configuration
- [ ] Peak memory noted per model, so a reader knows what hardware reproduces this
- [x] Structured rubric's margin over the naive baseline stated as a number
- [x] Routing argument produces a blended latency and a percentage saving, assumptions written out
- [x] A reliability-versus-cost comparison exists showing the frontier across model sizes
- [x] If any hosted model is run for contrast, `config/pricing.yaml` carries a dated rate for it; otherwise the cost column stays blank rather than showing an unverified number

Peak memory is **not** measured and stays unticked. Model sizes on disk (2.0 GB and
4.7 GB) are a proxy, not a measurement, and should not be published as one. Anyone
reproducing this on constrained hardware needs the real number.

## Results — 4 configurations, 1,920 gradings

| | 3B naive | 3B structured | 7B naive | 7B structured |
| --- | --- | --- | --- | --- |
| Control drift, weak band | **+0.30** | **+0.54** | flat | flat |
| Mean spread, t=0 | 0.03 | 0.09 | 0.03 | 0.02 |
| Mean spread, t=0.7 | 0.77 | 0.88 | **0.27** | 0.53 |
| Deterministic at t=0.7 | 10/30 | 1/30 | **22/30** | 6/30 |
| `corrupt_fact` | −0.007 | −0.042 | −0.007 | +0.000 |
| `corrupt_fact` unchanged on | 29/30 | 26/30 | 28/30 | 26/30 |
| Quality separation | 3.80 → 8.32 | 5.83 → 8.50 | 5.10 → 7.60 | 6.38 → 8.72 |
| Mean latency | 12.9 s | 26.5 s | 26.6 s | 47.9 s |
| Mean tokens in/out | 338 / 51 | 553 / 90 | 347 / 47 | 563 / 91 |

### The 2×2 separates on model size, not on rubric

**The control fails on both 3B configurations and passes on both 7B ones.** Rewording a
weak answer lifts its score at 3B under either rubric, and moves nothing at 7B under
either. Capacity fixes this; prompt design does not.

**No configuration detects a corrupted fact.** Swapping a real date or Act for a
plausible wrong one moves the score by at most 0.04 points, and by nothing at all on
26 to 29 answers out of 30, in every cell of the matrix. Across 1,920 gradings, two
model sizes and two rubric designs, not one configuration reads the facts.

**Stylistic judgement scales; factual verification does not.** That is the finding.
Going 3B → 7B buys a grader that stops rewarding polish and starts noticing broken
structure (`scramble_structure` −0.07 → −0.18, `pad_verbosity` −0.05 → −0.15). It does
not buy one that checks whether a claim is true.

### The structured rubric's margin over naive is negative

Measured, as the criterion asks. At 3B the structured rubric is worse on consistency
(0.09 vs 0.03 at t=0; 1/30 vs 10/30 deterministic at t=0.7), worse on control drift
(+0.54 vs +0.30), and costs 2.1× the latency. At 7B it is better at t=0 by 0.01 — noise
— and worse at t=0.7 (0.53 vs 0.27), for 1.8× the latency.

The project's own success criteria said the structured rubric beating naive was "the
argument for structured grading". It loses. Published as such.

One honest confound: naive scores one criterion, structured averages four. Fewer
numbers have fewer chances to disagree. But averaging four independent criteria should
*reduce* variance, so structured being noisier is still meaningful — just not clean.

### The routing argument, in latency

**3B structured costs 26.5 s. 7B naive costs 26.6 s.** At equal compute, the 7B with
the simpler rubric strictly dominates: flat control against +0.54, 22/30 deterministic
at t=0.7 against 1/30, and fewer tokens both ways (347/47 against 553/90).

**Spend compute on model capacity, not on rubric elaboration.** A team currently paying
for long rubric prompts on a small model is buying the worse half of the trade.

Against the most expensive configuration, 7B structured at 47.9 s, dropping to 7B naive
saves **44% of latency** while *improving* sampling robustness (t=0.7 spread 0.27
against 0.53). Assumptions: same corpus, same hardware, concurrency 2, no GPU
acceleration, and quality separation treated as adequate in both — 7B naive compresses
the top of its range (strong 7.60 against 8.72), which matters if fine discrimination
between good answers is the goal.

### Caveats

Two models, one family each. Thirty answers, ten questions, LLM-drafted
(`corpus/PROVENANCE.md`). `corrupt_fact` substitutes a plausible wrong twin, so this
measures tolerance of *believable* falsehood rather than of obvious nonsense. Peak
memory unmeasured. Nothing here describes a commercial grader.
