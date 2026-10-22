"""Streamlit presentation layer for GeoResistivity."""

from typing import cast

import streamlit as st

from georesistivity import (
    Measurement,
    MeasurementField,
    MeasurementFieldError,
    MeasurementResult,
    MeasurementWarning,
    calculate_measurement,
    create_resistivity_figure,
    find_log_incompatible_points,
    measurement_results_to_csv,
    measurement_results_to_dataframe,
    parse_number,
    prepare_plot_points,
)
from georesistivity.formatting import NumberFormat, format_full_precision, format_significant
from georesistivity.io import CsvDialect
from georesistivity.plotting import PlotScale

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
}
WARNING_MESSAGES: dict[MeasurementWarning, str] = {
    MeasurementWarning.NEGATIVE_APPARENT_RESISTIVITY: (
        "Negative apparent resistivity. Check the polarity of the potential electrodes, "
        "the current direction, and the cable connections."
    ),
}

# Widget keys for the numeric text fields that are cleared after a successful submission.
VALUE_KEYS = ("delta_v_raw", "current_raw", "geometric_factor_raw", "spacing_raw")


def initialize_session_state() -> None:
    """Initialize session-only application state."""
    st.session_state.setdefault("measurements", [])
    st.session_state.setdefault("last_result", None)
    st.session_state.setdefault("confirm_clear", False)
    st.session_state.setdefault("form_errors", [])
    st.session_state.setdefault("form_notices", [])
    st.session_state.setdefault("number_format", "pt-BR")
    st.session_state.setdefault("csv_dialect", "standard")


def get_measurements() -> list[MeasurementResult]:
    """Return the typed collection stored for the current session."""
    return cast(list[MeasurementResult], st.session_state["measurements"])


def get_number_format() -> NumberFormat:
    """Return the number format selected in the sidebar."""
    return cast(NumberFormat, st.session_state["number_format"])


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
            key="number_format",
            help="Used to display results. Input accepts either a comma or a period as the "
            "decimal separator; thousands separators are not accepted.",
        )
        st.selectbox(
            "CSV export format",
            options=tuple(CSV_DIALECTS),
            format_func=CSV_DIALECTS.__getitem__,
            key="csv_dialect",
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
            "The geometric factor K is supplied externally. This version does not "
            "assume or calculate any specific electrode array geometry."
        )

        st.subheader("Internal units")
        st.markdown("Voltage: **V**  \nCurrent: **A**  \nLength: **m**")

        st.divider()
        st.caption(
            "This application is intended for educational, research and scientific "
            "computing purposes. Interpretation of electrical resistivity data requires "
            "knowledge of the acquisition geometry and geological context."
        )


def _parse_field(
    field: MeasurementField,
    raw_value: str,
    errors: list[str],
) -> float | None:
    try:
        return parse_number(raw_value)
    except ValueError as exc:
        errors.append(f"**{FIELD_LABELS[field]}:** {exc}")
        return None


def submit_measurement() -> None:
    """Validate the submitted form, record the measurement, and reset the value fields.

    Runs as the submit-button callback, before the next script run, so the value fields can
    be cleared without affecting the selected units or the geometric factor source.
    """
    state = st.session_state
    errors: list[str] = []

    delta_v = _parse_field("delta_v", state["delta_v_raw"], errors)
    current = _parse_field("current", state["current_raw"], errors)
    geometric_factor = _parse_field("geometric_factor", state["geometric_factor_raw"], errors)
    spacing_supplied = bool(state["spacing_raw"].strip())
    spacing = (
        _parse_field("spacing_ab2", state["spacing_raw"], errors) if spacing_supplied else None
    )

    state["form_notices"] = []
    if errors or delta_v is None or current is None or geometric_factor is None:
        state["form_errors"] = errors
        return

    measurement = Measurement(
        delta_v_original=delta_v,
        voltage_unit=state["voltage_unit"],
        current_original=current,
        current_unit=state["current_unit"],
        geometric_factor_original=geometric_factor,
        geometric_factor_unit=state["geometric_factor_unit"],
        spacing_ab2_original=spacing,
        spacing_unit=state["spacing_unit"] if spacing is not None else None,
        geometric_factor_source=state["geometric_factor_source"].strip() or None,
    )
    try:
        result = calculate_measurement(measurement)
    except MeasurementFieldError as exc:
        state["form_errors"] = [f"**{FIELD_LABELS[exc.field]}:** {exc.reason}"]
        return
    except ValueError as exc:
        state["form_errors"] = [str(exc)]
        return

    results = get_measurements()
    notices: list[tuple[str, str]] = [("success", f"Measurement #{len(results) + 1} added.")]
    if results and results[-1].measurement == measurement:
        notices.append(
            (
                "warning",
                f"This measurement is identical to #{len(results)}. If it is not an "
                "intentional repeated reading, remove it with 'Remove last measurement'.",
            )
        )
    notices.extend(("warning", WARNING_MESSAGES[warning]) for warning in result.warnings)

    results.append(result)
    state["last_result"] = result
    state["confirm_clear"] = False
    state["form_errors"] = []
    state["form_notices"] = notices
    for key in VALUE_KEYS:
        state[key] = ""


