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

**Status:** ready-for-agent

- [ ] Two local model sizes × two rubrics run over the full corpus on identical inputs
- [ ] Wall-clock extrapolated from a subset run before the full sweep is launched
- [ ] Mean latency and mean tokens per evaluation reported for every configuration
- [ ] Peak memory noted per model, so a reader knows what hardware reproduces this
- [ ] Structured rubric's margin over the naive baseline stated as a number
- [ ] Routing argument produces a blended latency and a percentage saving, assumptions written out
- [ ] A reliability-versus-cost comparison exists showing the frontier across model sizes
- [ ] If any hosted model is run for contrast, `config/pricing.yaml` carries a dated rate for it; otherwise the cost column stays blank rather than showing an unverified number
