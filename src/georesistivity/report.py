"""Report of a vertical electrical sounding, as self-contained HTML or as an A4 PDF (D-12).

:func:`build_report` gathers the content once, in one language (D-11): survey and acquisition
details, a summary, the VES curve, the positions, every reading with its exclusion and the
time it was entered, the rows of the sheet that were not used and why, the quality warnings,
the change history, and the methods with their references. :func:`render_html` and
:func:`render_pdf` lay the same content out. Everything typed by the user is escaped in HTML,
so a project cannot inject markup into its report.

The footer identifies the project by the SHA-256 of its canonical JSON content (as
:func:`georesistivity.project.project_to_json` writes it, without the save time), so two
reports of the same content carry the same fingerprint. Matplotlib is imported only when a
report is drawn.
"""

import dataclasses
import datetime as dt
import hashlib
import html
import io
import math
import textwrap
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from georesistivity.field_sheet import SheetOutcome, SheetRow
from georesistivity.figures import evaluate_project_sheet, sounding_labels, survey_subtitle
from georesistivity.formatting import NumberFormat, format_full_precision, format_significant
from georesistivity.i18n import PROBLEMS, Language, count_in, text_for, text_in
from georesistivity.models import MeasurementWarning
from georesistivity.project import Project, project_to_json
from georesistivity.sheet_history import ROW_FIELDS, HistoryEntry, field_text
from georesistivity.survey import PointResult

if TYPE_CHECKING:
    from matplotlib.figure import Figure
    from matplotlib.lines import Line2D

ReportFormat = Literal["html", "pdf"]
REPORT_FORMATS: tuple[ReportFormat, ...] = ("html", "pdf")
REPORT_MIME: dict[ReportFormat, str] = {"html": "text/html", "pdf": "application/pdf"}

REFERENCES = (
    "Keller, G. V.; Frischknecht, F. C. Electrical Methods in Geophysical Prospecting. "
    "Pergamon, 1966.",
    "Taylor, J. R. An Introduction to Error Analysis. 2nd ed. University Science Books, 1997.",
    "Telford, W. M.; Geldart, L. P.; Sheriff, R. E. Applied Geophysics. 2nd ed. Cambridge "
    "University Press, 1990.",
)


# ---------------------------------------------------------------------------- history texts


def _value(name: str, value: str, language: Language) -> str:
    if name == "excluded":
        return text_in(language, "history.yes" if value == "true" else "history.no")
    return value if value.strip() else text_in(language, "history.empty_value")


def _row_summary(row: SheetRow, language: Language) -> str:
    return " · ".join(
        f"{text_in(language, f'history.field_{name}')} "
        f"{_value(name, field_text(row, name), language)}"
        for name in ROW_FIELDS
        if field_text(row, name).strip() and field_text(row, name) != "false"
    )


def describe_change(entry: HistoryEntry, language: Language) -> str:
    """One line describing a history entry, such as ``ΔV: 80 → 82``."""
    if entry.action == "edit" and entry.field is not None:
        return text_in(
            language,
            "history.edit",
            field=text_in(language, f"history.field_{entry.field}"),
            old=_value(entry.field, entry.old, language),
            new=_value(entry.field, entry.new, language),
        )
    if entry.action == "delete_row" and entry.old_row is not None:
        return text_in(
            language, "history.delete_row", summary=_row_summary(entry.old_row, language)
        )
    if entry.action == "replace_sheet":
        return text_in(
            language, f"history.replace_{entry.source or 'new_sheet'}", detail=entry.detail
        )
    if entry.action == "append_rows":
        rows = count_in(language, "count.row", len(entry.row_ids))
        return text_in(language, "history.append_rows", rows=rows, detail=entry.detail)
    if entry.action == "units":
        return text_in(language, "history.units", old=entry.old, new=entry.new)
    return text_in(language, "history.undo_entry", number=entry.undoes)


def history_time(moment: str, language: Language) -> str:
    """An ISO 8601 time as ``23/10/2026 09:00:00`` (or ``2026-10-23 09:00:00`` in English)."""
    return dt.datetime.fromisoformat(moment).strftime(text_in(language, "history.time_format"))


# ---------------------------------------------------------------------------- content


@dataclass(frozen=True, slots=True)
class ReportTable:
    """A titled table of text cells; ``numeric`` marks right-aligned columns."""

    title: str
    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    numeric: tuple[bool, ...] = ()
    empty: str = ""


