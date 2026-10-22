"""Tests for locale-tolerant and unambiguous numeric parsing."""

import math

import pytest

from georesistivity.validation import AmbiguousNumberError, parse_number


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


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("0,125", 0.125),
        ("0.125", 0.125),
        ("1,5", 1.5),
        ("1000,000", 1000.0),
        ("1,2345", 1.2345),
        ("12,75", 12.75),
        ("+5", 5.0),
        ("-2,5", -2.5),
        (".5", 0.5),
        ("5.", 5.0),
        ("1e3", 1000.0),
        ("1,5e-3", 0.0015),
        ("3,1340", 3.134),
    ],
)
def test_unambiguous_values_are_accepted(raw_value: str, expected: float) -> None:
    assert parse_number(raw_value) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("raw_value", "integer_hint", "decimal_hint"),
    [
        ("1,000", "1000", "1,0000"),
        ("3.134", "3134", "3.1340"),
        ("12,500", "12500", "12,5000"),
        ("-999.999", "-999999", "-999.9990"),
        ("1,000e3", "1000e3", "1,0000e3"),
    ],
)
def test_thousands_like_values_are_rejected_as_ambiguous(
    raw_value: str,
    integer_hint: str,
    decimal_hint: str,
) -> None:
    with pytest.raises(AmbiguousNumberError) as error:
        parse_number(raw_value)

    assert integer_hint in str(error.value)
    assert decimal_hint in str(error.value)


def test_ambiguous_number_error_is_a_value_error() -> None:
    assert issubclass(AmbiguousNumberError, ValueError)


@pytest.mark.parametrize(
    "raw_value",
    [
        "1_000",
        "1__0",
        "\u0661\u0662",  # Arabic-Indic digits
        "\uff11\uff12",  # full-width digits
        "1 000",
        "1,000,000",
        "1.000.000",
        "--5",
        "0x10",
        "1,5,",
        "e3",
    ],
)
def test_non_plain_numeric_syntax_is_rejected(raw_value: str) -> None:
    with pytest.raises(ValueError, match="invalid numeric value"):
        parse_number(raw_value)


@pytest.mark.parametrize("raw_value", ["infinity", "NaN", "1e400", "-1e400"])
def test_overflowing_or_non_finite_text_is_rejected(raw_value: str) -> None:
    with pytest.raises(ValueError, match="must be finite"):
        parse_number(raw_value)
