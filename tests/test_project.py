"""Tests for GeoResistivity project files (schema version 2, and migration from 1)."""

import datetime as dt
import json
from pathlib import Path
from typing import Any

import pytest

from georesistivity import __version__
from georesistivity.field_sheet import SheetRow, template_rows
from georesistivity.models import Measurement
from georesistivity.project import (
    SCHEMA,
    SCHEMA_VERSION,
    Project,
    ProjectFormatError,
    SheetSettings,
    SurveyInfo,
    project_from_dict,
    project_from_json,
    project_to_dict,
    project_to_json,
    saved_at,
)
from georesistivity.sheet_history import HistoryEntry

SURVEY = SurveyInfo(
    name="Synthetic sounding",
    area="Test area",
    local="Fazenda Exemplo",
    sev_number="01",
    date=dt.date(2026, 10, 22),
    operator="Operator",
    azimuth_deg=45.0,
    latitude=-15.8,
    longitude=-47.9,
    equipment="Resistivity meter",
    notes="synthetic data",
)


def full_project() -> Project:
    rows = list(template_rows())
    rows[0] = SheetRow(marker="VD", ab2="1", mn="0,5", delta_v="80", current="40")
    rows[1] = SheetRow(ab2="1,3", mn="0,5", delta_v="95")  # incomplete row is kept as typed
    rows[2] = SheetRow(ab2="1,8", mn="0,5", delta_v="1", current="1", excluded=True, reason="x")
    measurement = Measurement(
        delta_v_original=125.0,
        voltage_unit="mV",
        current_original=35.0,
        current_unit="mA",
        geometric_factor_original=625.0,
        geometric_factor_unit="m",
        spacing_ab2_original=20.0,
        spacing_unit="m",
        geometric_factor_source="table",
        mn_original=2.0,
        mn_unit="m",
    )
    return Project(
        survey=SURVEY,
        sheet_settings=SheetSettings(voltage_unit="V", current_unit="A", cv_limit_percent=3.0),
        sheet_rows=tuple(rows),
        measurements=(measurement,),
    )


def test_round_trip_keeps_everything_as_typed() -> None:
    project = full_project()

    assert project_from_json(project_to_json(project)) == project


def test_default_project_is_the_empty_standard_sheet() -> None:
    project = Project()

    assert project.sheet_rows == tuple(template_rows())
    assert not project.has_content()
    assert project_from_json(project_to_json(project)) == project


def test_document_shape() -> None:
    stamp = dt.datetime(2026, 10, 22, 18, 30, 5, tzinfo=dt.timezone(dt.timedelta(hours=-3)))

    data = project_to_dict(full_project(), saved_at=stamp)

    assert data["schema"] == SCHEMA
    assert data["schema_version"] == SCHEMA_VERSION == 2
    assert data["created_with"] == f"georesistivity {__version__}"
    assert data["saved_at"] == "2026-10-22T18:30:05-03:00"
    assert data["survey"]["date"] == "2026-10-22"
    assert data["survey"]["crs"] == "EPSG:4326"
    assert data["sheet"]["array"] == "schlumberger"
    assert data["sheet"]["rows"][0] == {
        "marker": "VD",
        "ab2": "1",
        "mn": "0,5",
        "delta_v": "80",
        "current": "40",
        "excluded": False,
        "reason": "",
        "id": "",
        "entered_at": "",
    }
    assert data["measurements"][0]["mn_original"] == 2.0
    assert data["history"] == []


def test_json_is_readable_utf8_text() -> None:
    project = Project(survey=SurveyInfo(local="São João"))

    text = project_to_json(project)

    assert "São João" in text
    assert text.endswith("\n")
    assert saved_at(text) is None
    assert saved_at(project_to_json(project, saved_at=dt.datetime(2026, 1, 2, 3, 4))) == (
        dt.datetime(2026, 1, 2, 3, 4)
    )


def test_has_content_and_reading_count() -> None:
    assert full_project().reading_count() == 3
    assert full_project().has_content()
    assert Project(survey=SurveyInfo(operator="X")).has_content()
    assert Project(sheet_rows=(SheetRow(marker="AZ", ab2="1", mn="0,5"),)).has_content()


