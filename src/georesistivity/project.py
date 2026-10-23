"""GeoResistivity project files (``*.geores.json``), schema version 1.

A project holds the survey details, the field sheet exactly as typed (including blank or
incomplete rows, so that saving never loses work in progress), and the single measurements.
Calculated values are not stored: they are recomputed from the original values when the
project is opened, which keeps the original values as the only source of truth.

Numeric cells of the field sheet are stored as the typed text and read with
:func:`georesistivity.validation.parse_number`, so a file reproduces the sheet exactly in
either decimal convention. Files are validated on load; every problem names its JSON path.
This module does not import Streamlit or pandas.
"""

import dataclasses
import datetime as dt
import json
import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, TypeVar

from georesistivity.field_sheet import SheetRow, template_rows
from georesistivity.messages import GeoValueError, Problem, problem_of
from georesistivity.models import Measurement
from georesistivity.stacking import DEFAULT_CV_THRESHOLD

SCHEMA = "georesistivity.project"
SCHEMA_VERSION = 1
FILE_SUFFIX = ".geores.json"
DEFAULT_CRS = "EPSG:4326"

_T = TypeVar("_T")


class ProjectFormatError(ValueError):
    """A project file that cannot be read, with the JSON path of the problem.

    ``reason`` is English; ``problem`` lets interfaces translate it.
    """

    def __init__(self, path: str, problem: Problem) -> None:
        self.path = path
        self.problem = problem
        self.reason = problem.text()
        super().__init__(f"{path}: {self.reason}" if path else self.reason)


@dataclass(frozen=True, slots=True)
class SurveyInfo:
    """Header of the field sheet: who, where, when, and how."""

    name: str = ""
    area: str = ""
    local: str = ""
    sev_number: str = ""
    date: dt.date | None = None
    operator: str = ""
    azimuth_deg: float | None = None
    """Azimuth of the AB line, in degrees from north (0 to 360)."""
    latitude: float | None = None
    longitude: float | None = None
    crs: str = DEFAULT_CRS
    """Coordinate reference system of latitude and longitude (WGS 84 by default)."""
    equipment: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        _check_range("azimuth_deg", self.azimuth_deg, 0.0, 360.0)
        _check_range("latitude", self.latitude, -90.0, 90.0)
        _check_range("longitude", self.longitude, -180.0, 180.0)

    def is_empty(self) -> bool:
        """Whether nothing was filled in, apart from the default coordinate system."""
        return self == SurveyInfo()


def _check_range(name: str, value: float | None, low: float, high: float) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise GeoValueError("project.not_finite", name=name)
    if not low <= value <= high:
        raise GeoValueError("project.range", name=name, low=low, high=high)


@dataclass(frozen=True, slots=True)
class SheetSettings:
    """Units and quality limit of the field sheet."""

    voltage_unit: str = "mV"
    current_unit: str = "mA"
    cv_limit_percent: float = 100.0 * DEFAULT_CV_THRESHOLD


@dataclass(frozen=True, slots=True)
class Project:
    """Everything a GeoResistivity session can save."""

    survey: SurveyInfo = field(default_factory=SurveyInfo)
    sheet_settings: SheetSettings = field(default_factory=SheetSettings)
    sheet_rows: tuple[SheetRow, ...] = field(default_factory=lambda: tuple(template_rows()))
    measurements: tuple[Measurement, ...] = ()

    def reading_count(self) -> int:
        """Number of field-sheet rows with DeltaV or I typed."""
        return sum(1 for row in self.sheet_rows if row.delta_v.strip() or row.current.strip())

    def has_content(self) -> bool:
        """Whether there is anything worth saving: readings, markers, details, measurements."""
        return (
            self.reading_count() > 0
            or any(row.marker.strip() or row.reason.strip() for row in self.sheet_rows)
            or not self.survey.is_empty()
            or bool(self.measurements)
        )

    def suggested_file_name(self) -> str:
        """File name from the SEV number and the place, e.g. ``SEV-01-Fazenda.geores.json``."""
        parts = ["SEV", self.survey.sev_number, self.survey.local or self.survey.name]
        stem = "-".join(_safe_name(part) for part in parts if _safe_name(part))
        return f"{stem if stem != 'SEV' else 'georesistivity-project'}{FILE_SUFFIX}"


