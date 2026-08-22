"""Scientific core for apparent-resistivity calculations."""

from georesistivity.core import apparent_resistivity, calculate_measurement
from georesistivity.models import Measurement, MeasurementResult
from georesistivity.units import (
    convert_current_to_amperes,
    convert_length_to_meters,
    convert_voltage_to_volts,
)
from georesistivity.validation import parse_number

__all__ = [
    "Measurement",
    "MeasurementResult",
    "apparent_resistivity",
    "calculate_measurement",
    "convert_current_to_amperes",
    "convert_length_to_meters",
    "convert_voltage_to_volts",
    "parse_number",
]
