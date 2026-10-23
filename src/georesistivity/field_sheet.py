"""Digital Schlumberger field sheet: rows typed by the user become sounding points.

Each row is one reading at one (AB/2, MN) position, as on the paper sheet: rows left without
DeltaV and I are positions that were not read. Two rows with the same AB/2 and different MN
are an overlap between MN segments; two rows with the same AB/2 and MN are repeated readings
of one position. Lengths are in meters. This module does not import Streamlit or pandas.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

from georesistivity.formatting import NumberFormat, format_full_precision
from georesistivity.geometry import GeometryError, field_sheet_cells, schlumberger_geometric_factor
from georesistivity.messages import Problem, problem_of
from georesistivity.models import MeasurementFieldError
from georesistivity.stacking import DEFAULT_CV_THRESHOLD
from georesistivity.survey import (
    PointResult,
    Reading,
    SoundingPoint,
    evaluate_point,
    evaluate_reading,
    sort_points,
)
from georesistivity.validation import parse_number

SheetColumn = Literal["ab2", "mn", "delta_v", "current", "reason"]
RowState = Literal["blank", "incomplete", "valid", "excluded", "invalid"]
"""``incomplete``: only one of DeltaV and I typed so far, and nothing else wrong."""


@dataclass(frozen=True, slots=True)
class SheetRow:
    """One row of the field sheet, exactly as typed.

    ``id`` and ``entered_at`` are kept by the program, not typed, and do not take part in
    comparisons: two rows are equal when their typed content is equal.
    """

    marker: str = ""
    ab2: str = ""
    mn: str = ""
    delta_v: str = ""
    current: str = ""
    excluded: bool = False
    reason: str = ""
    id: str = field(default="", compare=False)
    """Stable identifier of the row, used by the change history."""
    entered_at: str = field(default="", compare=False)
    """ISO 8601 time with offset at which DeltaV and I were first both filled in (D-14)."""

    def content(self) -> tuple[str, str, str, str, str, bool, str]:
        """The typed values, in column order."""
        return (
            self.marker,
            self.ab2,
            self.mn,
            self.delta_v,
            self.current,
            self.excluded,
            self.reason,
        )

    def has_reading(self) -> bool:
        """Whether both DeltaV and I are filled in."""
        return bool(self.delta_v.strip() and self.current.strip())


@dataclass(frozen=True, slots=True)
class RowIssue:
    """One problem in one column of a row; ``message`` is English, ``problem`` translatable."""

    column: SheetColumn
    message: str
    problem: Problem | None = field(default=None, compare=False)

    @classmethod
    def of(cls, column: SheetColumn, problem: Problem) -> "RowIssue":
        return cls(column, problem.text(), problem)


@dataclass(frozen=True, slots=True)
class RowStatus:
    """Whether a row was blank, used, excluded, or rejected, and why."""

    state: RowState
    issues: tuple[RowIssue, ...] = ()


@dataclass(frozen=True, slots=True)
class SheetOutcome:
    """Status of every row and the resulting sounding points, by AB/2 and MN."""

    rows: tuple[RowStatus, ...]
    points: tuple[PointResult, ...]
    invalid_rows: tuple[tuple[int, RowStatus], ...] = field(init=False)
    """1-based row numbers and statuses of the rejected rows."""
    incomplete_rows: tuple[tuple[int, RowStatus], ...] = field(init=False)
    """1-based row numbers and statuses of rows still waiting for DeltaV or I."""

    def __post_init__(self) -> None:
        for name, state in (("invalid_rows", "invalid"), ("incomplete_rows", "incomplete")):
            selected = tuple(
                (number, status)
                for number, status in enumerate(self.rows, start=1)
                if status.state == state
            )
            object.__setattr__(self, name, selected)


def template_rows(number_format: NumberFormat = "pt-BR") -> list[SheetRow]:
    """Return the empty rows of the standard Schlumberger field sheet (45 positions)."""
    return [
        SheetRow(
            ab2=format_full_precision(ab2, number_format=number_format),
            mn=format_full_precision(mn, number_format=number_format),
        )
        for ab2, mn in field_sheet_cells()
    ]


def _parse(column: SheetColumn, text: str, issues: list[RowIssue]) -> float | None:
    try:
        return parse_number(text)
    except ValueError as exc:
        issues.append(RowIssue.of(column, problem_of(exc)))
        return None


@dataclass(frozen=True, slots=True)
class _ParsedRow:
    ab2_m: float
    mn_m: float
    marker: str | None
    reading: Reading


def _evaluate_row(
    row: SheetRow,
    voltage_unit: str,
    current_unit: str,
) -> tuple[RowStatus, _ParsedRow | None]:
    if not row.delta_v.strip() and not row.current.strip():
        return RowStatus("blank"), None

    issues: list[RowIssue] = []
    ab2 = _parse("ab2", row.ab2, issues)
    mn = _parse("mn", row.mn, issues)
    missing: SheetColumn | None = None
    if not row.delta_v.strip():
        missing = "delta_v"
    elif not row.current.strip():
        missing = "current"
    delta_v = None if missing == "delta_v" else _parse("delta_v", row.delta_v, issues)
    current = None if missing == "current" else _parse("current", row.current, issues)
    reason = row.reason.strip()
    if row.excluded and not reason:
        issues.append(RowIssue.of("reason", Problem("sheet.reason_required")))

    if ab2 is not None and mn is not None:
        try:
            schlumberger_geometric_factor(ab2, mn)
        except GeometryError as exc:
            issues.append(RowIssue.of("ab2" if exc.parameter == "ab2" else "mn", exc.problem))
        except ValueError as exc:
            issues.append(RowIssue.of("ab2", problem_of(exc)))

    if issues:
        return RowStatus("invalid", tuple(issues)), None
    if missing is not None:
        return RowStatus("incomplete", (RowIssue.of(missing, Problem("sheet.not_typed")),)), None
    assert ab2 is not None and mn is not None and delta_v is not None and current is not None

    reading = Reading(
        delta_v_original=delta_v,
        voltage_unit=voltage_unit,
        current_original=current,
        current_unit=current_unit,
        excluded=row.excluded,
        exclusion_reason=reason or None,
        entered_at=row.entered_at or None,
    )
    try:
        evaluate_reading(reading)
    except MeasurementFieldError as exc:
        column: SheetColumn = "delta_v" if exc.field == "delta_v" else "current"
        return RowStatus("invalid", (RowIssue.of(column, exc.problem),)), None

    state: RowState = "excluded" if row.excluded else "valid"
    parsed = _ParsedRow(ab2, mn, row.marker.strip() or None, reading)
    return RowStatus(state), parsed


def evaluate_sheet(
    rows: Sequence[SheetRow],
    *,
    voltage_unit: str,
    current_unit: str,
    cv_threshold: float = DEFAULT_CV_THRESHOLD,
) -> SheetOutcome:
    """Validate every row and combine the readings of each (AB/2, MN) position.

    Blank rows are ignored and invalid rows are reported without affecting the others.
    Readings keep their row order within a position.
    """
    statuses: list[RowStatus] = []
    groups: dict[tuple[float, float], list[_ParsedRow]] = {}
    for row in rows:
        status, parsed = _evaluate_row(row, voltage_unit, current_unit)
        statuses.append(status)
        if parsed is not None:
            groups.setdefault((parsed.ab2_m, parsed.mn_m), []).append(parsed)

    points = []
    for (ab2_m, mn_m), parsed_rows in groups.items():
        marker = next((parsed.marker for parsed in parsed_rows if parsed.marker), None)
        point = SoundingPoint(
            ab2_m=ab2_m,
            mn_m=mn_m,
            readings=tuple(parsed.reading for parsed in parsed_rows),
            marker=marker,
        )
        points.append(evaluate_point(point, cv_threshold=cv_threshold))
    return SheetOutcome(tuple(statuses), sort_points(points))
