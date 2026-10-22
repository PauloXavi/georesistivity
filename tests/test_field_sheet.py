"""Tests for the digital Schlumberger field sheet (application layer)."""

import pytest

from georesistivity.field_sheet import (
    RowIssue,
    SheetOutcome,
    SheetRow,
    evaluate_sheet,
    template_rows,
)
from georesistivity.geometry import schlumberger_geometric_factor
from georesistivity.models import MeasurementWarning


def sheet(*rows: SheetRow, cv_threshold: float = 0.05) -> SheetOutcome:
    return evaluate_sheet(rows, voltage_unit="mV", current_unit="mA", cv_threshold=cv_threshold)


def test_template_has_the_45_field_sheet_positions() -> None:
    rows = template_rows()

    assert len(rows) == 45
    assert rows[0] == SheetRow(ab2="1", mn="0,5")
    assert rows[-1] == SheetRow(ab2="320", mn="100")
    assert all(not row.delta_v and not row.current for row in rows)


def test_template_can_use_the_en_number_format() -> None:
    assert template_rows("en")[1] == SheetRow(ab2="1.3", mn="0.5")


def test_blank_template_gives_no_points() -> None:
    outcome = sheet(*template_rows())

    assert outcome.points == ()
    assert {status.state for status in outcome.rows} == {"blank"}
    assert outcome.invalid_rows == ()


def test_filled_rows_become_points_with_k_and_rho_a() -> None:
    outcome = sheet(
        SheetRow(marker="VD", ab2="1", mn="0,5", delta_v="80", current="40"),
        SheetRow(ab2="1,3", mn="0,5"),
    )

    assert [status.state for status in outcome.rows] == ["valid", "blank"]
    (point,) = outcome.points
    assert point.point.marker == "VD"
    assert point.geometric_factor_m == pytest.approx(schlumberger_geometric_factor(1.0, 0.5))
    assert point.apparent_resistivity_ohm_m == pytest.approx(point.geometric_factor_m * 2.0)


def test_overlap_readings_are_separate_points_of_the_same_ab2() -> None:
    outcome = sheet(
        SheetRow(ab2="5,5", mn="0,5", delta_v="9", current="50"),
        SheetRow(ab2="5,5", mn="2", delta_v="33", current="50"),
    )

    assert [(p.point.ab2_m, p.point.mn_m) for p in outcome.points] == [(5.5, 0.5), (5.5, 2.0)]


def test_repeated_rows_of_one_position_are_combined() -> None:
    outcome = sheet(
        SheetRow(ab2="10", mn="2", delta_v="80", current="40"),
        SheetRow(ab2="10,0", mn="2", delta_v="81,6", current="40"),
        SheetRow(ab2="10", mn="2", delta_v="400", current="40", excluded=True, reason="noise"),
    )

    (point,) = outcome.points
    assert [status.state for status in outcome.rows] == ["valid", "valid", "excluded"]
    assert len(point.readings) == 3
    assert point.statistics is not None
    assert point.statistics.count == 2
    assert point.statistics.mean == pytest.approx(2.02)


def test_points_are_ordered_by_ab2_and_mn_whatever_the_row_order() -> None:
    outcome = sheet(
        SheetRow(ab2="10", mn="2", delta_v="80", current="40"),
        SheetRow(ab2="1", mn="0,5", delta_v="80", current="40"),
    )

    assert [p.point.ab2_m for p in outcome.points] == [1.0, 10.0]


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        (
            SheetRow(ab2="1", mn="3", delta_v="80", current="40"),
            RowIssue("mn", "MN/2 must be smaller than AB/2"),
        ),
        (
            SheetRow(ab2="0", mn="0,5", delta_v="80", current="40"),
            RowIssue("ab2", "must be positive"),
        ),
        (
            SheetRow(ab2="1", mn="0,5", delta_v="80", current="0"),
            RowIssue("current", "cannot be zero"),
        ),
        (
            SheetRow(ab2="1", mn="0,5", delta_v="80", current="40", excluded=True),
            RowIssue("reason", "is required to exclude a reading"),
        ),
    ],
)
def test_invalid_rows_are_reported_by_column(row: SheetRow, expected: RowIssue) -> None:
    outcome = sheet(row)

    assert outcome.points == ()
    assert outcome.invalid_rows == ((1, outcome.rows[0]),)
    assert outcome.rows[0].issues == (expected,)


def test_ambiguous_numbers_are_rejected_in_the_sheet() -> None:
    outcome = sheet(SheetRow(ab2="1", mn="0,5", delta_v="1,000", current="40"))

    (issue,) = outcome.rows[0].issues
    assert issue.column == "delta_v"
    assert "ambiguous" in issue.message


def test_invalid_rows_do_not_affect_the_valid_ones() -> None:
    outcome = sheet(
        SheetRow(ab2="1", mn="0,5", delta_v="abc", current="40"),
        SheetRow(ab2="1,3", mn="0,5", delta_v="80", current="40"),
    )

    assert [number for number, _ in outcome.invalid_rows] == [1]
    assert [p.point.ab2_m for p in outcome.points] == [1.3]


def test_unit_problems_are_reported_on_the_value_columns() -> None:
    outcome = evaluate_sheet(
        [SheetRow(ab2="1", mn="0,5", delta_v="80", current="40")],
        voltage_unit="kV",
        current_unit="mA",
    )

    (issue,) = outcome.rows[0].issues
    assert issue.column == "delta_v"


def test_overflowing_geometry_is_reported() -> None:
    outcome = sheet(SheetRow(ab2="1e300", mn="1e-300", delta_v="80", current="40"))

    (issue,) = outcome.rows[0].issues
    assert issue.column == "ab2"
    assert "too large" in issue.message


def test_cv_threshold_controls_the_high_variation_warning() -> None:
    rows = (
        SheetRow(ab2="10", mn="2", delta_v="80", current="40"),
        SheetRow(ab2="10", mn="2", delta_v="88", current="40"),
    )

    strict = sheet(*rows, cv_threshold=0.05)
    relaxed = sheet(*rows, cv_threshold=0.10)

    assert MeasurementWarning.STACK_HIGH_VARIATION in strict.points[0].warnings
    assert relaxed.points[0].warnings == ()


def test_marker_comes_from_the_first_row_that_has_one() -> None:
    outcome = sheet(
        SheetRow(ab2="10", mn="2", delta_v="80", current="40"),
        SheetRow(marker=" AZ ", ab2="10", mn="2", delta_v="80", current="40"),
    )

    assert outcome.points[0].point.marker == "AZ"


@pytest.mark.parametrize(
    ("row", "missing"),
    [
        (SheetRow(ab2="1", mn="0,5", delta_v="80"), "current"),
        (SheetRow(ab2="1", mn="0,5", current="40"), "delta_v"),
    ],
)
def test_row_with_only_one_value_is_incomplete_not_invalid(row: SheetRow, missing: str) -> None:
    outcome = sheet(row)

    assert outcome.rows[0].state == "incomplete"
    assert outcome.rows[0].issues == (RowIssue(missing, "not typed yet"),)  # type: ignore[arg-type]
    assert outcome.incomplete_rows == ((1, outcome.rows[0]),)
    assert outcome.invalid_rows == ()
    assert outcome.points == ()


def test_incomplete_row_with_another_problem_is_invalid() -> None:
    outcome = sheet(SheetRow(ab2="1", mn="3", delta_v="1,000"))

    assert outcome.rows[0].state == "invalid"
    assert [issue.column for issue in outcome.rows[0].issues] == ["delta_v", "mn"]
    assert outcome.incomplete_rows == ()
