"""Typed access to the Streamlit session state of the GeoResistivity interface."""

from collections.abc import Sequence
from typing import Any, Literal, cast

import streamlit as st

from georesistivity.app.common import CURRENT_UNITS, VOLTAGE_UNITS
from georesistivity.app.i18n import DEFAULT_LANGUAGE, LANGUAGE_KEY
from georesistivity.core import calculate_measurement
from georesistivity.field_sheet import SheetRow, template_rows
from georesistivity.formatting import NumberFormat
from georesistivity.io import CsvDialect
from georesistivity.messages import GeoValueError
from georesistivity.models import MeasurementResult
from georesistivity.project import Project, SheetSettings, SurveyInfo
from georesistivity.services import GeometricFactorMode, MeasurementInput
from georesistivity.stacking import DEFAULT_CV_THRESHOLD
from georesistivity.storage import new_session_id

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
MN = "mn_raw"
MN_UNIT = "mn_unit"
K_MODE = "geometric_factor_mode"

SHEET_ROWS = "sheet_rows"
SHEET_VERSION = "sheet_version"
SHEET_VOLTAGE_UNIT = "sheet_voltage_unit"
SHEET_CURRENT_UNIT = "sheet_current_unit"
SHEET_CV_LIMIT = "sheet_cv_limit_percent"
SHEET_ERROR_BARS = "sheet_error_bars"
SHEET_CONFIRM_NEW = "sheet_confirm_new"

SESSION_ID = "session_id"
CURRENT_SHEET_ROWS = "current_sheet_rows"
AUTOSAVE_DIGEST = "autosave_digest"
AUTOSAVE_STATUS = "autosave_status"
PROJECT_MESSAGE = "project_message"
OPEN_UPLOAD = "open_project_upload"
TEMPLATE_CHOICE = "sheet_template_choice"
TEMPLATE_NAME = "sheet_template_name"
TEMPLATE_MESSAGE = "sheet_template_message"
SURVEY_EXPANDED = "survey_details_expanded"
IMPORT_UPLOAD = "import_upload"
IMPORT_FILE = "import_file"
IMPORT_MESSAGE = "import_message"

META_NAME = "survey_name"
META_AREA = "survey_area"
META_LOCAL = "survey_local"
META_SEV = "survey_sev_number"
META_DATE = "survey_date"
META_OPERATOR = "survey_operator"
META_AZIMUTH = "survey_azimuth"
META_LATITUDE = "survey_latitude"
META_LONGITUDE = "survey_longitude"
META_EQUIPMENT = "survey_equipment"
META_NOTES = "survey_notes"
# Text fields of SurveyInfo and their widget keys.
META_TEXT_FIELDS = {
    "name": META_NAME,
    "area": META_AREA,
    "local": META_LOCAL,
    "sev_number": META_SEV,
    "operator": META_OPERATOR,
    "equipment": META_EQUIPMENT,
    "notes": META_NOTES,
}
# Optional fields of SurveyInfo (None when empty) and their widget keys.
META_OPTIONAL_FIELDS = {
    "date": META_DATE,
    "azimuth_deg": META_AZIMUTH,
    "latitude": META_LATITUDE,
    "longitude": META_LONGITUDE,
}

# Bounds of the CV limit input; projects outside them cannot be shown.
CV_LIMIT_RANGE = (0.1, 100.0)

K_CALCULATOR_ARRAY = "k_calculator_array"
K_CALCULATOR_UNIT = "k_calculator_unit"
K_CALCULATOR_PREFIX = "k_calculator_"

# Numeric text fields cleared after a measurement is added. Units, MN, and the K source are
# kept, because they usually stay the same over several readings.
VALUE_FIELDS = (DELTA_V, CURRENT, GEOMETRIC_FACTOR, SPACING)

NoticeKind = Literal["success", "warning"]
Notice = tuple[NoticeKind, str]


