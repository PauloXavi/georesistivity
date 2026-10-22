"""Explicit conversions from supported field units to SI units."""

import math
import re
from collections.abc import Mapping
from decimal import Decimal

from georesistivity.validation import ensure_finite_number

# Each unit maps to its power-of-ten exponent relative to the SI unit. Conversions shift the
# shortest decimal representation of the value by that exponent and round once, so values
# convert exactly as typed (9 mV -> 0.009 V, 0.3 mV -> 0.0003 V) instead of carrying the
# representation artifacts of multiplying by an inexact factor such as 1e-3.
# Micro is accepted as ASCII "u", MICRO SIGN (U+00B5), and GREEK SMALL LETTER MU (U+03BC).
_VOLTAGE_EXPONENTS: dict[str, int] = {
    "V": 0,
    "mV": -3,
    "uV": -6,
    "\u00b5V": -6,
    "\u03bcV": -6,
}

_CURRENT_EXPONENTS: dict[str, int] = {
    "A": 0,
    "mA": -3,
    "uA": -6,
    "\u00b5A": -6,
    "\u03bcA": -6,
}

_LENGTH_EXPONENTS: dict[str, int] = {
    "m": 0,
    "cm": -2,
    "mm": -3,
    "km": 3,
}


_QUANTITY_PATTERN = re.compile(r"(?P<number>.+?)\s*(?P<unit>[A-Za-z\u00b5\u03bc]+)")


def split_quantity(text: str) -> tuple[str, str]:
    """Split ``"125mV"`` or ``"0,125 V"`` into its number text and unit, unvalidated.

    The number is checked later with :func:`~georesistivity.validation.parse_number` and the
    unit by the conversion functions.
    """
    match = _QUANTITY_PATTERN.fullmatch(text.strip())
    if match is None:
        raise ValueError(f"missing unit in {text!r}; write it like 20m or 125mV")
    return match["number"], match["unit"]


def _convert_to_si(
    value: float,
    unit: str,
    exponents: Mapping[str, int],
    quantity_name: str,
) -> float:
    numeric_value = ensure_finite_number(value, quantity_name)
    if not isinstance(unit, str):
        raise TypeError(f"{quantity_name} unit must be a string")
    try:
        exponent = exponents[unit.strip()]
    except KeyError as exc:
        supported = ", ".join(exponents)
        raise ValueError(
            f"unsupported {quantity_name} unit {unit!r}; supported units: {supported}"
        ) from exc

    converted = float(Decimal(repr(numeric_value)).scaleb(exponent))

    if not math.isfinite(converted):
        raise ValueError(f"{quantity_name} value is too large to convert to SI units")
    if converted == 0.0 and numeric_value != 0.0:
        raise ValueError(f"{quantity_name} value is too small to convert to SI units")
    return converted


def convert_voltage_to_volts(value: float, unit: str) -> float:
    """Convert a voltage expressed in V, mV, uV, or µV to volts."""
    return _convert_to_si(value, unit, _VOLTAGE_EXPONENTS, "voltage")


def convert_current_to_amperes(value: float, unit: str) -> float:
    """Convert a current expressed in A, mA, uA, or µA to amperes."""
    return _convert_to_si(value, unit, _CURRENT_EXPONENTS, "current")


def convert_length_to_meters(value: float, unit: str) -> float:
    """Convert a length expressed in m, cm, mm, or km to meters."""
    return _convert_to_si(value, unit, _LENGTH_EXPONENTS, "length")
