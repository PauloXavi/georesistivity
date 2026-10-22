"""Field-sheet page: the digital Schlumberger sheet with its live curve."""

import math

import pandas as pd
import streamlit as st

from georesistivity.app import state
from georesistivity.app.common import (
    CURRENT_UNITS,
    OHM_METER,
    VOLTAGE_UNITS,
    WARNING_SHORT_LABELS,
)
from georesistivity.field_sheet import SheetColumn, SheetOutcome, SheetRow, evaluate_sheet
from georesistivity.formatting import NumberFormat, format_full_precision, format_significant
from georesistivity.io import sounding_points_to_csv, sounding_readings_to_csv
from georesistivity.plotting import create_sounding_figure, find_unplottable_sounding_points
from georesistivity.project import SheetTemplate
from georesistivity.storage import list_templates, save_template
from georesistivity.survey import PointResult

MARKER = "Marker"
AB2 = "AB/2 [m]"
MN = "MN [m]"
DELTA_V = "\u0394V"
CURRENT = "I"
EXCLUDED = "Exclude"
REASON = "Exclusion reason"
EDITOR_COLUMNS = (MARKER, AB2, MN, DELTA_V, CURRENT, EXCLUDED, REASON)

COLUMN_LABELS: dict[SheetColumn, str] = {
    "ab2": "AB/2",
    "mn": "MN",
    "delta_v": DELTA_V,
    "current": CURRENT,
    "reason": REASON,
}


def rows_to_dataframe(rows: list[SheetRow]) -> pd.DataFrame:
    """Build the editor table from field-sheet rows."""
    return pd.DataFrame(
        [
            {
                MARKER: row.marker,
                AB2: row.ab2,
                MN: row.mn,
                DELTA_V: row.delta_v,
                CURRENT: row.current,
                EXCLUDED: row.excluded,
                REASON: row.reason,
            }
            for row in rows
        ],
        columns=EDITOR_COLUMNS,
        # Numbered from 1, as in the "Row N" messages.
        index=pd.RangeIndex(1, len(rows) + 1),
    )


def _text(value: object) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value)


def rows_from_dataframe(dataframe: pd.DataFrame) -> list[SheetRow]:
    """Read field-sheet rows back from the edited table; empty cells become blank text."""
    return [
        SheetRow(
            marker=_text(record[MARKER]),
            ab2=_text(record[AB2]),
            mn=_text(record[MN]),
            delta_v=_text(record[DELTA_V]),
            current=_text(record[CURRENT]),
            excluded=record[EXCLUDED] is True,
            reason=_text(record[REASON]),
        )
        for record in dataframe.to_dict("records")
    ]


def _points_table(points: tuple[PointResult, ...], number_format: NumberFormat) -> pd.DataFrame:
    def full(value: float) -> str:
        return format_full_precision(value, number_format=number_format)

    def significant(value: float | None) -> str:
        return "" if value is None else format_significant(value, number_format=number_format)

    records = []
    for result in points:
        statistics = result.statistics
        variation = None if statistics is None else statistics.coefficient_of_variation
        excluded = sum(reading.reading.excluded for reading in result.readings)
        used = 0 if statistics is None else statistics.count
        records.append(
            {
                AB2: full(result.point.ab2_m),
                MN: full(result.point.mn_m),
                MARKER: result.point.marker or "",
                "K [m]": significant(result.geometric_factor_m),
                "Readings": f"{used}" + (f" (+{excluded} excluded)" if excluded else ""),
                f"\u03c1a [{OHM_METER}]": significant(result.apparent_resistivity_ohm_m),
                "CV [%]": "" if variation is None else significant(100.0 * variation),
                "Warnings": ", ".join(WARNING_SHORT_LABELS[w] for w in result.warnings),
            }
        )
    return pd.DataFrame(records)


def _render_settings() -> None:
    voltage_column, current_column, limit_column = st.columns(3)
    with voltage_column:
        st.selectbox("\u0394V unit", VOLTAGE_UNITS, key=state.SHEET_VOLTAGE_UNIT)
    with current_column:
        st.selectbox("I unit", CURRENT_UNITS, key=state.SHEET_CURRENT_UNIT)
    with limit_column:
        st.number_input(
            "CV limit [%]",
            min_value=state.CV_LIMIT_RANGE[0],
            max_value=state.CV_LIMIT_RANGE[1],
            step=0.5,
            key=state.SHEET_CV_LIMIT,
            help="Repeated readings of one position whose coefficient of variation exceeds "
            "this limit are flagged.",
        )


def _render_issues(outcome: SheetOutcome) -> None:
    if outcome.incomplete_rows:
        waiting = ", ".join(
            f"row {number} ({COLUMN_LABELS[status.issues[0].column]})"
            for number, status in outcome.incomplete_rows
        )
        st.caption(f"Waiting for a value in {waiting}.")
    if not outcome.invalid_rows:
        return
    lines = []
    for number, status in outcome.invalid_rows:
        details = "; ".join(
            f"{COLUMN_LABELS[issue.column]}: {issue.message}" for issue in status.issues
        )
        lines.append(f"**Row {number}** — {details}")
    st.error("These rows were not used:\n\n" + "\n\n".join(lines))


def _render_curve(points: tuple[PointResult, ...], number_format: NumberFormat) -> None:
    unplottable = find_unplottable_sounding_points(points)
    if unplottable:
        positions = ", ".join(
            f"AB/2 = {format_full_precision(p.point.ab2_m, number_format=number_format)} m "
            f"(MN = {format_full_precision(p.point.mn_m, number_format=number_format)} m)"
            for p in unplottable
        )
        st.warning(f"Not on the log-log curve because \u03c1a is not positive: {positions}.")
    if len(unplottable) == sum(p.apparent_resistivity_ohm_m is not None for p in points):
        return
    # A square bilog curve at full page width would be taller than the screen; 560 px still
    # shrinks to the container on phones.
    st.pyplot(create_sounding_figure(points, number_format=number_format), width=560)