@dataclass(frozen=True, slots=True)
class Report:
    """Everything a report shows, already in its language and number format."""

    language: Language
    title: str
    subtitle: str
    details_title: str
    details: tuple[tuple[str, str], ...]
    summary_title: str
    summary: tuple[str, ...]
    curve_title: str
    no_curve: str
    tables: tuple[ReportTable, ...]
    methods_title: str
    methods: tuple[str, ...]
    references_title: str
    footer: str
    number_format: NumberFormat
    points: tuple[PointResult, ...] = field(repr=False)
    error_bars: bool = True

    @property
    def has_curve(self) -> bool:
        return any((p.apparent_resistivity_ohm_m or 0.0) > 0.0 for p in self.points)


def project_digest(project: Project) -> str:
    """SHA-256 of the canonical JSON content of ``project`` (without the save time)."""
    return hashlib.sha256(project_to_json(project).encode("utf-8")).hexdigest()


def _details(
    project: Project, language: Language, number_format: NumberFormat
) -> list[tuple[str, str]]:
    survey = project.survey
    rows: list[tuple[str, str]] = []

    def add(key: str, value: str) -> None:
        if value.strip():
            rows.append((text_in(language, key), value.strip()))

    add("survey.name", survey.name)
    add("survey.sev", survey.sev_number)
    if survey.date is not None:
        add("survey.date", survey.date.strftime(text_in(language, "figure.date_format")))
    add("survey.area", survey.area)
    add("survey.place", survey.local)
    add("survey.operator", survey.operator)
    add("survey.equipment", survey.equipment)
    if survey.azimuth_deg is not None:
        add(
            "survey.azimuth", format_full_precision(survey.azimuth_deg, number_format=number_format)
        )
    if survey.latitude is not None and survey.longitude is not None:
        latitude = format_full_precision(survey.latitude, number_format=number_format)
        longitude = format_full_precision(survey.longitude, number_format=number_format)
        rows.append(
            (text_in(language, "report.coordinates", crs=survey.crs), f"{latitude}; {longitude}")
        )
    add("survey.notes", survey.notes)
    settings = project.sheet_settings
    rows.append((text_in(language, "report.array"), text_in(language, "report.array_schlumberger")))
    rows.append(
        (text_in(language, "report.units"), f"{settings.voltage_unit} / {settings.current_unit}")
    )
    cv_limit = format_full_precision(settings.cv_limit_percent, number_format=number_format)
    rows.append((text_in(language, "report.cv_limit"), f"{cv_limit}%"))
    rows.append((text_in(language, "report.estimator"), text_in(language, "report.estimator_mean")))
    return rows


def _summary(outcome: SheetOutcome, language: Language, number_format: NumberFormat) -> list[str]:
    points = outcome.points
    if not points:
        return [text_in(language, "report.summary_empty")]
    readings = [reading for point in points for reading in point.readings]
    excluded = sum(1 for reading in readings if reading.reading.excluded)
    spacings = len({point.point.ab2_m for point in points})
    lines = [
        text_in(
            language,
            "report.summary_counts",
            positions=count_in(language, "count.position", len(points)),
            spacings=count_in(language, "count.spacing", spacings),
            used=count_in(language, "count.reading_used", len(readings) - excluded),
            excluded=count_in(language, "count.reading_excluded", excluded),
        )
    ]
    rho = [p.apparent_resistivity_ohm_m for p in points if p.apparent_resistivity_ohm_m is not None]
    if rho:
        ab2 = [p.point.ab2_m for p in points]
        lines.append(
            text_in(
                language,
                "report.summary_range",
                ab2_min=format_full_precision(min(ab2), number_format=number_format),
                ab2_max=format_full_precision(max(ab2), number_format=number_format),
                rho_min=format_significant(min(rho), number_format=number_format),
                rho_max=format_significant(max(rho), number_format=number_format),
            )
        )
    flagged = sum(1 for point in points if point.warnings)
    if flagged:
        lines.append(text_for(language, flagged, "report.summary_warnings", n=flagged))
    unused = len(outcome.invalid_rows) + len(outcome.incomplete_rows)
    if unused:
        lines.append(text_for(language, unused, "report.summary_unused", n=unused))
    return lines


