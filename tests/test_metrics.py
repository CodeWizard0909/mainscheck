"""Seam: the metric functions over a list of Grading.

Every expected value here is worked out by hand and written as a literal. None of it
is recomputed using the code under test.
"""

from __future__ import annotations

from mainscheck.graders.base import Grading
from mainscheck.metrics import (
    bias,
    consistency,
    consistency_by_temperature,
    effect_by_quality,
    monotonicity,
    sensitivity,
)

CRITERIA = ("comprehension", "structure")


def grading(answer_id: str, scores: dict, *, variant="original", run=0, temp=0.0):
    return Grading(
        answer_id=answer_id,
        question_id="q1",
        variant=variant,
        run_index=run,
        model="m",
        rubric_id="structured",
        temperature=temp,
        scores=scores,
        input_tokens=100,
        output_tokens=50,
        latency_s=1.0,
    )


# --- consistency -------------------------------------------------------------


def test_a_grader_that_never_varies_reports_zero_spread():
    runs = [grading("a", {"comprehension": 7.0, "structure": 6.0}, run=i)
            for i in range(3)]

    result = consistency(runs)

    assert result.max_spread == 0.0
    assert result.per_criterion_sd["comprehension"] == 0.0


def test_spread_is_the_gap_between_the_highest_and_lowest_overall():
    # overalls by hand: (4+4)/2 = 4.0, (6+6)/2 = 6.0, (9+9)/2 = 9.0 -> spread 5.0
    runs = [
        grading("a", {"comprehension": 4.0, "structure": 4.0}, run=0),
        grading("a", {"comprehension": 6.0, "structure": 6.0}, run=1),
        grading("a", {"comprehension": 9.0, "structure": 9.0}, run=2),
    ]

    assert consistency(runs).max_spread == 5.0


def test_the_worst_criterion_is_the_one_that_wanders_most():
    # comprehension is rock steady at 5; structure swings 2 / 8 -> population SD 3.0
    runs = [
        grading("a", {"comprehension": 5.0, "structure": 2.0}, run=0),
        grading("a", {"comprehension": 5.0, "structure": 8.0}, run=1),
    ]

    result = consistency(runs)

    assert result.worst_criterion == "structure"
    assert result.worst_sd == 3.0
    assert result.per_criterion_sd["comprehension"] == 0.0


def test_a_single_run_cannot_measure_consistency():
    result = consistency([grading("a", {"comprehension": 7.0, "structure": 7.0})])

    assert result.max_spread == 0.0
    assert result.per_criterion_sd == {}


def test_consistency_never_blends_two_temperatures():
    """A model deterministic at each temperature must not look unstable.

    Every run here agrees with the others at its own temperature. Grouping by answer
    alone would compare 4.0 against 8.0 and report a spread of 4.0 - instability the
    model does not have.
    """
    runs = [
        grading("a", {"comprehension": 4.0, "structure": 4.0}, run=0, temp=0.0),
        grading("a", {"comprehension": 4.0, "structure": 4.0}, run=1, temp=0.0),
        grading("a", {"comprehension": 8.0, "structure": 8.0}, run=0, temp=0.7),
        grading("a", {"comprehension": 8.0, "structure": 8.0}, run=1, temp=0.7),
    ]

    result = consistency(runs)

    assert result.max_spread == 0.0
    assert result.deterministic == 2, "one group per temperature, both deterministic"
    assert result.answers == 2


def test_consistency_counts_answers_that_agree_across_repeats():
    runs = [
        grading("steady", {"comprehension": 7.0, "structure": 7.0}, run=0),
        grading("steady", {"comprehension": 7.0, "structure": 7.0}, run=1),
        grading("wobbly", {"comprehension": 5.0, "structure": 5.0}, run=0),
        grading("wobbly", {"comprehension": 8.0, "structure": 8.0}, run=1),
    ]

    result = consistency(runs)

    assert result.deterministic == 1
    assert result.answers == 2
    assert result.max_spread == 3.0
    assert result.mean_spread == 1.5


