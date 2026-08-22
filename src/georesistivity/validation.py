"""Validation helpers for numeric scientific inputs."""

import math
from numbers import Real


def ensure_finite_number(value: float, field_name: str) -> float:
    """Return a numeric value as ``float`` after checking that it is finite."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{field_name} must be a real number")

    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{field_name} must be finite")
    return converted


def parse_number(value: str) -> float:
    """Parse a decimal number using either a comma or a period separator."""
    if not isinstance(value, str):
        raise TypeError("value must be a string")

    normalized = value.strip()
    if not normalized:
        raise ValueError("value cannot be empty")
    if "," in normalized and "." in normalized:
        raise ValueError("ambiguous decimal separators")

    normalized = normalized.replace(",", ".")
    try:
        parsed = float(normalized)
    except ValueError as exc:
        raise ValueError(f"invalid numeric value: {value!r}") from exc

    if not math.isfinite(parsed):
        raise ValueError("value must be finite")
    return parsed
