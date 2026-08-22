"""Tests for tabular records and CSV export."""

import csv
from io import StringIO
from pathlib import Path

import pytest

from georesistivity import (
    TABLE_COLUMNS,
    Measurement,
    calculate_measurement,
    measurement_result_to_record,
    measurement_results_to_csv,
    measurement_results_to_dataframe,
)


def make_result(
    delta_v: float,
    *,
    spacing: float | None = None,
    source: str | None = None,
):
    measurement = Measurement(
        delta_v_original=delta_v,
        voltage_unit="mV",
        current_original=20.0,
        current_unit="mA",
        geometric_factor_original=5.0,
        geometric_factor_unit="m",
        spacing_ab2_original=spacing,
        spacing_unit="m" if spacing is not None else None,
        geometric_factor_source=source,
    )
    return calculate_measurement(measurement)


def test_measurement_result_becomes_traceable_record() -> None:
    result = make_result(100.0, spacing=2.5, source="table")

    record = measurement_result_to_record(result, acquisition_index=3)

    assert tuple(record) == TABLE_COLUMNS
    assert record["#"] == 3
    assert record["Delta V"] == 100.0
    assert record["Voltage unit"] == "mV"
    assert record["K source"] == "table"
    assert record["AB/2"] == 2.5
    assert record["Delta V [V]"] == pytest.approx(0.1)
    assert record["I [A]"] == pytest.approx(0.02)
    assert record["K [m]"] == pytest.approx(5.0)
    assert record["AB/2 [m]"] == pytest.approx(2.5)
    assert record["rho_a [ohm.m]"] == pytest.approx(25.0)


def test_dataframe_preserves_acquisition_order() -> None:
    results = [make_result(100.0), make_result(50.0), make_result(75.0)]

    dataframe = measurement_results_to_dataframe(results)

    assert tuple(dataframe.columns) == TABLE_COLUMNS
    assert dataframe["#"].tolist() == [1, 2, 3]
    assert dataframe["Delta V"].tolist() == [100.0, 50.0, 75.0]


def test_csv_export_contains_original_si_and_result_values() -> None:
    results = [make_result(100.0, spacing=2.5, source="equipment")]

    exported = measurement_results_to_csv(results)
    rows = list(csv.DictReader(StringIO(exported)))

    assert len(rows) == 1
    assert rows[0]["Delta V"] == "100.0"
    assert rows[0]["Voltage unit"] == "mV"
    assert rows[0]["K source"] == "equipment"
    assert float(rows[0]["Delta V [V]"]) == pytest.approx(0.1)
    assert float(rows[0]["rho_a [ohm.m]"]) == pytest.approx(25.0)


def test_sample_dataset_is_synthetic_and_scientifically_consistent() -> None:
    sample_path = Path("examples/sample_measurements.csv")
    with sample_path.open(encoding="utf-8", newline="") as sample_file:
        rows = list(csv.DictReader(sample_file))

    assert 6 <= len(rows) <= 10
    assert {row["dataset_note"] for row in rows} == {"synthetic demonstration data"}

    for row in rows:
        measurement = Measurement(
            delta_v_original=float(row["Delta V"]),
            voltage_unit=row["Voltage unit"],
            current_original=float(row["Current"]),
            current_unit=row["Current unit"],
            geometric_factor_original=float(row["K"]),
            geometric_factor_unit=row["K unit"],
            spacing_ab2_original=float(row["AB/2"]),
            spacing_unit=row["Spacing unit"],
            geometric_factor_source=row["K source"],
        )
        calculated = calculate_measurement(measurement)
        assert calculated.apparent_resistivity_ohm_m == pytest.approx(float(row["rho_a [ohm.m]"]))
