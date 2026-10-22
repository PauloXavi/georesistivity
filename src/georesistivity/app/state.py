"""Typed access to the Streamlit session state of the GeoResistivity interface."""

from typing import Literal, cast

import streamlit as st

from georesistivity.formatting import NumberFormat
from georesistivity.io import CsvDialect
from georesistivity.models import MeasurementResult
from georesistivity.services import MeasurementInput

# Session keys. Widget keys are session keys too, so they are defined here as well.
MEASUREMENTS = "measurements"
LAST_RESULT = "last_result"
CONFIRM_CLEAR = "confirm_clear"
FORM_ERRORS = "form_errors"
FORM_NOTICES = "form_notices"
NUMBER_FORMAT = "number_format"
CSV_DIALECT = "csv_dialect"

DELTA_V = "delta_v_raw"
VOLTAGE_UNIT = "voltage_unit"
CURRENT = "current_raw"
CURRENT_UNIT = "current_unit"
GEOMETRIC_FACTOR = "geometric_factor_raw"
GEOMETRIC_FACTOR_UNIT = "geometric_factor_unit"
SPACING = "spacing_raw"
SPACING_UNIT = "spacing_unit"
GEOMETRIC_FACTOR_SOURCE = "geometric_factor_source"

# Numeric text fields cleared after a measurement is added; units and K source are kept.
VALUE_FIELDS = (DELTA_V, CURRENT, GEOMETRIC_FACTOR, SPACING)

NoticeKind = Literal["success", "warning"]
Notice = tuple[NoticeKind, str]


def initialize() -> None:
    """Create the session entries that are not owned by a widget."""
    st.session_state.setdefault(MEASUREMENTS, [])
    st.session_state.setdefault(LAST_RESULT, None)
    st.session_state.setdefault(CONFIRM_CLEAR, False)
    st.session_state.setdefault(FORM_ERRORS, [])
    st.session_state.setdefault(FORM_NOTICES, [])
    st.session_state.setdefault(NUMBER_FORMAT, "pt-BR")
    st.session_state.setdefault(CSV_DIALECT, "standard")


def measurements() -> list[MeasurementResult]:
    """Measurements of the session, in acquisition order. The list is mutable."""
    return cast(list[MeasurementResult], st.session_state[MEASUREMENTS])


def last_result() -> MeasurementResult | None:
    return cast(MeasurementResult | None, st.session_state[LAST_RESULT])


def set_last_result(result: MeasurementResult | None) -> None:
    st.session_state[LAST_RESULT] = result


def confirm_clear() -> bool:
    return cast(bool, st.session_state[CONFIRM_CLEAR])


def set_confirm_clear(value: bool) -> None:
    st.session_state[CONFIRM_CLEAR] = value


def form_errors() -> list[str]:
    return cast(list[str], st.session_state[FORM_ERRORS])


def set_form_errors(errors: list[str]) -> None:
    st.session_state[FORM_ERRORS] = errors


def form_notices() -> list[Notice]:
    return cast(list[Notice], st.session_state[FORM_NOTICES])


def set_form_notices(notices: list[Notice]) -> None:
    st.session_state[FORM_NOTICES] = notices


def number_format() -> NumberFormat:
    return cast(NumberFormat, st.session_state[NUMBER_FORMAT])


def csv_dialect() -> CsvDialect:
    return cast(CsvDialect, st.session_state[CSV_DIALECT])


def measurement_input() -> MeasurementInput:
    """Read the measurement form widgets."""
    state = st.session_state
    return MeasurementInput(
        delta_v=state[DELTA_V],
        voltage_unit=state[VOLTAGE_UNIT],
        current=state[CURRENT],
        current_unit=state[CURRENT_UNIT],
        geometric_factor=state[GEOMETRIC_FACTOR],
        geometric_factor_unit=state[GEOMETRIC_FACTOR_UNIT],
        spacing_ab2=state[SPACING],
        spacing_unit=state[SPACING_UNIT],
        geometric_factor_source=state[GEOMETRIC_FACTOR_SOURCE],
    )


def clear_value_fields() -> None:
    """Empty the numeric fields. Only valid inside a widget callback."""
    for key in VALUE_FIELDS:
        st.session_state[key] = ""
