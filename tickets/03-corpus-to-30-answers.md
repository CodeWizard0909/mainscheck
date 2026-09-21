# 03: Corpus to 30 answers

**What to build:** A corpus of 30 self-authored UPSC Mains answers across GS2, GS3 and Essay, at three deliberate quality levels, all passing validation.

This is the project's reusable asset and its largest single block of work. The format is already proven by ticket 01, so this is filling in a known shape rather than designing one.

Answers are written against public previous-year questions. Coaching-institute answer copies may be read for calibration but never copied or redistributed. If any answer is LLM-drafted and then edited by hand, that fact is recorded now so the README can disclose it later — an LLM-written corpus graded by an LLM is a real limitation, and it must be stated rather than discovered.

**Blocked by:** 01 (tracer bullet proves the format before 29 more are written against it)

**Status:** ready-for-human

- [x] 30 answers committed, spread across GS2, GS3 and Essay
- [x] Roughly balanced across `strong`, `middling` and `weak` — exactly 10 each
- [x] Every answer carries at least three inline fact markers with plausible corrupted twins
- [x] Every answer has at least three paragraphs so structural perturbations apply
- [x] Every question referenced exists in `questions.yaml`, quoted verbatim including its directive word
- [x] `validate` passes on the whole corpus with no warnings
- [x] Drafting method recorded — see `corpus/PROVENANCE.md`

## Comments

Ten questions, three quality levels each. Nine questions are verbatim from UPSC Mains
2023; one is author-written and labelled `gs2-authored-q1` so it can never be cited as
a real paper. The earlier `gs2-2023-q5` id was retired for exactly that reason — it was
an invented question wearing a real paper's label, which is fabricated provenance in a
project about honest evaluation.

Holding the question constant across all three quality levels is deliberate: it
controls for question difficulty, so a score difference is attributable to answer
quality rather than to topic.

**The corpus is LLM-drafted and author-reviewed, all 30 answers.** That is disclosed in
`corpus/PROVENANCE.md` and in the README limitations, with an explicit account of which
results it undermines (monotonicity) and which it does not (self-consistency,
perturbation sensitivity). **This is the finding most likely to be attacked by a
reviewer, and the right response is that it was stated first rather than discovered.**

**Open item for a human.** A stub run across all 30 answers ranks `middling` (5.30)
marginally above `strong` (5.26). That is a stub limitation — it counts paragraphs and
date-like tokens, and strong answers signal quality through argument rather than
through countable features — so it says nothing about whether the corpus is genuinely
well-ordered. **Monotonicity is untested until a real model runs in ticket 04.** The
answers were deliberately not tuned to satisfy the stub; fitting a corpus to a fake
grader is the practice this benchmark exists to expose.

The single highest-value revision available is for a real UPSC aspirant to rewrite or
grade these answers. That would remove the circularity problem entirely and is worth
more than any further engineering.
