"""Import of CSV files into the field sheet or the single measurements.

The importer reads the CSV files that GeoResistivity exports, in both dialects, and other
spreadsheets after their columns are mapped. Reading follows four rules:

1. The encoding is UTF-8 (with or without BOM) or, failing that, Windows-1252, which is what
   Excel saves on Portuguese systems.
2. The separator is ``;``, ``,``, or tab, taken from an Excel ``sep=`` line or from the header.
3. The decimal separator applies to the whole file (decision D-1): a comma-separated file
   uses a point; otherwise the numeric cells declare it. When the cells do not settle it,
   each value follows :func:`~georesistivity.validation.parse_number`, which rejects
   thousands-like values such as ``1,000``.
4. Every rejected row is reported with its line in the file, its column, and the reason; no
   row is dropped silently.

This module does not import Streamlit or pandas.
"""

import codecs
import csv
import io
import re
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from georesistivity.field_sheet import SheetColumn, SheetRow, evaluate_sheet
from georesistivity.formatting import NumberFormat, format_for_input
from georesistivity.models import Measurement, MeasurementField
from georesistivity.services import MeasurementInput, evaluate_submission
from georesistivity.spreadsheet import restore_spreadsheet_text
from georesistivity.units import convert_current_to_amperes, convert_voltage_to_volts
from georesistivity.validation import parse_number, parse_number_with_decimal

ImportTarget = Literal["sheet", "measurements"]
DecimalSeparator = Literal[".", ","]
ImportField = Literal[
    "ab2",
    "mn",
    "delta_v",
    "current",
    "voltage_unit",
    "current_unit",
    "marker",
    "excluded",
    "reason",
    "geometric_factor",
    "geometric_factor_unit",
    "spacing_ab2",
    "spacing_unit",
    "mn_unit",
    "source",
]
Mapping_ = Mapping[ImportField, int | None]

DELIMITERS = (";", ",", "\t")

TARGET_FIELDS: dict[ImportTarget, tuple[ImportField, ...]] = {
    "sheet": (
        "ab2",
        "mn",
        "delta_v",
        "current",
        "voltage_unit",
        "current_unit",
        "marker",
        "excluded",
        "reason",
    ),
    "measurements": (
        "delta_v",
        "voltage_unit",
        "current",
        "current_unit",
        "geometric_factor",
        "geometric_factor_unit",
        "spacing_ab2",
        "spacing_unit",
        "mn",
        "mn_unit",
        "source",
    ),
}
REQUIRED_FIELDS: dict[ImportTarget, tuple[ImportField, ...]] = {
    "sheet": ("ab2", "mn", "delta_v", "current"),
    "measurements": ("delta_v", "current", "geometric_factor"),
}

# Header names recognized for each field, normalized (NFKC, case-folded, no spaces), in order
# of preference. They cover the GeoResistivity exports and common Portuguese names.
_SHEET_ALIASES: dict[ImportField, tuple[str, ...]] = {
    "ab2": ("ab/2[m]", "ab/2", "ab/2(m)", "ab2"),
    "mn": ("mn[m]", "mn", "mn(m)"),
    "delta_v": ("δv", "deltav", "dv", "ddp"),
    "current": ("i", "current", "corrente"),
    "voltage_unit": ("voltageunit", "unidadeδv", "unidadedev"),
    "current_unit": ("currentunit", "unidadei", "unidadedei"),
    "marker": ("marker", "cor", "color", "colour", "marcador"),
    "excluded": ("excluded", "exclude", "excluída", "excluida", "excluir"),
    "reason": ("exclusionreason", "reason", "motivo"),
}
_MEASUREMENT_ALIASES: dict[ImportField, tuple[str, ...]] = {
    "delta_v": ("deltav", "δv", "dv", "ddp"),
    "voltage_unit": ("voltageunit",),
    "current": ("current", "i", "corrente"),
    "current_unit": ("currentunit",),
    "geometric_factor": ("k", "geometricfactor", "fatorgeométrico", "k[m]"),
    "geometric_factor_unit": ("kunit",),
    "spacing_ab2": ("ab/2", "ab/2[m]", "ab2"),
    "spacing_unit": ("spacingunit",),
    "mn": ("mn", "mn[m]"),
    "mn_unit": ("mnunit",),
    "source": ("ksource", "source", "fonte"),
}
_ALIASES: dict[ImportTarget, dict[ImportField, tuple[str, ...]]] = {
    "sheet": _SHEET_ALIASES,
    "measurements": _MEASUREMENT_ALIASES,
}

