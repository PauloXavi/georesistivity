"""Field-sheet page: the digital Schlumberger sheet with its live curve."""

import math
from collections.abc import Callable, Sequence

import pandas as pd
import streamlit as st

from georesistivity.app import state
from georesistivity.app.common import CURRENT_UNITS, VOLTAGE_UNITS, warning_short
from georesistivity.app.i18n import (
    count,
    current_language,
    error_text,
    problem_text,
    t,
    t_for,
    translator,
)
from georesistivity.field_sheet import SheetColumn, SheetOutcome, SheetRow, evaluate_sheet
from georesistivity.figures import (
    DECADE_MM_RANGE,
    DEFAULT_DECADE_MM,
    FIGURE_FORMATS,
    FIGURE_MIME,
    FigureOptions,
    figure_file_name,
    sounding_figure_file,
    sounding_labels,
)
from georesistivity.formatting import NumberFormat, format_full_precision, format_significant
from georesistivity.io import sounding_points_to_csv, sounding_readings_to_csv
from georesistivity.plotting import (
    create_sounding_figure,
    find_unplottable_sounding_points,
    sounding_decades,
    sounding_error_bar,
)
from georesistivity.project import SheetTemplate, SurveyInfo
from georesistivity.storage import list_templates, save_template
from georesistivity.survey import PointResult

# Column names of the editor table. They identify the data and do not change with the
# language; the headers on screen come from the column configuration.
MARKER = "Marker"
AB2 = "AB/2 [m]"
MN = "MN [m]"
DELTA_V = "ΔV"
CURRENT = "I"
EXCLUDED = "Exclude"
REASON = "Exclusion reason"
EDITOR_COLUMNS = (MARKER, AB2, MN, DELTA_V, CURRENT, EXCLUDED, REASON)


def column_label(column: SheetColumn) -> str:
    return t(f"sheet.issue_{column}")


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
        readings = (
            t("points.readings_excluded", used=used, excluded=excluded) if excluded else str(used)
        )
        records.append(
            {
                t("points.ab2"): full(result.point.ab2_m),
                t("points.mn"): full(result.point.mn_m),
                t("points.marker"): result.point.marker or "",
                t("points.k"): significant(result.geometric_factor_m),
                t("points.readings"): readings,
                t("points.rho"): significant(result.apparent_resistivity_ohm_m),
                t("points.se"): significant(result.standard_error_ohm_m),
                t("points.cv"): "" if variation is None else significant(100.0 * variation),
                t("points.warnings"): ", ".join(warning_short(w) for w in result.warnings),
            }
        )
    return pd.DataFrame(records)


def _render_settings() -> None:
    voltage_column, current_column, limit_column = st.columns(3)
    with voltage_column:
        st.selectbox(t("sheet.dv_unit"), VOLTAGE_UNITS, key=state.SHEET_VOLTAGE_UNIT)
    with current_column:
        st.selectbox(t("sheet.i_unit"), CURRENT_UNITS, key=state.SHEET_CURRENT_UNIT)
    with limit_column:
        st.number_input(
            t("sheet.cv_limit"),
            min_value=state.CV_LIMIT_RANGE[0],
            max_value=state.CV_LIMIT_RANGE[1],
            step=0.5,
            key=state.SHEET_CV_LIMIT,
            help=t("sheet.cv_help"),
        )


def _render_issues(outcome: SheetOutcome) -> None:
    if outcome.incomplete_rows:
        waiting = ", ".join(
            t("sheet.waiting_row", number=number, column=column_label(status.issues[0].column))
            for number, status in outcome.incomplete_rows
        )
        st.caption(t("sheet.waiting", rows=waiting))
    if not outcome.invalid_rows:
        return
    lines = []
    for number, status in outcome.invalid_rows:
        details = "; ".join(
            f"{column_label(issue.column)}: {problem_text(issue.problem, issue.message)}"
            for issue in status.issues
        )
        lines.append(t("sheet.row_issue", number=number, details=details))
    st.error(t("sheet.not_used") + "\n\n" + "\n\n".join(lines))


