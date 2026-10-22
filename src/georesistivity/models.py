"""Domain models for individual apparent-resistivity measurements."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

MeasurementField = Literal["delta_v", "current", "geometric_factor", "spacing_ab2", "mn"]


class MeasurementFieldError(ValueError):
    """A measurement value rejected because of one specific input field."""

    def __init__(self, field: MeasurementField, reason: str) -> None:
        super().__init__(f"{field}: {reason}")
        self.field: MeasurementField = field
        self.reason = reason


class MeasurementWarning(StrEnum):
    """Quality flags attached to a calculated measurement without rejecting it."""

    NEGATIVE_APPARENT_RESISTIVITY = "negative_apparent_resistivity"
    """rho_a < 0, which usually indicates reversed polarity, swapped cables, or a reading
    error. The sign of DeltaV and I depends on the acquisition convention, so the value is
    kept and flagged instead of rejected."""

    SCHLUMBERGER_WIDE_MN = "schlumberger_wide_mn"
    """K was calculated for Schlumberger with (AB/2)/(MN/2) below
    :data:`georesistivity.geometry.SCHLUMBERGER_MIN_RATIO`. K is exact, but the reading
    averages the potential over an unusually wide interval."""

    STACK_HIGH_VARIATION = "stack_high_variation"
    """Repeated readings at one position vary more than the coefficient-of-variation limit."""

    STACK_MIXED_SIGNS = "stack_mixed_signs"
    """Repeated readings at one position have transfer resistances of both signs."""


@dataclass(frozen=True, slots=True)
class Measurement:
    """Original values and units supplied for one independent measurement."""

    delta_v_original: float
    voltage_unit: str
    current_original: float
    current_unit: str
    geometric_factor_original: float
    geometric_factor_unit: str
    spacing_ab2_original: float | None = None
    spacing_unit: str | None = None
    geometric_factor_source: str | None = None
    mn_original: float | None = None
    """Full M-N potential-electrode spacing, as on the field sheet (not MN/2)."""
    mn_unit: str | None = None

    def __post_init__(self) -> None:
        has_spacing = self.spacing_ab2_original is not None
        has_spacing_unit = self.spacing_unit is not None
        if has_spacing != has_spacing_unit:
            raise ValueError("spacing value and spacing unit must be provided together")
        if (self.mn_original is None) != (self.mn_unit is None):
            raise ValueError("MN value and MN unit must be provided together")


@dataclass(frozen=True, slots=True)
class MeasurementResult:
    """Original measurement, SI values, and its calculated scientific result."""

    measurement: Measurement
    delta_v_v: float
    current_a: float
    geometric_factor_m: float
    spacing_ab2_m: float | None
    apparent_resistivity_ohm_m: float
    warnings: tuple[MeasurementWarning, ...] = ()
    mn_m: float | None = None
