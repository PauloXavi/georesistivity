"""Project controls: survey details, open, save, autosave, and recovery of unsaved work."""

import datetime as dt
import hashlib
from pathlib import Path

import streamlit as st

from georesistivity.app import state
from georesistivity.app.i18n import count, error_text, t
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
        message = t("project.open_failed", source=source, error=error_text(exc))
        state.set_project_message(("error", message))
        return
    state.set_project_message(("success", t("project.opened", source=source)))


def open_uploaded_project() -> None:
    """File-uploader callback: replace the session with the uploaded project."""
    upload = st.session_state.get(state.OPEN_UPLOAD)
    if upload is None:
        return
    try:
        text = upload.getvalue().decode("utf-8")
    except UnicodeDecodeError:
        state.set_project_message(("error", t("project.not_utf8", name=upload.name)))
        return
    _load(text, upload.name)


def restore_autosave(path_text: str) -> None:
    """Button callback: replace the session with an autosave copy."""
    path = Path(path_text)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        state.set_project_message(("error", t("project.read_failed", error=exc)))
        return
    _load(text, t("project.autosave_source"))


def autosave(project: Project) -> None:
    """Save ``project`` to this session's autosave copy when it changed."""
    if not autosave_enabled():
        state.set_autosave_status(("info", "autosave.off", {}))
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
        state.set_autosave_status(("error", "autosave.failed", {"error": exc}))
        return
    state.set_autosave_digest(digest)
    moment = dt.datetime.now().strftime("%H:%M:%S")
    state.set_autosave_status(("success", "autosave.done", {"time": moment, "folder": path.parent}))


def _render_recovery(project: Project) -> None:
    if project.has_content() or not autosave_enabled():
        return
    entries = list_autosaves(exclude_session=state.session_id(), limit=RECOVERY_LIMIT)
    if not entries:
        return
    st.info(t("recovery.info"))
    for entry in entries:
        survey = entry.project.survey
        sev = t("recovery.sev", number=survey.sev_number) if survey.sev_number else ""
        title = survey.name or survey.local or sev
        details = [
            title or t("recovery.untitled"),
            count("count.reading", entry.project.reading_count()),
            entry.saved_at.strftime("%d/%m %H:%M"),
        ]
        st.caption(" · ".join(details))
        st.button(
            t("recovery.restore"),
            key=f"restore_{entry.session_id}",
            icon=":material/restore:",
            on_click=restore_autosave,
            args=(str(entry.path),),
            width="stretch",
        )


def render_project_controls(project: Project) -> None:
    """Open, save, autosave status, and recovery, for the sidebar."""
    st.subheader(t("project.title"))
    message = state.project_message()
    if message is not None:
        _show(message)
        state.set_project_message(None)  # shown once, right after the action
    _render_recovery(project)

    st.file_uploader(
        t("project.open"),
        type=["json"],
        key=state.OPEN_UPLOAD,
        on_change=open_uploaded_project,
        help=t("project.open_help"),
    )
    st.download_button(
        t("project.save"),
        data=project_to_json(project, saved_at=dt.datetime.now().astimezone()),
        file_name=project.suggested_file_name(),
        mime="application/json",
        icon=":material/save:",
        disabled=not project.has_content(),
        width="stretch",
        key="save_project",
    )
    status = state.autosave_status()
    if status is None:
        if autosave_enabled():
            st.caption(t("autosave.pending", folder=autosave_dir()))
        return
    kind, key, params = status
    text = t(key, **params)
    if kind == "success":
        st.caption(text)
    else:
        _show((kind, text))


def render_survey_details() -> None:
    """Header of the field sheet: area, place, SEV number, date, operator, and so on."""
    # A fixed "expanded" value keeps the panel open while typing; deriving it from the content
    # would collapse it after the first field.
    with st.expander(
        t("survey.title"), expanded=state.survey_expanded(), icon=":material/assignment:"
    ):
        name_column, sev_column, date_column = st.columns([3, 1, 2])
        with name_column:
            st.text_input(t("survey.name"), key=state.META_NAME)
        with sev_column:
            st.text_input(t("survey.sev"), key=state.META_SEV)
        with date_column:
            st.date_input(t("survey.date"), key=state.META_DATE, format="DD/MM/YYYY")

        area_column, local_column = st.columns(2)
        with area_column:
            st.text_input(t("survey.area"), key=state.META_AREA)
        with local_column:
            st.text_input(t("survey.place"), key=state.META_LOCAL)

        operator_column, equipment_column = st.columns(2)
        with operator_column:
            st.text_input(t("survey.operator"), key=state.META_OPERATOR)
        with equipment_column:
            st.text_input(t("survey.equipment"), key=state.META_EQUIPMENT)

        azimuth_column, latitude_column, longitude_column = st.columns(3)
        with azimuth_column:
            st.number_input(
                t("survey.azimuth"),
                min_value=0.0,
                max_value=360.0,
                step=1.0,
                format="%.1f",
                key=state.META_AZIMUTH,
                help=t("survey.azimuth_help"),
            )
        with latitude_column:
            st.number_input(
                t("survey.latitude"),
                min_value=-90.0,
                max_value=90.0,
                step=0.000001,
                format="%.6f",
                key=state.META_LATITUDE,
                help=t("survey.latitude_help"),
            )
        with longitude_column:
            st.number_input(
                t("survey.longitude"),
                min_value=-180.0,
                max_value=180.0,
                step=0.000001,
                format="%.6f",
                key=state.META_LONGITUDE,
                help=t("survey.longitude_help"),
            )
        st.text_area(t("survey.notes"), key=state.META_NOTES, height=80)
