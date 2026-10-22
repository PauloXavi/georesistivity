"""Tests for sounding points, repeated readings, and their warnings."""

import math

import pytest

from georesistivity.geometry import schlumberger_geometric_factor
from georesistivity.models import MeasurementFieldError, MeasurementWarning
from georesistivity.survey import (
    PointResult,
    Reading,
    SoundingPoint,
    evaluate_point,
    evaluate_reading,
    sort_points,
)


def reading(delta_v: float, current: float = 40.0, **kwargs: object) -> Reading:
    return Reading(delta_v, "mV", current, "mA", **kwargs)  # type: ignore[arg-type]


def test_excluded_reading_needs_a_reason() -> None:
    with pytest.raises(ValueError, match="needs a reason"):
        Reading(1.0, "V", 1.0, "A", excluded=True)
    with pytest.raises(ValueError, match="needs a reason"):
        Reading(1.0, "V", 1.0, "A", excluded=True, exclusion_reason="  ")


def test_reading_is_converted_and_gives_transfer_resistance() -> None:
    result = evaluate_reading(reading(80.0, 40.0))

    assert result.delta_v_v == pytest.approx(0.08)
    assert result.current_a == pytest.approx(0.04)
    assert result.resistance_ohm == pytest.approx(2.0)


@pytest.mark.parametrize(
    ("bad_reading", "field"),
    [
        (Reading(1.0, "kV", 1.0, "A"), "delta_v"),
        (Reading(1.0, "V", 1.0, "kA"), "current"),
        (Reading(1.0, "V", 0.0, "A"), "current"),
    ],
)
def test_reading_errors_name_the_field(bad_reading: Reading, field: str) -> None:
    with pytest.raises(MeasurementFieldError) as error:
        evaluate_reading(bad_reading)

    assert error.value.field == field


def test_single_reading_point_matches_the_single_measurement_formula() -> None:
    result = evaluate_point(SoundingPoint(1.0, 0.5, (reading(80.0),)))

    assert result.geometric_factor_m == pytest.approx(schlumberger_geometric_factor(1.0, 0.5))
    assert result.apparent_resistivity_ohm_m == pytest.approx(result.geometric_factor_m * 2.0)
    assert result.standard_error_ohm_m is None
    assert result.warnings == ()


def test_repeated_readings_use_the_mean_of_transfer_resistances() -> None:
    # R = 2.0, 2.04, 1.96 ohm (CV 2%). The ratio of means would weight readings by current.
    point = SoundingPoint(
        10.0, 2.0, (reading(80.0, 40.0), reading(81.6, 40.0), reading(98.0, 50.0))
    )

    result = evaluate_point(point)

    assert result.statistics is not None
    assert result.statistics.count == 3
    assert result.statistics.mean == pytest.approx(2.0)
    assert result.statistics.coefficient_of_variation == pytest.approx(0.02)
    k = schlumberger_geometric_factor(10.0, 2.0)
    assert result.apparent_resistivity_ohm_m == pytest.approx(k * 2.0)
    assert result.standard_error_ohm_m == pytest.approx(k * 0.04 / math.sqrt(3.0))
    assert result.warnings == ()


def test_excluded_readings_are_kept_but_not_used() -> None:
    point = SoundingPoint(
        10.0,
        2.0,
        (reading(80.0), reading(400.0, excluded=True, exclusion_reason="loose electrode")),
    )

    result = evaluate_point(point)

    assert len(result.readings) == 2
    assert result.statistics is not None
    assert result.statistics.count == 1
    assert result.statistics.mean == pytest.approx(2.0)


def test_point_with_every_reading_excluded_has_no_result() -> None:
    point = SoundingPoint(10.0, 2.0, (reading(80.0, excluded=True, exclusion_reason="noise"),))

    result = evaluate_point(point)

    assert result.statistics is None
    assert result.apparent_resistivity_ohm_m is None
    assert result.standard_error_ohm_m is None
    assert result.warnings == ()


def test_point_needs_readings() -> None:
    with pytest.raises(ValueError, match="at least one reading"):
        evaluate_point(SoundingPoint(10.0, 2.0, ()))


def test_high_variation_is_flagged_with_a_configurable_limit() -> None:
    point = SoundingPoint(10.0, 2.0, (reading(80.0), reading(88.0)))  # CV about 6.7%

    assert MeasurementWarning.STACK_HIGH_VARIATION in evaluate_point(point).warnings
    assert evaluate_point(point, cv_threshold=0.10).warnings == ()


def test_negative_and_mixed_sign_readings_are_flagged() -> None:
    mixed = evaluate_point(
        SoundingPoint(10.0, 2.0, (reading(-80.0), reading(-90.0), reading(10.0)))
    )

    assert MeasurementWarning.NEGATIVE_APPARENT_RESISTIVITY in mixed.warnings
    assert MeasurementWarning.STACK_MIXED_SIGNS in mixed.warnings


def test_wide_mn_is_flagged() -> None:
    result = evaluate_point(SoundingPoint(1.0, 0.8, (reading(80.0),)))

    assert result.warnings == (MeasurementWarning.SCHLUMBERGER_WIDE_MN,)


def test_invalid_geometry_is_rejected() -> None:
    with pytest.raises(ValueError, match="MN/2 must be smaller than AB/2"):
        evaluate_point(SoundingPoint(1.0, 3.0, (reading(80.0),)))


def test_points_are_sorted_by_ab2_then_mn() -> None:
    points = [
        evaluate_point(SoundingPoint(ab2, mn, (reading(80.0),)))
        for ab2, mn in [(10.0, 2.0), (5.5, 2.0), (5.5, 0.5), (1.0, 0.5)]
    ]

    ordered: tuple[PointResult, ...] = sort_points(points)

    assert [(p.point.ab2_m, p.point.mn_m) for p in ordered] == [
        (1.0, 0.5),
        (5.5, 0.5),
        (5.5, 2.0),
        (10.0, 2.0),
    ]