def _render_curve(points: tuple[PointResult, ...], number_format: NumberFormat) -> bool:
    """Draw the curve; ``False`` when no point can be plotted."""
    unplottable = find_unplottable_sounding_points(points)
    if unplottable:
        positions = ", ".join(
            t(
                "sheet.position",
                ab2=format_full_precision(p.point.ab2_m, number_format=number_format),
                mn=format_full_precision(p.point.mn_m, number_format=number_format),
            )
            for p in unplottable
        )
        st.warning(t("sheet.not_on_curve", positions=positions))
    plotted = sum(p.apparent_resistivity_ohm_m is not None for p in points) - len(unplottable)
    if not plotted:
        return False
    st.toggle(t("sheet.error_bars"), key=state.SHEET_ERROR_BARS, help=t("sheet.error_bars_help"))
    error_bars = state.sheet_error_bars()
    if error_bars:
        with_bars = sum(sounding_error_bar(p) is not None for p in points)
        if with_bars:
            positions = count("count.position", plotted)
            st.caption(
                t_for(with_bars, "sheet.error_bars_on", with_bars=with_bars, positions=positions)
            )
        else:
            st.caption(t("sheet.error_bars_none"))
    figure = create_sounding_figure(
        points,
        number_format=number_format,
        labels=sounding_labels(current_language()),
        error_bars=error_bars,
    )
    # A square bilog curve at full page width would be taller than the screen; 560 px still
    # shrinks to the container on phones.
    st.pyplot(figure, width=560)
    return True


FORMAT_KEYS = {"png": "export.format_png", "svg": "export.format_svg", "pdf": "export.format_pdf"}
SIZE_KEYS = {"standard": "export.size_standard", "scale": "export.size_scale"}


def figure_download(
    points: Sequence[PointResult], survey: SurveyInfo, options: FigureOptions
) -> Callable[[], bytes]:
    """File of the download button, drawn only when it is clicked (300 dpi PNG is slow)."""
    return lambda: sounding_figure_file(points, survey, options)


def _render_figure_export(points: tuple[PointResult, ...], number_format: NumberFormat) -> None:
    tr = translator()
    format_labels = {name: tr(FORMAT_KEYS[name]) for name in FIGURE_FORMATS}
    size_labels = {name: tr(key) for name, key in SIZE_KEYS.items()}

    def centimetres(value_mm: float) -> str:
        return format_full_precision(round(value_mm / 10.0, 2), number_format=number_format)

    with st.expander(t("export.title"), icon=":material/image:"):
        format_column, size_column = st.columns(2)
        with format_column:
            st.selectbox(
                t("export.format"),
                FIGURE_FORMATS,
                format_func=format_labels.__getitem__,
                key=state.FIGURE_FORMAT,
            )
        with size_column:
            st.radio(
                t("export.size"),
                tuple(SIZE_KEYS),
                format_func=size_labels.__getitem__,
                key=state.FIGURE_SIZE,
            )
        if state.figure_size() == "scale":
            low, high = DECADE_MM_RANGE
            default = format_full_precision(DEFAULT_DECADE_MM, number_format=number_format)
            st.number_input(
                t("export.decade_mm"),
                min_value=low,
                max_value=high,
                step=0.5,
                key=state.FIGURE_DECADE_MM,
                help=t("export.decade_help", default=default),
            )
            x_decades, y_decades = sounding_decades(points, error_bars=state.sheet_error_bars())
            decade_mm = state.figure_decade_mm()
            st.caption(
                t(
                    "export.scale_caption",
                    width=centimetres(x_decades * decade_mm),
                    height=centimetres(y_decades * decade_mm),
                    x_decades=x_decades,
                    y_decades=y_decades,
                )
            )
        st.checkbox(t("export.title_with_survey"), key=state.FIGURE_TITLE)

        options = state.figure_options()
        survey = state.survey_info()
        st.download_button(
            t("export.download", format=options.file_format.upper()),
            data=figure_download(points, survey, options),
            file_name=figure_file_name(survey, options.file_format),
            mime=FIGURE_MIME[options.file_format],
            icon=":material/download:",
            on_click="ignore",
            key="download_figure",
        )