def _points_table(
    points: Sequence[PointResult], language: Language, number_format: NumberFormat
) -> ReportTable:
    def full(value: float) -> str:
        return format_full_precision(value, number_format=number_format)

    def significant(value: float | None) -> str:
        return "" if value is None else format_significant(value, number_format=number_format)

    rows = []
    for result in points:
        statistics = result.statistics
        excluded = sum(reading.reading.excluded for reading in result.readings)
        used = 0 if statistics is None else statistics.count
        readings = (
            text_in(language, "points.readings_excluded", used=used, excluded=excluded)
            if excluded
            else str(used)
        )
        variation = None if statistics is None else statistics.coefficient_of_variation
        rows.append(
            (
                full(result.point.ab2_m),
                full(result.point.mn_m),
                result.point.marker or "",
                significant(result.geometric_factor_m),
                readings,
                significant(result.apparent_resistivity_ohm_m),
                significant(result.standard_error_ohm_m),
                "" if variation is None else significant(100.0 * variation),
                ", ".join(text_in(language, f"warning_short.{w.value}") for w in result.warnings),
            )
        )
    keys = ("ab2", "mn", "marker", "k", "readings", "rho", "se", "cv", "warnings")
    return ReportTable(
        title=text_in(language, "report.points"),
        columns=tuple(text_in(language, f"points.{key}") for key in keys),
        rows=tuple(rows),
        numeric=(True, True, False, True, True, True, True, True, False),
        empty=text_in(language, "report.empty_table"),
    )


def _readings_table(
    points: Sequence[PointResult], project: Project, language: Language, number_format: NumberFormat
) -> ReportTable:
    def full(value: float) -> str:
        return format_full_precision(value, number_format=number_format)

    def significant(value: float) -> str:
        return format_significant(value, number_format=number_format)

    rows = []
    for result in points:
        for reading_result in result.readings:
            reading = reading_result.reading
            rows.append(
                (
                    full(result.point.ab2_m),
                    full(result.point.mn_m),
                    full(reading.delta_v_original),
                    full(reading.current_original),
                    significant(reading_result.resistance_ohm),
                    significant(result.geometric_factor_m * reading_result.resistance_ohm),
                    text_in(language, "history.yes") if reading.excluded else "",
                    reading.exclusion_reason or "",
                    "" if not reading.entered_at else history_time(reading.entered_at, language),
                )
            )
    settings = project.sheet_settings
    columns = (
        text_in(language, "points.ab2"),
        text_in(language, "points.mn"),
        text_in(language, "report.col_delta_v", unit=settings.voltage_unit),
        text_in(language, "report.col_current", unit=settings.current_unit),
        text_in(language, "report.col_r"),
        text_in(language, "report.col_rho"),
        text_in(language, "report.col_excluded"),
        text_in(language, "report.col_reason"),
        text_in(language, "report.col_entered"),
    )
    return ReportTable(
        title=text_in(language, "report.readings"),
        columns=columns,
        rows=tuple(rows),
        numeric=(True, True, True, True, True, True, False, False, False),
        empty=text_in(language, "report.empty_table"),
    )


def _unused_table(outcome: SheetOutcome, language: Language) -> ReportTable:
    problems = PROBLEMS[language]
    rows = []
    for number, status in sorted([*outcome.invalid_rows, *outcome.incomplete_rows]):
        reasons = []
        for issue in status.issues:
            column = text_in(language, f"sheet.issue_{issue.column}")
            if status.state == "incomplete":
                reasons.append(text_in(language, "report.waiting", column=column))
            else:
                text = issue.message if issue.problem is None else issue.problem.text(problems)
                reasons.append(f"{column}: {text}")
        rows.append((str(number), "; ".join(reasons)))
    return ReportTable(
        title=text_in(language, "report.unused"),
        columns=(text_in(language, "report.col_row"), text_in(language, "report.col_problem")),
        rows=tuple(rows),
        numeric=(True, False),
        empty=text_in(language, "report.empty_table"),
    )


def _warnings_table(points: Sequence[PointResult], language: Language) -> ReportTable:
    counts = {warning: 0 for warning in MeasurementWarning}
    for point in points:
        for warning in point.warnings:
            counts[warning] += 1
    rows = tuple(
        (
            text_in(language, f"warning_short.{warning.value}"),
            text_in(language, f"warning.{warning.value}"),
            str(number),
        )
        for warning, number in counts.items()
        if number
    )
    return ReportTable(
        title=text_in(language, "report.warnings"),
        columns=(
            text_in(language, "report.col_warning"),
            text_in(language, "report.col_meaning"),
            text_in(language, "report.col_positions"),
        ),
        rows=rows,
        numeric=(False, False, True),
        empty=text_in(language, "report.empty_table"),
    )


