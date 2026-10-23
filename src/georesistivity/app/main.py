"""Streamlit presentation layer for GeoResistivity.

This module only renders widgets and forwards user actions. Input rules live in
:mod:`georesistivity.services`, session access in :mod:`georesistivity.app.state`, and texts in
:mod:`georesistivity.app.i18n` (Portuguese by default, or English).
"""

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from georesistivity.app import state
from georesistivity.app.common import (
    CURRENT_UNITS,
    LENGTH_UNITS,
    OHM_METER,
    VOLTAGE_UNITS,
    warning_message,
)
from georesistivity.app.field_sheet_view import render_field_sheet
from georesistivity.app.i18n import LANGUAGE_KEY, LANGUAGES, count, problem_text, t, translator
from georesistivity.app.import_view import render_import
from georesistivity.app.project_view import (
    autosave,
    render_project_controls,
    render_survey_details,
)
from georesistivity.formatting import NumberFormat, format_full_precision, format_significant
from georesistivity.geometry import ARRAY_PARAMETERS, ArrayType, GeometryParameter
from georesistivity.io import (
    CsvDialect,
    measurement_results_to_csv,
    measurement_results_to_dataframe,
)
from georesistivity.models import MeasurementField, MeasurementResult
from georesistivity.plotting import (
    PlotScale,
    SpacingFigureLabels,
    create_resistivity_figure,
    find_log_incompatible_points,
    prepare_plot_points,
)
from georesistivity.services import (
    GeometricFactorMode,
    calculate_geometric_factor,
    evaluate_submission,
)

NUMBER_FORMATS: dict[NumberFormat, str] = {
    "pt-BR": "pt-BR (1.234,5)",
    "en": "en (1,234.5)",
}
CSV_DIALECT_KEYS: dict[CsvDialect, str] = {
    "standard": "csv.standard",
    "excel-pt-br": "csv.excel_pt_br",
}
K_MODE_KEYS: dict[GeometricFactorMode, str] = {
    "external": "form.k_mode_external",
    "schlumberger": "form.k_mode_schlumberger",
}
K_CALCULATOR_ARRAYS: tuple[ArrayType, ...] = (
    "schlumberger",
    "wenner",
    "dipole-dipole",
    "pole-dipole",
    "general",
)
SCALES: tuple[PlotScale, ...] = ("linear", "log-log")
SCALE_KEYS: dict[PlotScale, str] = {"linear": "plot.linear", "log-log": "plot.loglog"}
SCHLUMBERGER_FORMULA = r"K = \pi \, \frac{(AB/2)^2 - (MN/2)^2}{MN}"


def field_label(field: MeasurementField) -> str:
    return t(f"field.{field}")


def parameter_label(parameter: GeometryParameter) -> str:
    return t(f"param.{parameter}")


def render_sidebar() -> DeltaGenerator:
    """Render preferences, project context, and the scientific basis.

    Returns the container of the project controls, which are filled in at the end of the run,
    once the field-sheet editor has produced the rows to save.
    """
    tr = translator()
    with st.sidebar:
        st.header("GeoResistivity")
        st.caption(t("sidebar.caption"))
        project_slot = st.container()

        st.subheader(t("sidebar.preferences"))
        st.selectbox(
            t("sidebar.language"),
            options=tuple(LANGUAGES),
            format_func=LANGUAGES.__getitem__,
            key=LANGUAGE_KEY,
        )
        st.selectbox(
            t("sidebar.number_format"),
            options=tuple(NUMBER_FORMATS),
            format_func=NUMBER_FORMATS.__getitem__,
            key=state.NUMBER_FORMAT,
            help=t("sidebar.number_format_help"),
        )
        st.selectbox(
            t("sidebar.csv_format"),
            options=tuple(CSV_DIALECT_KEYS),
            format_func=lambda dialect: tr(CSV_DIALECT_KEYS[dialect]),
            key=state.CSV_DIALECT,
        )

        st.subheader(t("sidebar.about"))
        st.write(t("sidebar.about_text"))

        st.subheader(t("sidebar.basis"))
        st.latex(r"\rho_a = K \frac{\Delta V}{I}")
        st.markdown(t("sidebar.basis_terms"))
        st.info(t("sidebar.k_info"))

        st.subheader(t("sidebar.units"))
        st.markdown(t("sidebar.units_text"))

        st.divider()
        st.caption(t("sidebar.disclaimer"))
    return project_slot


