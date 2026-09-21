"""Seam: perturbations applied to an Answer.

Expected values here are hand-written literals, never recomputed with the same
regexes the code uses. A test that rebuilt the expectation the way the implementation
does would pass by construction and could never disagree with it.
"""

from __future__ import annotations

from mainscheck.corpus import Answer
from mainscheck.perturb import apply_all, synonym_rewrite


def answer(body: str, quality: str = "strong") -> Answer:
    return Answer(
        answer_id="t1",
        question_id="q1",
        paper="GS2",
        quality=quality,
        body=body.strip(),
    )


CONTROL_BODY = """
The doctrine is important because it limits amending power under
{{f:Article 368|Article 370}}.

However, many critics argue the Court overreached in {{f:1973|1975}}.

This also shows the tension between the two positions.
"""

# Written out by hand from CONTROL_BODY: every connective and intensifier swapped,
# every fact left exactly as it was.
CONTROL_EXPECTED = (
    "The doctrine is significant since it limits amending power under\n"
    "Article 368.\n"
    "\n"
    "Nevertheless, numerous critics argue the Court overreached in 1973.\n"
    "\n"
    "This additionally demonstrates the tension between the two positions."
)


def test_control_rewrites_wording_and_nothing_else():
    """The control must change how the answer reads, never what it claims."""
    result = synonym_rewrite(answer(CONTROL_BODY))

    assert result is not None
    assert result.text == CONTROL_EXPECTED


def test_control_expects_no_score_change():
    result = synonym_rewrite(answer(CONTROL_BODY))

    assert result.direction == 0


def test_control_preserves_every_fact_it_was_given():
    """Facts are the one thing the control may never touch."""
    result = synonym_rewrite(answer(CONTROL_BODY))

    for fact in ("Article 368", "1973"):
        assert fact in result.text
    for wrong_twin in ("Article 370", "1975"):
        assert wrong_twin not in result.text


def test_control_returns_nothing_when_no_wording_can_change():
    """A control that returns unchanged text would pass while testing nothing."""
    bare = answer(
        "The Court held one thing.\n\nThe Court held another.\n\nSo it goes."
    )

    assert synonym_rewrite(bare) is None


def test_no_op_control_is_absent_from_the_applied_set():
    bare = answer(
        "The Court held one thing.\n\nThe Court held another.\n\nSo it goes."
    )

    names = {p.name for p in apply_all(bare)}

    assert "synonym_rewrite" not in names


# --- facts -------------------------------------------------------------------

FACT_BODY = """
The amending power sits in {{f:Article 368|Article 370}}.

The case was decided in {{f:1973|1981}}.

The doctrine has held since then.
"""


def by_name(a: Answer, name: str):
    for perturbation in apply_all(a):
        if perturbation.name == name:
            return perturbation
    return None


def test_deleting_a_fact_removes_it_and_keeps_the_others():
    result = by_name(answer(FACT_BODY), "delete_fact")

    removed = [f for f in ("Article 368", "1973") if f not in result.text]
    kept = [f for f in ("Article 368", "1973") if f in result.text]

    assert len(removed) == 1, "exactly one fact should go"
    assert len(kept) == 1, "the other should survive untouched"


def test_deleting_a_fact_expects_the_factual_score_to_fall():
    result = by_name(answer(FACT_BODY), "delete_fact")

    assert result.criterion == "factual_accuracy"
    assert result.direction == -1


def test_corrupting_a_fact_swaps_in_the_wrong_twin():
    result = by_name(answer(FACT_BODY), "corrupt_fact")

    swapped = [
        (right, wrong)
        for right, wrong in (("Article 368", "Article 370"), ("1973", "1981"))
        if wrong in result.text and right not in result.text
    ]

    assert len(swapped) == 1


def test_corrupting_keeps_the_answer_the_same_length_in_facts():
    """Corruption replaces; it must not drop information the way deletion does."""
    original = answer(FACT_BODY)
    result = by_name(original, "corrupt_fact")

    assert len(result.text.split()) == len(original.rendered().split())


def test_fact_markers_may_span_a_line_break():
    """Answers are wrapped, so a marker routinely straddles two lines."""
    wrapped = answer(
        "The case is {{f:Kesavananda Bharati v. State of\n"
        "Kerala (1973)|Kesavananda Bharati v. State of Kerala (1967)}} and it binds.\n\n"
        "The Court declined to define the structure.\n\n"
        "That choice has been criticised."
    )

    assert len(wrapped.facts) == 1
    assert "Kesavananda Bharati v. State of\nKerala (1973)" in wrapped.rendered()
    assert "1967" not in wrapped.rendered()


def test_answers_without_markers_yield_no_fact_perturbations():
    names = {
        p.name
        for p in apply_all(
            answer(
                "The Court ruled.\n\nIt was important.\n\nMany accepted the outcome."
            )
        )
    }

    assert "delete_fact" not in names
    assert "corrupt_fact" not in names


# --- structure ---------------------------------------------------------------

STRUCTURE_BODY = """
First, the doctrine limits amending power under {{f:Article 368|Article 370}}.

Second, the Court declined to define the structure exhaustively.

Third, later judgments filled it in.

In conclusion, the Constitution evolved through interpretation.
"""


def test_scrambling_keeps_every_paragraph_but_changes_their_order():
    original = answer(STRUCTURE_BODY)
    result = by_name(original, "scramble_structure")

    before = original.rendered().split("\n\n")
    after = result.text.split("\n\n")

    assert sorted(after) == sorted(before), "no paragraph may be lost or invented"
    assert after != before, "the order must actually change"


def test_removing_the_conclusion_drops_only_the_last_paragraph():
    original = answer(STRUCTURE_BODY)
    result = by_name(original, "remove_conclusion")

    assert "In conclusion, the Constitution evolved through interpretation." not in result.text
    assert "Third, later judgments filled it in." in result.text
    assert len(result.text.split("\n\n")) == len(original.paragraphs) - 1


def test_padding_lengthens_the_answer_without_touching_what_it_says():
    original = answer(STRUCTURE_BODY)
    result = by_name(original, "pad_verbosity")

    assert len(result.text) > len(original.rendered())
    for sentence in original.rendered().split("\n\n"):
        assert sentence in result.text, "original text must survive verbatim"


def test_padding_expects_no_criterion_to_rise():
    result = by_name(answer(STRUCTURE_BODY), "pad_verbosity")

    assert result.direction == 0


def test_structural_perturbations_are_absent_when_there_is_no_structure():
    """Two paragraphs give nothing to scramble or to cut a conclusion from."""
    short = answer("One paragraph here.\n\nAnd a second one.")

    names = {p.name for p in apply_all(short)}

    assert "scramble_structure" not in names
    assert "remove_conclusion" not in names


def test_a_single_paragraph_answer_does_not_raise():
    """Inapplicable perturbations return nothing; they never blow up the run."""
    names = {p.name for p in apply_all(answer("Just the one paragraph."))}

    assert "scramble_structure" not in names
    assert "remove_conclusion" not in names
    assert "delete_fact" not in names


def test_find_no_ops_names_what_did_not_apply():
    from mainscheck.perturb import find_no_ops

    reported = find_no_ops(answer("Just the one paragraph."))

    assert "scramble_structure" in reported
    assert "remove_conclusion" in reported
    assert "delete_fact" in reported
