# 05: Configuration matrix and economics

**What to build:** The same corpus graded by three models crossed with two rubrics, and the cost of each configuration reported beside its reliability.

The comparison that matters is the structured rubric against the naive "score this out of 10" baseline. If structured grading does not beat naive grading on consistency, that is the finding and it gets published as such.

The economics half answers a question the reliability half cannot: what does a trustworthy evaluation actually cost? At a fixed price per student for a full exam cycle with unlimited practice, margin is determined by tokens. The routing model estimates the saving from sending structure checks to a small model while factual accuracy and Essay stay on a large one.

Spend is a real risk here. Run the matrix on a small subset first and extrapolate before committing to the full run.

**Blocked by:** 04

**Status:** ready-for-agent

- [ ] Three models × two rubrics run over the full corpus on identical inputs
- [ ] Cost extrapolated from a subset run and checked before the full matrix is launched
- [ ] `config/pricing.yaml` filled from current published rates, with the date checked recorded
- [ ] Cost per evaluation and per thousand evaluations reported for every configuration
- [ ] Mean latency reported per configuration
- [ ] Structured rubric's margin over the naive baseline stated as a number
- [ ] Routing model produces a blended cost and a percentage saving, with its assumptions written out
- [ ] A cost-versus-reliability comparison exists showing the frontier across configurations