def submit_measurement() -> None:
    """Evaluate the submitted form and record the measurement when it is valid.

    Runs as the submit-button callback, before the next script run, so the value fields can
    be cleared without affecting the selected units or the geometric factor source.
    """
    results = state.measurements()
    outcome = evaluate_submission(state.measurement_input(), results)

    state.set_form_notices([])
    if outcome.result is None:
        if outcome.error is not None:
            state.set_form_errors([problem_text(outcome.error_problem, outcome.error)])
        else:
            state.set_form_errors(
                [
                    f"**{field_label(issue.field)}:** {problem_text(issue.problem, issue.message)}"
                    for issue in outcome.field_issues
                ]
            )
        return

    notices: list[state.Notice] = [("success", t("form.added", number=len(results) + 1))]
    if outcome.duplicate_of is not None:
        notices.append(
            (
                "warning",
                t("form.duplicate", number=outcome.duplicate_of, remove=t("session.remove_last")),
            )
        )
    notices.extend(("warning", warning_message(warning)) for warning in outcome.result.warnings)

    results.append(outcome.result)
    state.set_last_result(outcome.result)
    state.set_confirm_clear(False)
    state.set_form_errors([])
    state.set_form_notices(notices)
    state.clear_value_fields()


def render_measurement_form() -> None:
    """Render the measurement form and the outcome of the last submission."""
    tr = translator()
    st.subheader(t("form.title"))
    st.radio(
        t("form.k_mode"),
        options=tuple(K_MODE_KEYS),
        format_func=lambda mode: tr(K_MODE_KEYS[mode]),
        key=state.K_MODE,
        horizontal=True,
    )
    calculated = state.geometric_factor_mode() == "schlumberger"
    with st.form("measurement_form"):
        voltage_value_column, voltage_unit_column = st.columns([3, 1])
        with voltage_value_column:
            st.text_input(
                t("form.delta_v"), placeholder=t("form.delta_v_placeholder"), key=state.DELTA_V
            )
        with voltage_unit_column:
            st.selectbox(t("form.voltage_unit"), VOLTAGE_UNITS, index=1, key=state.VOLTAGE_UNIT)

        current_value_column, current_unit_column = st.columns([3, 1])
        with current_value_column:
            st.text_input(
                t("form.current"), placeholder=t("form.current_placeholder"), key=state.CURRENT
            )
        with current_unit_column:
            st.selectbox(t("form.current_unit"), CURRENT_UNITS, index=1, key=state.CURRENT_UNIT)

        if not calculated:
            factor_value_column, factor_unit_column = st.columns([3, 1])
            with factor_value_column:
                st.text_input(
                    t("form.k"), placeholder=t("form.k_placeholder"), key=state.GEOMETRIC_FACTOR
                )
            with factor_unit_column:
                st.selectbox(t("form.k_unit"), LENGTH_UNITS, key=state.GEOMETRIC_FACTOR_UNIT)

        spacing_value_column, spacing_unit_column = st.columns([3, 1])
        with spacing_value_column:
            st.text_input(
                t("form.ab2") if calculated else t("form.ab2_optional"),
                placeholder=(
                    t("form.ab2_placeholder") if calculated else t("form.ab2_placeholder_optional")
                ),
                key=state.SPACING,
            )
        with spacing_unit_column:
            st.selectbox(t("form.spacing_unit"), LENGTH_UNITS, key=state.SPACING_UNIT)

        mn_value_column, mn_unit_column = st.columns([3, 1])
        with mn_value_column:
            st.text_input(
                t("form.mn") if calculated else t("form.mn_optional"),
                placeholder=t("form.mn_placeholder"),
                key=state.MN,
            )
        with mn_unit_column:
            st.selectbox(t("form.mn_unit"), LENGTH_UNITS, key=state.MN_UNIT)

        if calculated:
            st.latex(SCHLUMBERGER_FORMULA)
            st.caption(t("form.formula_caption"))
        else:
            st.text_input(
                t("form.source"),
                placeholder=t("form.source_placeholder"),
                key=state.GEOMETRIC_FACTOR_SOURCE,
            )

        st.form_submit_button(
            t("form.submit"),
            type="primary",
            icon=":material/add:",
            width="stretch",
            on_click=submit_measurement,
            key="submit_measurement",
        )

    errors = state.form_errors()
    if errors:
        st.error(t("form.not_added") + "\n\n" + "\n\n".join(errors))

    for kind, message in state.form_notices():
        if kind == "success":
            st.success(message)
        else:
            st.warning(message)