_TRUE = {"true", "1", "yes", "y", "sim", "s", "x", "verdadeiro"}
_FALSE = {"false", "0", "no", "n", "não", "nao", "falso", ""}
_UNIT_ALIASES = {"uV": "µV", "μV": "µV", "uA": "µA", "μA": "µA"}

_COMMA_DECIMAL = re.compile(r"[+-]?\d*,\d+([eE][+-]?\d+)?")
_POINT_DECIMAL = re.compile(r"[+-]?\d*\.\d+([eE][+-]?\d+)?")


@dataclass(frozen=True, slots=True)
class CsvRow:
    """One data row and the line where it ends in the file."""

    line: int
    cells: tuple[str, ...]

    def cell(self, index: int | None) -> str:
        if index is None or index >= len(self.cells):
            return ""
        return self.cells[index]


@dataclass(frozen=True, slots=True)
class CsvTable:
    """A decoded CSV file: header, data rows, and how it was read."""

    header: tuple[str, ...]
    rows: tuple[CsvRow, ...]
    delimiter: str
    encoding: str


@dataclass(frozen=True, slots=True)
class ImportIssue:
    """A row that was not imported: its line in the file, the column, and the reason."""

    line: int
    column: str
    message: str


@dataclass(frozen=True, slots=True)
class SheetImport:
    """Field-sheet rows read from a file, the units they use, and the rejected rows."""

    rows: tuple[SheetRow, ...]
    voltage_unit: str
    current_unit: str
    issues: tuple[ImportIssue, ...]
    total_rows: int


@dataclass(frozen=True, slots=True)
class MeasurementImport:
    """Single measurements read from a file and the rejected rows."""

    measurements: tuple[Measurement, ...]
    issues: tuple[ImportIssue, ...]
    total_rows: int


# ---------------------------------------------------------------------------- reading


def decode_csv(data: bytes) -> tuple[str, str]:
    """Return the text of ``data`` and the name of the encoding that was used."""
    if data.startswith(codecs.BOM_UTF8):
        try:
            return data[len(codecs.BOM_UTF8) :].decode("utf-8"), "UTF-8 with BOM"
        except UnicodeDecodeError as exc:
            raise ValueError("the file starts like UTF-8 but is not valid UTF-8") from exc
    try:
        return data.decode("utf-8"), "UTF-8"
    except UnicodeDecodeError:
        pass
    try:
        return data.decode("cp1252"), "Windows-1252"
    except UnicodeDecodeError:
        return data.decode("latin-1"), "ISO-8859-1"


def _first_line(text: str) -> str:
    return next((line for line in text.splitlines() if line.strip()), "")


def detect_delimiter(text: str) -> str:
    """Return the separator of ``text``: an Excel ``sep=`` line, or the most frequent in the
    header among ``;``, ``,``, and tab (``,`` when the header has none)."""
    header = _first_line(text)
    if header.casefold().startswith("sep=") and len(header) > 4:
        return header[4]
    counts = {delimiter: header.count(delimiter) for delimiter in DELIMITERS}
    best = max(DELIMITERS, key=lambda delimiter: counts[delimiter])
    return best if counts[best] else ","


