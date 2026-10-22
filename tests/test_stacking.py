"""Tests for the statistics of repeated readings."""

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from georesistivity.stacking import DEFAULT_CV_THRESHOLD, stack


def test_single_reading_has_no_dispersion() -> None:
    result = stack([2.5])

    assert result.count == 1
    assert result.mean == 2.5
    assert result.standard_deviation is None
    assert result.coefficient_of_variation is None
    assert result.standard_error is None
    assert not result.mixed_signs


def test_hand_calculated_statistics() -> None:
    result = stack([2.0, 4.0, 6.0])

    assert result.count == 3
    assert result.mean == pytest.approx(4.0)
    assert result.standard_deviation == pytest.approx(2.0)
    assert result.coefficient_of_variation == pytest.approx(0.5)
    assert result.standard_error == pytest.approx(2.0 / math.sqrt(3.0))
    assert not result.mixed_signs


def test_identical_readings_have_zero_variation() -> None:
    result = stack([1.25, 1.25])

    assert result.standard_deviation == 0.0
    assert result.coefficient_of_variation == 0.0


def test_mixed_signs_are_detected() -> None:
    assert stack([1.0, -1.0, 2.0]).mixed_signs


def test_zero_mean_has_no_coefficient_of_variation() -> None:
    result = stack([1.0, -1.0])

    assert result.mean == 0.0
    assert result.coefficient_of_variation is None


def test_empty_input_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least one value"):
        stack([])


def test_non_finite_values_are_rejected() -> None:
    with pytest.raises(ValueError, match="must be finite"):
        stack([1.0, math.nan])


def test_default_threshold_is_five_percent() -> None:
    assert DEFAULT_CV_THRESHOLD == 0.05


@given(
    st.lists(
        st.floats(min_value=1e-6, max_value=1e6, allow_nan=False),
        min_size=2,
        max_size=20,
    ),
    st.floats(min_value=1e-3, max_value=1e3),
)
def test_coefficient_of_variation_is_scale_invariant(values: list[float], scale: float) -> None:
    original = stack(values)
    scaled = stack([value * scale for value in values])

    assert scaled.mean == pytest.approx(original.mean * scale, rel=1e-9)
    assert original.coefficient_of_variation is not None
    assert scaled.coefficient_of_variation == pytest.approx(
        original.coefficient_of_variation, rel=1e-6, abs=1e-12
    )
