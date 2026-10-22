"""Tests for local autosave copies and field-sheet templates."""

import datetime as dt
import os
import re
from pathlib import Path

import pytest

from georesistivity.field_sheet import SheetRow, template_rows
from georesistivity.project import (
    Project,
    ProjectFormatError,
    SheetTemplate,
    SurveyInfo,
    template_from_json,
    template_to_json,
)
from georesistivity.storage import (
    AUTOSAVE_VARIABLE,
    HOME_VARIABLE,
    atomic_write_text,
    autosave_enabled,
    autosave_path,
    data_home,
    list_autosaves,
    list_templates,
    new_session_id,
    save_template,
    write_autosave,
)


@pytest.fixture
def home(isolated_data_home: Path) -> Path:
    return isolated_data_home


def test_autosave_is_enabled_unless_switched_off(monkeypatch: pytest.MonkeyPatch) -> None:
    assert autosave_enabled()
    monkeypatch.setenv(AUTOSAVE_VARIABLE, "0")
    assert not autosave_enabled()


def test_data_home_defaults_to_the_user_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(HOME_VARIABLE)

    assert data_home() == Path.home() / "GeoResistivity"


def test_atomic_write_replaces_content_and_leaves_no_temporary_file(home: Path) -> None:
    target = home / "nested" / "file.json"

    atomic_write_text(target, "first")
    atomic_write_text(target, "second")

    assert target.read_text(encoding="utf-8") == "second"
    assert [path.name for path in target.parent.iterdir()] == ["file.json"]


def test_atomic_write_keeps_the_old_file_when_writing_fails(
    home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = home / "file.json"
    atomic_write_text(target, "old")

    def failing_replace(source: str, destination: Path) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", failing_replace)
    with pytest.raises(OSError, match="disk full"):
        atomic_write_text(target, "new")

    assert target.read_text(encoding="utf-8") == "old"
    assert [path.name for path in home.iterdir()] == ["file.json"]


def test_session_ids_are_unique_and_time_ordered() -> None:
    first = new_session_id(dt.datetime(2026, 10, 22, 9, 0, 0))
    second = new_session_id(dt.datetime(2026, 10, 22, 9, 0, 1))

    assert first.startswith("20261022-090000-")
    assert first < second
    assert new_session_id() != new_session_id()


def project_with(name: str) -> Project:
    rows = list(template_rows())
    rows[0] = SheetRow(ab2="1", mn="0,5", delta_v="80", current="40")
    return Project(survey=SurveyInfo(name=name), sheet_rows=tuple(rows))


def test_autosaves_are_listed_newest_first_without_the_current_session(home: Path) -> None:
    write_autosave("a", project_with("old"), now=dt.datetime(2026, 10, 22, 9, 0).astimezone())
    write_autosave("b", project_with("new"), now=dt.datetime(2026, 10, 22, 10, 0).astimezone())
    write_autosave("c", project_with("mine"), now=dt.datetime(2026, 10, 22, 11, 0).astimezone())

    entries = list_autosaves(exclude_session="c")

    assert [entry.session_id for entry in entries] == ["b", "a"]
    assert entries[0].project.survey.name == "new"
    assert entries[0].path == autosave_path("b")
    assert entries[0].saved_at == dt.datetime(2026, 10, 22, 10, 0).astimezone()


def test_autosave_listing_is_limited_and_skips_unreadable_files(home: Path) -> None:
    for minute in range(7):
        moment = dt.datetime(2026, 10, 22, 9, minute).astimezone()
        write_autosave(f"s{minute}", project_with(str(minute)), now=moment)
    autosave_path("broken").write_text("{", encoding="utf-8")

    entries = list_autosaves(limit=3)

    assert [entry.project.survey.name for entry in entries] == ["6", "5", "4"]
    assert autosave_path("broken").exists()


def test_autosave_listing_without_folder_is_empty() -> None:
    assert list_autosaves() == []
    assert list_templates() == []


def test_autosave_without_time_uses_the_file_time(home: Path) -> None:
    path = autosave_path("legacy")
    path.parent.mkdir(parents=True)
    path.write_text(
        '{"schema": "georesistivity.project", "schema_version": 1, "sheet": {"rows": []}}',
        encoding="utf-8",
    )

    (entry,) = list_autosaves()

    assert entry.session_id == "legacy"
    assert entry.saved_at.tzinfo is not None


def test_template_keeps_only_the_layout() -> None:
    rows = [
        SheetRow(marker=" VD ", ab2="1", mn="0,5", delta_v="80", current="40"),
        SheetRow(ab2="1", mn="0,5", delta_v="81", current="40"),  # repeated reading
        SheetRow(marker="AM", ab2="1,3", mn="0,5", excluded=True, reason="x"),
        SheetRow(),  # empty added row
    ]

    template = SheetTemplate.from_rows(" My cable ", rows)

    assert template.name == "My cable"
    assert template.rows == (
        SheetRow(marker="VD", ab2="1", mn="0,5"),
        SheetRow(marker="AM", ab2="1,3", mn="0,5"),
    )
    assert template.sheet_rows() == template.rows


@pytest.mark.parametrize(
    ("name", "rows", "message"),
    [
        ("  ", (SheetRow(ab2="1", mn="0,5"),), "needs a name"),
        ("x", (), "at least one row"),
        ("x", (SheetRow(ab2="1", mn="0,5", delta_v="1"),), "only marker, AB/2, and MN"),
    ],
)
def test_invalid_templates_are_rejected(
    name: str, rows: tuple[SheetRow, ...], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        SheetTemplate(name=name, rows=rows)


def test_templates_round_trip_through_files() -> None:
    cable = SheetTemplate.from_rows("Cabo 2026", [SheetRow(marker="VM", ab2="1", mn="0,5")])
    standard = SheetTemplate.from_rows("Padrão", list(template_rows()))

    path = save_template(cable)
    save_template(standard)
    save_template(cable)  # saving again replaces the file

    assert path.name == "Cabo_2026.template.json"
    assert list_templates() == [cable, standard]
    assert template_from_json(template_to_json(standard)) == standard


def test_unreadable_templates_are_skipped(home: Path) -> None:
    (home / "templates").mkdir()
    (home / "templates" / "broken.template.json").write_text("[]", encoding="utf-8")

    assert list_templates() == []


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("{", "not valid JSON"),
        ('{"schema": "x"}', "not a sheet template"),
        ('{"schema": "georesistivity.sheet-template", "schema_version": 2}', "must be 1"),
        (
            '{"schema": "georesistivity.sheet-template", "schema_version": 1, "name": "x",'
            ' "rows": [{"ab2": "1"}]}',
            "rows[0].mn: is required",
        ),
        (
            '{"schema": "georesistivity.sheet-template", "schema_version": 1, "name": "x",'
            ' "rows": [{"ab2": "1", "mn": "1", "delta_v": "3"}]}',
            "rows[0].delta_v: unknown field",
        ),
        (
            '{"schema": "georesistivity.sheet-template", "schema_version": 1, "name": "x",'
            ' "rows": []}',
            "at least one row",
        ),
    ],
)
def test_invalid_template_files_are_rejected(text: str, message: str) -> None:
    with pytest.raises(ProjectFormatError, match=re.escape(message)):
        template_from_json(text)
