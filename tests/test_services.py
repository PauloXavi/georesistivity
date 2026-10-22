"""Tests for the application use cases, without any interface."""

import pytest

from georesistivity import MeasurementWarning
from georesistivity.services import FieldIssue, MeasurementInput, evaluate_submission


def make_input(
    delta_v: str = "125",
    current: str = "35",
    geometric_factor: str = "625",
    *,
    spacing: str = "",
    source: str = "",
) -> MeasurementInput:
    return MeasurementInput(
        delta_v=delta_v,
        voltage_unit="mV",
        current=current,
        current_unit="mA",
        geometric_factor=geometric_factor,
        geometric_factor_unit="m",
        spacing_ab2=spacing,
        spacing_unit="m",
        geometric_factor_source=source,
    )


def test_valid_input_is_accepted() -> None:
    outcome = evaluate_submission(make_input(spacing="20", source=" table "), [])

    assert outcome.accepted
    assert outcome.result is not None
    assert outcome.result.apparent_resistivity_ohm_m == pytest.approx(2232.142857142857)
    assert outcome.result.spacing_ab2_m == 20.0
    assert outcome.result.measurement.geometric_factor_source == "table"
    assert outcome.field_issues == ()
    assert outcome.error is None
    assert outcome.duplicate_of is None


def test_blank_spacing_and_source_are_omitted() -> None:
    outcome = evaluate_submission(make_input(spacing="   ", source="  "), [])

    assert outcome.result is not None
    assert outcome.result.measurement.spacing_ab2_original is None
    assert outcome.result.measurement.spacing_unit is None
    assert outcome.result.measurement.geometric_factor_source is None


def test_every_invalid_field_is_reported_in_form_order() -> None:
    outcome = evaluate_submission(make_input("abc", "", "1,000", spacing="1_0"), [])

    assert not outcome.accepted
    assert [issue.field for issue in outcome.field_issues] == [
        "delta_v",
        "current",
        "geometric_factor",
        "spacing_ab2",
    ]
    assert "ambiguous" in outcome.field_issues[2].message


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        (make_input(current="0"), FieldIssue("current", "cannot be zero")),
        (make_input(geometric_factor="-625"), FieldIssue("geometric_factor", "must be positive")),
        (make_input(spacing="0"), FieldIssue("spacing_ab2", "must be positive")),
    ],
)
def test_calculation_problems_are_attributed_to_fields(
    entry: MeasurementInput,
    expected: FieldIssue,
) -> None:
    assert evaluate_submission(entry, []).field_issues == (expected,)


def test_unattributable_calculation_error_is_reported_as_general_error() -> None:
    entry = MeasurementInput(
        delta_v="1e306",
        voltage_unit="V",
        current="1e-306",
        current_unit="A",
        geometric_factor="5",
        geometric_factor_unit="m",
    )

    outcome = evaluate_submission(entry, [])

    assert not outcome.accepted
    assert outcome.field_issues == ()
    assert outcome.error is not None
    assert "result must be finite" in outcome.error


def test_identical_consecutive_measurement_is_flagged_as_duplicate() -> None:
    first = evaluate_submission(make_input(), [])
    assert first.result is not None

    second = evaluate_submission(make_input(), [first.result])

    assert second.accepted
    assert second.duplicate_of == 1


def test_only_the_previous_measurement_counts_as_duplicate() -> None:
    first = evaluate_submission(make_input(), [])
    other = evaluate_submission(make_input(delta_v="100"), [])
    assert first.result is not None
    assert other.result is not None

    outcome = evaluate_submission(make_input(), [first.result, other.result])

    assert outcome.duplicate_of is None


def test_negative_rho_a_is_accepted_with_its_warning() -> None:
    outcome = evaluate_submission(make_input(delta_v="-125"), [])

    assert outcome.result is not None
    assert outcome.result.warnings == (MeasurementWarning.NEGATIVE_APPARENT_RESISTIVITY,)


def test_previous_results_are_not_modified() -> None:
    first = evaluate_submission(make_input(), [])
    assert first.result is not None
    previous = [first.result]

    evaluate_submission(make_input(delta_v="100"), previous)

    assert previous == [first.result]
