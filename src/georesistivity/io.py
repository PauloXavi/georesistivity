"""Tabular serialization for apparent-resistivity measurement results."""

from collections.abc import Sequence
from typing import Literal

import pandas as pd

from georesistivity.models import MeasurementResult
from georesistivity.spreadsheet import neutralize_spreadsheet_formula
from georesistivity.survey import PointResult

CsvDialect = Literal["standard", "excel-pt-br"]
"""``standard``: UTF-8, comma-separated, decimal point (machine-readable default).
``excel-pt-br``: UTF-8 with BOM, semicolon-separated, decimal comma, which is what
Microsoft Excel expects on systems configured for Brazilian Portuguese."""

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
    "MN",
    "MN unit",
    "Delta V [V]",
    "I [A]",
    "K [m]",
    "AB/2 [m]",
    "MN [m]",
    "rho_a [ohm.m]",
    "Warnings",
)

_TEXT_COLUMNS = (
    "Voltage unit",
    "Current unit",
    "K unit",
    "K source",
    "Spacing unit",
    "MN unit",
    "Warnings",
)


_UTF8_BOM = "\ufeff"


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
        "MN": measurement.mn_original,
        "MN unit": measurement.mn_unit,
        "Delta V [V]": result.delta_v_v,
        "I [A]": result.current_a,
        "K [m]": result.geometric_factor_m,
        "AB/2 [m]": result.spacing_ab2_m,
        "MN [m]": result.mn_m,
        "rho_a [ohm.m]": result.apparent_resistivity_ohm_m,
        "Warnings": "; ".join(result.warnings) or None,
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


def _to_csv(
    dataframe: pd.DataFrame,
    text_columns: Sequence[str],
    dialect: CsvDialect,
) -> str:
    """Write ``dataframe`` as CSV, protecting ``text_columns`` against formula injection."""
    if dialect not in ("standard", "excel-pt-br"):
        raise ValueError(f"unsupported CSV dialect: {dialect!r}")
    safe = dataframe.copy()
    for column in text_columns:
        safe[column] = safe[column].map(neutralize_spreadsheet_formula)

    if dialect == "standard":
        return safe.to_csv(index=False, lineterminator="\n")
    csv_text = safe.to_csv(index=False, sep=";", decimal=",", lineterminator="\n")
    return _UTF8_BOM + csv_text


def measurement_results_to_csv(
    results: Sequence[MeasurementResult],
    *,
    dialect: CsvDialect = "standard",
) -> str:
    """Serialize results to CSV text.

    Free-text columns are protected against spreadsheet formula injection. The
    ``excel-pt-br`` dialect starts with a UTF-8 byte order mark so that symbols such as
    ``µ`` display correctly when the file is opened in Excel.
    """
    return _to_csv(measurement_results_to_dataframe(results), _TEXT_COLUMNS, dialect)


SOUNDING_POINT_COLUMNS = (
    "AB/2 [m]",
    "MN [m]",
    "Marker",
    "K [m]",
    "Readings used",
    "Readings excluded",
    "R mean [ohm]",
    "R std [ohm]",
    "CV [%]",
    "rho_a [ohm.m]",
    "rho_a std error [ohm.m]",
    "Warnings",
)

SOUNDING_READING_COLUMNS = (
    "AB/2 [m]",
    "MN [m]",
    "Marker",
    "Reading",
    "Delta V",
    "Voltage unit",
    "Current",
    "Current unit",
    "Delta V [V]",
    "I [A]",
    "R [ohm]",
    "K [m]",
    "rho_a [ohm.m]",
    "Excluded",
    "Exclusion reason",
)


def sounding_points_to_dataframe(points: Sequence[PointResult]) -> pd.DataFrame:
    """One row per (AB/2, MN) position with its combined result, in the given order."""
    records = []
    for result in points:
        statistics = result.statistics
        variation = None if statistics is None else statistics.coefficient_of_variation
        records.append(
            {
                "AB/2 [m]": result.point.ab2_m,
                "MN [m]": result.point.mn_m,
                "Marker": result.point.marker,
                "K [m]": result.geometric_factor_m,
                "Readings used": 0 if statistics is None else statistics.count,
                "Readings excluded": sum(r.reading.excluded for r in result.readings),
                "R mean [ohm]": None if statistics is None else statistics.mean,
                "R std [ohm]": None if statistics is None else statistics.standard_deviation,
                "CV [%]": None if variation is None else 100.0 * variation,
                "rho_a [ohm.m]": result.apparent_resistivity_ohm_m,
                "rho_a std error [ohm.m]": result.standard_error_ohm_m,
                "Warnings": "; ".join(result.warnings) or None,
            }
        )
    return pd.DataFrame(records, columns=SOUNDING_POINT_COLUMNS)


def sounding_readings_to_dataframe(points: Sequence[PointResult]) -> pd.DataFrame:
    """One row per reading, with original and SI values, including excluded readings."""
    records = []
    for result in points:
        for number, reading_result in enumerate(result.readings, start=1):
            reading = reading_result.reading
            records.append(
                {
                    "AB/2 [m]": result.point.ab2_m,
                    "MN [m]": result.point.mn_m,
                    "Marker": result.point.marker,
                    "Reading": number,
                    "Delta V": reading.delta_v_original,
                    "Voltage unit": reading.voltage_unit,
                    "Current": reading.current_original,
                    "Current unit": reading.current_unit,
                    "Delta V [V]": reading_result.delta_v_v,
                    "I [A]": reading_result.current_a,
                    "R [ohm]": reading_result.resistance_ohm,
                    "K [m]": result.geometric_factor_m,
                    "rho_a [ohm.m]": result.geometric_factor_m * reading_result.resistance_ohm,
                    "Excluded": reading.excluded,
                    "Exclusion reason": reading.exclusion_reason,
                }
            )
    return pd.DataFrame(records, columns=SOUNDING_READING_COLUMNS)


def sounding_points_to_csv(
    points: Sequence[PointResult],
    *,
    dialect: CsvDialect = "standard",
) -> str:
    """Serialize the combined sounding points to CSV text."""
    return _to_csv(sounding_points_to_dataframe(points), ("Marker", "Warnings"), dialect)


def sounding_readings_to_csv(
    points: Sequence[PointResult],
    *,
    dialect: CsvDialect = "standard",
) -> str:
    """Serialize every reading of the sounding to CSV text."""
    text_columns = ("Marker", "Voltage unit", "Current unit", "Exclusion reason")
    return _to_csv(sounding_readings_to_dataframe(points), text_columns, dialect)
