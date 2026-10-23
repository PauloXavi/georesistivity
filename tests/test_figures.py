"""Tests for figure files of the VES curve."""

import datetime as dt
import math
import re
import struct

import pytest

from georesistivity import __version__
from georesistivity.field_sheet import SheetRow, evaluate_sheet
from georesistivity.figures import (
    DECADE_MM_RANGE,
    DEFAULT_DECADE_MM,
    FIGURE_FORMATS,
    FigureOptions,
    check_decade_mm,
    evaluate_project_sheet,
    figure_file_name,
    figure_to_bytes,
    sounding_figure_file,
    sounding_labels,
    survey_subtitle,
)
from georesistivity.messages import GeoValueError
from georesistivity.plotting import create_sounding_figure
from georesistivity.project import Project, SheetSettings, SurveyInfo
from georesistivity.survey import PointResult

MM_PER_POINT = 25.4 / 72.0
SURVEY = SurveyInfo(sev_number="01", local="Fazenda Boa Vista", date=dt.date(2026, 10, 22))


def sounding(*rows: SheetRow) -> tuple[PointResult, ...]:
    return evaluate_sheet(rows, voltage_unit="mV", current_unit="mA").points


POINTS = sounding(
    SheetRow(ab2="1", mn="0,5", delta_v="80", current="40"),
    SheetRow(ab2="10", mn="2", delta_v="30", current="50"),
    SheetRow(ab2="10", mn="2", delta_v="34", current="50"),
)


def pdf_page_mm(data: bytes) -> tuple[float, float]:
    match = re.search(rb"/MediaBox \[ ?0 0 ([\d.]+) ([\d.]+) ?\]", data)
    assert match is not None
    return float(match[1]) * MM_PER_POINT, float(match[2]) * MM_PER_POINT


def svg_size_mm(data: bytes) -> tuple[float, float]:
    match = re.search(rb'width="([\d.]+)pt" height="([\d.]+)pt"', data)
    assert match is not None
    return float(match[1]) * MM_PER_POINT, float(match[2]) * MM_PER_POINT


def png_size_px(data: bytes) -> tuple[int, int]:
    width, height = struct.unpack(">II", data[16:24])  # IHDR chunk
    return width, height


def test_default_modulus_is_provisional_and_fits_a4() -> None:
    # 3 x 4 decades of 50 mm plus margins must fit 210 x 297 mm (decision D-15 is pending).
    assert DEFAULT_DECADE_MM == 50.0
    data = sounding_figure_file(POINTS, SURVEY, FigureOptions(file_format="pdf", decade_mm=50.0))
    width, height = pdf_page_mm(data)
    assert width <= 210.0
    assert height <= 297.0


@pytest.mark.parametrize("value", [DECADE_MM_RANGE[0], 62.5, DECADE_MM_RANGE[1]])
def test_accepted_modulus(value: float) -> None:
    assert check_decade_mm(value) == value


@pytest.mark.parametrize("value", [9.9, 250.1, math.nan, math.inf])
def test_modulus_out_of_range_is_rejected(value: float) -> None:
    with pytest.raises(GeoValueError) as error:
        check_decade_mm(value)

    assert error.value.problem.code == "figure.decade_mm"
    assert "between 10 and 250 mm" in str(error.value)


def test_options_reject_unknown_format_and_bad_modulus() -> None:
    with pytest.raises(ValueError, match="unsupported figure format"):
        FigureOptions(file_format="jpg")  # type: ignore[arg-type]
    with pytest.raises(GeoValueError):
        FigureOptions(decade_mm=5.0)


def test_survey_subtitle_in_each_language() -> None:
    assert survey_subtitle(SURVEY, "pt-BR") == "SEV 01 · Fazenda Boa Vista · 22/10/2026"
    assert survey_subtitle(SURVEY, "en") == "VES 01 · Fazenda Boa Vista · 2026-10-22"


def test_survey_subtitle_uses_what_is_filled_in() -> None:
    assert survey_subtitle(SurveyInfo(name="Campanha 2026"), "pt-BR") == "Campanha 2026"
    assert survey_subtitle(SurveyInfo(name="Campanha", local="Sítio"), "en") == "Sítio"
    assert survey_subtitle(SurveyInfo(), "pt-BR") == ""