def _history_table(history: Sequence[HistoryEntry], language: Language) -> ReportTable:
    undone = {entry.undoes for entry in history if entry.action == "undo"}
    rows = []
    for number, entry in enumerate(history, start=1):
        change = describe_change(entry, language)
        if number in undone:
            change = text_in(language, "history.undone", change=change)
        rows.append(
            (
                str(number),
                history_time(entry.at, language),
                "" if entry.row_number is None else str(entry.row_number),
                change,
            )
        )
    return ReportTable(
        title=text_in(language, "report.history"),
        columns=tuple(
            text_in(language, f"history.col_{key}") for key in ("number", "time", "row", "change")
        ),
        rows=tuple(rows),
        numeric=(True, False, True, False),
        empty=text_in(language, "report.no_history"),
    )


def build_report(
    project: Project,
    *,
    language: Language = "pt-BR",
    number_format: NumberFormat = "pt-BR",
    generated_at: dt.datetime | None = None,
    error_bars: bool = True,
) -> Report:
    """Gather the content of the report of ``project``, in ``language``."""
    from georesistivity import __version__

    moment = (generated_at or dt.datetime.now().astimezone()).isoformat(timespec="seconds")
    outcome = evaluate_project_sheet(project)
    cv_limit = format_full_precision(
        project.sheet_settings.cv_limit_percent, number_format=number_format
    )
    methods = (
        text_in(language, "report.method_k"),
        text_in(language, "report.method_rho"),
        text_in(language, "report.method_se", cv_limit=cv_limit),
        text_in(language, "report.method_wide_mn"),
        text_in(language, "report.method_entered"),
        text_in(language, "report.method_recomputed"),
    )
    tables = (
        _points_table(outcome.points, language, number_format),
        _readings_table(outcome.points, project, language, number_format),
        _unused_table(outcome, language),
        _warnings_table(outcome.points, language),
        _history_table(project.history, language),
    )
    return Report(
        language=language,
        title=text_in(language, "report.title"),
        subtitle=survey_subtitle(project.survey, language),
        details_title=text_in(language, "report.details"),
        details=tuple(_details(project, language, number_format)),
        summary_title=text_in(language, "report.summary"),
        summary=tuple(_summary(outcome, language, number_format)),
        curve_title=text_in(language, "report.curve"),
        no_curve=text_in(language, "report.no_curve"),
        tables=tables,
        methods_title=text_in(language, "report.methods"),
        methods=methods,
        references_title=text_in(language, "report.references"),
        footer=text_in(
            language,
            "report.footer",
            version=__version__,
            time=history_time(moment, language),
            digest=project_digest(project),
        ),
        number_format=number_format,
        points=outcome.points,
        error_bars=error_bars,
    )


def _curve(report: Report) -> "Figure":
    from georesistivity.plotting import create_sounding_figure

    return create_sounding_figure(
        report.points,
        number_format=report.number_format,
        labels=sounding_labels(report.language),
        error_bars=report.error_bars,
    )


# ---------------------------------------------------------------------------- HTML

_CSS = """
:root { color-scheme: light; }
html { background: #fff; }
body { font-family: "Helvetica Neue", Arial, sans-serif; color: #1d1d1f; background: #fff;
  margin: 2rem auto; padding: 0 1rem; max-width: 190mm; font-size: 10.5pt; line-height: 1.4; }
h1 { font-size: 17pt; margin: 0 0 .2rem; }
h2 { font-size: 12.5pt; margin: 1.6rem 0 .5rem; border-bottom: 1px solid #c7c7cc; }
.subtitle { color: #48484a; margin: 0 0 1rem; font-size: 11.5pt; }
dl { display: grid; grid-template-columns: max-content 1fr; gap: .15rem 1rem; margin: 0; }
dt { color: #48484a; } dd { margin: 0; white-space: pre-wrap; }
figure { margin: .5rem 0; } figure svg { width: 100%; max-width: 165mm; height: auto; }
table { border-collapse: collapse; width: 100%; font-size: 8.5pt; }
th, td { border-bottom: 1px solid #e5e5ea; padding: .2rem .35rem; text-align: left;
  vertical-align: top; }
th { background: #f2f2f7; } td.n, th.n { text-align: right; white-space: nowrap; }
ol { padding-left: 1.2rem; } footer { margin-top: 2rem; color: #6e6e73; font-size: 8pt;
  word-break: break-all; }
@page { size: A4; margin: 15mm; }
@media print { body { margin: 0; padding: 0; max-width: none; }
  thead { display: table-header-group; } tr, figure { break-inside: avoid; } }
"""


