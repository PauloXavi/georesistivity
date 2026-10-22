"""Streamlit presentation layer for GeoResistivity.

This module only renders widgets and forwards user actions. Input rules live in
:mod:`georesistivity.services` and session access in :mod:`georesistivity.app.state`.
"""

import streamlit as st

from georesistivity.app import state
from georesistivity.formatting import NumberFormat, format_full_precision, format_significant
from georesistivity.geometry import ARRAY_PARAMETERS, ArrayType, GeometryParameter
from georesistivity.io import (
    CsvDialect,
    measurement_results_to_csv,
    measurement_results_to_dataframe,
)
from georesistivity.models import MeasurementField, MeasurementResult, MeasurementWarning
from georesistivity.plotting import (
    PlotScale,
    create_resistivity_figure,
    find_log_incompatible_points,
    prepare_plot_points,
)
from georesistivity.services import (
    GeometricFactorMode,
    calculate_geometric_factor,
    evaluate_submission,
)

VOLTAGE_UNITS = ("V", "mV", "µV")
CURRENT_UNITS = ("A", "mA", "µA")
LENGTH_UNITS = ("m", "cm", "mm", "km")
OHM_METER = "\u03a9\u00b7m"

NUMBER_FORMATS: dict[NumberFormat, str] = {
    "pt-BR": "pt-BR (1.234,5)",
    "en": "en (1,234.5)",
}
CSV_DIALECTS: dict[CsvDialect, str] = {
    "standard": "Standard (comma, decimal point)",
    "excel-pt-br": "Excel pt-BR (semicolon, decimal comma)",
}
FIELD_LABELS: dict[MeasurementField, str] = {
    "delta_v": "Delta V",
    "current": "Current",
    "geometric_factor": "Geometric factor K",
    "spacing_ab2": "AB/2",
    "mn": "MN",
}
WARNING_MESSAGES: dict[MeasurementWarning, str] = {
    MeasurementWarning.NEGATIVE_APPARENT_RESISTIVITY: (
        "Negative apparent resistivity. Check the polarity of the potential electrodes, "
        "the current direction, and the cable connections."
    ),
    MeasurementWarning.SCHLUMBERGER_WIDE_MN: (
        "MN is wide for this AB/2: (AB/2)/(MN/2) is below 4. K uses the exact formula and "
        "stays correct, but the reading averages the potential over a wide interval; "
        "consider a smaller MN at this spacing."
    ),
}
K_MODES: dict[GeometricFactorMode, str] = {
    "external": "Enter K",
    "schlumberger": "Calculate K (Schlumberger)",
}
K_CALCULATOR_ARRAYS: dict[ArrayType, str] = {
    "schlumberger": "Schlumberger",
    "wenner": "Wenner-\u03b1",
    "dipole-dipole": "Dipole-dipole",
    "pole-dipole": "Pole-dipole (remote B)",
    "general": "General four-electrode",
}
GEOMETRY_LABELS: dict[GeometryParameter, str] = {
    "ab2": "AB/2",
    "mn": "MN (full spacing)",
    "a": "a (spacing)",
    "n": "n (dimensionless)",
    "am": "AM",
    "bm": "BM",
    "an": "AN",
    "bn": "BN",
}
SCHLUMBERGER_FORMULA = r"K = \pi \, \frac{(AB/2)^2 - (MN/2)^2}{MN}"


def render_sidebar() -> None:
    """Render preferences, project context, and the approved scientific basis."""
    with st.sidebar:
        st.header("GeoResistivity")
        st.caption("Scientific calculation workspace")

        st.subheader("Preferences")
        st.selectbox(
            "Number format",
            options=tuple(NUMBER_FORMATS),
            format_func=NUMBER_FORMATS.__getitem__,
            key=state.NUMBER_FORMAT,
            help="Used to display results. Input accepts either a comma or a period as the "
            "decimal separator; thousands separators are not accepted.",
        )
        st.selectbox(
            "CSV export format",
            options=tuple(CSV_DIALECTS),
            format_func=CSV_DIALECTS.__getitem__,
            key=state.CSV_DIALECT,
        )

        st.subheader("About")
        st.write(
            "A modernized educational calculator for recording independent "
            "apparent-resistivity measurements."
        )

        st.subheader("Scientific basis")
        st.latex(r"\rho_a = K \frac{\Delta V}{I}")
        st.markdown(
            """
            - $\\rho_a$: apparent resistivity [Ω·m]
            - $K$: geometric factor [m]
            - $\\Delta V$: potential difference [V]
            - $I$: injected current [A]
            """
        )
        st.info(
            "K can be entered directly or calculated for the Schlumberger array from AB/2 "
            "and MN with the exact formula. The K calculator covers Wenner, dipole-dipole, "
            "pole-dipole, and any four-electrode layout."
        )

        st.subheader("Internal units")
        st.markdown("Voltage: **V**  \nCurrent: **A**  \nLength: **m**")

        st.divider()
        st.caption(
            "This application is intended for educational, research and scientific "
            "computing purposes. Interpretation of electrical resistivity data requires "
            "knowledge of the acquisition geometry and geological context."
        )


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
            state.set_form_errors([outcome.error])
        else:
            state.set_form_errors(
                [
                    f"**{FIELD_LABELS[issue.field]}:** {issue.message}"
                    for issue in outcome.field_issues
                ]
            )
        return

    notices: list[state.Notice] = [("success", f"Measurement #{len(results) + 1} added.")]
    if outcome.duplicate_of is not None:
        notices.append(
            (
                "warning",
                f"This measurement is identical to #{outcome.duplicate_of}. If it is not an "
                "intentional repeated reading, remove it with 'Remove last measurement'.",
            )
        )
    notices.extend(("warning", WARNING_MESSAGES[warning]) for warning in outcome.result.warnings)

    results.append(outcome.result)
    state.set_last_result(outcome.result)
    state.set_confirm_clear(False)
    state.set_form_errors([])
    state.set_form_notices(notices)
    state.clear_value_fields()


