"""Tests for CSV import into the field sheet and the single measurements."""

import codecs
from pathlib import Path

import pytest

from georesistivity.core import calculate_measurement
from georesistivity.csv_import import (
    CsvTable,
    ImportIssue,
    MeasurementImport,
    SheetImport,
    decode_csv,
    detect_decimal,
    detect_delimiter,
    guess_mapping,
    guess_target,
    import_measurements,
    import_sheet,
    missing_required,
    normalize_unit,
    read_csv,
)
from georesistivity.field_sheet import SheetRow, evaluate_sheet
from georesistivity.io import (
    measurement_results_to_csv,
    sounding_points_to_csv,
    sounding_readings_to_csv,
)
from georesistivity.models import Measurement
from georesistivity.services import MeasurementInput, evaluate_submission


def table(text: str, **kwargs: str) -> CsvTable:
    return read_csv(text.encode("utf-8"), **kwargs)


# ---------------------------------------------------------------------------- reading


def test_encodings_are_detected() -> None:
    assert decode_csv("AB/2;µV\n".encode()) == ("AB/2;µV\n", "UTF-8")
    assert decode_csv(codecs.BOM_UTF8 + "µ".encode()) == ("µ", "UTF-8 with BOM")
    assert decode_csv("Motivo;ΔV não".encode("cp1252", errors="replace")) == (
        "Motivo;?V não",
        "Windows-1252",
    )
    assert decode_csv(b"\x81\xe9")[1] == "ISO-8859-1"


def test_broken_utf8_after_a_bom_is_rejected() -> None:
    with pytest.raises(ValueError, match="not valid UTF-8"):
        decode_csv(codecs.BOM_UTF8 + b"\xff")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("AB/2 [m];MN [m];ΔV\n1;0,5;80", ";"),
        ("AB/2 [m],MN [m],Delta V\n1,0.5,80", ","),
        ("AB/2\tMN\tΔV\n", "\t"),
        ("sep=;\nAB/2,x;y\n", ";"),
        ("\n\nonly\n", ","),
    ],
)
def test_delimiter_detection(text: str, expected: str) -> None:
    assert detect_delimiter(text) == expected


def test_read_csv_skips_blank_lines_strips_cells_and_keeps_line_numbers() -> None:
    result = table('sep=;\nAB/2 ; MN\n\n1 ; "0,5"\n;\n1,3;0,5\n')

    assert result.delimiter == ";"
    assert result.header == ("AB/2", "MN")
    assert [(row.line, row.cells) for row in result.rows] == [
        (3, ("1", "0,5")),
        (5, ("1,3", "0,5")),
    ]
    assert result.rows[0].cell(5) == ""
    assert result.rows[0].cell(None) == ""


def test_delimiter_can_be_chosen() -> None:
    assert table("a;b,c\n1;2,3", delimiter=",").header == ("a;b", "c")


def test_files_without_header_or_with_broken_quoting_are_rejected() -> None:
    with pytest.raises(ValueError, match="no header row"):
        table("\n \n")
    with pytest.raises(ValueError, match="not valid CSV"):
        read_csv(b'a,b\n"1,2\n')


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("a,b\n1.5,2", "."),
        ("a;b\n1,5;2", ","),
        ("a;b\n1.5;2", "."),
        ("a;b\n1,5;2.5", None),
        ("a;b\n1;2", None),
        ("a;b\n1,000;2", ","),
    ],
)
def test_decimal_detection(text: str, expected: str | None) -> None:
    data = table(text)

    assert detect_decimal(data, [0, 1]) == expected


# ---------------------------------------------------------------------------- mapping


SHEET_HEADER = ("AB/2 [m]", "MN [m]", "Marker", "Reading", "Delta V", "Voltage unit", "Current",
                "Current unit", "Delta V [V]", "I [A]", "R [ohm]", "K [m]", "rho_a [ohm.m]",
                "Excluded", "Exclusion reason")  # fmt: skip


def test_own_readings_export_is_mapped_to_the_sheet() -> None:
    assert guess_target(SHEET_HEADER) == "sheet"
    assert guess_mapping(SHEET_HEADER, "sheet") == {
        "ab2": 0,
        "mn": 1,
        "delta_v": 4,
        "current": 6,
        "voltage_unit": 5,
        "current_unit": 7,
        "marker": 2,
        "excluded": 13,
        "reason": 14,
    }


