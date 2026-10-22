"""Locale-aware number formatting for presenting scientific results."""

from typing import Literal

from georesistivity.validation import ensure_finite_number, is_ambiguous_number_text

NumberFormat = Literal["pt-BR", "en"]
"""``pt-BR``: ``1.234,5`` (decimal comma). ``en``: ``1,234.5`` (decimal point)."""

_PT_BR_SEPARATORS = str.maketrans({",": ".", ".": ","})
_SUPERSCRIPTS = str.maketrans(
    "-0123456789",
    "\u207b\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079",
)
_TIMES = "\u00d7"

# Outside this decimal-exponent range, values are shown in scientific notation.
_MIN_FIXED_EXPONENT = -3
_MAX_FIXED_EXPONENT = 8


def _localize(text: str, number_format: NumberFormat) -> str:
    if number_format == "pt-BR":
        return text.translate(_PT_BR_SEPARATORS)
    if number_format == "en":
        return text
    raise ValueError(f"unsupported number format: {number_format!r}")


def format_significant(
    value: float,
    *,
    number_format: NumberFormat = "pt-BR",
    significant_digits: int = 4,
    grouping: bool = True,
) -> str:
    """Format a value with a fixed number of significant digits.

    Values between 0.001 and 999,999,999 use positional notation with digit grouping
    (``2.232`` in pt-BR, ``2,232`` in en for 2232.14). Smaller or larger magnitudes use
    scientific notation (``2,947 x 10^-4`` rendered with a multiplication sign and
    superscript exponent). ``grouping=False`` omits the thousands separator, for tables.
    """
    number = ensure_finite_number(value, "value")
    if significant_digits < 1:
        raise ValueError("significant_digits must be at least 1")
    if number == 0.0:
        return "0"

    # The exponent of the value after rounding, so 999.96 becomes 1.000e+03.
    mantissa_text, exponent_text = format(number, f".{significant_digits - 1}e").split("e")
    exponent = int(exponent_text)

    if _MIN_FIXED_EXPONENT <= exponent <= _MAX_FIXED_EXPONENT:
        decimals = significant_digits - 1 - exponent
        rounded = round(number, decimals)
        separator = "," if grouping else ""
        text = format(rounded, f"{separator}.{max(decimals, 0)}f")
        return _localize(text, number_format)

    superscript = str(exponent).translate(_SUPERSCRIPTS)
    return f"{_localize(mantissa_text, number_format)} {_TIMES} 10{superscript}"


def format_full_precision(value: float, *, number_format: NumberFormat = "pt-BR") -> str:
    """Format a value with up to 12 significant digits and no digit grouping."""
    number = ensure_finite_number(value, "value")
    return _localize(f"{number:.12g}", number_format)


def format_for_input(
    value: float,
    *,
    number_format: NumberFormat = "pt-BR",
    exact: bool = False,
) -> str:
    """Format a value as text that :func:`~georesistivity.validation.parse_number` reads back
    and never rejects as ambiguous.

    By default up to 12 significant digits; with ``exact`` the shortest text that reads back
    the same float. No grouping; a trailing zero is added when the text would look like a
    thousands-grouped integer (``1,234`` becomes ``1,2340``).
    """
    if exact:
        number = ensure_finite_number(value, "value")
        text = repr(number)
        if text.endswith(".0"):
            text = text[:-2]
        text = _localize(text, number_format)
    else:
        text = format_full_precision(value, number_format=number_format)
    if not is_ambiguous_number_text(text):
        return text
    mantissa, _, exponent = text.partition("e")
    return f"{mantissa}0" + (f"e{exponent}" if exponent else "")
