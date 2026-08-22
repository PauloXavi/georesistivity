"""Domain models for individual apparent-resistivity measurements."""

from dataclasses import dataclass


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

    def __post_init__(self) -> None:
        has_spacing = self.spacing_ab2_original is not None
        has_spacing_unit = self.spacing_unit is not None
        if has_spacing != has_spacing_unit:
            raise ValueError("spacing value and spacing unit must be provided together")


@dataclass(frozen=True, slots=True)
class MeasurementResult:
    """Original measurement, SI values, and its calculated scientific result."""

    measurement: Measurement
    delta_v_v: float
    current_a: float
    geometric_factor_m: float
    spacing_ab2_m: float | None
    apparent_resistivity_ohm_m: float
