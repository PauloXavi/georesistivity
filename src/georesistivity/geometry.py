"""Geometric factor K of four-electrode resistivity arrays.

All lengths are in meters and K is returned in meters. The formulas assume point electrodes
on the surface of a homogeneous half-space, with current electrodes A and B and potential
electrodes M and N.

References:
    Telford, W. M.; Geldart, L. P.; Sheriff, R. E. Applied Geophysics, 2nd ed. Cambridge
    University Press, 1990.
    Keller, G. V.; Frischknecht, F. C. Electrical Methods in Geophysical Prospecting.
    Pergamon, 1966.
    Loke, M. H. Tutorial: 2-D and 3-D electrical imaging surveys. Geotomo Software.
"""

import math
from collections.abc import Mapping, Sequence
from typing import Literal

from georesistivity.validation import ensure_finite_number

ArrayType = Literal["schlumberger", "wenner", "dipole-dipole", "pole-dipole", "general"]
GeometryParameter = Literal["ab2", "mn", "a", "n", "am", "bm", "an", "bn"]

ARRAY_PARAMETERS: dict[ArrayType, tuple[GeometryParameter, ...]] = {
    "schlumberger": ("ab2", "mn"),
    "wenner": ("a",),
    "dipole-dipole": ("a", "n"),
    "pole-dipole": ("a", "n"),
    "general": ("am", "bm", "an", "bn"),
}
"""Parameters of each array. All are lengths in meters except the dimensionless ``n``."""

SCHLUMBERGER_MIN_RATIO = 4.0
"""Smallest (AB/2)/(MN/2) ratio accepted without a warning.

The classic rule AB >= 5 MN comes from the approximation K ~ pi L^2 / (2 l). K is computed
here with the exact formula, which is valid for any MN/2 < AB/2, so the warning only flags
unusually wide MN. The standard Schlumberger field sheet uses ratios down to 4.0
(AB/2 = 1.0 m with MN = 0.5 m).
"""


FIELD_SHEET_AB2_M: tuple[float, ...] = (
    1.0, 1.3, 1.8, 2.4, 3.2, 4.2, 5.5, 7.5, 10.0, 13.0, 18.0,
    24.0, 32.0, 42.0, 55.0, 75.0, 100.0, 130.0, 180.0, 240.0, 320.0,
)  # fmt: skip
"""AB/2 schedule [m] of the standard Schlumberger field sheet."""

FIELD_SHEET_MN_M: tuple[float, ...] = (0.5, 2.0, 5.0, 20.0, 50.0, 100.0)
"""MN spacings [m] (full M-N distance) of the standard Schlumberger field sheet."""

FIELD_SHEET_MN_RANGES_M: dict[float, tuple[float, float]] = {
    0.5: (1.0, 24.0),
    2.0: (5.5, 75.0),
    5.0: (18.0, 240.0),
    20.0: (55.0, 320.0),
    50.0: (130.0, 320.0),
    100.0: (240.0, 320.0),
}
"""First and last AB/2 [m] for which the standard field sheet tabulates K for each MN [m].

The ranges overlap, which is where an AB/2 is read with two MN (overlap readings).
"""


def field_sheet_cells() -> tuple[tuple[float, float], ...]:
    """Return the (AB/2, MN) pairs [m] of the standard field sheet, by AB/2 and then MN."""
    return tuple(
        (ab2, mn)
        for ab2 in FIELD_SHEET_AB2_M
        for mn in FIELD_SHEET_MN_M
        if FIELD_SHEET_MN_RANGES_M[mn][0] <= ab2 <= FIELD_SHEET_MN_RANGES_M[mn][1]
    )


class GeometryError(ValueError):
    """An electrode-geometry parameter that does not define a valid array."""

    def __init__(self, parameter: GeometryParameter, reason: str) -> None:
        super().__init__(f"{parameter}: {reason}")
        self.parameter: GeometryParameter = parameter
        self.reason = reason


def _positive(value: float, parameter: GeometryParameter) -> float:
    try:
        number = ensure_finite_number(value, parameter)
    except ValueError:
        raise GeometryError(parameter, "must be finite") from None
    if number <= 0.0:
        raise GeometryError(parameter, "must be positive")
    return number


