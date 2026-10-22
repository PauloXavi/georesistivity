"""Tests for the SI-only apparent-resistivity core."""

import math

import pytest

from georesistivity.core import apparent_resistivity, calculate_measurement
from georesistivity.models import Measurement, MeasurementFieldError, MeasurementWarning


def test_apparent_resistivity_identity() -> None:
    assert apparent_resistivity(1.0, 1.0, 1.0) == pytest.approx(1.0)


def test_apparent_resistivity_scales_inputs() -> None:
    assert apparent_resistivity(2.0, 0.5, 10.0) == pytest.approx(40.0)


def test_zero_current_is_rejected() -> None:
    with pytest.raises(ValueError, match="current_a cannot be zero"):
        apparent_resistivity(1.0, 0.0, 1.0)


def test_zero_geometric_factor_is_rejected() -> None:
    with pytest.raises(ValueError, match="geometric_factor_m cannot be zero"):
        apparent_resistivity(1.0, 1.0, 0.0)


@pytest.mark.parametrize(
    ("delta_v_v", "current_a", "geometric_factor_m"),
    [
        (math.nan, 1.0, 1.0),
        (1.0, math.nan, 1.0),
        (1.0, 1.0, math.nan),
        (math.inf, 1.0, 1.0),
        (1.0, -math.inf, 1.0),
        (1.0, 1.0, math.inf),
    ],
)
def test_non_finite_inputs_are_rejected(
    delta_v_v: float,
    current_a: float,
    geometric_factor_m: float,
) -> None:
    with pytest.raises(ValueError, match="must be finite"):
        apparent_resistivity(delta_v_v, current_a, geometric_factor_m)


@pytest.mark.parametrize(
    ("delta_v_v", "current_a", "geometric_factor_m", "expected"),
    [
        (-2.0, 1.0, 5.0, -10.0),
        (2.0, -1.0, 5.0, -10.0),
        (-2.0, -1.0, 5.0, 10.0),
    ],
)
def test_negative_values_keep_their_mathematical_sign(
    delta_v_v: float,
    current_a: float,
    geometric_factor_m: float,
    expected: float,
) -> None:
    assert apparent_resistivity(delta_v_v, current_a, geometric_factor_m) == pytest.approx(expected)


@pytest.mark.parametrize("geometric_factor_m", [-5.0, -1e-9])
def test_negative_geometric_factor_is_rejected(geometric_factor_m: float) -> None:
    with pytest.raises(ValueError, match="geometric_factor_m must be positive"):
        apparent_resistivity(2.0, 1.0, geometric_factor_m)


def make_measurement(
    *,
    delta_v: float = 100.0,
    current: float = 20.0,
    spacing: float | None = None,
    spacing_unit: str | None = None,
) -> Measurement:
    return Measurement(
        delta_v_original=delta_v,
        voltage_unit="mV",
        current_original=current,
        current_unit="mA",
        geometric_factor_original=5.0,
        geometric_factor_unit="m",
        spacing_ab2_original=spacing,
        spacing_unit=spacing_unit if spacing is not None else None,
    )


@pytest.mark.parametrize("spacing", [0.0, -3.0])
def test_non_positive_spacing_is_rejected(spacing: float) -> None:
    with pytest.raises(MeasurementFieldError, match="spacing_ab2: must be positive") as error:
        calculate_measurement(make_measurement(spacing=spacing, spacing_unit="m"))

    assert error.value.field == "spacing_ab2"


def test_negative_apparent_resistivity_is_kept_and_flagged() -> None:
    result = calculate_measurement(make_measurement(delta_v=-100.0))

    assert result.apparent_resistivity_ohm_m == pytest.approx(-25.0)
    assert result.warnings == (MeasurementWarning.NEGATIVE_APPARENT_RESISTIVITY,)


def test_positive_apparent_resistivity_has_no_warnings() -> None:
    result = calculate_measurement(make_measurement(delta_v=-100.0, current=-20.0))

    assert result.apparent_resistivity_ohm_m == pytest.approx(25.0)
    assert result.warnings == ()


def test_overflowing_result_is_rejected() -> None:
    with pytest.raises(ValueError, match="result must be finite"):
        apparent_resistivity(1e308, 1e-308, 1e308)


@pytest.mark.parametrize(
    ("overrides", "field", "reason"),
    [
        ({"current_original": 0.0}, "current", "cannot be zero"),
        ({"voltage_unit": "kV"}, "delta_v", "unsupported voltage unit"),
        ({"current_unit": "kA"}, "current", "unsupported current unit"),
        ({"geometric_factor_original": 0.0}, "geometric_factor", "must be positive"),
        ({"geometric_factor_original": -5.0}, "geometric_factor", "must be positive"),
        (
            {"geometric_factor_original": 1e306, "geometric_factor_unit": "km"},
            "geometric_factor",
            "too large",
        ),
        ({"spacing_ab2_original": 1e306, "spacing_unit": "km"}, "spacing_ab2", "too large"),
    ],
)
def test_calculation_errors_name_the_offending_field(
    overrides: dict[str, object],
    field: str,
    reason: str,
) -> None:
    arguments: dict[str, object] = {
        "delta_v_original": 100.0,
        "voltage_unit": "mV",
        "current_original": 20.0,
        "current_unit": "mA",
        "geometric_factor_original": 5.0,
        "geometric_factor_unit": "m",
        **overrides,
    }

    with pytest.raises(MeasurementFieldError) as error:
        calculate_measurement(Measurement(**arguments))  # type: ignore[arg-type]

    assert error.value.field == field
    assert reason in error.value.reason


def test_overflowing_measurement_result_is_not_attributed_to_one_field() -> None:
    measurement = Measurement(
        delta_v_original=1e306,
        voltage_unit="V",
        current_original=1e-306,
        current_unit="A",
        geometric_factor_original=5.0,
        geometric_factor_unit="m",
    )

    with pytest.raises(ValueError, match="result must be finite") as error:
        calculate_measurement(measurement)

    assert not isinstance(error.value, MeasurementFieldError)
