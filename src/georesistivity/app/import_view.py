"""Import page: preview a CSV file, map its columns, review problems, and import."""

import hashlib
from typing import Literal, cast

import pandas as pd
import streamlit as st

from georesistivity.app import state
from georesistivity.app.common import CURRENT_UNITS, LENGTH_UNITS, VOLTAGE_UNITS, plural
from georesistivity.core import calculate_measurement
from georesistivity.csv_import import (
    REQUIRED_FIELDS,
    TARGET_FIELDS,
    CsvTable,
    DecimalSeparator,
    ImportField,
    ImportIssue,
    ImportTarget,
    MeasurementImport,
    SheetImport,
    detect_decimal,
    guess_mapping,
    guess_target,
    import_measurements,
    import_sheet,
    missing_required,
    read_csv,
)

PREVIEW_ROWS = 10
NOT_IN_FILE = -1
AUTO = "auto"

TARGET_LABELS: dict[ImportTarget, str] = {
    "sheet": "Field sheet (readings by AB/2 and MN)",
    "measurements": "Single measurements (with K)",
}
FIELD_LABELS: dict[ImportField, str] = {
    "ab2": "AB/2 [m]",
    "mn": "MN [m]",
    "delta_v": "ΔV",
    "current": "I",
    "voltage_unit": "ΔV unit",
    "current_unit": "I unit",
    "marker": "Marker",
    "excluded": "Excluded",
    "reason": "Exclusion reason",
    "geometric_factor": "K",
    "geometric_factor_unit": "K unit",
    "spacing_ab2": "AB/2",
    "spacing_unit": "AB/2 unit",
    "mn_unit": "MN unit",
    "source": "K source",
}
DELIMITER_LABELS = {AUTO: "Detect", ";": "Semicolon ;", ",": "Comma ,", "\t": "Tab"}
DECIMAL_LABELS = {
    AUTO: "Detect from the numbers",
    ".": "Point (1.5)",
    ",": "Comma (1,5)",
    "strict": "Undecided: reject values such as 1,000",
}
SheetMode = Literal["replace", "append"]
MODE_LABELS: dict[SheetMode, str] = {
    "replace": "Replace the field sheet",
    "append": "Add after the current rows",
}
NUMERIC_FIELDS: tuple[ImportField, ...] = (
    "ab2",
    "mn",
    "delta_v",
    "current",
    "geometric_factor",
    "spacing_ab2",
)


def _file_key(name: str, data: bytes) -> str:
    return hashlib.sha1(name.encode("utf-8") + data, usedforsecurity=False).hexdigest()[:12]


def _key(file_key: str, name: str) -> str:
    return f"import_{file_key}_{name}"


def _read(file_key: str, data: bytes) -> CsvTable:
    delimiter = st.session_state.get(_key(file_key, "delimiter"), AUTO)
    return read_csv(data, delimiter=None if delimiter == AUTO else delimiter)


def _target(file_key: str, table: CsvTable) -> ImportTarget:
    return cast(
        ImportTarget, st.session_state.get(_key(file_key, "target"), guess_target(table.header))
    )


def _mapping(file_key: str, table: CsvTable, target: ImportTarget) -> dict[ImportField, int | None]:
    guessed = guess_mapping(table.header, target)
    mapping: dict[ImportField, int | None] = {}
    for field_name in TARGET_FIELDS[target]:
        default = NOT_IN_FILE if guessed[field_name] is None else guessed[field_name]
        chosen = st.session_state.get(_key(file_key, f"{target}_{field_name}"), default)
        mapping[field_name] = None if chosen == NOT_IN_FILE else cast(int, chosen)
    return mapping


def _decimal(
    file_key: str,
    table: CsvTable,
    mapping: dict[ImportField, int | None],
) -> DecimalSeparator | None:
    choice = st.session_state.get(_key(file_key, "decimal"), AUTO)
    if choice == AUTO:
        return detect_decimal(table, [mapping.get(name) for name in NUMERIC_FIELDS])
    return None if choice == "strict" else cast(DecimalSeparator, choice)