def _safe_name(text: str) -> str:
    kept = "".join(char if char.isalnum() or char in "-_" else " " for char in text.strip())
    return "_".join(kept.split())[:40]


# ---------------------------------------------------------------------------- writing


def _survey_to_dict(survey: SurveyInfo) -> dict[str, Any]:
    data = dataclasses.asdict(survey)
    data["date"] = None if survey.date is None else survey.date.isoformat()
    return data


def project_to_dict(project: Project, *, saved_at: dt.datetime | None = None) -> dict[str, Any]:
    """Return the JSON-compatible content of ``project``."""
    from georesistivity import __version__

    data: dict[str, Any] = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "created_with": f"georesistivity {__version__}",
    }
    if saved_at is not None:
        data["saved_at"] = saved_at.isoformat(timespec="seconds")
    data["survey"] = _survey_to_dict(project.survey)
    data["sheet"] = {
        "array": "schlumberger",
        **dataclasses.asdict(project.sheet_settings),
        "rows": [dataclasses.asdict(row) for row in project.sheet_rows],
    }
    data["measurements"] = [dataclasses.asdict(m) for m in project.measurements]
    return data


def project_to_json(project: Project, *, saved_at: dt.datetime | None = None) -> str:
    """Serialize ``project`` as indented UTF-8 JSON text."""
    return (
        json.dumps(project_to_dict(project, saved_at=saved_at), ensure_ascii=False, indent=2) + "\n"
    )


# ---------------------------------------------------------------------------- reading


