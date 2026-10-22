"""Scientific core for apparent-resistivity calculations.

Public names are imported lazily, so ``import georesistivity`` does not load pandas or
Matplotlib until a tabular or plotting function is actually used.
"""

from importlib import import_module
from typing import TYPE_CHECKING, Any

__version__ = "0.2.0"

_EXPORTS: dict[str, str] = {
    "AmbiguousNumberError": "georesistivity.validation",
    "Measurement": "georesistivity.models",
    "MeasurementField": "georesistivity.models",
    "MeasurementFieldError": "georesistivity.models",
    "MeasurementResult": "georesistivity.models",
    "MeasurementWarning": "georesistivity.models",
    "PlotPoint": "georesistivity.plotting",
    "TABLE_COLUMNS": "georesistivity.io",
    "apparent_resistivity": "georesistivity.core",
    "calculate_measurement": "georesistivity.core",
    "convert_current_to_amperes": "georesistivity.units",
    "convert_length_to_meters": "georesistivity.units",
    "convert_voltage_to_volts": "georesistivity.units",
    "create_resistivity_figure": "georesistivity.plotting",
    "find_log_incompatible_points": "georesistivity.plotting",
    "measurement_result_to_record": "georesistivity.io",
    "measurement_results_to_csv": "georesistivity.io",
    "measurement_results_to_dataframe": "georesistivity.io",
    "parse_number": "georesistivity.validation",
    "prepare_plot_points": "georesistivity.plotting",
}

__all__ = [
    "TABLE_COLUMNS",
    "AmbiguousNumberError",
    "Measurement",
    "MeasurementField",
    "MeasurementFieldError",
    "MeasurementResult",
    "MeasurementWarning",
    "PlotPoint",
    "__version__",
    "apparent_resistivity",
    "calculate_measurement",
    "convert_current_to_amperes",
    "convert_length_to_meters",
    "convert_voltage_to_volts",
    "create_resistivity_figure",
    "find_log_incompatible_points",
    "measurement_result_to_record",
    "measurement_results_to_csv",
    "measurement_results_to_dataframe",
    "parse_number",
    "prepare_plot_points",
]


def __getattr__(name: str) -> Any:
    try:
        module_name = _EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_EXPORTS})


if TYPE_CHECKING:
    from georesistivity.core import apparent_resistivity, calculate_measurement
    from georesistivity.io import (
        TABLE_COLUMNS,
        measurement_result_to_record,
        measurement_results_to_csv,
        measurement_results_to_dataframe,
    )
    from georesistivity.models import (
        Measurement,
        MeasurementField,
        MeasurementFieldError,
        MeasurementResult,
        MeasurementWarning,
    )
    from georesistivity.plotting import (
        PlotPoint,
        create_resistivity_figure,
        find_log_incompatible_points,
        prepare_plot_points,
    )
    from georesistivity.units import (
        convert_current_to_amperes,
        convert_length_to_meters,
        convert_voltage_to_volts,
    )
    from georesistivity.validation import AmbiguousNumberError, parse_number
