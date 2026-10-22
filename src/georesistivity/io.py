"""Tabular serialization for apparent-resistivity measurement results."""

from collections.abc import Sequence
from typing import Literal

import pandas as pd

from georesistivity.models import MeasurementResult

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

# Spreadsheet applications evaluate cells starting with these characters as formulas.
# See OWASP "CSV Injection".
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

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


def neutralize_spreadsheet_formula(value: object) -> object:
    """Prefix text that a spreadsheet would evaluate as a formula with an apostrophe."""
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return f"'{value}"
    return value


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
    dataframe = measurement_results_to_dataframe(results)
    for column in _TEXT_COLUMNS:
        dataframe[column] = dataframe[column].map(neutralize_spreadsheet_formula)

    if dialect == "standard":
        return dataframe.to_csv(index=False, lineterminator="\n")
    if dialect == "excel-pt-br":
        csv_text = dataframe.to_csv(index=False, sep=";", decimal=",", lineterminator="\n")
        return _UTF8_BOM + csv_text
    raise ValueError(f"unsupported CSV dialect: {dialect!r}")