def render_measurement_form() -> None:
    """Render the measurement form and the outcome of the last submission."""
    st.subheader("Measurement Input")
    st.radio(
        "Geometric factor K",
        options=tuple(K_MODES),
        format_func=K_MODES.__getitem__,
        key=state.K_MODE,
        horizontal=True,
    )
    calculated = state.geometric_factor_mode() == "schlumberger"
    with st.form("measurement_form"):
        voltage_value_column, voltage_unit_column = st.columns([3, 1])
        with voltage_value_column:
            st.text_input("Delta V", placeholder="e.g. 120,5", key=state.DELTA_V)
        with voltage_unit_column:
            st.selectbox("Voltage unit", VOLTAGE_UNITS, index=1, key=state.VOLTAGE_UNIT)

        current_value_column, current_unit_column = st.columns([3, 1])
        with current_value_column:
            st.text_input("Current", placeholder="e.g. 20", key=state.CURRENT)
        with current_unit_column:
            st.selectbox("Current unit", CURRENT_UNITS, index=1, key=state.CURRENT_UNIT)

        if not calculated:
            factor_value_column, factor_unit_column = st.columns([3, 1])
            with factor_value_column:
                st.text_input(
                    "Geometric Factor K",
                    placeholder="e.g. 5,89",
                    key=state.GEOMETRIC_FACTOR,
                )
            with factor_unit_column:
                st.selectbox("K unit", LENGTH_UNITS, key=state.GEOMETRIC_FACTOR_UNIT)

        spacing_value_column, spacing_unit_column = st.columns([3, 1])
        with spacing_value_column:
            st.text_input(
                "AB/2" if calculated else "AB/2 — optional",
                placeholder="e.g. 20" if calculated else "Leave blank if unknown",
                key=state.SPACING,
            )
        with spacing_unit_column:
            st.selectbox("Spacing unit", LENGTH_UNITS, key=state.SPACING_UNIT)

        mn_value_column, mn_unit_column = st.columns([3, 1])
        with mn_value_column:
            st.text_input(
                "MN — full M-N spacing" if calculated else "MN — optional",
                placeholder="e.g. 2",
                key=state.MN,
            )
        with mn_unit_column:
            st.selectbox("MN unit", LENGTH_UNITS, key=state.MN_UNIT)

        if calculated:
            st.latex(SCHLUMBERGER_FORMULA)
            st.caption(
                "Exact Schlumberger formula. MN is the full distance between M and N, as on "
                "the field sheet. The K source is recorded automatically."
            )
        else:
            st.text_input(
                "Geometric factor source — optional",
                placeholder="e.g. equipment, table, field sheet",
                key=state.GEOMETRIC_FACTOR_SOURCE,
            )

        st.form_submit_button(
            "Calculate and add measurement",
            type="primary",
            icon=":material/add:",
            width="stretch",
            on_click=submit_measurement,
            key="submit_measurement",
        )

    errors = state.form_errors()
    if errors:
        st.error("Measurement could not be added.\n\n" + "\n\n".join(errors))

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
    st.subheader("Latest Result")
    st.metric(
        "Apparent Resistivity",
        f"{format_significant(rho_a, number_format=number_format)} {OHM_METER}",
    )
    with st.expander("Converted values"):
        st.write(f"Delta V = {full(result.delta_v_v)} V")
        st.write(f"I = {full(result.current_a)} A")
        st.write(f"K = {full(result.geometric_factor_m)} m")
        if result.measurement.geometric_factor_source is not None:
            st.caption(f"K source: {result.measurement.geometric_factor_source}")
        if result.spacing_ab2_m is not None:
            st.write(f"AB/2 = {full(result.spacing_ab2_m)} m")
        if result.mn_m is not None:
            st.write(f"MN = {full(result.mn_m)} m")
        st.write(f"$\\rho_a$ = {full(rho_a)} {OHM_METER}")