_NUMERIC = ' class="n"'


def _e(text: str) -> str:
    return html.escape(text, quote=True)


def _html_table(table: ReportTable) -> str:
    numeric = table.numeric or (False,) * len(table.columns)
    parts = [f"<section><h2>{_e(table.title)}</h2>"]
    if not table.rows:
        parts.append(f"<p>{_e(table.empty)}</p></section>")
        return "".join(parts)
    head = "".join(
        f"<th{_NUMERIC if right else ''}>{_e(column)}</th>"
        for column, right in zip(table.columns, numeric, strict=True)
    )
    parts.append(f"<table><thead><tr>{head}</tr></thead><tbody>")
    for row in table.rows:
        cells = "".join(
            f"<td{_NUMERIC if right else ''}>{_e(cell)}</td>"
            for cell, right in zip(row, numeric, strict=True)
        )
        parts.append(f"<tr>{cells}</tr>")
    parts.append("</tbody></table></section>")
    return "".join(parts)


def render_html(report: Report) -> str:
    """The report as one self-contained HTML page, with the curve embedded as SVG."""
    from georesistivity.figures import figure_to_bytes

    details = "".join(
        f"<dt>{_e(label)}</dt><dd>{_e(value)}</dd>" for label, value in report.details
    )
    summary = "".join(f"<p>{_e(line)}</p>" for line in report.summary)
    if report.has_curve:
        svg = figure_to_bytes(_curve(report), "svg").decode("utf-8")
        curve = f"<figure>{svg[svg.index('<svg') :]}</figure>"
    else:
        curve = f"<p>{_e(report.no_curve)}</p>"
    methods = "".join(f"<p>{_e(line)}</p>" for line in report.methods)
    references = "".join(f"<li>{_e(reference)}</li>" for reference in REFERENCES)
    subtitle = f'<p class="subtitle">{_e(report.subtitle)}</p>' if report.subtitle else ""
    return (
        f'<!DOCTYPE html>\n<html lang="{report.language}">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="color-scheme" content="light">\n'
        f'<meta name="generator" content="GeoResistivity">\n'
        f"<title>{_e(report.title)}</title>\n<style>{_CSS}</style>\n</head>\n<body>\n"
        f"<header><h1>{_e(report.title)}</h1>{subtitle}</header>\n"
        f"<section><h2>{_e(report.details_title)}</h2><dl>{details}</dl></section>\n"
        f"<section><h2>{_e(report.summary_title)}</h2>{summary}</section>\n"
        f"<section><h2>{_e(report.curve_title)}</h2>{curve}</section>\n"
        + "\n".join(_html_table(table) for table in report.tables)
        + f"\n<section><h2>{_e(report.methods_title)}</h2>{methods}"
        f"<h3>{_e(report.references_title)}</h3><ol>{references}</ol></section>\n"
        f"<footer>{_e(report.footer)}</footer>\n</body>\n</html>\n"
    )


# ---------------------------------------------------------------------------- PDF

A4_MM = (210.0, 297.0)
MARGIN_MM = 15.0
FOOTER_MM = 10.0
BODY_PT = 8.0
TABLE_PT = 6.8
POINT_MM = 25.4 / 72.0
LINE_SPACING = 1.3
CHAR_EM = 0.55
"""Average character width as a fraction of the font size, used to wrap text (slightly wide,
so that text stays inside its column)."""


def _line_mm(size_pt: float) -> float:
    return size_pt * LINE_SPACING * POINT_MM


def _chars(width_mm: float, size_pt: float) -> int:
    return max(4, math.floor(width_mm / (size_pt * CHAR_EM * POINT_MM)))