def _finite_result(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("geometric factor is too large to represent")
    return value


def _inverse_distance(value: float, parameter: GeometryParameter) -> float:
    if isinstance(value, float) and value == math.inf:
        return 0.0
    return 1.0 / _positive(value, parameter)


def general_geometric_factor(am: float, bm: float, an: float, bn: float) -> float:
    """Return ``K = 2 pi / (1/AM - 1/BM - 1/AN + 1/BN)`` for any four-electrode layout.

    Pass ``math.inf`` as the distance to a remote electrode ("at infinity"), as in pole
    arrays. The result is negative when M and N are swapped relative to A and B.
    """
    denominator = (
        _inverse_distance(am, "am")
        - _inverse_distance(bm, "bm")
        - _inverse_distance(an, "an")
        + _inverse_distance(bn, "bn")
    )
    if denominator == 0.0:
        raise ValueError("electrode layout gives no potential difference; K is undefined")
    return _finite_result(2.0 * math.pi / denominator)


def schlumberger_geometric_factor(ab2: float, mn: float) -> float:
    """Return the exact Schlumberger K for half current spacing AB/2 and potential spacing MN.

    ``K = pi (L^2 - l^2) / (2 l)`` with ``L = AB/2`` and ``l = MN/2``. Note that ``mn`` is the
    full M-N distance, as on the field sheet, not MN/2.
    """
    half_current = _positive(ab2, "ab2")
    half_potential = _positive(mn, "mn") / 2.0
    if half_potential >= half_current:
        raise GeometryError("mn", "MN/2 must be smaller than AB/2")
    # (L - l)(L + l) instead of L^2 - l^2: no cancellation, and overflow gives inf, not an
    # OverflowError.
    difference_of_squares = (half_current - half_potential) * (half_current + half_potential)
    return _finite_result(math.pi * difference_of_squares / (2.0 * half_potential))


def schlumberger_spacing_ratio(ab2: float, mn: float) -> float:
    """Return (AB/2)/(MN/2), compared against :data:`SCHLUMBERGER_MIN_RATIO`."""
    return _positive(ab2, "ab2") / (_positive(mn, "mn") / 2.0)


def wenner_geometric_factor(a: float) -> float:
    """Return the Wenner-alpha K = 2 pi a for electrode spacing ``a``."""
    return _finite_result(2.0 * math.pi * _positive(a, "a"))


def dipole_dipole_geometric_factor(a: float, n: float) -> float:
    """Return the dipole-dipole K = pi n (n+1) (n+2) a.

    ``a`` is the dipole length and ``n a`` the distance between the inner electrodes B and M.
    """
    spacing = _positive(a, "a")
    factor = _positive(n, "n")
    return _finite_result(math.pi * factor * (factor + 1.0) * (factor + 2.0) * spacing)


def pole_dipole_geometric_factor(a: float, n: float) -> float:
    """Return the pole-dipole K = 2 pi n (n+1) a, with the remote electrode B at infinity.

    ``a`` is the M-N dipole length and ``n a`` the distance from A to M. In practice the
    remote electrode should be several times farther than the largest A-N distance.
    """
    spacing = _positive(a, "a")
    factor = _positive(n, "n")
    return _finite_result(2.0 * math.pi * factor * (factor + 1.0) * spacing)


def geometric_factor(array: ArrayType, parameters: Mapping[GeometryParameter, float]) -> float:
    """Return K for ``array`` from the parameters listed in :data:`ARRAY_PARAMETERS`."""
    if array not in ARRAY_PARAMETERS:
        raise ValueError(f"unsupported array: {array!r}")
    for parameter in ARRAY_PARAMETERS[array]:
        if parameter not in parameters:
            raise GeometryError(parameter, "is required")

    if array == "schlumberger":
        return schlumberger_geometric_factor(parameters["ab2"], parameters["mn"])
    if array == "wenner":
        return wenner_geometric_factor(parameters["a"])
    if array == "dipole-dipole":
        return dipole_dipole_geometric_factor(parameters["a"], parameters["n"])
    if array == "pole-dipole":
        return pole_dipole_geometric_factor(parameters["a"], parameters["n"])
    return general_geometric_factor(
        parameters["am"], parameters["bm"], parameters["an"], parameters["bn"]
    )


def schlumberger_k_table(
    ab2_values: Sequence[float],
    mn_values: Sequence[float],
) -> list[list[float | None]]:
    """Return K [m] for every AB/2 (rows) and MN (columns); ``None`` where MN/2 >= AB/2."""
    table: list[list[float | None]] = []
    for ab2 in ab2_values:
        row: list[float | None] = []
        for mn in mn_values:
            try:
                row.append(schlumberger_geometric_factor(ab2, mn))
            except GeometryError as exc:
                if exc.parameter != "mn" or "smaller than AB/2" not in exc.reason:
                    raise
                row.append(None)
        table.append(row)
    return table
