"""Tests for the geometric factor of four-electrode arrays."""

import math
from collections.abc import Callable
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from georesistivity.geometry import (
    ARRAY_PARAMETERS,
    SCHLUMBERGER_MIN_RATIO,
    GeometryError,
    dipole_dipole_geometric_factor,
    general_geometric_factor,
    geometric_factor,
    pole_dipole_geometric_factor,
    schlumberger_geometric_factor,
    schlumberger_spacing_ratio,
    wenner_geometric_factor,
)

# Pre-computed K table printed on the author's field sheet "Sondagem Eletrica Vertical -
# Arranjo Schlumberger" (rows: AB/2 in m; columns: full MN in m). Only these constants are
# used; no field readings. Values are kept as printed, including their number of decimals.
FIELD_SHEET_K_TABLE: dict[float, dict[float, str]] = {
    1.0: {0.5: "5.89"},
    1.3: {0.5: "10.22"},
    1.8: {0.5: "19.96"},
    2.4: {0.5: "35.80"},
    3.2: {0.5: "63.95"},
    4.2: {0.5: "110.4"},
    5.5: {0.5: "189.7", 2: "45.95"},
    7.5: {0.5: "353.0", 2: "86.79"},
    10: {0.5: "627.9", 2: "155.5"},
    13: {0.5: "1061.4", 2: "263.9"},
    18: {0.5: "2035.4", 2: "507.4", 5: "199.6"},
    24: {0.5: "3618.7", 2: "903.2", 5: "358.0"},
    32: {2: "1606.9", 5: "639.5"},
    42: {2: "2769.3", 5: "1104.4"},
    55: {2: "4750.1", 5: "1896.7", 20: "459.5"},
    75: {2: "8834.2", 5: "3530.4", 20: "867.9"},
    100: {5: "6279.3", 20: "1555.1"},
    130: {5: "10615", 20: "2638.9", 50: "1022.6"},
    180: {5: "20354", 20: "5073.7", 50: "1996.5"},
    240: {5: "36187", 20: "9032.1", 50: "3579.8", 100: "1731.0"},
    320: {20: "16069.2", 50: "6394.7", 100: "3138.5"},
}
FIELD_SHEET_CELLS = [
    (ab2, mn, printed) for ab2, row in FIELD_SHEET_K_TABLE.items() for mn, printed in row.items()
]


def test_field_sheet_table_has_45_cells() -> None:
    assert len(FIELD_SHEET_CELLS) == 45


@pytest.mark.parametrize(("ab2", "mn", "printed"), FIELD_SHEET_CELLS)
def test_schlumberger_reproduces_the_field_sheet_k_table(
    ab2: float, mn: float, printed: str
) -> None:
    exponent = Decimal(printed).as_tuple().exponent
    assert isinstance(exponent, int)
    last_printed_digit = 10.0**exponent

    calculated = schlumberger_geometric_factor(ab2, mn)

    # The sheet rounds (or, for 10.22, truncates) to its last printed digit.
    assert abs(calculated - float(printed)) < last_printed_digit


def test_field_sheet_spacings_never_trigger_the_wide_mn_warning() -> None:
    ratios = [schlumberger_spacing_ratio(ab2, mn) for ab2, mn, _ in FIELD_SHEET_CELLS]

    assert min(ratios) == pytest.approx(4.0)
    assert all(ratio >= SCHLUMBERGER_MIN_RATIO for ratio in ratios)


@pytest.mark.parametrize(
    ("ab2", "mn", "expected"),
    [
        (1.0, 0.5, math.pi * 1.875),
        (20.0, 2.0, math.pi * 399.0 / 2.0),
        (5.5, 2.0, math.pi * 14.625),
    ],
)
def test_schlumberger_hand_calculated_values(ab2: float, mn: float, expected: float) -> None:
    assert schlumberger_geometric_factor(ab2, mn) == pytest.approx(expected, rel=1e-15)


def test_other_arrays_hand_calculated_values() -> None:
    assert wenner_geometric_factor(10.0) == pytest.approx(20.0 * math.pi)
    assert dipole_dipole_geometric_factor(5.0, 2.0) == pytest.approx(math.pi * 2 * 3 * 4 * 5)
    assert pole_dipole_geometric_factor(5.0, 2.0) == pytest.approx(2.0 * math.pi * 2 * 3 * 5)


