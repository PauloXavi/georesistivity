"""Units and quality-warning texts shared by the interface pages."""

from georesistivity.app.i18n import t
from georesistivity.models import MeasurementWarning

VOLTAGE_UNITS = ("V", "mV", "µV")
CURRENT_UNITS = ("A", "mA", "µA")
LENGTH_UNITS = ("m", "cm", "mm", "km")
OHM_METER = "Ω·m"


def warning_message(warning: MeasurementWarning) -> str:
    """Full explanation of a quality warning, in the current language."""
    return t(f"warning.{warning.value}")


def warning_short(warning: MeasurementWarning) -> str:
    """Short label of a quality warning for tables, in the current language."""
    return t(f"warning_short.{warning.value}")