def _evaluate(file_key: str, table: CsvTable) -> SheetImport | MeasurementImport:
    target = _target(file_key, table)
    mapping = _mapping(file_key, table, target)
    decimal = _decimal(file_key, table, mapping)
    voltage_unit, current_unit = state.sheet_units()
    voltage_unit = st.session_state.get(_key(file_key, "voltage_unit"), voltage_unit)
    current_unit = st.session_state.get(_key(file_key, "current_unit"), current_unit)
    if target == "sheet":
        return import_sheet(
            table,
            mapping,
            decimal=decimal,
            voltage_unit=voltage_unit,
            current_unit=current_unit,
            number_format=state.number_format(),
        )
    return import_measurements(
        table,
        mapping,
        decimal=decimal,
        voltage_unit=voltage_unit,
        current_unit=current_unit,
        length_unit=st.session_state.get(_key(file_key, "length_unit"), "m"),
    )


def apply_import() -> None:
    """Import-button callback: recompute the import from the current choices and apply it."""
    current = state.import_file()
    if current is None:
        return
    name, data = current
    file_key = _file_key(name, data)
    try:
        table = _read(file_key, data)
        result = _evaluate(file_key, table)
    except ValueError as exc:
        state.set_import_message(("error", f"Nothing was imported: {exc}"))
        return

    if isinstance(result, MeasurementImport):
        results = [calculate_measurement(m) for m in result.measurements]
        state.measurements().extend(results)
        if results:
            state.set_last_result(results[-1])
        state.set_import_message(
            (
                "success",
                f"Imported {plural(len(results), 'measurement')} from {name} into "
                "Single measurement.",
            )
        )
        return

    mode = st.session_state.get(_key(file_key, "mode"), "replace")
    if mode == "append":
        if (
            state.sheet_has_readings()
            and (result.voltage_unit, result.current_unit) != state.sheet_units()
        ):
            state.set_import_message(
                ("error", "Nothing was imported: the units differ from the sheet's.")
            )
            return
        state.append_to_sheet(result.rows)
    else:
        state.replace_sheet(result.rows, result.voltage_unit, result.current_unit)
    state.set_import_message(
        (
            "success",
            f"Imported {plural(len(result.rows), 'row')} from {name} into the Field sheet tab.",
        )
    )


def _issues_table(issues: tuple[ImportIssue, ...]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"Line": issue.line, "Column": issue.column, "Problem": issue.message} for issue in issues]
    )


def _render_preview(table: CsvTable) -> None:
    width = len(table.header)
    names = [f"{index + 1}. {name or '(no name)'}" for index, name in enumerate(table.header)]
    rows = [list(row.cells[:width]) + [""] * (width - len(row.cells)) for row in table.rows]
    st.dataframe(pd.DataFrame(rows[:PREVIEW_ROWS], columns=names), hide_index=True, width="stretch")
    if len(table.rows) > PREVIEW_ROWS:
        st.caption(f"First {PREVIEW_ROWS} of {len(table.rows)} data rows.")


def _render_mapping(file_key: str, table: CsvTable, target: ImportTarget) -> None:
    guessed = guess_mapping(table.header, target)
    options = (NOT_IN_FILE, *range(len(table.header)))

    def label(index: int) -> str:
        return (
            "— not in the file —" if index == NOT_IN_FILE else f"{index + 1}. {table.header[index]}"
        )

    st.markdown("**Columns**")
    fields = TARGET_FIELDS[target]
    columns = st.columns(3)
    for position, field_name in enumerate(fields):
        default = guessed[field_name]
        required = field_name in REQUIRED_FIELDS[target]
        with columns[position % 3]:
            st.selectbox(
                FIELD_LABELS[field_name] + (" *" if required else ""),
                options=options,
                index=0 if default is None else default + 1,
                format_func=label,
                key=_key(file_key, f"{target}_{field_name}"),
            )