def test_own_measurement_export_is_mapped_to_measurements() -> None:
    header = ("#", "Delta V", "Voltage unit", "Current", "Current unit", "K", "K unit",
              "K source", "AB/2", "Spacing unit", "MN", "MN unit", "Delta V [V]", "I [A]",
              "K [m]", "AB/2 [m]", "MN [m]", "rho_a [ohm.m]", "Warnings")  # fmt: skip

    mapping = guess_mapping(header, "measurements")

    assert guess_target(header) == "measurements"
    assert mapping == {
        "delta_v": 1,
        "voltage_unit": 2,
        "current": 3,
        "current_unit": 4,
        "geometric_factor": 5,
        "geometric_factor_unit": 6,
        "spacing_ab2": 8,
        "spacing_unit": 9,
        "mn": 10,
        "mn_unit": 11,
        "source": 7,
    }
    assert missing_required("measurements", mapping) == ()


def test_portuguese_headers_are_recognized() -> None:
    mapping = guess_mapping(("Cor", "AB/2", "MN", "ΔV", "I", "Excluir", "Motivo"), "sheet")

    assert mapping["marker"] == 0
    assert mapping["delta_v"] == 3
    assert mapping["excluded"] == 5
    assert mapping["reason"] == 6
    assert missing_required("sheet", mapping) == ()


def test_unknown_headers_leave_required_fields_missing() -> None:
    mapping = guess_mapping(("x", "y"), "sheet")

    assert missing_required("sheet", mapping) == ("ab2", "mn", "delta_v", "current")


def test_units_are_normalized() -> None:
    assert normalize_unit(" uV ") == "µV"
    assert normalize_unit("μA") == "µA"
    assert normalize_unit("mV") == "mV"


# ---------------------------------------------------------------------------- sheet import


def sheet_import(text: str, decimal: str | None = None, **kwargs: str) -> SheetImport:
    data = table(text)
    mapping = guess_mapping(data.header, "sheet")
    return import_sheet(
        data,
        mapping,
        decimal=decimal,  # type: ignore[arg-type]
        voltage_unit=kwargs.get("voltage_unit", "mV"),
        current_unit=kwargs.get("current_unit", "mA"),
        number_format=kwargs.get("number_format", "pt-BR"),  # type: ignore[arg-type]
    )


def test_sheet_rows_are_imported_with_unambiguous_text() -> None:
    result = sheet_import(
        "Cor;AB/2;MN;ΔV;I;Excluir;Motivo\n"
        "VD;1;0,5;1,234;40;;\n"
        "AM;1,3;0,5;;;;\n"
        "AZ;1,8;0,5;95;40;sim;eletrodo solto\n",
        decimal=",",
    )

    assert result.issues == ()
    assert result.total_rows == 3
    assert result.rows == (
        SheetRow(marker="VD", ab2="1", mn="0,5", delta_v="1,2340", current="40"),
        SheetRow(marker="AM", ab2="1,3", mn="0,5"),
        SheetRow(marker="AZ", ab2="1,8", mn="0,5", delta_v="95", current="40", excluded=True,
                 reason="eletrodo solto"),
    )  # fmt: skip


def test_declared_decimal_comma_reads_thousands_like_values_as_decimals() -> None:
    result = sheet_import("AB/2;MN;ΔV;I\n1;0,5;1,000;40\n", decimal=",")

    assert result.rows[0].delta_v == "1"


def test_without_a_declared_decimal_thousands_like_values_are_rejected() -> None:
    result = sheet_import("AB/2;MN;ΔV;I\n1;0,5;1,000;40\n", decimal=None)

    assert result.rows == ()
    (issue,) = result.issues
    assert issue.line == 2
    assert issue.column == "ΔV"
    assert "ambiguous" in issue.message


def test_sheet_units_come_from_the_unit_columns() -> None:
    result = sheet_import(
        "AB/2,MN,Delta V,Voltage unit,Current,Current unit\n"
        "1,0.5,0.08,V,0.04,A\n"
        "1.3,0.5,95,mV,40,mA\n"
        "1.8,0.5,1,kV,1,A\n",
        decimal=".",
    )

    assert result.voltage_unit == "V"
    assert result.current_unit == "A"
    assert len(result.rows) == 1
    assert [(issue.line, issue.column) for issue in result.issues] == [
        (3, "Voltage unit"),
        (3, "Current unit"),
        (4, "Voltage unit"),
    ]
    assert "'mV' differs from 'V'" in result.issues[0].message


