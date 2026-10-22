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


@pytest.mark.parametrize("unit", ["\u00b5V", "\u03bcV", " \u00b5V "])
def test_micro_sign_and_greek_mu_are_both_accepted(unit: str) -> None:
    assert convert_voltage_to_volts(2.0, unit) == pytest.approx(2e-6)


@pytest.mark.parametrize("unit", ["\u00b5A", "\u03bcA"])
def test_micro_ampere_unicode_variants(unit: str) -> None:
    assert convert_current_to_amperes(5.0, unit) == pytest.approx(5e-6)


def test_units_are_case_sensitive() -> None:
    with pytest.raises(ValueError, match="unsupported voltage unit"):
        convert_voltage_to_volts(1.0, "MV")


def test_non_string_unit_is_rejected() -> None:
    with pytest.raises(TypeError, match="unit must be a string"):
        convert_length_to_meters(1.0, None)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("value", "unit", "expected_repr"),
    [
        (9.0, "mV", "0.009"),
        (13.0, "mA", "0.013"),
        (100.0, "uV", "0.0001"),
        (7.0, "cm", "0.07"),
        (1.5, "km", "1500.0"),
        (0.3, "mV", "0.0003"),
        (12.34, "mA", "0.01234"),
        (0.07, "uV", "7e-08"),
    ],
)
def test_sub_unit_conversion_has_no_representation_artifacts(
    value: float,
    unit: str,
    expected_repr: str,
) -> None:
    converters = {
        "mV": convert_voltage_to_volts,
        "uV": convert_voltage_to_volts,
        "mA": convert_current_to_amperes,
        "cm": convert_length_to_meters,
        "km": convert_length_to_meters,
    }
    assert repr(converters[unit](value, unit)) == expected_repr


def test_overflow_after_conversion_is_rejected() -> None:
    with pytest.raises(ValueError, match="length value is too large"):
        convert_length_to_meters(1e306, "km")


def test_underflow_to_zero_after_conversion_is_rejected() -> None:
    with pytest.raises(ValueError, match="current value is too small"):
        convert_current_to_amperes(1e-320, "uA")


def test_zero_stays_zero_after_conversion() -> None:
    assert convert_voltage_to_volts(0.0, "mV") == 0.0