def _expect_object(value: object, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProjectFormatError(path, Problem("project.must_be_object"))
    return value


def _check_keys(data: Mapping[str, Any], path: str, allowed: set[str], required: set[str]) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ProjectFormatError(
            f"{path}.{unknown[0]}" if path else unknown[0], Problem("project.unknown_field")
        )
    missing = sorted(required - set(data))
    if missing:
        raise ProjectFormatError(
            f"{path}.{missing[0]}" if path else missing[0], Problem("project.required")
        )


def _typed(value: object, path: str, kind: type[_T], code: str) -> _T:
    if (isinstance(value, bool) and kind is not bool) or not isinstance(value, kind):
        raise ProjectFormatError(path, Problem(code))
    return value


def _text(value: object, path: str) -> str:
    return _typed(value, path, str, "project.must_be_text")


def _optional_number(value: object, path: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ProjectFormatError(path, Problem("project.must_be_number_or_null"))
    return float(value)


def _optional_text(value: object, path: str) -> str | None:
    return None if value is None else _text(value, path)


def _build(path: str, factory: Callable[[], _T]) -> _T:
    try:
        return factory()
    except (TypeError, ValueError) as exc:
        raise ProjectFormatError(path, problem_of(exc)) from exc


_SURVEY_KEYS = {field.name for field in dataclasses.fields(SurveyInfo)}
_SETTINGS_KEYS = {field.name for field in dataclasses.fields(SheetSettings)}
_ROW_KEYS = {field.name for field in dataclasses.fields(SheetRow)}
_MEASUREMENT_KEYS = {field.name for field in dataclasses.fields(Measurement)}
_MEASUREMENT_REQUIRED = {
    "delta_v_original",
    "voltage_unit",
    "current_original",
    "current_unit",
    "geometric_factor_original",
    "geometric_factor_unit",
}


def _read_survey(value: object) -> SurveyInfo:
    path = "survey"
    data = _expect_object(value, path)
    _check_keys(data, path, _SURVEY_KEYS, set())
    text_fields = ("name", "area", "local", "sev_number", "operator", "crs", "equipment", "notes")
    values: dict[str, Any] = {
        name: _text(data[name], f"{path}.{name}") for name in text_fields if name in data
    }
    for name in ("azimuth_deg", "latitude", "longitude"):
        if name in data:
            values[name] = _optional_number(data[name], f"{path}.{name}")
    if data.get("date") is not None:
        date_text = _text(data["date"], f"{path}.date")
        try:
            values["date"] = dt.date.fromisoformat(date_text)
        except ValueError:
            raise ProjectFormatError(f"{path}.date", Problem("project.date")) from None
    return _build(path, lambda: SurveyInfo(**values))


def _read_sheet(value: object) -> tuple[SheetSettings, tuple[SheetRow, ...]]:
    path = "sheet"
    data = _expect_object(value, path)
    _check_keys(data, path, {"array", "rows", *_SETTINGS_KEYS}, {"rows"})
    if data.get("array", "schlumberger") != "schlumberger":
        raise ProjectFormatError(f"{path}.array", Problem("project.array"))

    settings: dict[str, Any] = {}
    for name in ("voltage_unit", "current_unit"):
        if name in data:
            settings[name] = _text(data[name], f"{path}.{name}")
    if "cv_limit_percent" in data:
        limit = _optional_number(data["cv_limit_percent"], f"{path}.cv_limit_percent")
        if limit is None or not 0.0 < limit <= 100.0:
            raise ProjectFormatError(f"{path}.cv_limit_percent", Problem("project.cv_limit"))
        settings["cv_limit_percent"] = limit

    rows_value = _typed(data["rows"], f"{path}.rows", list, "project.must_be_list")
    rows = []
    for index, row_value in enumerate(rows_value):
        row_path = f"{path}.rows[{index}]"
        row = _expect_object(row_value, row_path)
        _check_keys(row, row_path, _ROW_KEYS, set())
        values: dict[str, Any] = {
            name: _text(row[name], f"{row_path}.{name}")
            for name in ("marker", "ab2", "mn", "delta_v", "current", "reason")
            if name in row
        }
        if "excluded" in row:
            values["excluded"] = _typed(
                row["excluded"], f"{row_path}.excluded", bool, "project.must_be_flag"
            )
        rows.append(SheetRow(**values))
    return SheetSettings(**settings), tuple(rows)


def _read_measurements(value: object) -> tuple[Measurement, ...]:
    path = "measurements"
    items = _typed(value, path, list, "project.must_be_list")
    measurements = []
    for index, item in enumerate(items):
        item_path = f"{path}[{index}]"
        data = _expect_object(item, item_path)
        _check_keys(data, item_path, _MEASUREMENT_KEYS, _MEASUREMENT_REQUIRED)
        values: dict[str, Any] = {}
        for name in _MEASUREMENT_KEYS & set(data):
            field_path = f"{item_path}.{name}"
            if name.endswith("_original"):
                number = _optional_number(data[name], field_path)
                if number is None and name in _MEASUREMENT_REQUIRED:
                    raise ProjectFormatError(field_path, Problem("project.must_be_number"))
                values[name] = number
            elif name in _MEASUREMENT_REQUIRED:
                values[name] = _text(data[name], field_path)
            else:
                values[name] = _optional_text(data[name], field_path)
        measurements.append(_build_measurement(item_path, values))
    return tuple(measurements)


def _build_measurement(path: str, values: dict[str, Any]) -> Measurement:
    return _build(path, lambda: Measurement(**values))


# Migrations from older schema versions: version -> function returning the next version.
_MIGRATIONS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {}


def project_from_dict(data: object) -> Project:
    """Validate and read the JSON content of a project, migrating older versions."""
    document = _expect_object(data, "")
    if document.get("schema") != SCHEMA:
        raise ProjectFormatError("schema", Problem("project.not_project", {"expected": SCHEMA}))
    version = document.get("schema_version")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise ProjectFormatError("schema_version", Problem("project.bad_version"))
    if version > SCHEMA_VERSION:
        raise ProjectFormatError(
            "schema_version",
            Problem("project.newer_version", {"version": version, "supported": SCHEMA_VERSION}),
        )
    while version < SCHEMA_VERSION:
        document = _MIGRATIONS[version](document)
        version = document["schema_version"]

    _check_keys(
        document,
        "",
        {"schema", "schema_version", "created_with", "saved_at", "survey", "sheet", "measurements"},
        {"schema", "schema_version", "sheet"},
    )
    survey = _read_survey(document.get("survey", {}))
    settings, rows = _read_sheet(document["sheet"])
    measurements = _read_measurements(document.get("measurements", []))
    return Project(
        survey=survey, sheet_settings=settings, sheet_rows=rows, measurements=measurements
    )


def project_from_json(text: str) -> Project:
    """Read a project from JSON text."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProjectFormatError(
            "", Problem("project.invalid_json", {"line": exc.lineno, "column": exc.colno})
        ) from exc
    return project_from_dict(data)


def saved_at(text: str) -> dt.datetime | None:
    """Return the ``saved_at`` time of a project file's JSON text, if present and valid."""
    try:
        data = json.loads(text)
        return dt.datetime.fromisoformat(data["saved_at"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------- sheet templates

TEMPLATE_SCHEMA = "georesistivity.sheet-template"
TEMPLATE_SCHEMA_VERSION = 1
_TEMPLATE_ROW_KEYS = {"marker", "ab2", "mn"}


@dataclass(frozen=True, slots=True)
class SheetTemplate:
    """A reusable field-sheet layout: AB/2, MN, and marker colour of each row, no readings."""

    name: str
    rows: tuple[SheetRow, ...]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise GeoValueError("template.needs_name")
        if not self.rows:
            raise GeoValueError("template.needs_rows")
        if any(row.delta_v or row.current or row.excluded or row.reason for row in self.rows):
            raise GeoValueError("template.layout_only")

    @classmethod
    def from_rows(cls, name: str, rows: tuple[SheetRow, ...] | list[SheetRow]) -> "SheetTemplate":
        """Keep the layout of ``rows``: one row per (AB/2, MN), readings removed."""
        seen: set[tuple[str, str]] = set()
        layout = []
        for row in rows:
            key = (row.ab2.strip(), row.mn.strip())
            if not any(key) or key in seen:
                continue
            seen.add(key)
            layout.append(SheetRow(marker=row.marker.strip(), ab2=key[0], mn=key[1]))
        return cls(name=name.strip(), rows=tuple(layout))

    def sheet_rows(self) -> tuple[SheetRow, ...]:
        """Rows of a new, empty sheet with this layout."""
        return self.rows


def template_to_json(template: SheetTemplate) -> str:
    """Serialize a sheet template as JSON text."""
    data = {
        "schema": TEMPLATE_SCHEMA,
        "schema_version": TEMPLATE_SCHEMA_VERSION,
        "name": template.name,
        "rows": [{"marker": row.marker, "ab2": row.ab2, "mn": row.mn} for row in template.rows],
    }
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def template_from_json(text: str) -> SheetTemplate:
    """Read and validate a sheet template."""
    try:
        data = _expect_object(json.loads(text), "")
    except json.JSONDecodeError as exc:
        raise ProjectFormatError(
            "", Problem("project.invalid_json", {"line": exc.lineno, "column": exc.colno})
        ) from exc
    if data.get("schema") != TEMPLATE_SCHEMA:
        raise ProjectFormatError(
            "schema", Problem("template.not_template", {"expected": TEMPLATE_SCHEMA})
        )
    if data.get("schema_version") != TEMPLATE_SCHEMA_VERSION:
        raise ProjectFormatError(
            "schema_version", Problem("template.bad_version", {"version": TEMPLATE_SCHEMA_VERSION})
        )
    _check_keys(data, "", {"schema", "schema_version", "name", "rows"}, {"name", "rows"})
    name = _text(data["name"], "name")
    rows = []
    for index, value in enumerate(_typed(data["rows"], "rows", list, "project.must_be_list")):
        path = f"rows[{index}]"
        row = _expect_object(value, path)
        _check_keys(row, path, _TEMPLATE_ROW_KEYS, {"ab2", "mn"})
        rows.append(
            SheetRow(
                marker=_text(row.get("marker", ""), f"{path}.marker"),
                ab2=_text(row["ab2"], f"{path}.ab2"),
                mn=_text(row["mn"], f"{path}.mn"),
            )
        )
    return _build("", lambda: SheetTemplate(name=name, rows=tuple(rows)))
