"""Readings and electrode positions of a vertical electrical sounding (VES).

A sounding point is one Schlumberger electrode position, defined by AB/2 and the full MN
spacing. The same AB/2 may appear with two MN (overlap readings), and each position may hold
repeated readings, which are combined as the mean of their transfer resistances (D-7).
"""

from collections.abc import Sequence
from dataclasses import dataclass

from georesistivity.geometry import (
    SCHLUMBERGER_MIN_RATIO,
    schlumberger_geometric_factor,
    schlumberger_spacing_ratio,
)
from georesistivity.models import MeasurementFieldError, MeasurementWarning
from georesistivity.stacking import DEFAULT_CV_THRESHOLD, StackStatistics, stack
from georesistivity.units import convert_current_to_amperes, convert_voltage_to_volts


@dataclass(frozen=True, slots=True)
class Reading:
    """One DeltaV and I reading with original values and units."""

    delta_v_original: float
    voltage_unit: str
    current_original: float
    current_unit: str
    excluded: bool = False
    exclusion_reason: str | None = None

    def __post_init__(self) -> None:
        if self.excluded and not (self.exclusion_reason and self.exclusion_reason.strip()):
            raise ValueError("an excluded reading needs a reason")


@dataclass(frozen=True, slots=True)
class SoundingPoint:
    """One Schlumberger electrode position and its readings, in acquisition order."""

    ab2_m: float
    mn_m: float
    readings: tuple[Reading, ...]
    marker: str | None = None
    """Cable or reel marker colour of this AB/2, as on the field sheet."""


@dataclass(frozen=True, slots=True)
class ReadingResult:
    """A reading converted to SI, with its transfer resistance."""

    reading: Reading
    delta_v_v: float
    current_a: float
    resistance_ohm: float


@dataclass(frozen=True, slots=True)
class PointResult:
    """Geometric factor, statistics, and apparent resistivity of one sounding point."""

    point: SoundingPoint
    geometric_factor_m: float
    readings: tuple[ReadingResult, ...]
    """Every reading, including excluded ones."""
    statistics: StackStatistics | None
    """Statistics of the transfer resistance of the included readings; ``None`` if all
    readings are excluded."""
    warnings: tuple[MeasurementWarning, ...] = ()

    @property
    def apparent_resistivity_ohm_m(self) -> float | None:
        """``K * mean(R)``, or ``None`` when no reading is included."""
        if self.statistics is None:
            return None
        return self.geometric_factor_m * self.statistics.mean

    @property
    def standard_error_ohm_m(self) -> float | None:
        """``K * standard error of R``, or ``None`` for fewer than two included readings."""
        if self.statistics is None or self.statistics.standard_error is None:
            return None
        return self.geometric_factor_m * self.statistics.standard_error


def evaluate_reading(reading: Reading) -> ReadingResult:
    """Convert one reading to SI and compute ``R = DeltaV / I``."""
    try:
        delta_v_v = convert_voltage_to_volts(reading.delta_v_original, reading.voltage_unit)
    except ValueError as exc:
        raise MeasurementFieldError("delta_v", str(exc)) from exc
    try:
        current_a = convert_current_to_amperes(reading.current_original, reading.current_unit)
    except ValueError as exc:
        raise MeasurementFieldError("current", str(exc)) from exc
    if current_a == 0.0:
        raise MeasurementFieldError("current", "cannot be zero")
    return ReadingResult(reading, delta_v_v, current_a, delta_v_v / current_a)


def evaluate_point(
    point: SoundingPoint,
    *,
    cv_threshold: float = DEFAULT_CV_THRESHOLD,
) -> PointResult:
    """Compute K, combine the included readings, and flag quality problems."""
    if not point.readings:
        raise ValueError("a sounding point needs at least one reading")
    geometric_factor_m = schlumberger_geometric_factor(point.ab2_m, point.mn_m)
    readings = tuple(evaluate_reading(reading) for reading in point.readings)
    included = [result.resistance_ohm for result in readings if not result.reading.excluded]
    statistics = stack(included) if included else None

    warnings: list[MeasurementWarning] = []
    if statistics is not None:
        if statistics.mean < 0.0:
            warnings.append(MeasurementWarning.NEGATIVE_APPARENT_RESISTIVITY)
        variation = statistics.coefficient_of_variation
        if variation is not None and variation > cv_threshold:
            warnings.append(MeasurementWarning.STACK_HIGH_VARIATION)
        if statistics.mixed_signs:
            warnings.append(MeasurementWarning.STACK_MIXED_SIGNS)
    if schlumberger_spacing_ratio(point.ab2_m, point.mn_m) < SCHLUMBERGER_MIN_RATIO:
        warnings.append(MeasurementWarning.SCHLUMBERGER_WIDE_MN)

    return PointResult(point, geometric_factor_m, readings, statistics, tuple(warnings))


def sort_points(points: Sequence[PointResult]) -> tuple[PointResult, ...]:
    """Order points by AB/2 and then MN, as on the field sheet."""
    return tuple(sorted(points, key=lambda result: (result.point.ab2_m, result.point.mn_m)))
