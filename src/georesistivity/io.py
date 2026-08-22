"""Tabular serialization for apparent-resistivity measurement results."""

from collections.abc import Sequence

import pandas as pd

from georesistivity.models import MeasurementResult

TABLE_COLUMNS = (
    "#",
    "Delta V",
    "Voltage unit",
    "Current",
    "Current unit",
    "K",
    "K unit",
    "K source",
    "AB/2",
    "Spacing unit",
    "Delta V [V]",
    "I [A]",
    "K [m]",
    "AB/2 [m]",
    "rho_a [ohm.m]",
)


def measurement_result_to_record(
    result: MeasurementResult,
    acquisition_index: int,
) -> dict[str, object]:
    """Convert one result to a traceable tabular record."""
    measurement = result.measurement
    return {
        "#": acquisition_index,
        "Delta V": measurement.delta_v_original,
        "Voltage unit": measurement.voltage_unit,
        "Current": measurement.current_original,
        "Current unit": measurement.current_unit,
        "K": measurement.geometric_factor_original,
        "K unit": measurement.geometric_factor_unit,
        "K source": measurement.geometric_factor_source,
        "AB/2": measurement.spacing_ab2_original,
        "Spacing unit": measurement.spacing_unit,
        "Delta V [V]": result.delta_v_v,
        "I [A]": result.current_a,
        "K [m]": result.geometric_factor_m,
        "AB/2 [m]": result.spacing_ab2_m,
        "rho_a [ohm.m]": result.apparent_resistivity_ohm_m,
    }


def measurement_results_to_dataframe(
    results: Sequence[MeasurementResult],
) -> pd.DataFrame:
    """Build a DataFrame without changing the acquisition order."""
    records = [
        measurement_result_to_record(result, acquisition_index=index)
        for index, result in enumerate(results, start=1)
    ]
    return pd.DataFrame(records, columns=TABLE_COLUMNS)


def measurement_results_to_csv(results: Sequence[MeasurementResult]) -> str:
    """Serialize results to UTF-8-compatible CSV text."""
    return measurement_results_to_dataframe(results).to_csv(index=False, lineterminator="\n")