def read_csv(data: bytes, *, delimiter: str | None = None) -> CsvTable:
    """Decode and split a CSV file. Blank lines are skipped; cells are stripped."""
    text, encoding = decode_csv(data)
    chosen = delimiter or detect_delimiter(text)
    if _first_line(text).casefold().startswith("sep="):
        text = text.split("\n", 1)[1] if "\n" in text else ""

    header: tuple[str, ...] | None = None
    rows: list[CsvRow] = []
    # skipinitialspace reads 'a; "b"' like 'a;"b"'; strict rejects broken quoting instead of
    # guessing where a cell ends.
    reader = csv.reader(
        io.StringIO(text, newline=""), delimiter=chosen, skipinitialspace=True, strict=True
    )
    try:
        for record in reader:
            cells = tuple(cell.strip() for cell in record)
            if not any(cells):
                continue
            if header is None:
                header = cells
            else:
                rows.append(CsvRow(reader.line_num, cells))
    except csv.Error as exc:
        raise ValueError(f"the file is not valid CSV (line {reader.line_num}): {exc}") from exc
    if header is None:
        raise ValueError("the file has no header row")
    return CsvTable(header=header, rows=tuple(rows), delimiter=chosen, encoding=encoding)


def detect_decimal(table: CsvTable, columns: Sequence[int | None]) -> DecimalSeparator | None:
    """Return the decimal separator declared by the numeric ``columns``, if they settle it."""
    if table.delimiter == ",":
        return "."
    comma = point = False
    for row in table.rows:
        for index in columns:
            cell = row.cell(index)
            comma = comma or _COMMA_DECIMAL.fullmatch(cell) is not None
            point = point or _POINT_DECIMAL.fullmatch(cell) is not None
    if comma and not point:
        return ","
    if point and not comma:
        return "."
    return None


def _normalize_header(name: str) -> str:
    return "".join(unicodedata.normalize("NFKC", name).casefold().split())


def guess_target(header: Sequence[str]) -> ImportTarget:
    """Single measurements when the file has a K column, otherwise the field sheet."""
    names = {_normalize_header(name) for name in header}
    return "measurements" if names & {"k", "kunit", "geometricfactor"} else "sheet"


def guess_mapping(header: Sequence[str], target: ImportTarget) -> dict[ImportField, int | None]:
    """Map each field of ``target`` to the first header with a recognized name."""
    normalized = [_normalize_header(name) for name in header]
    used: set[int] = set()
    mapping: dict[ImportField, int | None] = {}
    for field_name in TARGET_FIELDS[target]:
        mapping[field_name] = None
        for alias in _ALIASES[target][field_name]:
            index = next(
                (i for i, name in enumerate(normalized) if name == alias and i not in used), None
            )
            if index is not None:
                mapping[field_name] = index
                used.add(index)
                break
    return mapping


def missing_required(target: ImportTarget, mapping: Mapping_) -> tuple[ImportField, ...]:
    """Required fields of ``target`` without a column."""
    return tuple(name for name in REQUIRED_FIELDS[target] if mapping.get(name) is None)


# ---------------------------------------------------------------------------- converting


def _number(text: str, decimal: DecimalSeparator | None) -> float:
    return parse_number(text) if decimal is None else parse_number_with_decimal(text, decimal)


def _flag(text: str) -> bool:
    folded = text.strip().casefold()
    if folded in _TRUE:
        return True
    if folded in _FALSE:
        return False
    raise ValueError(f"{text!r} is not yes or no")


def normalize_unit(text: str) -> str:
    """Return the canonical name of a unit (``uV`` and ``μV`` become ``µV``)."""
    stripped = text.strip()
    return _UNIT_ALIASES.get(stripped, stripped)


class _RowProblems:
    def __init__(self, table: CsvTable, mapping: Mapping_, row: CsvRow) -> None:
        self.table = table
        self.mapping = mapping
        self.row = row
        self.issues: list[ImportIssue] = []

    def column(self, field_name: ImportField) -> str:
        index = self.mapping.get(field_name)
        if index is None or index >= len(self.table.header):
            return field_name
        return self.table.header[index]

    def add(self, field_name: ImportField, message: str) -> None:
        self.issues.append(ImportIssue(self.row.line, self.column(field_name), message))

    def text(self, field_name: ImportField) -> str:
        return self.row.cell(self.mapping.get(field_name))

    def number(self, field_name: ImportField, decimal: DecimalSeparator | None) -> float | None:
        text = self.text(field_name)
        if not text:
            return None
        try:
            return _number(text, decimal)
        except ValueError as exc:
            self.add(field_name, str(exc))
            return None


