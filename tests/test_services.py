"""Tests for the application use cases, without any interface."""

import math

import pytest

from georesistivity import MeasurementWarning
from georesistivity.geometry import ArrayType, GeometryParameter
from georesistivity.services import (
    FieldIssue,
    MeasurementInput,
    ParameterIssue,
    calculate_geometric_factor,
    evaluate_submission,
)


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


def schlumberger_input(
    ab2: str = "20",
    mn: str = "2",
    *,
    ab2_unit: str = "m",
    mn_unit: str = "m",
    geometric_factor: str = "",
) -> MeasurementInput:
    return MeasurementInput(
        delta_v="125",
        voltage_unit="mV",
        current="35",
        current_unit="mA",
        geometric_factor=geometric_factor,
        spacing_ab2=ab2,
        spacing_unit=ab2_unit,
        mn=mn,
        mn_unit=mn_unit,
        geometric_factor_mode="schlumberger",
    )


def test_schlumberger_mode_calculates_k_from_ab2_and_mn() -> None:
    outcome = evaluate_submission(schlumberger_input(), [])

    assert outcome.result is not None
    measurement = outcome.result.measurement
    assert measurement.geometric_factor_original == pytest.approx(math.pi * 399.0 / 2.0)
    assert measurement.geometric_factor_unit == "m"
    assert measurement.geometric_factor_source == (
        "calculated: schlumberger (AB/2 = 20 m, MN = 2 m)"
    )
    assert measurement.mn_original == 2.0
    assert outcome.result.mn_m == 2.0
    assert outcome.result.apparent_resistivity_ohm_m == pytest.approx(
        math.pi * 399.0 / 2.0 * 0.125 / 0.035
    )
    assert outcome.result.warnings == ()


def test_schlumberger_mode_converts_units_before_calculating() -> None:
    in_meters = evaluate_submission(schlumberger_input("20", "2"), [])
    mixed = evaluate_submission(schlumberger_input("0,02", "200", ab2_unit="km", mn_unit="cm"), [])

    assert in_meters.result is not None
    assert mixed.result is not None
    assert mixed.result.geometric_factor_m == pytest.approx(in_meters.result.geometric_factor_m)
    assert mixed.result.measurement.geometric_factor_source == (
        "calculated: schlumberger (AB/2 = 0.02 km, MN = 200 cm)"
    )


def test_schlumberger_mode_ignores_typed_k() -> None:
    outcome = evaluate_submission(schlumberger_input(geometric_factor="not a number"), [])

    assert outcome.accepted


@pytest.mark.parametrize(
    ("ab2", "mn", "expected"),
    [
        ("", "2", (FieldIssue("spacing_ab2", "is required to calculate K"),)),
        ("20", "", (FieldIssue("mn", "is required to calculate K"),)),
        ("20", "40", (FieldIssue("mn", "MN/2 must be smaller than AB/2"),)),
        ("20", "0", (FieldIssue("mn", "must be positive"),)),
        ("-20", "2", (FieldIssue("spacing_ab2", "must be positive"),)),
    ],
)
def test_schlumberger_mode_reports_geometry_problems_by_field(
    ab2: str,
    mn: str,
    expected: tuple[FieldIssue, ...],
) -> None:
    assert evaluate_submission(schlumberger_input(ab2, mn), []).field_issues == expected


def test_schlumberger_mode_reports_unit_problems_by_field() -> None:
    outcome = evaluate_submission(schlumberger_input(mn_unit="ft"), [])

    assert [issue.field for issue in outcome.field_issues] == ["mn"]
    assert "unsupported length unit" in outcome.field_issues[0].message


def test_overflowing_calculated_k_is_a_general_error() -> None:
    outcome = evaluate_submission(schlumberger_input("1e300", "1e-300"), [])

    assert outcome.error is not None
    assert "too large" in outcome.error


def test_wide_mn_is_flagged_only_below_the_field_sheet_ratio() -> None:
    at_limit = evaluate_submission(schlumberger_input("1", "0,5"), [])
    wide = evaluate_submission(schlumberger_input("1", "0,6"), [])

    assert at_limit.result is not None
    assert at_limit.result.warnings == ()
    assert wide.result is not None
    assert wide.result.warnings == (MeasurementWarning.SCHLUMBERGER_WIDE_MN,)


def test_external_mode_records_optional_mn_without_warning() -> None:
    entry = MeasurementInput(
        delta_v="125",
        voltage_unit="mV",
        current="35",
        current_unit="mA",
        geometric_factor="625",
        spacing_ab2="1",
        mn="0,9",
    )

    outcome = evaluate_submission(entry, [])

    assert outcome.result is not None
    assert outcome.result.mn_m == pytest.approx(0.9)
    assert outcome.result.warnings == ()


@pytest.mark.parametrize(
    ("array", "values", "unit", "expected"),
    [
        ("schlumberger", {"ab2": "20", "mn": "2"}, "m", math.pi * 399.0 / 2.0),
        ("wenner", {"a": "1000"}, "cm", 20.0 * math.pi),
        ("dipole-dipole", {"a": "5", "n": "2"}, "m", math.pi * 2 * 3 * 4 * 5),
        ("pole-dipole", {"a": "0,005", "n": "2"}, "km", 2.0 * math.pi * 2 * 3 * 5),
        ("general", {"am": "4", "bm": "6", "an": "6", "bn": "4"}, "m", 12.0 * math.pi),
    ],
)
def test_stand_alone_k_calculation(
    array: ArrayType,
    values: dict[GeometryParameter, str],
    unit: str,
    expected: float,
) -> None:
    outcome = calculate_geometric_factor(array, values, unit)

    assert outcome.issues == ()
    assert outcome.value_m == pytest.approx(expected)


def test_stand_alone_k_reports_every_invalid_parameter() -> None:
    outcome = calculate_geometric_factor("dipole-dipole", {"a": "", "n": "1,000"}, "m")

    assert [issue.parameter for issue in outcome.issues] == ["a", "n"]
    assert outcome.value_m is None


def test_stand_alone_k_reports_geometry_and_overflow_problems() -> None:
    invalid = calculate_geometric_factor("schlumberger", {"ab2": "1", "mn": "5"}, "m")
    overflow = calculate_geometric_factor("wenner", {"a": "1e308"}, "m")
    undefined = calculate_geometric_factor(
        "general", {"am": "5", "bm": "5", "an": "5", "bn": "5"}, "m"
    )

    assert invalid.issues == (ParameterIssue("mn", "MN/2 must be smaller than AB/2"),)
    assert overflow.error is not None
    assert undefined.error is not None
