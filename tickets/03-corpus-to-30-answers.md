# 03: Corpus to 30 answers

**What to build:** A corpus of 30 self-authored UPSC Mains answers across GS2, GS3 and Essay, at three deliberate quality levels, all passing validation.

This is the project's reusable asset and its largest single block of work. The format is already proven by ticket 01, so this is filling in a known shape rather than designing one.

Answers are written against public previous-year questions. Coaching-institute answer copies may be read for calibration but never copied or redistributed. If any answer is LLM-drafted and then edited by hand, that fact is recorded now so the README can disclose it later — an LLM-written corpus graded by an LLM is a real limitation, and it must be stated rather than discovered.

**Blocked by:** 01 (tracer bullet proves the format before 29 more are written against it)

**Status:** ready-for-agent

- [ ] 30 answers committed, spread across GS2, GS3 and Essay
- [ ] Roughly balanced across `strong`, `middling` and `weak`
- [ ] Every answer carries at least three inline fact markers with plausible corrupted twins
- [ ] Every answer has at least three paragraphs so structural perturbations apply
- [ ] Every question referenced exists in `questions.yaml`, quoted verbatim including its directive word
- [ ] `validate` passes on the whole corpus with no warnings
- [ ] Drafting method per answer recorded, for the README's limitations section