@pytest.mark.parametrize(
    ("survey", "expected"),
    [
        (SurveyInfo(), "georesistivity-project.geores.json"),
        (
            SurveyInfo(sev_number="01", local="Fazenda São João"),
            "SEV-01-Fazenda_São_João.geores.json",
        ),
        (SurveyInfo(sev_number="7/a", name="Linha 3"), "SEV-7_a-Linha_3.geores.json"),
    ],
)
def test_suggested_file_name(survey: SurveyInfo, expected: str) -> None:
    assert Project(survey=survey).suggested_file_name() == expected


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"azimuth_deg": 361.0}, "azimuth_deg must be between 0 and 360"),
        ({"latitude": -91.0}, "latitude must be between -90 and 90"),
        ({"longitude": 181.0}, "longitude must be between -180 and 180"),
        ({"latitude": float("nan")}, "latitude must be a finite number"),
    ],
)
def test_survey_ranges_are_validated(kwargs: dict[str, float], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        SurveyInfo(**kwargs)  # type: ignore[arg-type]


def document(**changes: Any) -> dict[str, Any]:
    data = project_to_dict(full_project())
    for dotted, value in changes.items():
        target = data
        *parents, last = dotted.split("__")
        for key in parents:
            target = target[int(key)] if key.isdigit() else target[key]
        key: int | str = int(last) if last.isdigit() else last
        if value is ...:
            del target[key]
        else:
            target[key] = value
    return data


@pytest.mark.parametrize(
    ("changes", "path", "reason"),
    [
        ({"schema": "other"}, "schema", "not a GeoResistivity project"),
        ({"schema_version": 3}, "schema_version", "newer than this program supports"),
        ({"schema_version": "1"}, "schema_version", "positive integer"),
        ({"schema_version": 0}, "schema_version", "positive integer"),
        ({"extra": 1}, "extra", "unknown field"),
        ({"sheet": ...}, "sheet", "is required"),
        ({"survey__date": "22/10/2026"}, "survey.date", "must be a date written as YYYY-MM-DD"),
        ({"survey__latitude": "south"}, "survey.latitude", "must be a number or null"),
        ({"survey__latitude": 100}, "survey", "latitude must be between"),
        ({"survey__name": 3}, "survey.name", "must be text"),
        ({"survey__color": "red"}, "survey.color", "unknown field"),
        ({"sheet__array": "wenner"}, "sheet.array", "only 'schlumberger'"),
        ({"sheet__rows": {}}, "sheet.rows", "must be a list"),
        ({"sheet__cv_limit_percent": 0}, "sheet.cv_limit_percent", "between 0 and 100"),
        ({"sheet__rows__0__delta_v": 80}, "sheet.rows[0].delta_v", "must be text"),
        ({"sheet__rows__0__excluded": "no"}, "sheet.rows[0].excluded", "true or false"),
        ({"sheet__rows__1": []}, "sheet.rows[1]", "must be an object"),
        ({"measurements": {}}, "measurements", "must be a list"),
        ({"measurements__0__current_original": None}, "measurements[0].current_original", "number"),
        ({"measurements__0__voltage_unit": None}, "measurements[0].voltage_unit", "must be text"),
        ({"measurements__0__mn_unit": None}, "measurements[0]", "MN value and MN unit"),
        ({"measurements__0__current_unit": ...}, "measurements[0].current_unit", "is required"),
        (
            {"measurements__0__geometric_factor_source": 5},
            "measurements[0].geometric_factor_source",
            "text",
        ),
    ],
)
def test_invalid_documents_name_the_problem(
    changes: dict[str, Any],
    path: str,
    reason: str,
) -> None:
    with pytest.raises(ProjectFormatError) as error:
        project_from_dict(document(**changes))

    assert error.value.path == path
    assert reason in error.value.reason


def test_optional_sections_may_be_missing() -> None:
    data = document(survey=..., measurements=...)
    del data["sheet"]["voltage_unit"]

    project = project_from_dict(data)

    assert project.survey == SurveyInfo()
    assert project.measurements == ()
    assert project.sheet_settings.voltage_unit == "mV"


def test_invalid_json_and_non_object_documents_are_rejected() -> None:
    with pytest.raises(ProjectFormatError, match="not valid JSON"):
        project_from_json("{")
    with pytest.raises(ProjectFormatError, match="must be an object"):
        project_from_json("[]")


def test_rows_are_not_validated_on_load_but_kept_as_typed() -> None:
    data = document()
    data["sheet"]["rows"][0]["delta_v"] = "1,000"

    project = project_from_dict(json.loads(json.dumps(data)))

    assert project.sheet_rows[0].delta_v == "1,000"


def test_older_versions_are_migrated_before_reading(monkeypatch: pytest.MonkeyPatch) -> None:
    import georesistivity.project as project_module

    def to_version_3(data: dict[str, Any]) -> dict[str, Any]:
        return {**data, "schema_version": 3, "survey": {"notes": "migrated"}}

    version_2 = document()  # written before the version changes
    monkeypatch.setattr(project_module, "SCHEMA_VERSION", 3)
    monkeypatch.setitem(project_module._MIGRATIONS, 2, to_version_3)

    project = project_from_dict(version_2)

    assert project.survey.notes == "migrated"


def test_boolean_is_not_accepted_as_a_number() -> None:
    with pytest.raises(ProjectFormatError, match="must be a number or null"):
        project_from_dict(document(survey__azimuth_deg=True))


V1_FILE = Path(__file__).with_name("data") / "synthetic_v1.geores.json"
TIME = "2026-10-23T09:00:00-03:00"


def project_with_history() -> Project:
    rows = (
        SheetRow(ab2="1", mn="0,5", delta_v="82", current="40", id="ra", entered_at=TIME),
        SheetRow(ab2="1,3", mn="0,5", id="rb"),
    )
    deleted = SheetRow(ab2="1,8", mn="0,5", delta_v="9", current="50", id="rc", entered_at=TIME)
    history = (
        HistoryEntry(TIME, "edit", row="ra", row_number=1, field="delta_v", old="80", new="82"),
        HistoryEntry(TIME, "delete_row", row="rc", row_number=3, old_row=deleted),
        HistoryEntry(
            TIME,
            "replace_sheet",
            source="import",
            detail="a.csv",
            old_rows=(deleted,),
            old_units=("V", "A"),
        ),
        HistoryEntry(TIME, "append_rows", source="import", detail="b.csv", row_ids=("rb",)),
        HistoryEntry(TIME, "units", old="V / A", new="mV / mA", old_units=("V", "A")),
        HistoryEntry(TIME, "undo", row="ra", row_number=1, field="delta_v", undoes=1),
    )
    return Project(sheet_rows=rows, history=history)


def test_version_2_keeps_row_ids_reading_times_and_history() -> None:
    project = project_with_history()

    read = project_from_json(project_to_json(project))

    assert read == project
    assert [(row.id, row.entered_at) for row in read.sheet_rows] == [("ra", TIME), ("rb", "")]
    assert read.history[1].old_row is not None
    assert read.history[1].old_row.id == "rc"


def test_history_entries_store_only_their_own_fields() -> None:
    data = project_to_dict(project_with_history())

    assert data["history"][0] == {
        "at": TIME,
        "action": "edit",
        "row": "ra",
        "row_number": 1,
        "field": "delta_v",
        "old": "80",
        "new": "82",
    }
    assert data["history"][3] == {
        "at": TIME,
        "action": "append_rows",
        "source": "import",
        "detail": "b.csv",
        "row_ids": ["rb"],
    }


def test_version_1_file_is_migrated_with_new_row_ids() -> None:
    project = project_from_json(V1_FILE.read_text(encoding="utf-8"))

    assert [row.delta_v for row in project.sheet_rows] == ["80", "45", ""]
    assert project.sheet_rows[1].reason == "loose electrode"
    assert len({row.id for row in project.sheet_rows}) == 3
    assert all(row.id and row.entered_at == "" for row in project.sheet_rows)
    assert project.history == ()
    assert project_to_dict(project)["schema_version"] == 2


def history_document(**changes: Any) -> dict[str, Any]:
    data = project_to_dict(project_with_history())
    for dotted, value in changes.items():
        target = data
        *parents, last = dotted.split("__")
        for key in parents:
            target = target[int(key)] if key.isdigit() else target[key]
        key: int | str = int(last) if last.isdigit() else last
        target[key] = value
    return data


@pytest.mark.parametrize(
    ("changes", "path", "reason"),
    [
        ({"sheet__rows__1__id": "ra"}, "sheet.rows[1].id", "'ra' is used by more than one row"),
        ({"sheet__rows__0__entered_at": "yesterday"}, "sheet.rows[0].entered_at", "with offset"),
        (
            {"sheet__rows__0__entered_at": "2026-10-23T09:00:00"},
            "sheet.rows[0].entered_at",
            "offset",
        ),
        ({"history": {}}, "history", "must be a list"),
        ({"history__0__action": "move"}, "history[0].action", "must be one of: edit"),
        ({"history__0__field": "colour"}, "history[0].field", "must be one of: marker"),
        ({"history__2__source": "web"}, "history[2].source", "must be one of: import"),
        ({"history__0__at": "now"}, "history[0].at", "with offset"),
        ({"history__0__row_number": 0}, "history[0].row_number", "earlier entry"),
        ({"history__5__undoes": 6}, "history[5].undoes", "earlier entry"),
        ({"history__2__old_units": ["V"]}, "history[2].old_units", "DeltaV unit and the current"),
        ({"history__1__old_row": {"ab2": 1}}, "history[1].old_row.ab2", "must be text"),
        ({"history__0__extra": 1}, "history[0].extra", "unknown field"),
    ],
)
def test_invalid_history_names_the_problem(changes: dict[str, Any], path: str, reason: str) -> None:
    with pytest.raises(ProjectFormatError) as error:
        project_from_dict(history_document(**changes))

    assert error.value.path == path
    assert reason in error.value.reason


def test_rows_in_the_history_may_leave_out_default_fields() -> None:
    project = project_from_dict(history_document(history__1__old_row={"ab2": "1,8"}))

    assert project.history[1].old_row == SheetRow(ab2="1,8")