def test_unsupported_file_unit_rejects_every_row() -> None:
    result = sheet_import("AB/2,MN,Delta V,Voltage unit,Current\n1,0.5,1,kV,1\n", decimal=".")

    assert result.rows == ()
    assert "unsupported voltage unit 'kV'" in result.issues[0].message


@pytest.mark.parametrize(
    ("line", "column", "message"),
    [
        ("1;3;80;40;;", "MN", "MN/2 must be smaller than AB/2"),
        ("1;0,5;80;;;", "I", "is empty, but the other value is filled"),
        ("1;0,5;80;40;sim;", "Motivo", "is required to exclude a reading"),
        ("1;0,5;80;40;talvez;", "Excluir", "'talvez' is not yes or no"),
        (";0,5;80;40;;", "AB/2", "value cannot be empty"),
        ("1;;;;;", "MN", "value cannot be empty"),
        ("abc;0,5;80;40;;", "AB/2", "invalid numeric value"),
        ("1;0,5;80;0;;", "I", "cannot be zero"),
    ],
)
def test_rejected_sheet_rows_name_line_and_column(line: str, column: str, message: str) -> None:
    result = sheet_import(f"AB/2;MN;ΔV;I;Excluir;Motivo\n{line}\n", decimal=",")

    assert result.rows == ()
    assert result.issues[0] == ImportIssue(2, column, result.issues[0].message)
    assert message in result.issues[0].message


def test_sheet_import_needs_the_required_columns() -> None:
    data = table("x,y\n1,2")

    with pytest.raises(ValueError, match="no column for: ab2, mn, delta_v, current"):
        import_sheet(
            data,
            guess_mapping(data.header, "sheet"),
            decimal=".",
            voltage_unit="mV",
            current_unit="mA",
        )


def test_issue_column_falls_back_to_the_field_name() -> None:
    # The flag sits in a fifth cell without a header, and no reason column is mapped.
    data = table("AB/2;MN;ΔV;I\n1;0,5;80;40;sim\n")
    mapping = {**guess_mapping(data.header, "sheet"), "excluded": 4, "reason": None}

    result = import_sheet(data, mapping, decimal=",", voltage_unit="mV", current_unit="mA")

    assert result.issues[0].column == "reason"


# ---------------------------------------------------------------------------- measurements


def measurement_import(text: str, decimal: str | None = ".") -> MeasurementImport:
    data = table(text)
    return import_measurements(
        data,
        guess_mapping(data.header, "measurements"),
        decimal=decimal,  # type: ignore[arg-type]
        voltage_unit="mV",
        current_unit="mA",
    )


def test_measurements_use_default_units_when_columns_are_missing() -> None:
    result = measurement_import("Delta V,Current,K,AB/2\n125,35,625,20\n")

    (measurement,) = result.measurements
    assert measurement.voltage_unit == "mV"
    assert measurement.current_unit == "mA"
    assert measurement.geometric_factor_unit == "m"
    assert measurement.spacing_ab2_original == 20.0
    assert measurement.spacing_unit == "m"
    assert result.issues == ()


def test_measurement_rows_are_validated_like_the_form() -> None:
    result = measurement_import(
        "Delta V,Current,K,MN\n125,35,-625,\n125,0,625,\nabc,35,625,\n1e306,1e-306,5,\n"
    )

    assert result.measurements == ()
    assert [(issue.line, issue.column) for issue in result.issues] == [
        (2, "K"),
        (3, "Current"),
        (4, "Delta V"),
        (5, ""),
    ]
    assert "must be positive" in result.issues[0].message
    assert "result must be finite" in result.issues[3].message


def test_measurement_import_needs_the_required_columns() -> None:
    data = table("Delta V,Current\n1,2")

    with pytest.raises(ValueError, match="no column for: geometric_factor"):
        import_measurements(
            data,
            guess_mapping(data.header, "measurements"),
            decimal=".",
            voltage_unit="mV",
            current_unit="mA",
        )


# ---------------------------------------------------------------------------- round trips


def sheet_rows() -> list[SheetRow]:
    return [
        SheetRow(marker="VD", ab2="1", mn="0,5", delta_v="80", current="40"),
        SheetRow(marker="AM", ab2="5,5", mn="0,5", delta_v="9,1", current="50"),
        SheetRow(marker="AM", ab2="5,5", mn="2", delta_v="33,3", current="50"),
        SheetRow(marker="AM", ab2="5,5", mn="2", delta_v="34", current="50"),
        SheetRow(ab2="7,5", mn="2", delta_v="1,234", current="45,5", excluded=True,
                 reason="=noise"),
        SheetRow(ab2="7,5", mn="2", delta_v="20", current="45,5"),
    ]  # fmt: skip


