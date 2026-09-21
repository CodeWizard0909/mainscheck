# Corpus provenance

Stated plainly, because a benchmark about honest evaluation cannot be vague about
where its own data came from.

## Questions

| Source | Questions | Provenance |
| --- | --- | --- |
| UPSC Mains 2023 | `gs2-2023-q1` to `q3`, `gs3-2023-q1` to `q3`, `essay-2023-a2`, `b3`, `b4` | Wording taken from published reproductions of the 2023 papers (GS2 16-09-2023, GS3 17-09-2023, Essay 15-09-2023). Directive words preserved verbatim, since comprehension is a scored criterion. |
| Author-written | `gs2-authored-q1` | Written in UPSC style for this corpus. **Not** from any published paper, and labelled as such so it is never cited as one. |

Sources checked for the 2023 wording:
[GS2](https://www.clearias.com/gs-paper-2-upsc-2023-mains-question-paper-and-analysis/) ·
[GS3](https://www.clearias.com/gs-paper-3-upsc-2023-mains-question-paper-and-analysis/) ·
[Essay](https://www.clearias.com/essay-paper-upsc-2023-mains-question-paper-and-analysis/)

## Answers

**All 30 answers were drafted by a large language model and reviewed by the author.
None was written by a UPSC aspirant, and none was written under examination
conditions.**

This is the corpus's most serious limitation and it is deliberate that you read it
first. An LLM-written corpus graded by an LLM has a circularity problem: the answers
may exhibit precisely the features an LLM grader rewards, for reasons that have
nothing to do with what a human examiner would value.

What this does and does not undermine:

- **Self-consistency is unaffected.** Whether a grader returns the same score twice for
  identical text does not depend on who wrote the text.
- **Perturbation sensitivity is largely unaffected.** Deleting a fact from an answer
  makes it worse regardless of the author.
- **Monotonicity is affected.** The `strong` / `middling` / `weak` labels encode the
  author's judgement of quality, not an examiner's. A grader that agrees with those
  labels has agreed with the author, which is a weaker claim than it looks.

The labels were assigned by deliberate construction rather than after the fact: weak
answers were written with padding, assertion without evidence and generic conclusions;
middling answers with correct content and thin analysis; strong answers with a
position defended against a counter-argument.

## Facts

Every `{{f:correct|corrupted}}` marker pairs a real fact with a plausible wrong twin,
usually a shifted year or an adjacent Act, Article or case name. The corrupted forms
exist only for the `corrupt_fact` perturbation and are never shown to a grader as
though true.

Marked facts were checked at the time of writing. Any error in a marked "correct" fact
is a corpus bug, not an intentional distractor — report it.

## What was not used

No coaching-institute answer copies were copied, quoted or redistributed. Published
toppers' copies were read for calibration of tone and length only. No scraped material
of any kind is in this repository.