def test_per_temperature_split_reports_each_separately():
    runs = [
        grading("a", {"comprehension": 6.0, "structure": 6.0}, run=0, temp=0.0),
        grading("a", {"comprehension": 6.0, "structure": 6.0}, run=1, temp=0.0),
        grading("a", {"comprehension": 5.0, "structure": 5.0}, run=0, temp=0.7),
        grading("a", {"comprehension": 9.0, "structure": 9.0}, run=1, temp=0.7),
    ]

    split = consistency_by_temperature(runs)

    assert split[0.0].max_spread == 0.0
    assert split[0.7].max_spread == 4.0


# --- effect by quality band ------------------------------------------------


LABELS = {"w1": "weak", "w2": "weak", "s1": "strong", "s2": "strong"}


def test_a_control_flat_on_strong_answers_but_not_weak_is_reported_per_band():
    """The aggregate would pass a 0.2 gate while hiding the entire finding."""
    runs = [
        # weak answers: rewording lifts them
        grading("w1", {"comprehension": 3.0, "structure": 3.0}),
        grading("w1", {"comprehension": 5.0, "structure": 5.0}, variant="synonym_rewrite"),
        grading("w2", {"comprehension": 4.0, "structure": 4.0}),
        grading("w2", {"comprehension": 4.0, "structure": 4.0}, variant="synonym_rewrite"),
        # strong answers: exactly flat
        grading("s1", {"comprehension": 9.0, "structure": 9.0}),
        grading("s1", {"comprehension": 9.0, "structure": 9.0}, variant="synonym_rewrite"),
        grading("s2", {"comprehension": 8.0, "structure": 8.0}),
        grading("s2", {"comprehension": 8.0, "structure": 8.0}, variant="synonym_rewrite"),
    ]

    banded = effect_by_quality(runs, LABELS, "synonym_rewrite")

    assert banded.per_band["weak"] == 1.0  # (+2.0 and 0.0) / 2
    assert banded.per_band["strong"] == 0.0
    assert banded.max_per_band["weak"] == 2.0
    assert banded.counts == {"weak": 2, "strong": 2}
    assert banded.worst_band == "weak"

    # The aggregate the gate would have seen: (2 + 0 + 0 + 0) / 4 = 0.5
    aggregate = sensitivity(runs, {"synonym_rewrite": 0}).control_drift
    assert aggregate == 0.5
    assert banded.per_band["weak"] > aggregate, "the band is worse than the average"


def test_banded_effect_can_be_pinned_to_one_temperature():
    runs = [
        grading("w1", {"comprehension": 3.0, "structure": 3.0}, temp=0.0),
        grading("w1", {"comprehension": 6.0, "structure": 6.0}, variant="synonym_rewrite", temp=0.0),
        grading("w1", {"comprehension": 9.0, "structure": 9.0}, temp=0.7),
    ]

    banded = effect_by_quality(runs, LABELS, "synonym_rewrite", temperature=0.0)

    assert banded.per_band["weak"] == 3.0, "the 0.7 baseline must not be averaged in"


# --- sensitivity -------------------------------------------------------------


def test_a_perturbation_that_lowers_the_score_reports_a_negative_delta():
    # baseline overall 8.0; perturbed overall 5.0 -> delta -3.0
    runs = [
        grading("a", {"comprehension": 8.0, "structure": 8.0}),
        grading("a", {"comprehension": 5.0, "structure": 5.0}, variant="delete_fact"),
    ]

    result = sensitivity(runs, {"delete_fact": -1})

    assert result.per_perturbation["delete_fact"] == -3.0
    assert result.passed("delete_fact") is True


