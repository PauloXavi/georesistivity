"""Labels and options shared by the interface pages."""

from georesistivity.models import MeasurementWarning

VOLTAGE_UNITS = ("V", "mV", "µV")
CURRENT_UNITS = ("A", "mA", "µA")
LENGTH_UNITS = ("m", "cm", "mm", "km")
OHM_METER = "\u03a9\u00b7m"

WARNING_MESSAGES: dict[MeasurementWarning, str] = {
    MeasurementWarning.NEGATIVE_APPARENT_RESISTIVITY: (
        "Negative apparent resistivity. Check the polarity of the potential electrodes, "
        "the current direction, and the cable connections."
    ),
    MeasurementWarning.SCHLUMBERGER_WIDE_MN: (
        "MN is wide for this AB/2: (AB/2)/(MN/2) is below 4. K uses the exact formula and "
        "stays correct, but the reading averages the potential over a wide interval; "
        "consider a smaller MN at this spacing."
    ),
    MeasurementWarning.STACK_HIGH_VARIATION: (
        "Repeated readings vary more than the coefficient-of-variation limit."
    ),
    MeasurementWarning.STACK_MIXED_SIGNS: (
        "Repeated readings have both positive and negative values."
    ),
}

WARNING_SHORT_LABELS: dict[MeasurementWarning, str] = {
    MeasurementWarning.NEGATIVE_APPARENT_RESISTIVITY: "negative \u03c1a",
    MeasurementWarning.SCHLUMBERGER_WIDE_MN: "wide MN",
    MeasurementWarning.STACK_HIGH_VARIATION: "CV above limit",
    MeasurementWarning.STACK_MIXED_SIGNS: "mixed signs",
}
