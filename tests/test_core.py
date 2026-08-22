"""Tests for the SI-only apparent-resistivity core."""

import math

import pytest

from georesistivity.core import apparent_resistivity


def test_apparent_resistivity_identity() -> None:
    assert apparent_resistivity(1.0, 1.0, 1.0) == pytest.approx(1.0)


def test_apparent_resistivity_scales_inputs() -> None:
    assert apparent_resistivity(2.0, 0.5, 10.0) == pytest.approx(40.0)


def test_zero_current_is_rejected() -> None:
    with pytest.raises(ValueError, match="current_a cannot be zero"):
        apparent_resistivity(1.0, 0.0, 1.0)


def test_zero_geometric_factor_is_rejected() -> None:
    with pytest.raises(ValueError, match="geometric_factor_m cannot be zero"):
        apparent_resistivity(1.0, 1.0, 0.0)


@pytest.mark.parametrize(
    ("delta_v_v", "current_a", "geometric_factor_m"),
    [
        (math.nan, 1.0, 1.0),
        (1.0, math.nan, 1.0),
        (1.0, 1.0, math.nan),
        (math.inf, 1.0, 1.0),
        (1.0, -math.inf, 1.0),
        (1.0, 1.0, math.inf),
    ],
)
def test_non_finite_inputs_are_rejected(
    delta_v_v: float,
    current_a: float,
    geometric_factor_m: float,
) -> None:
    with pytest.raises(ValueError, match="must be finite"):
        apparent_resistivity(delta_v_v, current_a, geometric_factor_m)


@pytest.mark.parametrize(
    ("delta_v_v", "current_a", "geometric_factor_m", "expected"),
    [
        (-2.0, 1.0, 5.0, -10.0),
        (2.0, -1.0, 5.0, -10.0),
        (-2.0, -1.0, 5.0, 10.0),
        (2.0, 1.0, -5.0, -10.0),
    ],
)
def test_negative_values_keep_their_mathematical_sign(
    delta_v_v: float,
    current_a: float,
    geometric_factor_m: float,
    expected: float,
) -> None:
    assert apparent_resistivity(delta_v_v, current_a, geometric_factor_m) == pytest.approx(expected)
