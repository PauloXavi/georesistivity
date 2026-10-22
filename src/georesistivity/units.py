"""Explicit conversions from supported field units to SI units."""

from collections.abc import Mapping

from georesistivity.validation import ensure_finite_number

# Micro is accepted as ASCII "u", MICRO SIGN (U+00B5), and GREEK SMALL LETTER MU (U+03BC).
_VOLTAGE_FACTORS: dict[str, float] = {
    "V": 1.0,
    "mV": 1e-3,
    "uV": 1e-6,
    "\u00b5V": 1e-6,
    "\u03bcV": 1e-6,
}

_CURRENT_FACTORS: dict[str, float] = {
    "A": 1.0,
    "mA": 1e-3,
    "uA": 1e-6,
    "\u00b5A": 1e-6,
    "\u03bcA": 1e-6,
}

_LENGTH_FACTORS: dict[str, float] = {
    "m": 1.0,
    "cm": 1e-2,
    "mm": 1e-3,
    "km": 1e3,
}


def _convert_to_si(
    value: float,
    unit: str,
    factors: Mapping[str, float],
    quantity_name: str,
) -> float:
    numeric_value = ensure_finite_number(value, quantity_name)
    if not isinstance(unit, str):
        raise TypeError(f"{quantity_name} unit must be a string")
    try:
        factor = factors[unit.strip()]
    except KeyError as exc:
        supported = ", ".join(factors)
        raise ValueError(
            f"unsupported {quantity_name} unit {unit!r}; supported units: {supported}"
        ) from exc
    return numeric_value * factor


def convert_voltage_to_volts(value: float, unit: str) -> float:
    """Convert a voltage expressed in V, mV, uV, or µV to volts."""
    return _convert_to_si(value, unit, _VOLTAGE_FACTORS, "voltage")


def convert_current_to_amperes(value: float, unit: str) -> float:
    """Convert a current expressed in A, mA, uA, or µA to amperes."""
    return _convert_to_si(value, unit, _CURRENT_FACTORS, "current")


def convert_length_to_meters(value: float, unit: str) -> float:
    """Convert a length expressed in m, cm, mm, or km to meters."""
    return _convert_to_si(value, unit, _LENGTH_FACTORS, "length")
