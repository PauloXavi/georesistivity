"""Tests for locale-aware presentation of numeric results."""

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from georesistivity.formatting import format_for_input, format_full_precision, format_significant
from georesistivity.validation import parse_number


@pytest.mark.parametrize(
    ("value", "pt_br", "en"),
    [
        (2232.142857, "2.232", "2,232"),
        (3571.428, "3.571", "3,571"),
        (3.5714, "3,571", "3.571"),
        (25.0, "25,00", "25.00"),
        (0.002947, "0,002947", "0.002947"),
        (12345.6, "12.350", "12,350"),
        (123456789.0, "123.500.000", "123,500,000"),
        (-2232.14, "-2.232", "-2,232"),
        (0.0, "0", "0"),
    ],
)
def test_four_significant_digits_in_both_formats(value: float, pt_br: str, en: str) -> None:
    assert format_significant(value, number_format="pt-BR") == pt_br
    assert format_significant(value, number_format="en") == en


def test_rounding_that_crosses_a_power_of_ten_keeps_four_digits() -> None:
    assert format_significant(999.96, number_format="en") == "1,000"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.0002947, "2,947 \u00d7 10\u207b\u2074"),
        (1.234e12, "1,234 \u00d7 10\u00b9\u00b2"),
        (-5e-9, "-5,000 \u00d7 10\u207b\u2079"),
    ],
)
def test_extreme_magnitudes_use_scientific_notation(value: float, expected: str) -> None:
    assert format_significant(value, number_format="pt-BR") == expected


def test_small_results_are_no_longer_shown_as_zero() -> None:
    assert format_significant(0.0029, number_format="en") == "0.002900"


def test_significant_digits_are_configurable() -> None:
    assert format_significant(2232.142857, number_format="en", significant_digits=6) == "2,232.14"


def test_invalid_arguments_are_rejected() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        format_significant(1.0, significant_digits=0)
    with pytest.raises(ValueError, match="must be finite"):
        format_significant(math.inf)
    with pytest.raises(ValueError, match="unsupported number format"):
        format_significant(1.0, number_format="fr")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("value", "pt_br", "en"),
    [
        (0.125, "0,125", "0.125"),
        (2232.142857142857, "2232,14285714", "2232.14285714"),
        (1e-4, "0,0001", "0.0001"),
        (7e-08, "7e-08", "7e-08"),
    ],
)
def test_full_precision_has_no_grouping(value: float, pt_br: str, en: str) -> None:
    assert format_full_precision(value, number_format="pt-BR") == pt_br
    assert format_full_precision(value, number_format="en") == en


def test_grouping_can_be_disabled_for_tables() -> None:
    assert format_significant(
        36187.0, number_format="pt-BR", significant_digits=5, grouping=False
    ) == ("36187")
    assert format_significant(2035.4, number_format="en", significant_digits=5, grouping=False) == (
        "2035.4"
    )


@pytest.mark.parametrize(
    ("value", "pt_br", "en"),
    [
        (1.234, "1,2340", "1.2340"),
        (999.999, "999,9990", "999.9990"),
        (0.125, "0,125", "0.125"),
        (1234.5, "1234,5", "1234.5"),
        (80.0, "80", "80"),
        (1.234e-20, "1,2340e-20", "1.2340e-20"),  # the exponent does not remove the doubt
    ],
)
def test_input_text_is_never_ambiguous(value: float, pt_br: str, en: str) -> None:
    assert format_for_input(value, number_format="pt-BR") == pt_br
    assert format_for_input(value, number_format="en") == en
    assert parse_number(pt_br) == pytest.approx(value)
    assert parse_number(en) == pytest.approx(value)


@given(st.floats(allow_nan=False, allow_infinity=False, min_value=-1e15, max_value=1e15))
def test_input_text_round_trips_through_parse_number(value: float) -> None:
    for number_format in ("pt-BR", "en"):
        text = format_for_input(value, number_format=number_format)  # type: ignore[arg-type]
        assert parse_number(text) == pytest.approx(value, rel=1e-11, abs=1e-300)