def test_sounding_labels_in_each_language() -> None:
    portuguese = sounding_labels("pt-BR", subtitle="SEV 01")
    english = sounding_labels("en")

    assert portuguese.title == "Sondagem elétrica vertical (Schlumberger)\nSEV 01"
    assert portuguese.y_axis == "Resistividade aparente [Ω·m]"
    assert portuguese.error_bars == "±1 erro-padrão da média (n ≥ 2)"
    assert english.title == "Vertical Electrical Sounding (Schlumberger)"
    assert english.mn_legend.format(mn="2") == "MN = 2 m"


def test_figure_file_name_follows_the_project_file_name() -> None:
    assert figure_file_name(SURVEY, "pdf") == "SEV-01-Fazenda_Boa_Vista-ves-curve.pdf"
    assert figure_file_name(SurveyInfo(), "svg") == "georesistivity-ves-curve.svg"


def test_standard_figure_is_7_inches_in_every_format() -> None:
    files = {
        file_format: sounding_figure_file(POINTS, SURVEY, FigureOptions(file_format=file_format))
        for file_format in FIGURE_FORMATS
    }

    assert files["png"].startswith(b"\x89PNG\r\n\x1a\n")
    assert png_size_px(files["png"]) == (2100, 2100)  # 7 in at 300 dpi
    assert files["svg"].startswith(b"<?xml")
    assert svg_size_mm(files["svg"]) == pytest.approx((177.8, 177.8))
    assert files["pdf"].startswith(b"%PDF")
    assert pdf_page_mm(files["pdf"]) == pytest.approx((177.8, 177.8))


@pytest.mark.parametrize("file_format", FIGURE_FORMATS)
def test_files_are_reproducible_and_name_the_program(file_format: str) -> None:
    options = FigureOptions(file_format=file_format, decade_mm=50.0)  # type: ignore[arg-type]

    first = sounding_figure_file(POINTS, SURVEY, options)
    second = sounding_figure_file(POINTS, SURVEY, options)

    assert first == second
    assert f"GeoResistivity {__version__}".encode() in first
    assert b"CreationDate" not in first
    assert b"<dc:date>" not in first


def test_scaled_figure_has_the_modulus_on_both_axes() -> None:
    # 62.5 mm per decade: 3 x 62.5 = 187.5 mm by 4 x 62.5 = 250 mm of plot, plus the 22 + 6 mm
    # side margins, the 15 mm bottom margin, and 4 + 2 x 5.5 mm for a two-line title.
    options = FigureOptions(file_format="svg", decade_mm=62.5)

    width, height = svg_size_mm(sounding_figure_file(POINTS, SURVEY, options))

    assert width == pytest.approx(22.0 + 187.5 + 6.0)
    assert height == pytest.approx(15.0 + 250.0 + 15.0)


def test_title_without_survey_details_has_one_line() -> None:
    options = FigureOptions(file_format="pdf", decade_mm=50.0, title_with_survey=False)

    _, height = pdf_page_mm(sounding_figure_file(POINTS, SURVEY, options))

    assert height == pytest.approx(15.0 + 200.0 + 4.0 + 5.5)


def test_figure_needs_a_plottable_point() -> None:
    points = sounding(SheetRow(ab2="1", mn="0,5", delta_v="-80", current="40"))

    with pytest.raises(GeoValueError) as error:
        sounding_figure_file(points, SURVEY, FigureOptions())

    assert error.value.problem.code == "figure.nothing_to_plot"


def test_unknown_format_cannot_be_saved() -> None:
    figure = create_sounding_figure(POINTS)

    with pytest.raises(ValueError, match="unsupported figure format"):
        figure_to_bytes(figure, "jpg")  # type: ignore[arg-type]


def test_project_sheet_uses_its_own_units_and_cv_limit() -> None:
    rows = (
        SheetRow(ab2="10", mn="2", delta_v="30", current="50"),
        SheetRow(ab2="10", mn="2", delta_v="34", current="50"),
    )
    project = Project(
        sheet_settings=SheetSettings(voltage_unit="V", current_unit="mA", cv_limit_percent=10.0),
        sheet_rows=rows,
    )

    (point,) = evaluate_project_sheet(project).points

    # DeltaV in volts: R = 600 and 680 ohm, rho_a = 640 * 49.5 pi; CV 8.8% is below 10%.
    assert point.apparent_resistivity_ohm_m == pytest.approx(640 * 49.5 * math.pi)
    assert point.warnings == ()
