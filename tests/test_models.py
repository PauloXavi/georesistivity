"""Tests for measurement provenance and converted results."""

import pytest

from georesistivity.core import calculate_measurement
from georesistivity.models import Measurement


def test_optional_spacing_and_geometric_factor_source_default_to_none() -> None:
    measurement = Measurement(
        delta_v_original=1.0,
        voltage_unit="V",
        current_original=1.0,
        current_unit="A",
        geometric_factor_original=1.0,
        geometric_factor_unit="m",
    )

    assert measurement.spacing_ab2_original is None
    assert measurement.spacing_unit is None
    assert measurement.geometric_factor_source is None


def test_measurement_preserves_original_values_and_units() -> None:
    measurement = Measurement(
        delta_v_original=125.5,
        voltage_unit="mV",
        current_original=20.0,
        current_unit="mA",
        geometric_factor_original=250.0,
        geometric_factor_unit="cm",
        spacing_ab2_original=1.5,
        spacing_unit="km",
        geometric_factor_source="field sheet",
    )

    assert measurement.delta_v_original == 125.5
    assert measurement.voltage_unit == "mV"
    assert measurement.current_original == 20.0
    assert measurement.current_unit == "mA"
    assert measurement.geometric_factor_original == 250.0
    assert measurement.geometric_factor_unit == "cm"
    assert measurement.spacing_ab2_original == 1.5
    assert measurement.spacing_unit == "km"
    assert measurement.geometric_factor_source == "field sheet"


@pytest.mark.parametrize(
    ("spacing", "spacing_unit"),
    [(1.0, None), (None, "m")],
)
def test_spacing_value_and_unit_must_be_provided_together(
    spacing: float | None,
    spacing_unit: str | None,
) -> None:
    with pytest.raises(ValueError, match="must be provided together"):
        Measurement(
            delta_v_original=1.0,
            voltage_unit="V",
            current_original=1.0,
            current_unit="A",
            geometric_factor_original=1.0,
            geometric_factor_unit="m",
            spacing_ab2_original=spacing,
            spacing_unit=spacing_unit,
        )


def test_calculation_preserves_original_measurement_and_converts_to_si() -> None:
    measurement = Measurement(
        delta_v_original=1000.0,
        voltage_unit="mV",
        current_original=500.0,
        current_unit="mA",
        geometric_factor_original=100.0,
        geometric_factor_unit="cm",
        spacing_ab2_original=2.0,
        spacing_unit="km",
        geometric_factor_source="unknown",
    )

    result = calculate_measurement(measurement)

    assert result.measurement is measurement
    assert result.delta_v_v == pytest.approx(1.0)
    assert result.current_a == pytest.approx(0.5)
    assert result.geometric_factor_m == pytest.approx(1.0)
    assert result.spacing_ab2_m == pytest.approx(2000.0)
    assert result.apparent_resistivity_ohm_m == pytest.approx(2.0)


def test_geometric_factor_source_does_not_affect_calculation() -> None:
    base_arguments = {
        "delta_v_original": 2.0,
        "voltage_unit": "V",
        "current_original": 1.0,
        "current_unit": "A",
        "geometric_factor_original": 5.0,
        "geometric_factor_unit": "m",
    }
    manual = calculate_measurement(Measurement(**base_arguments, geometric_factor_source="manual"))
    unknown = calculate_measurement(Measurement(**base_arguments, geometric_factor_source=None))

    assert manual.apparent_resistivity_ohm_m == unknown.apparent_resistivity_ohm_m


@pytest.mark.parametrize(("mn", "mn_unit"), [(1.0, None), (None, "m")])
def test_mn_value_and_unit_must_be_provided_together(
    mn: float | None,
    mn_unit: str | None,
) -> None:
    with pytest.raises(ValueError, match="MN value and MN unit"):
        Measurement(
            delta_v_original=1.0,
            voltage_unit="V",
            current_original=1.0,
            current_unit="A",
            geometric_factor_original=1.0,
            geometric_factor_unit="m",
            mn_original=mn,
            mn_unit=mn_unit,
        )


def test_mn_is_converted_and_does_not_affect_the_calculation() -> None:
    base = {
        "delta_v_original": 2.0,
        "voltage_unit": "V",
        "current_original": 1.0,
        "current_unit": "A",
        "geometric_factor_original": 5.0,
        "geometric_factor_unit": "m",
    }
    without_mn = calculate_measurement(Measurement(**base))
    with_mn = calculate_measurement(Measurement(**base, mn_original=50.0, mn_unit="cm"))

    assert without_mn.mn_m is None
    assert with_mn.mn_m == pytest.approx(0.5)
    assert with_mn.apparent_resistivity_ohm_m == without_mn.apparent_resistivity_ohm_m
