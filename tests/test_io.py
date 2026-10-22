"""Tests for tabular records and CSV export."""

import csv
from io import StringIO
from pathlib import Path

import pandas as pd
import pytest

from georesistivity import (
    TABLE_COLUMNS,
    Measurement,
    calculate_measurement,
    measurement_result_to_record,
    measurement_results_to_csv,
    measurement_results_to_dataframe,
)
from georesistivity.field_sheet import SheetRow, evaluate_sheet
from georesistivity.io import (
    SOUNDING_POINT_COLUMNS,
    SOUNDING_READING_COLUMNS,
    sounding_points_to_csv,
    sounding_points_to_dataframe,
    sounding_readings_to_csv,
    sounding_readings_to_dataframe,
)
from georesistivity.survey import PointResult


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
    sample_path = Path(__file__).resolve().parents[1] / "examples" / "sample_measurements.csv"
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


@pytest.mark.parametrize(
    "source",
    ['=HYPERLINK("http://example.com","x")', "+1+1", "-2+3", "@SUM(A1)", "\tcmd", "\rcmd"],
)
def test_csv_export_neutralizes_spreadsheet_formulas(source: str) -> None:
    results = [make_result(100.0, source=source)]

    rows = list(csv.DictReader(StringIO(measurement_results_to_csv(results))))

    assert rows[0]["K source"] == f"'{source}"


def test_dataframe_keeps_original_text_for_display() -> None:
    source = "=1+1"
    dataframe = measurement_results_to_dataframe([make_result(100.0, source=source)])

    assert dataframe["K source"].tolist() == [source]


def test_plain_text_is_not_modified_in_csv() -> None:
    results = [make_result(100.0, source="field sheet 3")]

    rows = list(csv.DictReader(StringIO(measurement_results_to_csv(results))))

    assert rows[0]["K source"] == "field sheet 3"


def test_standard_csv_has_no_byte_order_mark() -> None:
    exported = measurement_results_to_csv([make_result(100.0)])

    assert not exported.startswith("\ufeff")
    assert exported.startswith("#,Delta V,")


def test_excel_pt_br_csv_uses_bom_semicolon_and_decimal_comma() -> None:
    results = [make_result(125.0, spacing=2.5, source="tabela")]

    exported = measurement_results_to_csv(results, dialect="excel-pt-br")

    assert exported.startswith("\ufeff#;Delta V;")
    rows = list(csv.DictReader(StringIO(exported.removeprefix("\ufeff")), delimiter=";"))
    assert rows[0]["Delta V"] == "125,0"
    assert rows[0]["Delta V [V]"] == "0,125"
    assert rows[0]["AB/2 [m]"] == "2,5"
    assert rows[0]["rho_a [ohm.m]"] == "31,25"
    assert rows[0]["K source"] == "tabela"


def test_excel_pt_br_csv_round_trips_micro_sign() -> None:
    measurement = Measurement(
        delta_v_original=10.0,
        voltage_unit="µV",
        current_original=1.0,
        current_unit="mA",
        geometric_factor_original=5.0,
        geometric_factor_unit="m",
    )

    exported = measurement_results_to_csv(
        [calculate_measurement(measurement)], dialect="excel-pt-br"
    )

    assert "µV" in exported.encode("utf-8").decode("utf-8-sig")


def test_unknown_csv_dialect_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported CSV dialect"):
        measurement_results_to_csv([make_result(1.0)], dialect="tsv")  # type: ignore[arg-type]


def test_warnings_are_recorded_in_table_and_csv() -> None:
    results = [make_result(-100.0), make_result(100.0)]

    dataframe = measurement_results_to_dataframe(results)
    rows = list(csv.DictReader(StringIO(measurement_results_to_csv(results))))

    assert dataframe["Warnings"].iloc[0] == "negative_apparent_resistivity"
    assert pd.isna(dataframe["Warnings"].iloc[1])
    assert rows[0]["Warnings"] == "negative_apparent_resistivity"
    assert rows[1]["Warnings"] == ""


def test_mn_is_exported_with_original_and_si_values() -> None:
    measurement = Measurement(
        delta_v_original=100.0,
        voltage_unit="mV",
        current_original=20.0,
        current_unit="mA",
        geometric_factor_original=626.7477,
        geometric_factor_unit="m",
        spacing_ab2_original=20.0,
        spacing_unit="m",
        mn_original=200.0,
        mn_unit="cm",
    )

    rows = list(
        csv.DictReader(StringIO(measurement_results_to_csv([calculate_measurement(measurement)])))
    )

    assert rows[0]["MN"] == "200.0"
    assert rows[0]["MN unit"] == "cm"
    assert rows[0]["MN [m]"] == "2.0"


def sounding_points() -> tuple[PointResult, ...]:
    rows = (
        SheetRow(marker="VD", ab2="10", mn="2", delta_v="80", current="40"),
        SheetRow(marker="VD", ab2="10", mn="2", delta_v="81,6", current="40"),
        SheetRow(ab2="10", mn="2", delta_v="400", current="40", excluded=True, reason="=noise"),
        SheetRow(ab2="1", mn="0,5", delta_v="80", current="40"),
    )
    return evaluate_sheet(rows, voltage_unit="mV", current_unit="mA").points


def test_sounding_points_table_has_one_row_per_position() -> None:
    dataframe = sounding_points_to_dataframe(sounding_points())

    assert tuple(dataframe.columns) == SOUNDING_POINT_COLUMNS
    assert dataframe["AB/2 [m]"].tolist() == [1.0, 10.0]
    row = dataframe.iloc[1]
    assert row["Marker"] == "VD"
    assert row["Readings used"] == 2
    assert row["Readings excluded"] == 1
    assert row["R mean [ohm]"] == pytest.approx(2.02)
    assert row["CV [%]"] == pytest.approx(100 * 0.04 / 2.02 / 2**0.5, rel=1e-6)
    assert row["rho_a [ohm.m]"] == pytest.approx(row["K [m]"] * 2.02)
    assert pd.isna(dataframe.iloc[0]["CV [%]"])


def test_sounding_readings_table_keeps_excluded_readings() -> None:
    dataframe = sounding_readings_to_dataframe(sounding_points())

    assert tuple(dataframe.columns) == SOUNDING_READING_COLUMNS
    assert len(dataframe) == 4
    excluded = dataframe[dataframe["Excluded"]]
    assert excluded["Exclusion reason"].tolist() == ["=noise"]
    assert excluded["Reading"].tolist() == [3]


def test_sounding_csv_exports_protect_text_and_support_excel_pt_br() -> None:
    readings = sounding_readings_to_csv(sounding_points())
    points = sounding_points_to_csv(sounding_points(), dialect="excel-pt-br")

    rows = list(csv.DictReader(StringIO(readings)))
    assert [row["Exclusion reason"] for row in rows if row["Excluded"] == "True"] == ["'=noise"]
    assert points.startswith("﻿AB/2 [m];MN [m];Marker;")
    assert "\n10,0;2,0;VD;" in points


def test_sounding_exports_reject_unknown_dialect() -> None:
    with pytest.raises(ValueError, match="unsupported CSV dialect"):
        sounding_points_to_csv(sounding_points(), dialect="tsv")  # type: ignore[arg-type]
