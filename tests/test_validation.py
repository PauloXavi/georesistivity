"""Tests for locale-tolerant and unambiguous numeric parsing."""

import math

import pytest

from georesistivity.validation import parse_number


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("10", 10.0),
        ("10.5", 10.5),
        ("10,5", 10.5),
        (" 10,5 ", 10.5),
    ],
)
def test_parse_supported_decimal_formats(raw_value: str, expected: float) -> None:
    assert parse_number(raw_value) == pytest.approx(expected)


@pytest.mark.parametrize("raw_value", ["", "   "])
def test_empty_input_is_rejected(raw_value: str) -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        parse_number(raw_value)


def test_non_numeric_input_is_rejected() -> None:
    with pytest.raises(ValueError, match="invalid numeric value"):
        parse_number("not a number")


@pytest.mark.parametrize("raw_value", ["1.234,56", "1,234.56"])
def test_ambiguous_separators_are_rejected(raw_value: str) -> None:
    with pytest.raises(ValueError, match="ambiguous decimal separators"):
        parse_number(raw_value)


@pytest.mark.parametrize("raw_value", [str(math.nan), str(math.inf), "-inf"])
def test_non_finite_parsed_values_are_rejected(raw_value: str) -> None:
    with pytest.raises(ValueError, match="must be finite"):
        parse_number(raw_value)


def test_non_string_input_is_rejected() -> None:
    with pytest.raises(TypeError, match="must be a string"):
        parse_number(10.5)  # type: ignore[arg-type]