def _wrap(text: str, width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        lines.extend(textwrap.wrap(paragraph, width, break_long_words=True) or [""])
    return lines


class _Pages:
    """A minimal top-to-bottom layout of text and tables on A4 pages (millimetres)."""

    def __init__(self, footer: str, page_label: str) -> None:
        from matplotlib.figure import Figure

        self._figure_class = Figure
        self.footer = footer
        self.page_label = page_label
        """``Página {page} de {pages}``."""
        self.pages: list[Figure] = []
        self.width = A4_MM[0] - 2 * MARGIN_MM
        self.bottom = A4_MM[1] - MARGIN_MM - FOOTER_MM
        self.y = 0.0
        self.new_page()

    @property
    def page(self) -> "Figure":
        return self.pages[-1]

    def new_page(self) -> None:
        self.pages.append(self._figure_class(figsize=(A4_MM[0] / 25.4, A4_MM[1] / 25.4)))
        self.y = MARGIN_MM

    def room(self, height: float) -> None:
        if self.y + height > self.bottom:
            self.new_page()

    def text(
        self,
        x: float,
        text: str,
        size: float,
        *,
        weight: str = "normal",
        color: str = "#1d1d1f",
        align: str = "left",
    ) -> None:
        self.page.text(
            (MARGIN_MM + x) / A4_MM[0],
            1.0 - self.y / A4_MM[1],
            text,
            fontsize=size,
            fontweight=weight,
            color=color,
            ha=align,
            va="top",
        )

    def paragraph(
        self,
        text: str,
        size: float = BODY_PT,
        *,
        weight: str = "normal",
        indent: float = 0.0,
        color: str = "#1d1d1f",
    ) -> None:
        for line in _wrap(text, _chars(self.width - indent, size)):
            self.room(_line_mm(size))
            self.text(indent, line, size, weight=weight, color=color)
            self.y += _line_mm(size)

    def heading(self, text: str, size: float = 11.0) -> None:
        self.room(_line_mm(size) + 2 * _line_mm(BODY_PT))  # keep the heading with its content
        self.y += 2.0
        self.text(0.0, text, size, weight="bold")
        self.y += _line_mm(size) + 1.0

    def rule(self, color: str = "#c7c7cc") -> None:
        y = 1.0 - self.y / A4_MM[1]
        self.page.add_artist(
            _line(MARGIN_MM / A4_MM[0], (MARGIN_MM + self.width) / A4_MM[0], y, color)
        )

    def table(self, table: ReportTable) -> None:
        self.heading(table.title)
        if not table.rows:
            self.paragraph(table.empty)
            return
        numeric = table.numeric or (False,) * len(table.columns)
        widths = _column_widths(table, self.width)
        header = [
            _wrap(c, _chars(w - 1.5, TABLE_PT)) for c, w in zip(table.columns, widths, strict=True)
        ]

        def draw(cells: list[list[str]], *, bold: bool) -> None:
            height = max(len(lines) for lines in cells) * _line_mm(TABLE_PT) + 1.2
            x = 0.0
            for lines, width, right in zip(cells, widths, numeric, strict=True):
                for number, line in enumerate(lines):
                    saved = self.y
                    self.y += 0.6 + number * _line_mm(TABLE_PT)
                    self.text(
                        x + (width - 0.8 if right else 0.8),
                        line,
                        TABLE_PT,
                        weight="bold" if bold else "normal",
                        align="right" if right else "left",
                    )
                    self.y = saved
                x += width
            self.y += height
            self.rule("#e5e5ea" if not bold else "#8e8e93")

        draw(header, bold=True)
        for row in table.rows:
            cells = [_wrap(c, _chars(w - 1.5, TABLE_PT)) for c, w in zip(row, widths, strict=True)]
            height = max(len(lines) for lines in cells) * _line_mm(TABLE_PT) + 1.2
            if self.y + height > self.bottom:
                self.new_page()
                draw(header, bold=True)  # repeat the header on every page
            draw(cells, bold=False)

    def finish(self) -> None:
        total = len(self.pages)
        for number, page in enumerate(self.pages, start=1):
            page.text(
                MARGIN_MM / A4_MM[0],
                MARGIN_MM / A4_MM[1],
                "\n".join(_wrap(self.footer, _chars(self.width - 25.0, 6.0))),
                fontsize=6.0,
                color="#6e6e73",
                ha="left",
                va="bottom",
            )
            page.text(
                (A4_MM[0] - MARGIN_MM) / A4_MM[0],
                MARGIN_MM / A4_MM[1],
                self.page_label.format(page=number, pages=total),
                fontsize=6.5,
                color="#6e6e73",
                ha="right",
                va="bottom",
            )


def _line(x0: float, x1: float, y: float, color: str) -> "Line2D":
    from matplotlib.lines import Line2D

    return Line2D([x0, x1], [y, y], linewidth=0.4, color=color)  # figure coordinates


def _column_widths(table: ReportTable, total: float) -> list[float]:
    """Column widths [mm] proportional to the text they hold, within limits."""
    lengths = []
    for index, column in enumerate(table.columns):
        cells = [row[index] for row in table.rows]
        longest_word = max(
            (len(word) for text in [column, *cells] for word in text.split()), default=4
        )
        typical = max([len(column), *(len(cell) for cell in cells)])
        lengths.append(max(longest_word, min(typical, 60), 4))
    scale = total / sum(lengths)
    return [length * scale for length in lengths]


def render_pdf(report: Report) -> bytes:
    """The report as an A4 PDF: header, details, summary, and curve first, then the tables."""
    import matplotlib
    from matplotlib.backends.backend_pdf import PdfPages

    from georesistivity import __version__
    from georesistivity.plotting import draw_sounding_curve

    page_label = text_in(report.language, "report.page", page="{page}", pages="{pages}")
    pages = _Pages(report.footer, page_label)
    pages.text(0.0, report.title, 14.0, weight="bold")
    pages.y += _line_mm(14.0)
    if report.subtitle:
        pages.paragraph(report.subtitle, 10.0, color="#48484a")
    pages.heading(report.details_title)
    label_width = 42.0
    for label, value in report.details:
        lines = _wrap(value, _chars(pages.width - label_width, BODY_PT))
        pages.room(_line_mm(BODY_PT) * len(lines))
        pages.text(0.0, label, BODY_PT, color="#48484a")
        for line in lines:
            pages.text(label_width, line, BODY_PT)
            pages.y += _line_mm(BODY_PT)
    pages.heading(report.summary_title)
    for line in report.summary:
        pages.paragraph(line)

    pages.heading(report.curve_title)
    if report.has_curve:
        side = min(pages.width * 0.78, pages.bottom - pages.y - 12.0)
        if side < 90.0:
            pages.new_page()
            side = pages.width * 0.78
        left = MARGIN_MM + (pages.width - side) / 2 + 6.0
        axes = pages.page.add_axes(
            (
                left / A4_MM[0],
                1.0 - (pages.y + side) / A4_MM[1],
                (side - 12.0) / A4_MM[0],
                (side - 10.0) / A4_MM[1],
            )
        )
        labels = sounding_labels(report.language)
        draw_sounding_curve(
            axes,
            report.points,
            number_format=report.number_format,
            labels=dataclasses.replace(labels, title=""),
            error_bars=report.error_bars,
        )
        for text in [
            axes.xaxis.label,
            axes.yaxis.label,
            *axes.get_xticklabels(),
            *axes.get_yticklabels(),
        ]:
            text.set_fontsize(7.5)
        legend = axes.get_legend()
        assert legend is not None  # every MN segment has an entry
        for text in legend.get_texts():
            text.set_fontsize(6.5)
        pages.y += side + 8.0  # room for the tick labels and the AB/2 label below the box
    else:
        pages.paragraph(report.no_curve)

    for table in report.tables:
        pages.table(table)
    pages.heading(report.methods_title)
    for line in report.methods:
        pages.paragraph(line)
        pages.y += 1.0
    pages.heading(report.references_title, 10.0)
    for number, reference in enumerate(REFERENCES, start=1):
        pages.paragraph(f"{number}. {reference}", 7.5)
    pages.finish()

    buffer = io.BytesIO()
    metadata = {
        "Creator": f"GeoResistivity {__version__}",
        "CreationDate": None,
        "Title": report.title,
    }
    with matplotlib.rc_context({"pdf.fonttype": 42}), PdfPages(buffer, metadata=metadata) as pdf:
        for page in pages.pages:
            pdf.savefig(page)
    return buffer.getvalue()


def report_file(report: Report, report_format: ReportFormat) -> bytes:
    """The report as HTML (UTF-8) or PDF bytes."""
    if report_format == "html":
        return render_html(report).encode("utf-8")
    if report_format == "pdf":
        return render_pdf(report)
    raise ValueError(f"unsupported report format: {report_format!r}")


def report_file_name(project: Project, report_format: ReportFormat) -> str:
    """``SEV-01-Fazenda-report.pdf``, or ``georesistivity-report.pdf`` without details."""
    from georesistivity.project import survey_file_stem

    return f"{survey_file_stem(project.survey) or 'georesistivity'}-report.{report_format}"
