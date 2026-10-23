"""Figure files of the VES curve: texts in a language, survey title, and PNG, SVG, or PDF.

The interface and the ``georesistivity plot`` command share this module; it does not import
Streamlit, and it imports Matplotlib only when a figure is drawn, so the command line starts
quickly. Files are reproducible: the same sheet and options give the same bytes, because no
creation date is written and SVG element ids come from a fixed salt.
"""

import io
import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from georesistivity.field_sheet import SheetOutcome, evaluate_sheet
from georesistivity.formatting import NumberFormat
from georesistivity.i18n import Language, text_in
from georesistivity.messages import GeoValueError
from georesistivity.project import Project, SurveyInfo, survey_file_stem
from georesistivity.survey import PointResult

if TYPE_CHECKING:
    from matplotlib.figure import Figure

    from georesistivity.plotting import SoundingFigureLabels

FigureFormat = Literal["png", "svg", "pdf"]
FIGURE_FORMATS: tuple[FigureFormat, ...] = ("png", "svg", "pdf")
FIGURE_MIME: dict[FigureFormat, str] = {
    "png": "image/png",
    "svg": "image/svg+xml",
    "pdf": "application/pdf",
}
PNG_DPI = 300

DEFAULT_DECADE_MM = 50.0
"""Provisional modulus of the to-scale figure [mm per decade] (decision D-15, pending).

It is not the modulus of a particular bilog paper: it was chosen so that the 3 x 4 decades of
the field sheet (1-1000 m, 1-10 000 ohm.m) fit on A4 printed at 100%.
"""
DECADE_MM_RANGE = (10.0, 250.0)
"""Accepted modulus [mm per decade]."""


def check_decade_mm(value: float) -> float:
    """Return ``value`` if it is an accepted modulus [mm per decade]."""
    low, high = DECADE_MM_RANGE
    if not (math.isfinite(value) and low <= value <= high):
        raise GeoValueError("figure.decade_mm", low=low, high=high, value=value)
    return value


@dataclass(frozen=True, slots=True)
class FigureOptions:
    """How to draw and save the VES curve."""

    file_format: FigureFormat = "png"
    decade_mm: float | None = None
    """Millimetres per decade for a to-scale figure; ``None`` for the standard 7 x 7 in."""
    error_bars: bool = True
    title_with_survey: bool = True
    language: Language = "pt-BR"
    number_format: NumberFormat = "pt-BR"

    def __post_init__(self) -> None:
        if self.file_format not in FIGURE_FORMATS:
            raise ValueError(f"unsupported figure format: {self.file_format!r}")
        if self.decade_mm is not None:
            check_decade_mm(self.decade_mm)


def survey_subtitle(survey: SurveyInfo, language: Language) -> str:
    """``SEV 01 · Fazenda Boa Vista · 22/10/2026`` from the filled-in survey details."""
    parts: list[str] = []
    if survey.sev_number:
        parts.append(text_in(language, "figure.survey_number", number=survey.sev_number))
    place = survey.local or survey.name
    if place:
        parts.append(place)
    if survey.date is not None:
        parts.append(survey.date.strftime(text_in(language, "figure.date_format")))
    return " · ".join(parts)


def sounding_labels(language: Language, *, subtitle: str = "") -> "SoundingFigureLabels":
    """Texts of the VES figure in ``language``, with an optional second title line."""
    from georesistivity.plotting import SoundingFigureLabels

    title = text_in(language, "figure.sounding_title")
    return SoundingFigureLabels(
        title=f"{title}\n{subtitle}" if subtitle else title,
        x_axis=text_in(language, "figure.ab2_axis"),
        y_axis=text_in(language, "figure.rho_axis"),
        mn_legend=text_in(language, "figure.mn_legend", mn="{mn}"),
        quality_warning=text_in(language, "figure.quality_warning"),
        error_bars=text_in(language, "figure.error_bars"),
    )


def figure_file_name(survey: SurveyInfo, file_format: FigureFormat) -> str:
    """``SEV-01-Fazenda-ves-curve.pdf``, or ``georesistivity-ves-curve.pdf`` without details."""
    return f"{survey_file_stem(survey) or 'georesistivity'}-ves-curve.{file_format}"


def figure_to_bytes(figure: "Figure", file_format: FigureFormat) -> bytes:
    """Save ``figure`` as PNG (300 dpi), SVG, or PDF, keeping its physical size.

    PDF fonts are embedded as TrueType (type 42) rather than Type 3, as journals and print
    shops expect.
    """
    import matplotlib

    from georesistivity import __version__

    creator = f"GeoResistivity {__version__}"
    metadata: dict[FigureFormat, dict[str, str | None]] = {
        "png": {"Software": creator},
        "svg": {"Creator": creator, "Date": None},
        "pdf": {"Creator": creator, "CreationDate": None},
    }
    if file_format not in FIGURE_FORMATS:
        raise ValueError(f"unsupported figure format: {file_format!r}")
    buffer = io.BytesIO()
    with matplotlib.rc_context({"svg.hashsalt": "georesistivity", "pdf.fonttype": 42}):
        figure.savefig(
            buffer,
            format=file_format,
            dpi=PNG_DPI if file_format == "png" else "figure",
            metadata=metadata[file_format],
        )
    return buffer.getvalue()


def sounding_figure_file(
    points: Sequence[PointResult], survey: SurveyInfo, options: FigureOptions
) -> bytes:
    """The VES curve of ``points`` as a file, titled with ``survey`` if the options ask."""
    from georesistivity.plotting import create_sounding_figure, sounding_segments

    if not sounding_segments(points):
        raise GeoValueError("figure.nothing_to_plot")
    subtitle = survey_subtitle(survey, options.language) if options.title_with_survey else ""
    figure = create_sounding_figure(
        points,
        number_format=options.number_format,
        labels=sounding_labels(options.language, subtitle=subtitle),
        error_bars=options.error_bars,
        decade_mm=options.decade_mm,
    )
    return figure_to_bytes(figure, options.file_format)


def evaluate_project_sheet(project: Project) -> SheetOutcome:
    """The field sheet of ``project`` evaluated with its own units and CV limit."""
    settings = project.sheet_settings
    return evaluate_sheet(
        project.sheet_rows,
        voltage_unit=settings.voltage_unit,
        current_unit=settings.current_unit,
        cv_threshold=settings.cv_limit_percent / 100.0,
    )
