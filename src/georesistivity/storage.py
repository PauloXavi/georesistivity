"""Local files of an installation: autosave copies and field-sheet templates.

Files live under ``~/GeoResistivity`` (or the directory in the ``GEORESISTIVITY_HOME``
environment variable). Every write is atomic: the text goes to a temporary file in the same
directory, which then replaces the target, so a crash never leaves a half-written file.
Each interface session autosaves to its own file, so two devices on the same computer (for
example a laptop and a tablet in LAN mode) never overwrite each other's work.
"""

import contextlib
import datetime as dt
import os
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from georesistivity.project import (
    FILE_SUFFIX,
    Project,
    ProjectFormatError,
    SheetTemplate,
    project_from_json,
    project_to_json,
    saved_at,
    template_from_json,
    template_to_json,
)

HOME_VARIABLE = "GEORESISTIVITY_HOME"
_AUTOSAVE_PREFIX = "session-"
_TEMPLATE_SUFFIX = ".template.json"


def data_home() -> Path:
    """Directory of the local GeoResistivity files."""
    override = os.environ.get(HOME_VARIABLE)
    return Path(override) if override else Path.home() / "GeoResistivity"


def autosave_dir() -> Path:
    return data_home() / "autosave"


def templates_dir() -> Path:
    return data_home() / "templates"


def atomic_write_text(path: Path, text: str) -> None:
    """Write UTF-8 ``text`` to ``path`` so that readers see the old or the new content only."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)
        raise


def new_session_id(now: dt.datetime | None = None) -> str:
    """Return a unique, time-ordered identifier for an interface session."""
    moment = now or dt.datetime.now()
    return f"{moment:%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:8]}"


def autosave_path(session_id: str) -> Path:
    return autosave_dir() / f"{_AUTOSAVE_PREFIX}{session_id}{FILE_SUFFIX}"


def write_autosave(session_id: str, project: Project, *, now: dt.datetime | None = None) -> Path:
    """Save ``project`` as the autosave copy of ``session_id`` and return its path."""
    path = autosave_path(session_id)
    moment = now or dt.datetime.now().astimezone()
    atomic_write_text(path, project_to_json(project, saved_at=moment))
    return path


@dataclass(frozen=True, slots=True)
class AutosaveEntry:
    """A readable autosave copy, newest first in :func:`list_autosaves`."""

    path: Path
    session_id: str
    saved_at: dt.datetime
    project: Project


def list_autosaves(*, exclude_session: str | None = None, limit: int = 5) -> list[AutosaveEntry]:
    """Return the newest readable autosave copies, skipping ``exclude_session``.

    Unreadable files are left untouched and not listed.
    """
    directory = autosave_dir()
    if not directory.is_dir():
        return []
    entries = []
    for path in directory.glob(f"{_AUTOSAVE_PREFIX}*{FILE_SUFFIX}"):
        session_id = path.name.removeprefix(_AUTOSAVE_PREFIX).removesuffix(FILE_SUFFIX)
        if session_id == exclude_session:
            continue
        try:
            text = path.read_text(encoding="utf-8")
            project = project_from_json(text)
        except (OSError, UnicodeDecodeError, ProjectFormatError):
            continue
        moment = saved_at(text) or dt.datetime.fromtimestamp(path.stat().st_mtime).astimezone()
        entries.append(AutosaveEntry(path, session_id, moment, project))
    entries.sort(key=lambda entry: _sortable(entry.saved_at), reverse=True)
    return entries[:limit]


def _sortable(moment: dt.datetime) -> dt.datetime:
    return moment if moment.tzinfo is not None else moment.astimezone()


def _template_file_name(name: str) -> str:
    kept = "".join(char if char.isalnum() or char in "-_" else " " for char in name.strip())
    stem = "_".join(kept.split())[:60] or "template"
    return f"{stem}{_TEMPLATE_SUFFIX}"


def save_template(template: SheetTemplate) -> Path:
    """Save ``template``, replacing a template with the same file name."""
    path = templates_dir() / _template_file_name(template.name)
    atomic_write_text(path, template_to_json(template))
    return path


def list_templates() -> list[SheetTemplate]:
    """Return the readable saved templates, by name."""
    directory = templates_dir()
    if not directory.is_dir():
        return []
    templates = []
    for path in directory.glob(f"*{_TEMPLATE_SUFFIX}"):
        try:
            templates.append(template_from_json(path.read_text(encoding="utf-8")))
        except (OSError, UnicodeDecodeError, ProjectFormatError):
            continue
    return sorted(templates, key=lambda template: template.name.casefold())