def initialize() -> None:
    """Create the session entries that are not owned by a widget."""
    st.session_state.setdefault(LANGUAGE_KEY, DEFAULT_LANGUAGE)
    st.session_state.setdefault(MEASUREMENTS, [])
    st.session_state.setdefault(LAST_RESULT, None)
    st.session_state.setdefault(CONFIRM_CLEAR, False)
    st.session_state.setdefault(FORM_ERRORS, [])
    st.session_state.setdefault(FORM_NOTICES, [])
    st.session_state.setdefault(NUMBER_FORMAT, "pt-BR")
    st.session_state.setdefault(CSV_DIALECT, "standard")
    st.session_state.setdefault(K_MODE, "external")
    st.session_state.setdefault(SHEET_ROWS, template_rows())
    st.session_state.setdefault(SHEET_VERSION, 0)
    st.session_state.setdefault(SHEET_VOLTAGE_UNIT, "mV")
    st.session_state.setdefault(SHEET_CURRENT_UNIT, "mA")
    st.session_state.setdefault(SHEET_CV_LIMIT, 100.0 * DEFAULT_CV_THRESHOLD)
    st.session_state.setdefault(SHEET_ERROR_BARS, True)
    st.session_state.setdefault(SHEET_CONFIRM_NEW, False)
    st.session_state.setdefault(SESSION_ID, new_session_id())
    st.session_state.setdefault(CURRENT_SHEET_ROWS, None)
    st.session_state.setdefault(AUTOSAVE_DIGEST, None)
    st.session_state.setdefault(AUTOSAVE_STATUS, None)
    st.session_state.setdefault(PROJECT_MESSAGE, None)
    st.session_state.setdefault(TEMPLATE_CHOICE, "")
    st.session_state.setdefault(TEMPLATE_NAME, "")
    st.session_state.setdefault(TEMPLATE_MESSAGE, None)
    st.session_state.setdefault(SURVEY_EXPANDED, True)
    st.session_state.setdefault(IMPORT_FILE, None)
    st.session_state.setdefault(IMPORT_MESSAGE, None)
    for key in META_TEXT_FIELDS.values():
        st.session_state.setdefault(key, "")
    for key in META_OPTIONAL_FIELDS.values():
        st.session_state.setdefault(key, None)


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


def geometric_factor_mode() -> GeometricFactorMode:
    return cast(GeometricFactorMode, st.session_state[K_MODE])


def measurement_input() -> MeasurementInput:
    """Read the measurement form widgets.

    Widgets that the current K mode does not show have no session entry, so they read as
    empty.
    """
    state = st.session_state
    return MeasurementInput(
        delta_v=state.get(DELTA_V, ""),
        voltage_unit=state[VOLTAGE_UNIT],
        current=state.get(CURRENT, ""),
        current_unit=state[CURRENT_UNIT],
        geometric_factor=state.get(GEOMETRIC_FACTOR, ""),
        geometric_factor_unit=state.get(GEOMETRIC_FACTOR_UNIT, "m"),
        spacing_ab2=state.get(SPACING, ""),
        spacing_unit=state[SPACING_UNIT],
        geometric_factor_source=state.get(GEOMETRIC_FACTOR_SOURCE, ""),
        mn=state.get(MN, ""),
        mn_unit=state[MN_UNIT],
        geometric_factor_mode=geometric_factor_mode(),
    )


def clear_value_fields() -> None:
    """Empty the numeric fields. Only valid inside a widget callback."""
    for key in VALUE_FIELDS:
        st.session_state[key] = ""


def sheet_rows() -> list[SheetRow]:
    """Rows the field-sheet editor starts from (the template or a reset sheet)."""
    return cast(list[SheetRow], st.session_state[SHEET_ROWS])


def sheet_editor_key() -> str:
    """Key of the field-sheet editor; a new key discards the editor's edits."""
    return f"sheet_editor_{st.session_state[SHEET_VERSION]}"


def reset_sheet(rows: Sequence[SheetRow] | None = None) -> None:
    """Start a new sheet from ``rows`` (the standard layout by default)."""
    st.session_state[SHEET_ROWS] = (
        list(rows) if rows is not None else template_rows(number_format())
    )
    st.session_state[SHEET_VERSION] = cast(int, st.session_state[SHEET_VERSION]) + 1
    st.session_state[SHEET_CONFIRM_NEW] = False
    st.session_state[CURRENT_SHEET_ROWS] = None


def set_current_sheet_rows(rows: list[SheetRow]) -> None:
    """Remember the rows shown by the editor in this run, for saving."""
    st.session_state[CURRENT_SHEET_ROWS] = rows


def current_sheet_rows() -> list[SheetRow]:
    """Rows of the sheet as currently edited, or the starting rows before the editor runs."""
    rows = st.session_state[CURRENT_SHEET_ROWS]
    return cast(list[SheetRow], rows) if rows is not None else sheet_rows()


def sheet_units() -> tuple[str, str]:
    """Units of DeltaV and I selected for the field sheet."""
    state = st.session_state
    return cast(str, state[SHEET_VOLTAGE_UNIT]), cast(str, state[SHEET_CURRENT_UNIT])


def sheet_cv_threshold() -> float:
    """Coefficient-of-variation limit of the field sheet, as a fraction."""
    return cast(float, st.session_state[SHEET_CV_LIMIT]) / 100.0


def sheet_error_bars() -> bool:
    """Whether the sounding curve shows error bars."""
    return cast(bool, st.session_state[SHEET_ERROR_BARS])


def sheet_confirm_new() -> bool:
    return cast(bool, st.session_state[SHEET_CONFIRM_NEW])


def set_sheet_confirm_new(value: bool) -> None:
    st.session_state[SHEET_CONFIRM_NEW] = value


def session_id() -> str:
    return cast(str, st.session_state[SESSION_ID])


