# 01: Tracer bullet — one answer graded end to end

**What to build:** A single UPSC Mains answer goes in, a real grading call comes back, and a report page opens showing an actual number. This proves the whole path — corpus parsing, perturbation, grading, caching, metrics, report — works before any bulk work is committed to it.

Deliberately tiny. Three answers at most, few repeats, one configuration. The point is to see the pipeline produce a real result, not to produce a meaningful result.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] `ANTHROPIC_API_KEY` set and a live grading call succeeds against the structured rubric
- [ ] Two more answers exist for the same question, one `middling` and one `weak`, so a spread is visible
- [ ] A run with `--limit 3 --repeats 3` completes and writes a results JSON
- [ ] The report builds and opens, showing consistency and cost columns with real values
- [ ] Re-running the same command is near-instant and shows cache hits, confirming the cache works
- [ ] Token counts and latency are non-zero on every stored grading