def render_latest_result() -> None:
    """Render the most recently calculated result and its SI traceability."""
    result = state.last_result()
    if result is None:
        return

    number_format = state.number_format()

    def full(value: float) -> str:
        return format_full_precision(value, number_format=number_format)

    rho_a = result.apparent_resistivity_ohm_m
    st.subheader(t("result.title"))
    st.metric(
        t("result.metric"),
        f"{format_significant(rho_a, number_format=number_format)} {OHM_METER}",
    )
    with st.expander(t("result.converted")):
        st.write(f"ΔV = {full(result.delta_v_v)} V")
        st.write(f"I = {full(result.current_a)} A")
        st.write(f"K = {full(result.geometric_factor_m)} m")
        if result.measurement.geometric_factor_source is not None:
            st.caption(t("result.k_source", source=result.measurement.geometric_factor_source))
        if result.spacing_ab2_m is not None:
            st.write(f"AB/2 = {full(result.spacing_ab2_m)} m")
        if result.mn_m is not None:
            st.write(f"MN = {full(result.mn_m)} m")
        st.write(f"$\\rho_a$ = {full(rho_a)} {OHM_METER}")


def render_k_calculator() -> None:
    """Render a stand-alone K calculator for every supported array."""
    tr = translator()
    with st.expander(t("kcalc.title")):
        array_column, unit_column = st.columns([3, 1])
        with array_column:
            array: ArrayType = st.selectbox(
                t("kcalc.array"),
                options=K_CALCULATOR_ARRAYS,
                format_func=lambda name: tr(f"array.{name}"),
                key=state.K_CALCULATOR_ARRAY,
            )
        with unit_column:
            length_unit: str = st.selectbox(
                t("kcalc.length_unit"), LENGTH_UNITS, key=state.K_CALCULATOR_UNIT
            )

        with st.form("k_calculator_form"):
            parameters = ARRAY_PARAMETERS[array]
            columns = st.columns(len(parameters))
            raw_values: dict[GeometryParameter, str] = {}
            for column, parameter in zip(columns, parameters, strict=True):
                with column:
                    raw_values[parameter] = st.text_input(
                        parameter_label(parameter),
                        key=f"{state.K_CALCULATOR_PREFIX}{array}_{parameter}",
                    )
            submitted = st.form_submit_button(t("kcalc.submit"), key="calculate_k")

        if not submitted:
            return
        outcome = calculate_geometric_factor(array, raw_values, length_unit)
        if outcome.value_m is not None:
            value = format_full_precision(outcome.value_m, number_format=state.number_format())
            st.success(f"K = {value} m")
            st.caption(t("kcalc.hint", enter_k=t("form.k_mode_external")))
        elif outcome.issues:
            st.error(
                t("kcalc.failed")
                + "\n\n"
                + "\n\n".join(
                    f"**{parameter_label(issue.parameter)}:** "
                    f"{problem_text(issue.problem, issue.message)}"
                    for issue in outcome.issues
                )
            )
        else:
            error = problem_text(outcome.error_problem, outcome.error or "")
            st.error(t("kcalc.failed_error", error=error))


