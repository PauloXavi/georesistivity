"""Project controls: survey details, open, save, autosave, and recovery of unsaved work."""

import datetime as dt
import hashlib
from pathlib import Path

import streamlit as st

from georesistivity.app import state
from georesistivity.project import Project, project_from_json, project_to_json
from georesistivity.storage import (
    autosave_dir,
    autosave_enabled,
    list_autosaves,
    write_autosave,
)

RECOVERY_LIMIT = 3


def _show(message: state.Message) -> None:
    kind, text = message
    {"success": st.success, "info": st.info, "warning": st.warning, "error": st.error}[kind](text)


def _load(project_text: str, source: str) -> None:
    try:
        project = project_from_json(project_text)
        state.apply_project(project)
    except ValueError as exc:
        state.set_project_message(("error", f"Could not open {source}: {exc}"))
        return
    state.set_project_message(("success", f"Opened {source}."))


def open_uploaded_project() -> None:
    """File-uploader callback: replace the session with the uploaded project."""
    upload = st.session_state.get(state.OPEN_UPLOAD)
    if upload is None:
        return
    try:
        text = upload.getvalue().decode("utf-8")
    except UnicodeDecodeError:
        state.set_project_message(("error", f"Could not open {upload.name}: not UTF-8 text."))
        return
    _load(text, upload.name)


def restore_autosave(path_text: str) -> None:
    """Button callback: replace the session with an autosave copy."""
    path = Path(path_text)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        state.set_project_message(("error", f"Could not read the autosave copy: {exc}"))
        return
    _load(text, "the autosave copy")


def autosave(project: Project) -> None:
    """Save ``project`` to this session's autosave copy when it changed."""
    if not autosave_enabled():
        state.set_autosave_status(("info", "Autosave is off on this installation."))
        return
    if not project.has_content():
        return
    text = project_to_json(project)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if digest == state.autosave_digest():
        return
    try:
        path = write_autosave(state.session_id(), project)
    except OSError as exc:
        state.set_autosave_status(("error", f"Autosave failed: {exc}. Save the project file."))
        return
    state.set_autosave_digest(digest)
    moment = dt.datetime.now().strftime("%H:%M:%S")
    state.set_autosave_status(("success", f"Autosaved at {moment} in {path.parent}."))


def _render_recovery(project: Project) -> None:
    if project.has_content() or not autosave_enabled():
        return
    entries = list_autosaves(exclude_session=state.session_id(), limit=RECOVERY_LIMIT)
    if not entries:
        return
    st.info("Work from an earlier session was autosaved. Restore it to continue.")
    for entry in entries:
        survey = entry.project.survey
        title = (
            survey.name or survey.local or (f"SEV {survey.sev_number}" if survey.sev_number else "")
        )
        details = [
            title or "Untitled",
            f"{entry.project.reading_count()} readings",
            entry.saved_at.strftime("%d/%m %H:%M"),
        ]
        st.caption(" · ".join(details))
        st.button(
            "Restore",
            key=f"restore_{entry.session_id}",
            icon=":material/restore:",
            on_click=restore_autosave,
            args=(str(entry.path),),
            width="stretch",
        )


def render_project_controls(project: Project) -> None:
    """Open, save, autosave status, and recovery, for the sidebar."""
    st.subheader("Project")
    message = state.project_message()
    if message is not None:
        _show(message)
        state.set_project_message(None)  # shown once, right after the action
    _render_recovery(project)

    st.file_uploader(
        "Open project",
        type=["json"],
        key=state.OPEN_UPLOAD,
        on_change=open_uploaded_project,
        help="A .geores.json file saved by GeoResistivity. It replaces the current sheet, "
        "survey details, and single measurements.",
    )
    st.download_button(
        "Save project",
        data=project_to_json(project, saved_at=dt.datetime.now().astimezone()),
        file_name=project.suggested_file_name(),
        mime="application/json",
        icon=":material/save:",
        disabled=not project.has_content(),
        width="stretch",
        key="save_project",
    )
    status = state.autosave_status()
    if status is not None and status[0] != "success":
        _show(status)
    elif status is not None:
        st.caption(status[1])
    elif autosave_enabled():
        st.caption(f"Autosave starts with the first value typed, in {autosave_dir()}.")


def render_survey_details() -> None:
    """Header of the field sheet: area, place, SEV number, date, operator, and so on."""
    survey = state.survey_info()
    with st.expander("Survey details", expanded=survey.is_empty(), icon=":material/assignment:"):
        name_column, sev_column, date_column = st.columns([3, 1, 2])
        with name_column:
            st.text_input("Survey name", key=state.META_NAME)
        with sev_column:
            st.text_input("SEV nº", key=state.META_SEV)
        with date_column:
            st.date_input("Date", key=state.META_DATE, format="DD/MM/YYYY")

        area_column, local_column = st.columns(2)
        with area_column:
            st.text_input("Area", key=state.META_AREA)
        with local_column:
            st.text_input("Place", key=state.META_LOCAL)

        operator_column, equipment_column = st.columns(2)
        with operator_column:
            st.text_input("Operator", key=state.META_OPERATOR)
        with equipment_column:
            st.text_input("Equipment", key=state.META_EQUIPMENT)

        azimuth_column, latitude_column, longitude_column = st.columns(3)
        with azimuth_column:
            st.number_input(
                "Azimuth of AB [°]",
                min_value=0.0,
                max_value=360.0,
                step=1.0,
                format="%.1f",
                key=state.META_AZIMUTH,
                help="Direction of the current-electrode line, in degrees from north.",
            )
        with latitude_column:
            st.number_input(
                "Latitude [°]",
                min_value=-90.0,
                max_value=90.0,
                step=0.000001,
                format="%.6f",
                key=state.META_LATITUDE,
                help="WGS 84 decimal degrees; negative south of the equator.",
            )
        with longitude_column:
            st.number_input(
                "Longitude [°]",
                min_value=-180.0,
                max_value=180.0,
                step=0.000001,
                format="%.6f",
                key=state.META_LONGITUDE,
                help="WGS 84 decimal degrees; negative west of Greenwich.",
            )
        st.text_area("Notes", key=state.META_NOTES, height=80)
