"""Import page: preview a CSV file, map its columns, review problems, and import."""

import hashlib
from typing import Literal, cast

import pandas as pd
import streamlit as st

from georesistivity.app import state
from georesistivity.app.common import CURRENT_UNITS, LENGTH_UNITS, VOLTAGE_UNITS
from georesistivity.app.i18n import count, error_text, problem_text, t, t_for
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

TARGET_KEYS: dict[ImportTarget, str] = {
    "sheet": "import.target_sheet",
    "measurements": "import.target_measurements",
}
DELIMITER_KEYS = {
    AUTO: "import.separator_auto",
    ";": "import.separator_semicolon",
    ",": "import.separator_comma",
    "\t": "import.separator_tab",
}
DECIMAL_KEYS = {
    ".": "import.decimal_point",
    ",": "import.decimal_comma",
    "strict": "import.decimal_strict",
}
DECIMAL_CHOICES = (AUTO, ".", ",", "strict")
SheetMode = Literal["replace", "append"]
MODE_KEYS: dict[SheetMode, str] = {"replace": "import.replace", "append": "import.append"}
NUMERIC_FIELDS: tuple[ImportField, ...] = (
    "ab2",
    "mn",
    "delta_v",
    "current",
    "geometric_factor",
    "spacing_ab2",
)


def field_label(field_name: ImportField) -> str:
    return t(f"importfield.{field_name}")


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
        state.set_import_message(("error", t("import.nothing", error=error_text(exc))))
        return

    if isinstance(result, MeasurementImport):
        results = [calculate_measurement(m) for m in result.measurements]
        state.measurements().extend(results)
        if results:
            state.set_last_result(results[-1])
        imported = count("count.measurement", len(results))
        message = t_for(len(results), "import.done_measurements", measurements=imported, name=name)
        state.set_import_message(("success", message))
        return

    mode = st.session_state.get(_key(file_key, "mode"), "replace")
    if mode == "append":
        if (
            state.sheet_has_readings()
            and (result.voltage_unit, result.current_unit) != state.sheet_units()
        ):
            state.set_import_message(("error", t("import.units_differ")))
            return
        state.append_to_sheet(result.rows, file_name=name)
    else:
        state.replace_sheet(result.rows, result.voltage_unit, result.current_unit, file_name=name)
    imported_rows = count("count.row", len(result.rows))
    message = t_for(len(result.rows), "import.done_sheet", rows=imported_rows, name=name)
    state.set_import_message(("success", message))


def _issues_table(issues: tuple[ImportIssue, ...]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                t("import.issue_line"): issue.line,
                t("import.issue_column"): issue.column,
                t("import.issue_problem"): problem_text(issue.problem, issue.message),
            }
            for issue in issues
        ]
    )


def _render_preview(table: CsvTable) -> None:
    width = len(table.header)
    names = [
        f"{index + 1}. {name or t('import.no_name')}" for index, name in enumerate(table.header)
    ]
    rows = [list(row.cells[:width]) + [""] * (width - len(row.cells)) for row in table.rows]
    st.dataframe(pd.DataFrame(rows[:PREVIEW_ROWS], columns=names), hide_index=True, width="stretch")
    if len(table.rows) > PREVIEW_ROWS:
        st.caption(
            t(
                "import.first_rows",
                shown=PREVIEW_ROWS,
                rows=count("count.data_row", len(table.rows)),
            )
        )


