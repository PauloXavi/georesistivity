"""Validation helpers for numeric scientific inputs."""

import math
import re
from numbers import Real

# ASCII digits only, one optional decimal separator ("." or ","), optional exponent.
_NUMBER_PATTERN = re.compile(r"[+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][+-]?\d+)?", re.ASCII)

# A single separator after a non-zero integer part of one to three digits and followed by
# exactly three digits reads equally well as a thousands separator ("1,000" -> 1000) or as a
# decimal separator ("1,000" -> 1.0). Such values are rejected instead of guessed.
_AMBIGUOUS_PATTERN = re.compile(
    r"(?P<sign>[+-]?)(?P<integer>[1-9]\d{0,2})(?P<separator>[.,])(?P<fraction>\d{3})"
    r"(?P<exponent>[eE][+-]?\d+)?",
    re.ASCII,
)


class AmbiguousNumberError(ValueError):
    """Raised when a value could be read with either a thousands or a decimal separator."""


def ensure_finite_number(value: float, field_name: str) -> float:
    """Return a numeric value as ``float`` after checking that it is finite."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{field_name} must be a real number")

    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{field_name} must be finite")
    return converted


def is_ambiguous_number_text(text: str) -> bool:
    """Whether ``text`` reads as either a thousands-grouped integer or a decimal (``1,000``)."""
    return _AMBIGUOUS_PATTERN.fullmatch(text.strip()) is not None


def parse_number_with_decimal(value: str, decimal_separator: str) -> float:
    """Parse ``value`` written with a known decimal separator (``.`` or ``,``).

    Used when a whole source, such as a CSV file, declares its convention: ``1,000`` is then
    1.0 with a decimal comma, and the other separator is rejected instead of guessed.
    """
    if decimal_separator not in (".", ","):
        raise ValueError(f"unsupported decimal separator: {decimal_separator!r}")
    if not isinstance(value, str):
        raise TypeError("value must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError("value cannot be empty")
    other = "," if decimal_separator == "." else "."
    if other in normalized:
        raise ValueError(
            f"{value.strip()!r} uses {other!r}, but the decimal separator is "
            f"{decimal_separator!r}; thousands separators are not accepted"
        )
    if _NUMBER_PATTERN.fullmatch(normalized) is None:
        if _is_non_finite_token(normalized):
            raise ValueError("value must be finite")
        raise ValueError(f"invalid numeric value: {value!r}")
    parsed = float(normalized.replace(",", "."))
    if not math.isfinite(parsed):
        raise ValueError("value must be finite")
    return parsed


def parse_number(value: str) -> float:
    """Parse a decimal number written with either a comma or a period separator.

    Accepted input uses ASCII digits, an optional sign, at most one decimal separator
    (``.`` or ``,``), and an optional exponent (``1,5e-3``). Thousands separators are never
    accepted. Values such as ``1,000`` or ``3.134`` raise :class:`AmbiguousNumberError`
    because they could mean either a thousand-scale integer or a decimal number.
    """
    if not isinstance(value, str):
        raise TypeError("value must be a string")

    normalized = value.strip()
    if not normalized:
        raise ValueError("value cannot be empty")
    if "," in normalized and "." in normalized:
        raise ValueError(
            "ambiguous decimal separators; thousands separators are not accepted "
            "(type 1234.5 or 1234,5)"
        )

    ambiguous = _AMBIGUOUS_PATTERN.fullmatch(normalized)
    if ambiguous is not None:
        sign = ambiguous["sign"]
        integer = ambiguous["integer"]
        separator = ambiguous["separator"]
        fraction = ambiguous["fraction"]
        exponent = ambiguous["exponent"] or ""
        raise AmbiguousNumberError(
            f"ambiguous value {value.strip()!r}: {separator!r} may be a thousands or a "
            f"decimal separator. Type {sign}{integer}{fraction}{exponent} for the integer, "
            f"or {sign}{integer}{separator}{fraction}0{exponent} for the decimal value"
        )

    if _NUMBER_PATTERN.fullmatch(normalized) is None:
        if _is_non_finite_token(normalized):
            raise ValueError("value must be finite")
        raise ValueError(f"invalid numeric value: {value!r}")

    parsed = float(normalized.replace(",", "."))
    if not math.isfinite(parsed):
        raise ValueError("value must be finite")
    return parsed


def _is_non_finite_token(text: str) -> bool:
    try:
        return not math.isfinite(float(text))
    except ValueError:
        return False