def _render_exports(points: tuple[PointResult, ...]) -> None:
    dialect = state.csv_dialect()
    points_column, readings_column = st.columns(2)
    with points_column:
        st.download_button(
            t("sheet.export_points"),
            data=sounding_points_to_csv(points, dialect=dialect),
            file_name="georesistivity_ves_points.csv",
            mime="text/csv",
            icon=":material/download:",
            disabled=not points,
            width="stretch",
        )
    with readings_column:
        st.download_button(
            t("sheet.export_readings"),
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
        state.set_template_message(("error", t("templates.not_saved", error=error_of(exc))))
        return
    state.set_template_message(
        ("success", t("templates.saved", name=template.name, folder=path.parent))
    )


def error_of(error: BaseException) -> str:
    """An error in the current language; operating-system errors keep their own text."""
    return str(error) if isinstance(error, OSError) else error_text(error)


def _render_layout_tools() -> None:
    templates = {template.name: template for template in list_templates()}
    standard = t("templates.standard")

    def _layout_label(choice: str) -> str:
        return standard if choice == STANDARD_LAYOUT else choice

    with st.expander(t("templates.title"), icon=":material/note_add:"):
        st.selectbox(
            t("templates.layout"),
            options=(STANDARD_LAYOUT, *templates),
            format_func=_layout_label,
            key=state.TEMPLATE_CHOICE,
        )
        if not state.sheet_confirm_new():
            if st.button(t("templates.new"), icon=":material/note_add:", key="sheet_new"):
                state.set_sheet_confirm_new(True)
                st.rerun()
        else:
            st.warning(t("templates.new_question"))
            confirm_column, cancel_column = st.columns(2)
            with confirm_column:
                if st.button(t("templates.new_confirm"), type="primary", key="sheet_new_confirm"):
                    choice = st.session_state[state.TEMPLATE_CHOICE]
                    template = templates.get(choice)
                    state.reset_sheet(None if template is None else template.sheet_rows())
                    st.rerun()
            with cancel_column:
                if st.button(t("common.cancel"), key="sheet_new_cancel"):
                    state.set_sheet_confirm_new(False)
                    st.rerun()

        st.divider()
        st.caption(t("templates.caption"))
        name_column, save_column = st.columns([3, 1], vertical_alignment="bottom")
        with name_column:
            st.text_input(t("templates.name"), key=state.TEMPLATE_NAME)
        with save_column:
            st.button(
                t("templates.save"),
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
    st.subheader(t("sheet.title"))
    st.caption(t("sheet.caption"))
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
                t("sheet.col_marker"), help=t("sheet.col_marker_help"), width="small"
            ),
            AB2: st.column_config.TextColumn(t("sheet.col_ab2"), width="small"),
            MN: st.column_config.TextColumn(
                t("sheet.col_mn"), help=t("sheet.col_mn_help"), width="small"
            ),
            DELTA_V: st.column_config.TextColumn(t("sheet.col_delta_v", unit=voltage_unit)),
            CURRENT: st.column_config.TextColumn(t("sheet.col_current", unit=current_unit)),
            EXCLUDED: st.column_config.CheckboxColumn(
                t("sheet.col_exclude"), default=False, width="small"
            ),
            REASON: st.column_config.TextColumn(t("sheet.col_reason")),
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
        st.info(t("sheet.empty"))
    else:
        spacings = len({p.point.ab2_m for p in points})
        st.caption(
            t_for(
                len(points),
                "sheet.summary",
                positions=count("count.position", len(points)),
                spacings=count("count.spacing", spacings),
            )
        )
        st.dataframe(_points_table(points, number_format), hide_index=True, width="stretch")
        if _render_curve(points, number_format):
            _render_figure_export(points, number_format)

    _render_exports(points)
    _render_layout_tools()