def _render_units(
    file_key: str, target: ImportTarget, mapping: dict[ImportField, int | None]
) -> None:
    voltage_unit, current_unit = state.sheet_units()
    needs: list[tuple[str, str, tuple[str, ...], str]] = []
    if mapping.get("voltage_unit") is None:
        needs.append(("voltage_unit", "ΔV unit", VOLTAGE_UNITS, voltage_unit))
    if mapping.get("current_unit") is None:
        needs.append(("current_unit", "I unit", CURRENT_UNITS, current_unit))
    if target == "measurements":
        needs.append(("length_unit", "Length unit (K, AB/2, MN)", LENGTH_UNITS, "m"))
    if not needs:
        return
    st.markdown("**Units for columns without a unit column**")
    for column, (name, title, options, default) in zip(st.columns(len(needs)), needs, strict=True):
        with column:
            st.selectbox(title, options, index=options.index(default), key=_key(file_key, name))


def render_import_file(name: str, data: bytes) -> None:
    """Preview, mapping, problems, and the import button for one CSV file."""
    state.set_import_file(name, data)
    file_key = _file_key(name, data)

    st.selectbox(
        "Separator",
        options=tuple(DELIMITER_LABELS),
        format_func=DELIMITER_LABELS.__getitem__,
        key=_key(file_key, "delimiter"),
    )
    try:
        table = _read(file_key, data)
    except ValueError as exc:
        st.error(f"The file could not be read: {exc}")
        return
    separator = DELIMITER_LABELS.get(table.delimiter, repr(table.delimiter)).lower()
    st.caption(f"{name}: {table.encoding}, {separator}, {plural(len(table.rows), 'data row')}.")
    _render_preview(table)

    st.radio(
        "Import into",
        options=tuple(TARGET_LABELS),
        index=tuple(TARGET_LABELS).index(guess_target(table.header)),
        format_func=TARGET_LABELS.__getitem__,
        key=_key(file_key, "target"),
        horizontal=True,
    )
    target = _target(file_key, table)
    _render_mapping(file_key, table, target)
    mapping = _mapping(file_key, table, target)

    detected = detect_decimal(table, [mapping.get(field) for field in NUMERIC_FIELDS])
    st.selectbox(
        "Decimal separator of the file",
        options=tuple(DECIMAL_LABELS),
        format_func=lambda choice: (
            f"Detect from the numbers ({DECIMAL_LABELS.get(detected or 'strict', '')})"
            if choice == AUTO
            else DECIMAL_LABELS[choice]
        ),
        key=_key(file_key, "decimal"),
    )
    _render_units(file_key, target, mapping)

    missing = missing_required(target, mapping)
    if missing:
        st.warning(
            "Choose a column for: " + ", ".join(FIELD_LABELS[name] for name in missing) + "."
        )
        return

    result = _evaluate(file_key, table)
    ready = len(result.rows) if isinstance(result, SheetImport) else len(result.measurements)
    st.markdown(f"**{ready} of {plural(result.total_rows, 'row')} ready to import.**")
    if result.issues:
        st.error(f"{plural(len(result.issues), 'problem')}; these rows will be left out:")
        st.dataframe(_issues_table(result.issues), hide_index=True, width="stretch")

    if isinstance(result, SheetImport):
        st.caption(f"ΔV in {result.voltage_unit}, I in {result.current_unit}; lengths in meters.")
        st.radio(
            "How",
            options=tuple(MODE_LABELS),
            format_func=MODE_LABELS.__getitem__,
            key=_key(file_key, "mode"),
            horizontal=True,
        )
    st.button(
        f"Import {plural(ready, 'row')}",
        type="primary",
        icon=":material/upload:",
        disabled=ready == 0,
        on_click=apply_import,
        key=_key(file_key, "import"),
    )


def render_import() -> None:
    """Import page."""
    st.subheader("Import CSV")
    st.caption(
        "Import readings into the field sheet or single measurements from a CSV file, "
        "including the files GeoResistivity exports (standard or Excel pt-BR). Rows with "
        "problems are listed and left out."
    )
    message = state.import_message()
    if message is not None:
        (st.success if message[0] == "success" else st.error)(message[1])
        state.set_import_message(None)
    upload = st.file_uploader("CSV file", type=["csv", "txt"], key=state.IMPORT_UPLOAD)
    if upload is None:
        return
    render_import_file(upload.name, upload.getvalue())