@pytest.mark.parametrize(
    ("call", "parameter", "reason"),
    [
        (lambda: schlumberger_geometric_factor(0.0, 1.0), "ab2", "must be positive"),
        (lambda: schlumberger_geometric_factor(10.0, -1.0), "mn", "must be positive"),
        (lambda: schlumberger_geometric_factor(1.0, 2.0), "mn", "smaller than AB/2"),
        (lambda: schlumberger_geometric_factor(1.0, 3.0), "mn", "smaller than AB/2"),
        (lambda: schlumberger_geometric_factor(math.nan, 1.0), "ab2", "must be finite"),
        (lambda: wenner_geometric_factor(0.0), "a", "must be positive"),
        (lambda: dipole_dipole_geometric_factor(1.0, 0.0), "n", "must be positive"),
        (lambda: pole_dipole_geometric_factor(-1.0, 1.0), "a", "must be positive"),
        (lambda: general_geometric_factor(0.0, 1.0, 1.0, 1.0), "am", "must be positive"),
    ],
)
def test_invalid_geometry_names_the_parameter(
    call: Callable[[], float],
    parameter: str,
    reason: str,
) -> None:
    with pytest.raises(GeometryError) as error:
        call()

    assert error.value.parameter == parameter
    assert reason in error.value.reason


def test_layout_without_potential_difference_is_rejected() -> None:
    with pytest.raises(ValueError, match="K is undefined"):
        general_geometric_factor(5.0, 5.0, 5.0, 5.0)


@pytest.mark.parametrize(
    "call",
    [
        lambda: wenner_geometric_factor(1e308),
        lambda: schlumberger_geometric_factor(1e300, 1e-300),
        lambda: dipole_dipole_geometric_factor(1e200, 1e100),
    ],
)
def test_overflowing_k_is_rejected(call: Callable[[], float]) -> None:
    with pytest.raises(ValueError, match="too large"):
        call()


def test_swapped_potential_electrodes_give_negative_general_k() -> None:
    assert general_geometric_factor(6.0, 4.0, 4.0, 6.0) < 0.0


def test_dispatch_matches_the_specific_functions() -> None:
    assert geometric_factor("schlumberger", {"ab2": 20.0, "mn": 2.0}) == (
        schlumberger_geometric_factor(20.0, 2.0)
    )
    assert geometric_factor("wenner", {"a": 3.0}) == wenner_geometric_factor(3.0)
    assert geometric_factor("dipole-dipole", {"a": 3.0, "n": 2.0}) == (
        dipole_dipole_geometric_factor(3.0, 2.0)
    )
    assert geometric_factor("pole-dipole", {"a": 3.0, "n": 2.0}) == (
        pole_dipole_geometric_factor(3.0, 2.0)
    )
    assert geometric_factor("general", {"am": 4.0, "bm": 6.0, "an": 6.0, "bn": 4.0}) == (
        general_geometric_factor(4.0, 6.0, 6.0, 4.0)
    )


def test_dispatch_reports_missing_parameter() -> None:
    with pytest.raises(GeometryError, match="mn: is required"):
        geometric_factor("schlumberger", {"ab2": 20.0})


def test_dispatch_rejects_unknown_array() -> None:
    with pytest.raises(ValueError, match="unsupported array"):
        geometric_factor("square", {})  # type: ignore[arg-type]


def test_every_array_lists_its_parameters() -> None:
    assert set(ARRAY_PARAMETERS) == {
        "schlumberger",
        "wenner",
        "dipole-dipole",
        "pole-dipole",
        "general",
    }


spacings = st.floats(min_value=1e-2, max_value=1e3, allow_nan=False)
dipole_factors = st.floats(min_value=0.5, max_value=20.0, allow_nan=False)


@given(spacings, st.floats(min_value=0.01, max_value=0.99))
def test_schlumberger_equals_the_general_formula(ab2: float, fraction: float) -> None:
    mn = 2.0 * ab2 * fraction
    half = mn / 2.0
    # A at -L, B at +L, M at -l, N at +l.
    general = general_geometric_factor(ab2 - half, ab2 + half, ab2 + half, ab2 - half)

    assert schlumberger_geometric_factor(ab2, mn) == pytest.approx(general, rel=1e-9)


@given(spacings)
def test_wenner_equals_the_general_formula(a: float) -> None:
    # A, M, N, B equally spaced by a.
    assert wenner_geometric_factor(a) == pytest.approx(
        general_geometric_factor(a, 2.0 * a, 2.0 * a, a), rel=1e-12
    )


@given(spacings, dipole_factors)
def test_dipole_dipole_equals_the_general_formula(a: float, n: float) -> None:
    # B, A, M, N on a line: B at 0, A at a, M at a + n a, N at 2a + n a.
    a_position, b_position = a, 0.0
    m_position, n_position = a + n * a, 2.0 * a + n * a
    general = general_geometric_factor(
        m_position - a_position,
        m_position - b_position,
        n_position - a_position,
        n_position - b_position,
    )

    assert dipole_dipole_geometric_factor(a, n) == pytest.approx(general, rel=1e-9)


@given(spacings, dipole_factors)
def test_pole_dipole_equals_the_general_formula_with_remote_b(a: float, n: float) -> None:
    general = general_geometric_factor(n * a, math.inf, (n + 1.0) * a, math.inf)

    assert pole_dipole_geometric_factor(a, n) == pytest.approx(general, rel=1e-12)