def render_k_calculator() -> None:
    """Render a stand-alone K calculator for every supported array."""
    with st.expander("K calculator"):
        array_column, unit_column = st.columns([3, 1])
        with array_column:
            array: ArrayType = st.selectbox(
                "Array",
                options=tuple(K_CALCULATOR_ARRAYS),
                format_func=K_CALCULATOR_ARRAYS.__getitem__,
                key=state.K_CALCULATOR_ARRAY,
            )
        with unit_column:
            length_unit: str = st.selectbox(
                "Length unit", LENGTH_UNITS, key=state.K_CALCULATOR_UNIT
            )

        with st.form("k_calculator_form"):
            parameters = ARRAY_PARAMETERS[array]
            columns = st.columns(len(parameters))
            raw_values: dict[GeometryParameter, str] = {}
            for column, parameter in zip(columns, parameters, strict=True):
                with column:
                    raw_values[parameter] = st.text_input(
                        GEOMETRY_LABELS[parameter],
                        key=f"{state.K_CALCULATOR_PREFIX}{array}_{parameter}",
                    )
            submitted = st.form_submit_button("Calculate K", key="calculate_k")

        if not submitted:
            return
        outcome = calculate_geometric_factor(array, raw_values, length_unit)
        if outcome.value_m is not None:
            value = format_full_precision(outcome.value_m, number_format=state.number_format())
            st.success(f"K = {value} m")
            st.caption("To use it, choose 'Enter K' and type this value with the unit m.")
        elif outcome.issues:
            st.error(
                "K could not be calculated.\n\n"
                + "\n\n".join(
                    f"**{GEOMETRY_LABELS[parameter]}:** {reason}"
                    for parameter, reason in outcome.issues
                )
            )
        else:
            st.error(f"K could not be calculated: {outcome.error}")


def render_measurement_controls(results: list[MeasurementResult]) -> None:
    """Render session controls and explicit clear confirmation."""
    remove_column, clear_column, export_column = st.columns(3)
    with remove_column:
        remove_last = st.button(
            "Remove last measurement",
            icon=":material/undo:",
            disabled=not results,
            width="stretch",
        )
    with clear_column:
        request_clear = st.button(
            "Clear all measurements",
            icon=":material/delete:",
            disabled=not results,
            width="stretch",
        )
    with export_column:
        st.download_button(
            "Export CSV",
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

    st.warning("Clear every measurement from this session?")
    confirm_column, cancel_column = st.columns(2)
    with confirm_column:
        confirm_clear = st.button(
            "Confirm clear",
            type="primary",
            icon=":material/delete_forever:",
            width="stretch",
        )
    with cancel_column:
        cancel_clear = st.button(
            "Cancel",
            icon=":material/close:",
            width="stretch",
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
    st.subheader("Session Measurements")
    if results:
        st.dataframe(
            measurement_results_to_dataframe(results),
            hide_index=True,
            width="stretch",
        )
        st.caption(f"{len(results)} measurement{'s' if len(results) != 1 else ''} in this session.")
    else:
        st.info("No measurements have been added yet.")

    render_measurement_controls(results)


def render_plot(results: list[MeasurementResult]) -> None:
    """Render the optional spacing plot without mutating stored measurements."""
    if sum(result.spacing_ab2_m is not None for result in results) < 2:
        if results:
            st.info("Add AB/2 to at least two measurements to display the spacing plot.")
        return

    st.subheader("Spacing Plot")
    option_column, scale_column = st.columns([1, 1])
    with option_column:
        sort_by_spacing = st.checkbox("Sort by AB/2 for visualization")
    with scale_column:
        scale_label = st.segmented_control(
            "Scale",
            options=("Linear", "Log-log"),
            default="Linear",
            required=True,
        )

    points = prepare_plot_points(results, sort_by_spacing=sort_by_spacing)
    scale: PlotScale = "log-log" if scale_label == "Log-log" else "linear"
    incompatible = find_log_incompatible_points(points) if scale == "log-log" else ()
    if incompatible:
        rows = ", ".join(f"#{index}" for index in incompatible)
        st.warning(
            "Log-log scale requires positive AB/2 and apparent-resistivity values. "
            f"The following acquisition rows cannot be represented: {rows}. "
            "No points were removed."
        )
        return

    figure = create_resistivity_figure(points, scale=scale)
    st.pyplot(figure, width="stretch")
    if sort_by_spacing:
        st.caption("The plot is sorted by AB/2; the table remains in acquisition order.")


def main() -> None:
    """Run the Streamlit application."""
    st.set_page_config(
        page_title="GeoResistivity",
        page_icon=":material/electric_bolt:",
        layout="wide",
        initial_sidebar_state="auto",
    )
    state.initialize()
    render_sidebar()

    st.title("GeoResistivity")
    st.caption("Apparent Resistivity Calculator")
    st.write(
        "Calculate and record apparent resistivity from the measured potential difference "
        "and current, with the geometric factor entered or calculated from the geometry."
    )

    render_measurement_form()
    render_latest_result()
    render_k_calculator()
    st.divider()

    results = state.measurements()
    render_measurements(results)
    render_plot(results)


if __name__ == "__main__":
    main()
