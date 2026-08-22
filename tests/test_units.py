"""Tests for explicit conversions to SI units."""

import pytest

from georesistivity.units import (
    convert_current_to_amperes,
    convert_length_to_meters,
    convert_voltage_to_volts,
)


def test_millivolts_to_volts() -> None:
    assert convert_voltage_to_volts(1000.0, "mV") == pytest.approx(1.0)


def test_milliamperes_to_amperes() -> None:
    assert convert_current_to_amperes(1000.0, "mA") == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("value", "unit", "expected"),
    [
        (100.0, "cm", 1.0),
        (1000.0, "mm", 1.0),
        (1.0, "km", 1000.0),
        (3.5, "m", 3.5),
    ],
)
def test_length_to_meters(value: float, unit: str, expected: float) -> None:
    assert convert_length_to_meters(value, unit) == pytest.approx(expected)


@pytest.mark.parametrize("unit", ["uV", "µV"])
def test_microvolt_aliases(unit: str) -> None:
    assert convert_voltage_to_volts(1_000_000.0, unit) == pytest.approx(1.0)


@pytest.mark.parametrize("unit", ["uA", "µA"])
def test_microampere_aliases(unit: str) -> None:
    assert convert_current_to_amperes(1_000_000.0, unit) == pytest.approx(1.0)


def test_unknown_unit_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported voltage unit"):
        convert_voltage_to_volts(1.0, "kV")
