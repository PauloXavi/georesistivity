"""Property-based tests for parsing, conversion, calculation, formatting, and export."""

import csv
import math
from io import StringIO

import pytest
from hypothesis import given
from hypothesis import strategies as st

from georesistivity import (
    AmbiguousNumberError,
    Measurement,
    apparent_resistivity,
    calculate_measurement,
    convert_length_to_meters,
    convert_voltage_to_volts,
    measurement_results_to_csv,
    parse_number,
)
from georesistivity.formatting import format_significant

FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

moderate_floats = st.floats(min_value=-1e12, max_value=1e12, allow_nan=False, allow_infinity=False)
positive_floats = st.floats(min_value=1e-6, max_value=1e6, allow_nan=False, allow_infinity=False)


@given(st.integers(min_value=-(10**15), max_value=10**15))
def test_integers_parse_exactly(number: int) -> None:
    assert parse_number(str(number)) == float(number)


@given(moderate_floats)
def test_comma_and_period_are_interchangeable(number: float) -> None:
    text = repr(number)
    try:
        with_period = parse_number(text)
    except AmbiguousNumberError:
        with pytest.raises(AmbiguousNumberError):
            parse_number(text.replace(".", ","))
        return

    assert parse_number(text.replace(".", ",")) == with_period == number


@given(
    st.integers(min_value=1, max_value=999),
    st.integers(min_value=0, max_value=999),
    st.sampled_from([",", "."]),
    st.sampled_from(["", "-", "+"]),
)
def test_thousands_like_values_are_never_accepted(
    integer: int,
    fraction: int,
    separator: str,
    sign: str,
) -> None:
    with pytest.raises(AmbiguousNumberError):
        parse_number(f"{sign}{integer}{separator}{fraction:03d}")


@given(st.text(max_size=20))
def test_parse_number_returns_finite_float_or_raises_value_error(text: str) -> None:
    try:
        parsed = parse_number(text)
    except ValueError:
        return
    assert math.isfinite(parsed)


@given(moderate_floats)
def test_kilometers_convert_like_multiplying_by_one_thousand(length: float) -> None:
    assert convert_length_to_meters(length, "km") == pytest.approx(length * 1000.0)


@given(moderate_floats.filter(lambda value: value == 0.0 or abs(value) > 1e-300))
def test_conversion_preserves_sign(voltage: float) -> None:
    converted = convert_voltage_to_volts(voltage, "mV")
    assert math.copysign(1.0, converted) == math.copysign(1.0, voltage)


@given(positive_floats, positive_floats, positive_floats, positive_floats)
def test_rho_a_is_invariant_to_common_scaling_of_delta_v_and_current(
    delta_v: float,
    current: float,
    geometric_factor: float,
    scale: float,
) -> None:
    assert apparent_resistivity(delta_v * scale, current * scale, geometric_factor) == (
        pytest.approx(apparent_resistivity(delta_v, current, geometric_factor), rel=1e-12)
    )


@given(
    positive_floats,
    positive_floats,
    positive_floats,
    st.sampled_from([1.0, -1.0]),
    st.sampled_from([1.0, -1.0]),
)
def test_rho_a_sign_follows_delta_v_and_current(
    delta_v: float,
    current: float,
    geometric_factor: float,
    delta_v_sign: float,
    current_sign: float,
) -> None:
    rho_a = apparent_resistivity(delta_v * delta_v_sign, current * current_sign, geometric_factor)
    assert math.copysign(1.0, rho_a) == delta_v_sign * current_sign


@given(st.floats(min_value=1e-3, max_value=9.99e8, allow_nan=False))
def test_four_significant_digits_stay_within_rounding_error(value: float) -> None:
    shown = float(format_significant(value, number_format="en").replace(",", ""))
    assert shown == pytest.approx(value, rel=5e-4)


@given(st.text(min_size=1, max_size=30).filter(lambda text: text.strip()))
def test_csv_text_cells_never_start_with_a_formula_prefix(source: str) -> None:
    measurement = Measurement(
        delta_v_original=1.0,
        voltage_unit="V",
        current_original=1.0,
        current_unit="A",
        geometric_factor_original=1.0,
        geometric_factor_unit="m",
        geometric_factor_source=source,
    )
    exported = measurement_results_to_csv([calculate_measurement(measurement)])

    rows = list(csv.DictReader(StringIO(exported)))
    assert not rows[0]["K source"].startswith(FORMULA_PREFIXES)