def _text_of(value: float | None, number_format: NumberFormat) -> str:
    if value is None:
        return ""
    return format_for_input(value, number_format=number_format, exact=True)


def _file_unit(table: CsvTable, index: int | None, default: str) -> str:
    """The unit of the first row that names one, or ``default``."""
    if index is None:
        return default
    for row in table.rows:
        unit = normalize_unit(row.cell(index))
        if unit:
            return unit
    return default


_UNIT_FIELDS: tuple[tuple[ImportField, Callable[[float, str], float]], ...] = (
    ("voltage_unit", convert_voltage_to_volts),
    ("current_unit", convert_current_to_amperes),
)
_SHEET_NUMBER_FIELDS: tuple[ImportField, ...] = ("ab2", "mn", "delta_v", "current")
_SHEET_ISSUE_FIELDS: dict[SheetColumn, ImportField] = {
    "ab2": "ab2",
    "mn": "mn",
    "delta_v": "delta_v",
    "current": "current",
    "reason": "reason",
}


def _sheet_candidate(
    problems: _RowProblems,
    units: Mapping[ImportField, str],
    decimal: DecimalSeparator | None,
    number_format: NumberFormat,
) -> SheetRow | None:
    for field_name, converter in _UNIT_FIELDS:
        unit = units[field_name]
        text = normalize_unit(problems.text(field_name))
        if text and text != unit:
            problems.add(field_name, f"{text!r} differs from {unit!r}, used by the other rows")
        try:
            converter(1.0, unit)
        except ValueError as exc:
            problems.add(field_name, str(exc))

    values = {name: problems.number(name, decimal) for name in _SHEET_NUMBER_FIELDS}
    excluded = False
    try:
        excluded = _flag(problems.text("excluded"))
    except ValueError as exc:
        problems.add("excluded", str(exc))
    if problems.issues:
        return None
    return SheetRow(
        marker=restore_spreadsheet_text(problems.text("marker")),
        ab2=_text_of(values["ab2"], number_format),
        mn=_text_of(values["mn"], number_format),
        delta_v=_text_of(values["delta_v"], number_format),
        current=_text_of(values["current"], number_format),
        excluded=excluded,
        reason=restore_spreadsheet_text(problems.text("reason")),
    )


def import_sheet(
    table: CsvTable,
    mapping: Mapping_,
    *,
    decimal: DecimalSeparator | None,
    voltage_unit: str,
    current_unit: str,
    number_format: NumberFormat = "pt-BR",
) -> SheetImport:
    """Read field-sheet rows.

    Lengths are in meters. DeltaV and I use one unit each for the whole sheet: the unit of
    their unit column when it is mapped (every row must agree), otherwise the defaults. Rows
    with neither DeltaV nor I are kept as positions not read yet.
    """
    missing = missing_required("sheet", mapping)
    if missing:
        raise ValueError(f"no column for: {', '.join(missing)}")
    units: dict[ImportField, str] = {
        "voltage_unit": _file_unit(table, mapping.get("voltage_unit"), voltage_unit),
        "current_unit": _file_unit(table, mapping.get("current_unit"), current_unit),
    }

    issues: list[ImportIssue] = []
    candidates: list[tuple[CsvRow, SheetRow]] = []
    for row in table.rows:
        problems = _RowProblems(table, mapping, row)
        candidate = _sheet_candidate(problems, units, decimal, number_format)
        if candidate is None:
            issues.extend(problems.issues)
        else:
            candidates.append((row, candidate))

    outcome = evaluate_sheet(
        [candidate for _, candidate in candidates],
        voltage_unit=units["voltage_unit"],
        current_unit=units["current_unit"],
    )
    kept = []
    for (row, candidate), status in zip(candidates, outcome.rows, strict=True):
        problems = _RowProblems(table, mapping, row)
        if status.state == "incomplete":
            for issue in status.issues:
                problems.add(
                    _SHEET_ISSUE_FIELDS[issue.column], "is empty, but the other value is filled"
                )
        elif status.state == "invalid":
            for issue in status.issues:
                problems.add(_SHEET_ISSUE_FIELDS[issue.column], issue.message)
        elif not candidate.ab2 or not candidate.mn:
            problems.add("ab2" if not candidate.ab2 else "mn", "value cannot be empty")
        if problems.issues:
            issues.extend(problems.issues)
        else:
            kept.append(candidate)
    return SheetImport(
        rows=tuple(kept),
        voltage_unit=units["voltage_unit"],
        current_unit=units["current_unit"],
        issues=tuple(sorted(issues, key=lambda issue: issue.line)),
        total_rows=len(table.rows),
    )