def _render_exports(points: tuple[PointResult, ...]) -> None:
    dialect = state.csv_dialect()
    points_column, readings_column = st.columns(2)
    with points_column:
        st.download_button(
            "Export points (CSV)",
            data=sounding_points_to_csv(points, dialect=dialect),
            file_name="georesistivity_ves_points.csv",
            mime="text/csv",
            icon=":material/download:",
            disabled=not points,
            width="stretch",
        )
    with readings_column:
        st.download_button(
            "Export readings (CSV)",
            data=sounding_readings_to_csv(points, dialect=dialect),
            file_name="georesistivity_ves_readings.csv",
            mime="text/csv",
            icon=":material/download:",
            disabled=not points,
            width="stretch",
        )


STANDARD_LAYOUT = ""


def save_layout_as_template() -> None:
    """Button callback: save the current layout, before the layout list is drawn again."""
    try:
        template = SheetTemplate.from_rows(
            st.session_state[state.TEMPLATE_NAME], state.current_sheet_rows()
        )
        path = save_template(template)
    except (ValueError, OSError) as exc:
        state.set_template_message(("error", f"The template was not saved: {exc}"))
        return
    state.set_template_message(("success", f"Template '{template.name}' saved in {path.parent}."))


def _layout_label(choice: str) -> str:
    return "Standard field sheet (45 positions)" if choice == STANDARD_LAYOUT else choice


def _render_layout_tools() -> None:
    templates = {template.name: template for template in list_templates()}
    with st.expander("New sheet and templates", icon=":material/note_add:"):
        st.selectbox(
            "Layout for a new sheet",
            options=(STANDARD_LAYOUT, *templates),
            format_func=_layout_label,
            key=state.TEMPLATE_CHOICE,
        )
        if not state.sheet_confirm_new():
            if st.button("New sheet", icon=":material/note_add:", key="sheet_new"):
                state.set_sheet_confirm_new(True)
                st.rerun()
        else:
            st.warning("Start a new sheet? Every value typed in this sheet will be discarded.")
            confirm_column, cancel_column = st.columns(2)
            with confirm_column:
                if st.button(
                    "Discard and start new sheet", type="primary", key="sheet_new_confirm"
                ):
                    choice = st.session_state[state.TEMPLATE_CHOICE]
                    template = templates.get(choice)
                    state.reset_sheet(None if template is None else template.sheet_rows())
                    st.rerun()
            with cancel_column:
                if st.button("Cancel", key="sheet_new_cancel"):
                    state.set_sheet_confirm_new(False)
                    st.rerun()

        st.divider()
        st.caption(
            "Save the AB/2, MN, and marker colours of this sheet as a template, without "
            "readings, to start new sheets with them."
        )
        name_column, save_column = st.columns([3, 1], vertical_alignment="bottom")
        with name_column:
            st.text_input("Template name", key=state.TEMPLATE_NAME)
        with save_column:
            st.button(
                "Save template",
                key="save_template",
                on_click=save_layout_as_template,
                width="stretch",
            )
        message = state.template_message()
        if message is not None:
            (st.success if message[0] == "success" else st.error)(message[1])
            state.set_template_message(None)  # shown once, right after saving


def render_field_sheet() -> None:
    """Render the digital Schlumberger field sheet, its results, and its curve."""
    st.subheader("Schlumberger field sheet")
    st.caption(
        "Type \u0394V and I in the rows you read; blank rows are ignored. A second row with the "
        "same AB/2 and the next MN is an overlap reading. Add a row with the same AB/2 and MN "
        "to record a repeated reading. K uses the exact formula with MN as the full M-N "
        "spacing. The sheet is autosaved on this computer; use Save project in the sidebar "
        "to keep a file."
    )
    _render_settings()

    voltage_unit, current_unit = state.sheet_units()
    edited = st.data_editor(
        rows_to_dataframe(state.sheet_rows()),
        key=state.sheet_editor_key(),
        num_rows="dynamic",
        hide_index=False,
        height=460,
        width="stretch",
        column_config={
            MARKER: st.column_config.TextColumn(
                MARKER, help="Cable or reel marker colour of this AB/2", width="small"
            ),
            AB2: st.column_config.TextColumn(AB2, width="small"),
            MN: st.column_config.TextColumn(MN, help="Full M-N spacing", width="small"),
            DELTA_V: st.column_config.TextColumn(f"{DELTA_V} [{voltage_unit}]"),
            CURRENT: st.column_config.TextColumn(f"{CURRENT} [{current_unit}]"),
            EXCLUDED: st.column_config.CheckboxColumn(EXCLUDED, default=False, width="small"),
            REASON: st.column_config.TextColumn(REASON),
        },
    )

    number_format = state.number_format()
    rows = rows_from_dataframe(edited)
    state.set_current_sheet_rows(rows)
    outcome = evaluate_sheet(
        rows,
        voltage_unit=voltage_unit,
        current_unit=current_unit,
        cv_threshold=state.sheet_cv_threshold(),
    )
    _render_issues(outcome)

    points = outcome.points
    if not points:
        st.info("Type \u0394V and I in a row to see the result and the curve.")
    else:
        spacings = len({p.point.ab2_m for p in points})
        st.caption(
            f"{len(points)} position{'s' if len(points) != 1 else ''} read at {spacings} "
            f"AB/2 spacing{'s' if spacings != 1 else ''}."
        )
        st.dataframe(_points_table(points, number_format), hide_index=True, width="stretch")
        _render_curve(points, number_format)

    _render_exports(points)
    _render_layout_tools()
