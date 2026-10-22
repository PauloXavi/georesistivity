"""Scientific calculations for apparent electrical resistivity."""

import math

from georesistivity.models import Measurement, MeasurementResult, MeasurementWarning
from georesistivity.units import (
    convert_current_to_amperes,
    convert_length_to_meters,
    convert_voltage_to_volts,
)
from georesistivity.validation import ensure_finite_number


def apparent_resistivity(
    delta_v_v: float,
    current_a: float,
    geometric_factor_m: float,
) -> float:
    """Calculate apparent resistivity from SI values.

    The scientific equation is ``rho_a = K * DeltaV / I``, where ``rho_a`` is
    apparent resistivity [ohm.m], ``K`` is the externally supplied geometric
    factor [m], ``DeltaV`` is potential difference [V], and ``I`` is current
    [A]. No electrode geometry is assumed, and this version does not calculate
    the geometric factor.

    ``K`` must be positive, as it is for conventional four-electrode arrays.
    ``DeltaV`` and ``I`` keep their sign because the sign convention depends on the
    acquisition setup, so the result may be negative.
    """
    delta_v = ensure_finite_number(delta_v_v, "delta_v_v")
    current = ensure_finite_number(current_a, "current_a")
    geometric_factor = ensure_finite_number(geometric_factor_m, "geometric_factor_m")

    if current == 0.0:
        raise ValueError("current_a cannot be zero")
    if geometric_factor == 0.0:
        raise ValueError("geometric_factor_m cannot be zero")
    if geometric_factor < 0.0:
        raise ValueError("geometric_factor_m must be positive")

    result = geometric_factor * delta_v / current
    if not math.isfinite(result):
        raise ValueError("apparent resistivity result must be finite")
    return result


def calculate_measurement(measurement: Measurement) -> MeasurementResult:
    """Convert and calculate one independent measurement without aggregation.

    AB/2, when supplied, must be positive. A negative apparent resistivity is kept and
    flagged with :attr:`MeasurementWarning.NEGATIVE_APPARENT_RESISTIVITY`.
    """
    delta_v_v = convert_voltage_to_volts(
        measurement.delta_v_original,
        measurement.voltage_unit,
    )
    current_a = convert_current_to_amperes(
        measurement.current_original,
        measurement.current_unit,
    )
    geometric_factor_m = convert_length_to_meters(
        measurement.geometric_factor_original,
        measurement.geometric_factor_unit,
    )
    spacing_ab2_m = None
    if measurement.spacing_ab2_original is not None and measurement.spacing_unit is not None:
        spacing_ab2_m = convert_length_to_meters(
            measurement.spacing_ab2_original,
            measurement.spacing_unit,
        )
        if spacing_ab2_m <= 0.0:
            raise ValueError("spacing_ab2 must be positive")

    rho_a = apparent_resistivity(delta_v_v, current_a, geometric_factor_m)
    warnings = (MeasurementWarning.NEGATIVE_APPARENT_RESISTIVITY,) if rho_a < 0.0 else ()

    return MeasurementResult(
        measurement=measurement,
        delta_v_v=delta_v_v,
        current_a=current_a,
        geometric_factor_m=geometric_factor_m,
        spacing_ab2_m=spacing_ab2_m,
        apparent_resistivity_ohm_m=rho_a,
        warnings=warnings,
    )