def render_measurement_controls(results: list[MeasurementResult]) -> None:
    """Render session controls and explicit clear confirmation."""
    remove_column, clear_column, export_column = st.columns(3)
    with remove_column:
        remove_last = st.button(
            t("session.remove_last"),
            icon=":material/undo:",
            disabled=not results,
            width="stretch",
            key="remove_last_measurement",
        )
    with clear_column:
        request_clear = st.button(
            t("session.clear_all"),
            icon=":material/delete:",
            disabled=not results,
            width="stretch",
            key="clear_all_measurements",
        )
    with export_column:
        st.download_button(
            t("session.export"),
            data=measurement_results_to_csv(results, dialect=state.csv_dialect()),
            file_name="georesistivity_measurements.csv",
            mime="text/csv",
            icon=":material/download:",
            disabled=not results,
            width="stretch",
        )

    if remove_last:
        results.pop()
        state.set_last_result(results[-1] if results else None)
        state.set_confirm_clear(False)
        state.set_form_notices([])
        st.rerun()

    if request_clear:
        state.set_confirm_clear(True)

    if not state.confirm_clear():
        return

    st.warning(t("session.clear_question"))
    confirm_column, cancel_column = st.columns(2)
    with confirm_column:
        confirm_clear = st.button(
            t("session.clear_confirm"),
            type="primary",
            icon=":material/delete_forever:",
            width="stretch",
            key="confirm_clear_measurements",
        )
    with cancel_column:
        cancel_clear = st.button(
            t("common.cancel"),
            icon=":material/close:",
            width="stretch",
            key="cancel_clear_measurements",
        )

    if confirm_clear:
        results.clear()
        state.set_last_result(None)
        state.set_confirm_clear(False)
        state.set_form_notices([])
        st.rerun()
    if cancel_clear:
        state.set_confirm_clear(False)
        st.rerun()


def render_measurements(results: list[MeasurementResult]) -> None:
    """Render the acquisition-order table and its controls."""
    st.subheader(t("session.title"))
    if results:
        table = measurement_results_to_dataframe(results)
        table.columns = [t(f"table.{column}") for column in table.columns]
        st.dataframe(table, hide_index=True, width="stretch")
        st.caption(count("session.count", len(results)))
    else:
        st.info(t("session.empty"))

    render_measurement_controls(results)


def render_plot(results: list[MeasurementResult]) -> None:
    """Render the optional spacing plot without mutating stored measurements."""
    tr = translator()
    if sum(result.spacing_ab2_m is not None for result in results) < 2:
        if results:
            st.info(t("plot.need_two"))
        return

    st.subheader(t("plot.title"))
    option_column, scale_column = st.columns([1, 1])
    with option_column:
        sort_by_spacing = st.checkbox(t("plot.sort"), key="plot_sort_by_spacing")
    with scale_column:
        scale = st.segmented_control(
            t("plot.scale"),
            options=SCALES,
            format_func=lambda option: tr(SCALE_KEYS[option]),
            default="linear",
            required=True,
            key="plot_scale",
        )

    points = prepare_plot_points(results, sort_by_spacing=sort_by_spacing)
    chosen: PlotScale = "log-log" if scale == "log-log" else "linear"
    incompatible = find_log_incompatible_points(points) if chosen == "log-log" else ()
    if incompatible:
        rows = ", ".join(f"#{index}" for index in incompatible)
        st.warning(t("plot.log_incompatible", rows=rows))
        return

    labels = SpacingFigureLabels(
        title=t("figure.spacing_title"),
        x_axis=t("figure.ab2_axis"),
        y_axis=t("figure.rho_axis"),
    )
    figure = create_resistivity_figure(points, scale=chosen, labels=labels)
    st.pyplot(figure, width="stretch")
    if sort_by_spacing:
        st.caption(t("plot.sorted_caption"))


def main() -> None:
    """Run the Streamlit application."""
    st.set_page_config(
        page_title="GeoResistivity",
        page_icon=":material/electric_bolt:",
        layout="wide",
        initial_sidebar_state="auto",
    )
    state.initialize()
    project_slot = render_sidebar()

    st.title("GeoResistivity")
    st.caption(t("app.subtitle"))
    st.write(t("app.intro"))

    sheet_tab, single_tab, import_tab = st.tabs([t("tab.sheet"), t("tab.single"), t("tab.import")])
    with sheet_tab:
        render_survey_details()
        render_field_sheet()
    with single_tab:
        render_measurement_form()
        render_latest_result()
        render_k_calculator()
        st.divider()
        results = state.measurements()
        render_measurements(results)
        render_plot(results)
    with import_tab:
        render_import()

    project = state.current_project()
    autosave(project)
    with project_slot:
        render_project_controls(project)


if __name__ == "__main__":
    main()