_SUBMISSION_FIELDS: dict[MeasurementField, ImportField] = {
    "delta_v": "delta_v",
    "current": "current",
    "geometric_factor": "geometric_factor",
    "spacing_ab2": "spacing_ab2",
    "mn": "mn",
}
_MEASUREMENT_NUMBER_FIELDS: tuple[ImportField, ...] = (
    "delta_v",
    "current",
    "geometric_factor",
    "spacing_ab2",
    "mn",
)


def _measurement_entry(
    problems: _RowProblems,
    decimal: DecimalSeparator | None,
    defaults: Mapping[ImportField, str],
) -> MeasurementInput | None:
    numbers = {name: problems.number(name, decimal) for name in _MEASUREMENT_NUMBER_FIELDS}
    if problems.issues:
        return None

    def unit(field_name: ImportField) -> str:
        return normalize_unit(problems.text(field_name)) or defaults[field_name]

    return MeasurementInput(
        delta_v=_text_of(numbers["delta_v"], "en"),
        voltage_unit=unit("voltage_unit"),
        current=_text_of(numbers["current"], "en"),
        current_unit=unit("current_unit"),
        geometric_factor=_text_of(numbers["geometric_factor"], "en"),
        geometric_factor_unit=unit("geometric_factor_unit"),
        spacing_ab2=_text_of(numbers["spacing_ab2"], "en"),
        spacing_unit=unit("spacing_unit"),
        geometric_factor_source=restore_spreadsheet_text(problems.text("source")),
        mn=_text_of(numbers["mn"], "en"),
        mn_unit=unit("mn_unit"),
    )


def import_measurements(
    table: CsvTable,
    mapping: Mapping_,
    *,
    decimal: DecimalSeparator | None,
    voltage_unit: str,
    current_unit: str,
    length_unit: str = "m",
) -> MeasurementImport:
    """Read single measurements with a typed K, through the same rules as the form.

    Units come from their columns when mapped and filled, otherwise from the defaults.
    """
    missing = missing_required("measurements", mapping)
    if missing:
        raise ValueError(f"no column for: {', '.join(missing)}")
    defaults: dict[ImportField, str] = {
        "voltage_unit": voltage_unit,
        "current_unit": current_unit,
        "geometric_factor_unit": length_unit,
        "spacing_unit": length_unit,
        "mn_unit": length_unit,
    }

    measurements: list[Measurement] = []
    issues: list[ImportIssue] = []
    for row in table.rows:
        problems = _RowProblems(table, mapping, row)
        entry = _measurement_entry(problems, decimal, defaults)
        if entry is None:
            issues.extend(problems.issues)
            continue
        outcome = evaluate_submission(entry, [])
        if outcome.result is not None:
            measurements.append(outcome.result.measurement)
            continue
        if outcome.error is not None:
            issues.append(ImportIssue(row.line, "", outcome.error))
        for issue in outcome.field_issues:
            problems.add(_SUBMISSION_FIELDS[issue.field], issue.message)
        issues.extend(problems.issues)
    return MeasurementImport(
        measurements=tuple(measurements),
        issues=tuple(issues),
        total_rows=len(table.rows),
    )