def survey_info() -> SurveyInfo:
    """Survey details from the form widgets."""
    state = st.session_state
    values: dict[str, Any] = {
        name: cast(str, state[key]).strip() for name, key in META_TEXT_FIELDS.items()
    }
    values.update({name: state[key] for name, key in META_OPTIONAL_FIELDS.items()})
    return SurveyInfo(**values)


def current_project() -> Project:
    """Everything this session would save, as of the current run."""
    voltage_unit, current_unit = sheet_units()
    return Project(
        survey=survey_info(),
        sheet_settings=SheetSettings(
            voltage_unit=voltage_unit,
            current_unit=current_unit,
            cv_limit_percent=cast(float, st.session_state[SHEET_CV_LIMIT]),
        ),
        sheet_rows=tuple(current_sheet_rows()),
        measurements=tuple(result.measurement for result in measurements()),
    )


def apply_project(project: Project) -> None:
    """Replace the session content with ``project``. Only valid inside a widget callback.

    Everything is checked before anything changes, so a project that cannot be shown leaves
    the session as it was.
    """
    settings = project.sheet_settings
    if settings.voltage_unit not in VOLTAGE_UNITS:
        raise GeoValueError("project.unsupported_voltage_unit", unit=settings.voltage_unit)
    if settings.current_unit not in CURRENT_UNITS:
        raise GeoValueError("project.unsupported_current_unit", unit=settings.current_unit)
    low, high = CV_LIMIT_RANGE
    if not low <= settings.cv_limit_percent <= high:
        raise GeoValueError("project.cv_limit_shown", low=low, high=high)
    results = [calculate_measurement(measurement) for measurement in project.measurements]

    state = st.session_state
    for name, key in META_TEXT_FIELDS.items():
        state[key] = getattr(project.survey, name)
    for name, key in META_OPTIONAL_FIELDS.items():
        state[key] = getattr(project.survey, name)
    state[SHEET_VOLTAGE_UNIT] = settings.voltage_unit
    state[SHEET_CURRENT_UNIT] = settings.current_unit
    state[SHEET_CV_LIMIT] = settings.cv_limit_percent
    reset_sheet(project.sheet_rows)
    state[MEASUREMENTS] = results
    state[LAST_RESULT] = results[-1] if results else None
    state[CONFIRM_CLEAR] = False
    state[FORM_ERRORS] = []
    state[FORM_NOTICES] = []
    state[AUTOSAVE_DIGEST] = None
    state[SURVEY_EXPANDED] = project.survey.is_empty()


def autosave_digest() -> str | None:
    return cast(str | None, st.session_state[AUTOSAVE_DIGEST])


def set_autosave_digest(digest: str) -> None:
    st.session_state[AUTOSAVE_DIGEST] = digest


Message = tuple[Literal["success", "info", "warning", "error"], str]


Status = tuple[Literal["success", "info", "warning", "error"], str, dict[str, object]]
"""A message kept across runs as (kind, text key, parameters), shown in the current language."""


def autosave_status() -> Status | None:
    return cast(Status | None, st.session_state[AUTOSAVE_STATUS])


def set_autosave_status(status: Status) -> None:
    st.session_state[AUTOSAVE_STATUS] = status


def project_message() -> Message | None:
    return cast(Message | None, st.session_state[PROJECT_MESSAGE])


def set_project_message(message: Message | None) -> None:
    st.session_state[PROJECT_MESSAGE] = message


def template_message() -> Message | None:
    return cast(Message | None, st.session_state[TEMPLATE_MESSAGE])


def set_template_message(message: Message | None) -> None:
    st.session_state[TEMPLATE_MESSAGE] = message


def survey_expanded() -> bool:
    """Whether the survey details open expanded; changes only when a project is loaded."""
    return cast(bool, st.session_state[SURVEY_EXPANDED])


def import_file() -> tuple[str, bytes] | None:
    """Name and content of the CSV file being imported."""
    return cast(tuple[str, bytes] | None, st.session_state[IMPORT_FILE])


def set_import_file(name: str, data: bytes) -> None:
    st.session_state[IMPORT_FILE] = (name, data)


def import_message() -> Message | None:
    return cast(Message | None, st.session_state[IMPORT_MESSAGE])


def set_import_message(message: Message | None) -> None:
    st.session_state[IMPORT_MESSAGE] = message


def sheet_has_readings() -> bool:
    return any(row.delta_v.strip() or row.current.strip() for row in current_sheet_rows())


def replace_sheet(rows: Sequence[SheetRow], voltage_unit: str, current_unit: str) -> None:
    """Start the sheet over with ``rows`` and their units. Only valid inside a callback."""
    st.session_state[SHEET_VOLTAGE_UNIT] = voltage_unit
    st.session_state[SHEET_CURRENT_UNIT] = current_unit
    reset_sheet(rows)


def append_to_sheet(rows: Sequence[SheetRow]) -> None:
    """Add ``rows`` after the current sheet rows. Only valid inside a callback."""
    reset_sheet([*current_sheet_rows(), *rows])
