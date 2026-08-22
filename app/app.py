"""Streamlit presentation layer for GeoResistivity."""

from typing import cast

import streamlit as st

from georesistivity import (
    Measurement,
    MeasurementResult,
    calculate_measurement,
    create_resistivity_figure,
    find_log_incompatible_points,
    measurement_results_to_csv,
    measurement_results_to_dataframe,
    parse_number,
    prepare_plot_points,
)

VOLTAGE_UNITS = ("V", "mV", "µV")
CURRENT_UNITS = ("A", "mA", "µA")
LENGTH_UNITS = ("m", "cm", "mm", "km")


def initialize_session_state() -> None:
    """Initialize session-only application state."""
    st.session_state.setdefault("measurements", [])
    st.session_state.setdefault("last_result", None)
    st.session_state.setdefault("confirm_clear", False)


def get_measurements() -> list[MeasurementResult]:
    """Return the typed collection stored for the current session."""
    return cast(list[MeasurementResult], st.session_state["measurements"])


def render_sidebar() -> None:
    """Render project context and the approved scientific basis."""
    with st.sidebar:
        st.header("GeoResistivity")
        st.caption("Scientific calculation workspace")

        st.subheader("About")
        st.write(
            "A modernized educational calculator for recording independent "
            "apparent-resistivity measurements."
        )

        st.subheader("Scientific basis")
        st.latex(r"\rho_a = K \frac{\Delta V}{I}")
        st.markdown(
            """
            - $\\rho_a$: apparent resistivity [ohm.m]
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


def render_measurement_form() -> None:
    """Render the measurement form and process one submission."""
    st.subheader("Measurement Input")
    with st.form("measurement_form"):
        voltage_value_column, voltage_unit_column = st.columns([3, 1])
        with voltage_value_column:
            delta_v_raw = st.text_input("Delta V", placeholder="e.g. 120,5")
        with voltage_unit_column:
            voltage_unit = st.selectbox("Voltage unit", VOLTAGE_UNITS, index=1)

        current_value_column, current_unit_column = st.columns([3, 1])
        with current_value_column:
            current_raw = st.text_input("Current", placeholder="e.g. 20")
        with current_unit_column:
            current_unit = st.selectbox("Current unit", CURRENT_UNITS, index=1)

        factor_value_column, factor_unit_column = st.columns([3, 1])
        with factor_value_column:
            geometric_factor_raw = st.text_input("Geometric Factor K", placeholder="e.g. 5,89")
        with factor_unit_column:
            geometric_factor_unit = st.selectbox("K unit", LENGTH_UNITS)

        spacing_value_column, spacing_unit_column = st.columns([3, 1])
        with spacing_value_column:
            spacing_raw = st.text_input("AB/2 — optional", placeholder="Leave blank if unknown")
        with spacing_unit_column:
            spacing_unit_selection = st.selectbox("Spacing unit", LENGTH_UNITS)

        geometric_factor_source = st.text_input(
            "Geometric factor source — optional",
            placeholder="e.g. equipment, table, field sheet",
        )

        submitted = st.form_submit_button(
            "Calculate and add measurement",
            type="primary",
            icon=":material/add:",
            width="stretch",
        )

    if not submitted:
        return

    try:
        spacing_supplied = bool(spacing_raw.strip())
        measurement = Measurement(
            delta_v_original=parse_number(delta_v_raw),
            voltage_unit=voltage_unit,
            current_original=parse_number(current_raw),
            current_unit=current_unit,
            geometric_factor_original=parse_number(geometric_factor_raw),
            geometric_factor_unit=geometric_factor_unit,
            spacing_ab2_original=parse_number(spacing_raw) if spacing_supplied else None,
            spacing_unit=spacing_unit_selection if spacing_supplied else None,
            geometric_factor_source=geometric_factor_source.strip() or None,
        )
        result = calculate_measurement(measurement)
    except (TypeError, ValueError) as exc:
        st.error(f"Measurement could not be added: {exc}")
        return

    get_measurements().append(result)
    st.session_state["last_result"] = result
    st.session_state["confirm_clear"] = False
    st.success("Measurement added to this session.")


def render_latest_result() -> None:
    """Render the most recently calculated result and its SI traceability."""
    result = cast(MeasurementResult | None, st.session_state["last_result"])
    if result is None:
        return

    st.subheader("Latest Result")
    st.metric(
        "Apparent Resistivity",
        f"{result.apparent_resistivity_ohm_m:,.2f} ohm·m",
    )
    with st.expander("Converted values"):
        st.write(f"Delta V = {result.delta_v_v:.12g} V")
        st.write(f"I = {result.current_a:.12g} A")
        st.write(f"K = {result.geometric_factor_m:.12g} m")
        if result.spacing_ab2_m is not None:
            st.write(f"AB/2 = {result.spacing_ab2_m:.12g} m")


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
            data=measurement_results_to_csv(results),
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
    acquisition_order_points = prepare_plot_points(results)
    if len(acquisition_order_points) < 2:
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
        )

    points = prepare_plot_points(results, sort_by_spacing=sort_by_spacing)
    scale = "log-log" if scale_label == "Log-log" else "linear"
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
        initial_sidebar_state="expanded",
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
