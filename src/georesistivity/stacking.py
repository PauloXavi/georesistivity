"""Statistics of repeated readings at one electrode position (stacking).

Repeated readings are combined as the mean of their transfer resistances
``R_i = DeltaV_i / I_i`` (decision D-7 in docs/ARCHITECTURE.md), so that every reading has the
same weight, as resistivity meters do per stack. The apparent resistivity is then
``rho_a = K * mean(R_i)``.
"""

import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass

from georesistivity.validation import ensure_finite_number

DEFAULT_CV_THRESHOLD = 0.05
"""Coefficient of variation (5%) above which repeated readings are flagged."""


@dataclass(frozen=True, slots=True)
class StackStatistics:
    """Summary of one or more readings of the same quantity."""

    count: int
    mean: float
    standard_deviation: float | None
    """Sample standard deviation (n - 1); ``None`` for a single reading."""
    coefficient_of_variation: float | None
    """``standard_deviation / |mean|`` as a fraction; ``None`` for a single reading or a zero
    mean."""
    standard_error: float | None
    """Standard error of the mean, ``standard_deviation / sqrt(count)``."""
    mixed_signs: bool
    """Whether the readings have both positive and negative values."""


def stack(values: Sequence[float]) -> StackStatistics:
    """Return the statistics of ``values``, which must be finite and not empty."""
    numbers = [ensure_finite_number(value, "value") for value in values]
    if not numbers:
        raise ValueError("at least one value is required")

    count = len(numbers)
    mean = statistics.fmean(numbers)
    mixed_signs = any(number > 0.0 for number in numbers) and any(
        number < 0.0 for number in numbers
    )
    if count == 1:
        return StackStatistics(
            count=1,
            mean=mean,
            standard_deviation=None,
            coefficient_of_variation=None,
            standard_error=None,
            mixed_signs=False,
        )

    deviation = statistics.stdev(numbers, xbar=mean)
    return StackStatistics(
        count=count,
        mean=mean,
        standard_deviation=deviation,
        coefficient_of_variation=deviation / abs(mean) if mean != 0.0 else None,
        standard_error=deviation / math.sqrt(count),
        mixed_signs=mixed_signs,
    )