def _render_mapping(file_key: str, table: CsvTable, target: ImportTarget) -> None:
    guessed = guess_mapping(table.header, target)
    options = (NOT_IN_FILE, *range(len(table.header)))

    not_in_file = t("import.not_in_file")

    def label(index: int) -> str:
        return not_in_file if index == NOT_IN_FILE else f"{index + 1}. {table.header[index]}"

    st.markdown(f"**{t('import.columns')}**")
    fields = TARGET_FIELDS[target]
    columns = st.columns(3)
    for position, field_name in enumerate(fields):
        default = guessed[field_name]
        required = field_name in REQUIRED_FIELDS[target]
        with columns[position % 3]:
            st.selectbox(
                field_label(field_name) + (" *" if required else ""),
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
        needs.append(("voltage_unit", field_label("voltage_unit"), VOLTAGE_UNITS, voltage_unit))
    if mapping.get("current_unit") is None:
        needs.append(("current_unit", field_label("current_unit"), CURRENT_UNITS, current_unit))
    if target == "measurements":
        needs.append(("length_unit", t("import.length_unit"), LENGTH_UNITS, "m"))
    if not needs:
        return
    st.markdown(f"**{t('import.units')}**")
    for column, (name, title, options, default) in zip(st.columns(len(needs)), needs, strict=True):
        with column:
            st.selectbox(title, options, index=options.index(default), key=_key(file_key, name))


def _decimal_labels(detected: DecimalSeparator | None) -> dict[str, str]:
    labels = {choice: t(key) for choice, key in DECIMAL_KEYS.items()}
    labels[AUTO] = t("import.decimal_auto", detected=labels[detected or "strict"])
    return labels


def render_import_file(name: str, data: bytes) -> None:
    """Preview, mapping, problems, and the import button for one CSV file."""
    state.set_import_file(name, data)
    file_key = _file_key(name, data)
    delimiter_labels = {choice: t(key) for choice, key in DELIMITER_KEYS.items()}
    target_labels = {target: t(key) for target, key in TARGET_KEYS.items()}
    mode_labels = {mode: t(key) for mode, key in MODE_KEYS.items()}

    st.selectbox(
        t("import.separator"),
        options=tuple(DELIMITER_KEYS),
        format_func=delimiter_labels.__getitem__,
        key=_key(file_key, "delimiter"),
    )
    try:
        table = _read(file_key, data)
    except ValueError as exc:
        st.error(t("import.unreadable", error=error_text(exc)))
        return
    separator_key = DELIMITER_KEYS.get(table.delimiter)
    separator = t(separator_key).lower() if separator_key else repr(table.delimiter)
    rows = count("count.data_row", len(table.rows))
    st.caption(
        t("import.read_as", name=name, encoding=table.encoding, separator=separator, rows=rows)
    )
    _render_preview(table)

    st.radio(
        t("import.target"),
        options=tuple(TARGET_KEYS),
        index=tuple(TARGET_KEYS).index(guess_target(table.header)),
        format_func=target_labels.__getitem__,
        key=_key(file_key, "target"),
        horizontal=True,
    )
    target = _target(file_key, table)
    _render_mapping(file_key, table, target)
    mapping = _mapping(file_key, table, target)

    detected = detect_decimal(table, [mapping.get(field) for field in NUMERIC_FIELDS])
    st.selectbox(
        t("import.decimal"),
        options=DECIMAL_CHOICES,
        format_func=_decimal_labels(detected).__getitem__,
        key=_key(file_key, "decimal"),
    )
    _render_units(file_key, target, mapping)

    missing = missing_required(target, mapping)
    if missing:
        fields = ", ".join(field_label(field_name) for field_name in missing)
        st.warning(t("import.choose_columns", fields=fields))
        return

    result = _evaluate(file_key, table)
    ready = len(result.rows) if isinstance(result, SheetImport) else len(result.measurements)
    rows_text = count("count.row", result.total_rows)
    st.markdown(f"**{t_for(ready, 'import.ready', ready=ready, rows=rows_text)}**")
    if result.issues:
        st.error(t("import.problems", problems=count("count.problem", len(result.issues))))
        st.dataframe(_issues_table(result.issues), hide_index=True, width="stretch")

    if isinstance(result, SheetImport):
        st.caption(
            t("import.units_caption", voltage=result.voltage_unit, current=result.current_unit)
        )
        st.radio(
            t("import.how"),
            options=tuple(MODE_KEYS),
            format_func=mode_labels.__getitem__,
            key=_key(file_key, "mode"),
            horizontal=True,
        )
    st.button(
        t("import.button", rows=count("count.row", ready)),
        type="primary",
        icon=":material/upload:",
        disabled=ready == 0,
        on_click=apply_import,
        key=_key(file_key, "import"),
    )


def render_import() -> None:
    """Import page."""
    st.subheader(t("import.title"))
    st.caption(t("import.caption"))
    message = state.import_message()
    if message is not None:
        (st.success if message[0] == "success" else st.error)(message[1])
        state.set_import_message(None)
    upload = st.file_uploader(t("import.file"), type=["csv", "txt"], key=state.IMPORT_UPLOAD)
    if upload is None:
        return
    render_import_file(upload.name, upload.getvalue())