def test_a_perturbation_that_moves_the_wrong_way_fails():
    runs = [
        grading("a", {"comprehension": 5.0, "structure": 5.0}),
        grading("a", {"comprehension": 8.0, "structure": 8.0}, variant="delete_fact"),
    ]

    result = sensitivity(runs, {"delete_fact": -1})

    assert result.per_perturbation["delete_fact"] == 3.0
    assert result.passed("delete_fact") is False, "deleting a fact must not raise a score"


def test_a_flat_control_passes_and_reports_no_drift():
    runs = [
        grading("a", {"comprehension": 7.0, "structure": 7.0}),
        grading("a", {"comprehension": 7.0, "structure": 7.0},
                variant="synonym_rewrite"),
    ]

    result = sensitivity(runs, {"synonym_rewrite": 0})

    assert result.control_drift == 0.0
    assert result.passed("synonym_rewrite") is True


def test_a_control_that_moves_the_score_fails():
    """The whole benchmark rests on this: a drifting control invalidates the rest."""
    runs = [
        grading("a", {"comprehension": 7.0, "structure": 7.0}),
        grading("a", {"comprehension": 8.0, "structure": 8.0},
                variant="synonym_rewrite"),
    ]

    result = sensitivity(runs, {"synonym_rewrite": 0})

    assert result.control_drift == 1.0
    assert result.passed("synonym_rewrite") is False


# --- monotonicity ------------------------------------------------------------


def test_correctly_ordered_answers_give_perfect_rank_correlation():
    runs = [
        grading("weak_one", {"comprehension": 3.0, "structure": 3.0}),
        grading("mid_one", {"comprehension": 6.0, "structure": 6.0}),
        grading("strong_one", {"comprehension": 9.0, "structure": 9.0}),
    ]
    labels = {"weak_one": "weak", "mid_one": "middling", "strong_one": "strong"}

    result = monotonicity(runs, labels)

    assert result.spearman_rho == 1.0
    assert result.inversion_rate == 0.0


def test_a_deliberately_inverted_set_is_reported_as_inverted():
    """Strong scored lowest, weak highest: every pair is the wrong way round."""
    runs = [
        grading("weak_one", {"comprehension": 9.0, "structure": 9.0}),
        grading("mid_one", {"comprehension": 6.0, "structure": 6.0}),
        grading("strong_one", {"comprehension": 3.0, "structure": 3.0}),
    ]
    labels = {"weak_one": "weak", "mid_one": "middling", "strong_one": "strong"}

    result = monotonicity(runs, labels)

    assert result.spearman_rho == -1.0
    assert result.inversion_rate == 1.0


def test_one_swapped_pair_out_of_three_is_a_third_inverted():
    # strong 5.0 < middling 6.0 is wrong; the other two pairs are right.
    runs = [
        grading("weak_one", {"comprehension": 3.0, "structure": 3.0}),
        grading("mid_one", {"comprehension": 6.0, "structure": 6.0}),
        grading("strong_one", {"comprehension": 5.0, "structure": 5.0}),
    ]
    labels = {"weak_one": "weak", "mid_one": "middling", "strong_one": "strong"}

    assert monotonicity(runs, labels).inversion_rate == 1 / 3


# --- bias --------------------------------------------------------------------


def test_padding_that_raises_the_score_is_reported_as_length_bias():
    # +2.0 overall for 200 added characters -> +1.0 per 100
    runs = [
        grading("a", {"comprehension": 5.0, "structure": 5.0}),
        grading("a", {"comprehension": 7.0, "structure": 7.0},
                variant="pad_verbosity"),
    ]
    lengths = {("a", "original"): 400, ("a", "pad_verbosity"): 600}

    assert bias(runs, lengths).length_bias == 1.0


def test_padding_that_changes_nothing_shows_no_length_bias():
    runs = [
        grading("a", {"comprehension": 5.0, "structure": 5.0}),
        grading("a", {"comprehension": 5.0, "structure": 5.0},
                variant="pad_verbosity"),
    ]
    lengths = {("a", "original"): 400, ("a", "pad_verbosity"): 600}

    assert bias(runs, lengths).length_bias == 0.0