@pytest.mark.parametrize("dialect", ["standard", "excel-pt-br"])
def test_readings_export_round_trips_into_the_same_points(dialect: str) -> None:
    original = evaluate_sheet(sheet_rows(), voltage_unit="µV", current_unit="mA").points
    exported = sounding_readings_to_csv(original, dialect=dialect)  # type: ignore[arg-type]

    data = read_csv(exported.encode("utf-8"))
    mapping = guess_mapping(data.header, "sheet")
    decimal = detect_decimal(data, [mapping["ab2"], mapping["mn"], mapping["delta_v"]])
    imported = import_sheet(data, mapping, decimal=decimal, voltage_unit="V", current_unit="A")

    assert imported.issues == ()
    assert (imported.voltage_unit, imported.current_unit) == ("µV", "mA")
    again = evaluate_sheet(imported.rows, voltage_unit="µV", current_unit="mA").points
    assert again == original


def test_points_export_has_no_raw_readings_to_import() -> None:
    points = evaluate_sheet(sheet_rows(), voltage_unit="mV", current_unit="mA").points
    data = read_csv(sounding_points_to_csv(points).encode("utf-8"))

    assert missing_required("sheet", guess_mapping(data.header, "sheet")) == ("delta_v", "current")


def measurements() -> list[Measurement]:
    entries = [
        MeasurementInput("125", "mV", "35", "mA", "625", "m", "20", "m", "=table", "2", "m"),
        MeasurementInput("0,08", "V", "40", "µA", "6,25", "km"),
        MeasurementInput("1,2340", "µV", "1", "A", "1", "cm", "", "m", "", "50", "cm"),
        MeasurementInput("125", "mV", "35", "mA", spacing_ab2="20", mn="2",
                         geometric_factor_mode="schlumberger"),
    ]  # fmt: skip
    results = []
    for entry in entries:
        outcome = evaluate_submission(entry, [])
        assert outcome.result is not None, outcome
        results.append(outcome.result.measurement)
    return results


@pytest.mark.parametrize("dialect", ["standard", "excel-pt-br"])
def test_measurement_export_round_trips_into_the_same_measurements(dialect: str) -> None:
    original = measurements()
    exported = measurement_results_to_csv(
        [calculate_measurement(m) for m in original],
        dialect=dialect,  # type: ignore[arg-type]
    )

    data = read_csv(exported.encode("utf-8"))
    mapping = guess_mapping(data.header, "measurements")
    numeric = [mapping[name] for name in ("delta_v", "current", "geometric_factor")]
    imported = import_measurements(
        data,
        mapping,
        decimal=detect_decimal(data, numeric),
        voltage_unit="V",
        current_unit="A",
    )

    assert imported.issues == ()
    assert list(imported.measurements) == original


def test_bundled_sample_dataset_imports_as_measurements() -> None:
    path = Path(__file__).resolve().parents[1] / "examples" / "sample_measurements.csv"
    data = read_csv(path.read_bytes())
    mapping = guess_mapping(data.header, "measurements")

    result = import_measurements(
        data,
        mapping,
        decimal=detect_decimal(data, [mapping["delta_v"], mapping["current"]]),
        voltage_unit="V",
        current_unit="A",
    )

    assert guess_target(data.header) == "measurements"
    assert result.issues == ()
    assert len(result.measurements) == 8
    assert result.measurements[0].spacing_ab2_original == 1.0
    assert result.measurements[0].geometric_factor_source == "synthetic demonstration data"


def test_synthetic_ves_example_imports_into_the_field_sheet() -> None:
    path = Path(__file__).resolve().parents[1] / "examples" / "synthetic_ves_excel_pt_br.csv"
    data = read_csv(path.read_bytes())
    mapping = guess_mapping(data.header, "sheet")
    decimal = detect_decimal(data, [mapping["ab2"], mapping["mn"], mapping["delta_v"]])

    result = import_sheet(data, mapping, decimal=decimal, voltage_unit="mV", current_unit="mA")
    points = evaluate_sheet(result.rows, voltage_unit="mV", current_unit="mA").points

    assert (data.delimiter, decimal) == (";", ",")
    assert result.issues == ()
    assert len(points) == 36
    repeated = next(p for p in points if (p.point.ab2_m, p.point.mn_m) == (10.0, 2.0))
    assert len(repeated.readings) == 3
    assert repeated.statistics is not None
    assert repeated.statistics.count == 2