def render_measurement_form() -> None:
    """Render the measurement form and the outcome of the last submission."""
    st.subheader("Measurement Input")
    with st.form("measurement_form"):
        voltage_value_column, voltage_unit_column = st.columns([3, 1])
        with voltage_value_column:
            st.text_input("Delta V", placeholder="e.g. 120,5", key="delta_v_raw")
        with voltage_unit_column:
            st.selectbox("Voltage unit", VOLTAGE_UNITS, index=1, key="voltage_unit")

        current_value_column, current_unit_column = st.columns([3, 1])
        with current_value_column:
            st.text_input("Current", placeholder="e.g. 20", key="current_raw")
        with current_unit_column:
            st.selectbox("Current unit", CURRENT_UNITS, index=1, key="current_unit")

        factor_value_column, factor_unit_column = st.columns([3, 1])
        with factor_value_column:
            st.text_input(
                "Geometric Factor K",
                placeholder="e.g. 5,89",
                key="geometric_factor_raw",
            )
        with factor_unit_column:
            st.selectbox("K unit", LENGTH_UNITS, key="geometric_factor_unit")

        spacing_value_column, spacing_unit_column = st.columns([3, 1])
        with spacing_value_column:
            st.text_input(
                "AB/2 — optional",
                placeholder="Leave blank if unknown",
                key="spacing_raw",
            )
        with spacing_unit_column:
            st.selectbox("Spacing unit", LENGTH_UNITS, key="spacing_unit")

        st.text_input(
            "Geometric factor source — optional",
            placeholder="e.g. equipment, table, field sheet",
            key="geometric_factor_source",
        )

        st.form_submit_button(
            "Calculate and add measurement",
            type="primary",
            icon=":material/add:",
            width="stretch",
            on_click=submit_measurement,
            key="submit_measurement",
        )

    errors = cast(list[str], st.session_state["form_errors"])
    if errors:
        st.error("Measurement could not be added.\n\n" + "\n\n".join(errors))

    for kind, message in cast(list[tuple[str, str]], st.session_state["form_notices"]):
        if kind == "success":
            st.success(message)
        else:
            st.warning(message)


def render_latest_result() -> None:
    """Render the most recently calculated result and its SI traceability."""
    result = cast(MeasurementResult | None, st.session_state["last_result"])
    if result is None:
        return

    number_format = get_number_format()

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
        if result.spacing_ab2_m is not None:
            st.write(f"AB/2 = {full(result.spacing_ab2_m)} m")
        st.write(f"$\\rho_a$ = {full(rho_a)} {OHM_METER}")


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
            data=measurement_results_to_csv(
                results,
                dialect=cast(CsvDialect, st.session_state["csv_dialect"]),
            ),
            file_name="georesistivity_measurements.csv",
            mime="text/csv",
            icon=":material/download:",
            disabled=not results,
            width="stretch",
        )

    if remove_last:
        results.pop()
        st.session_state["last_result"] = results[-1] if results else None
        st.session_state["confirm_clear"] = False
        st.session_state["form_notices"] = []
        st.rerun()

    if request_clear:
        st.session_state["confirm_clear"] = True

    if not st.session_state["confirm_clear"]:
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
        st.session_state["last_result"] = None
        st.session_state["confirm_clear"] = False
        st.session_state["form_notices"] = []
        st.rerun()
    if cancel_clear:
        st.session_state["confirm_clear"] = False
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
    initialize_session_state()
    render_sidebar()

    st.title("GeoResistivity")
    st.caption("Apparent Resistivity Calculator")
    st.write(
        "Calculate and record apparent resistivity from the externally supplied geometric "
        "factor and measured potential difference and current."
    )

    render_measurement_form()
    render_latest_result()
    st.divider()

    results = get_measurements()
    render_measurements(results)
    render_plot(results)


if __name__ == "__main__":
    main()
