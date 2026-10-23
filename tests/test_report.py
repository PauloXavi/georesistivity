"""Tests for the VES report."""

import datetime as dt
import hashlib
import re

import pytest

from georesistivity import __version__
from georesistivity.field_sheet import SheetRow
from georesistivity.i18n import TEXTS, Language
from georesistivity.project import Project, SheetSettings, SurveyInfo, project_to_json
from georesistivity.report import (
    REFERENCES,
    Report,
    ReportTable,
    build_report,
    describe_change,
    history_time,
    project_digest,
    render_html,
    render_pdf,
    report_file,
    report_file_name,
)
from georesistivity.sheet_history import HistoryEntry

TIME = "2026-10-23T09:14:00-03:00"
GENERATED = dt.datetime(2026, 10, 23, 10, 0, tzinfo=dt.timezone(dt.timedelta(hours=-3)))
SURVEY = SurveyInfo(
    name="Campanha",
    sev_number="01",
    local="Fazenda <b>Boa</b> & Vista",
    date=dt.date(2026, 10, 23),
    azimuth_deg=45.0,
    latitude=-15.5,
    longitude=-47.25,
)
ROWS = (
    SheetRow(marker="VM", ab2="1", mn="0,5", delta_v="80", current="40", id="r1", entered_at=TIME),
    SheetRow(ab2="10", mn="2", delta_v="30", current="50", id="r2", entered_at=TIME),
    SheetRow(ab2="10", mn="2", delta_v="34", current="50", id="r3"),
    SheetRow(
        ab2="10",
        mn="2",
        delta_v="90",
        current="50",
        excluded=True,
        reason="eletrodo solto",
        id="r4",
    ),
    SheetRow(ab2="13", mn="2", delta_v="abc", current="50", id="r5"),
    SheetRow(ab2="18", mn="2", delta_v="5", id="r6"),
    SheetRow(ab2="24", mn="2", id="r7"),
)
HISTORY = (
    HistoryEntry(TIME, "edit", row="r2", row_number=2, field="delta_v", old="29", new="30"),
    HistoryEntry(TIME, "units", old="V / mA", new="mV / mA", old_units=("V", "mA")),
    HistoryEntry(TIME, "undo", undoes=2),
)
PROJECT = Project(survey=SURVEY, sheet_settings=SheetSettings(), sheet_rows=ROWS, history=HISTORY)


def report(language: Language = "pt-BR", project: Project = PROJECT) -> Report:
    return build_report(
        project,
        language=language,
        number_format="pt-BR" if language == "pt-BR" else "en",
        generated_at=GENERATED,
    )


def table(content: Report, title: str) -> ReportTable:
    return next(t for t in content.tables if t.title == title)


def test_header_and_details_show_only_what_was_filled_in() -> None:
    content = report()

    assert content.title == "Relatório de sondagem elétrica vertical (Schlumberger)"
    assert content.subtitle == "SEV 01 · Fazenda <b>Boa</b> & Vista · 23/10/2026"
    details = dict(content.details)
    assert details["SEV nº"] == "01"
    assert details["Azimute de AB [°]"] == "45"
    assert details["Coordenadas (EPSG:4326)"] == "-15,5; -47,25"
    assert details["Unidades de ΔV / I"] == "mV / mA"
    assert details["Limite de CV"] == "5%"
    assert "Operador" not in details  # left empty


def test_summary_counts_positions_readings_warnings_and_unused_rows() -> None:
    assert report().summary == (
        "2 posições em 2 espaçamentos AB/2: 3 leituras usadas e 1 excluída.",
        "AB/2 de 1 a 10 m; \u03c1a de 11,78 a 99,53 Ω·m.",
        "1 posição com aviso de qualidade.",
        "2 linhas da folha não foram usadas (veja abaixo).",
    )


def test_points_and_readings_tables() -> None:
    content = report()

    points = table(content, "Posições")
    assert points.rows[1][:8] == (
        "10",
        "2",
        "",
        "155,5",
        "2 (+1 excluídas)",
        "99,53",
        "6,220",  # 1.98 pi
        "8,839",
    )
    assert points.rows[1][8] == "CV acima do limite"
    readings = table(content, "Leituras")
    assert readings.columns[2:4] == ("ΔV [mV]", "I [mA]")
    excluded = readings.rows[3]
    assert excluded[6:] == ("sim", "eletrodo solto", "")
    assert readings.rows[1][8] == "23/10/2026 09:14:00"


def test_rows_not_used_say_why() -> None:
    unused = table(report(), "Linhas da folha não usadas")

    assert unused.rows == (
        ("5", "ΔV: valor numérico inválido: 'abc'"),
        ("6", "I: ainda não digitado"),
    )


def test_warnings_and_history_tables() -> None:
    content = report()

    warnings = table(content, "Avisos de qualidade")
    meaning = TEXTS["pt-BR"]["warning.stack_high_variation"]
    assert warnings.rows == (("CV acima do limite", meaning, "1"),)
    history = table(content, "Histórico de alterações")
    assert [row[3] for row in history.rows] == [
        "ΔV: 29 → 30",
        "Unidades de ΔV / I: V / mA → mV / mA (desfeita)",
        "Desfeito o registro nº 2",
    ]


def test_methods_references_and_footer() -> None:
    content = report()

    assert any("K = π (L² \u2212 l²) / (2 l)" in line for line in content.methods)
    assert any("acima de 5%" in line for line in content.methods)
    assert len(REFERENCES) == 3
    digest = hashlib.sha256(project_to_json(PROJECT).encode("utf-8")).hexdigest()
    assert project_digest(PROJECT) == digest
    assert content.footer == (
        f"GeoResistivity {__version__} · gerado em 23/10/2026 10:00:00 · "
        f"SHA-256 do projeto: {digest}"
    )


def test_report_in_english() -> None:
    content = report("en")

    assert content.title == "Vertical electrical sounding report (Schlumberger)"
    assert content.subtitle == "VES 01 · Fazenda <b>Boa</b> & Vista · 2026-10-23"
    assert content.summary[1] == "AB/2 from 1 to 10 m; \u03c1a from 11.78 to 99.53 Ω·m."
    assert dict(content.details)["VES no."] == "01"


def test_html_is_self_contained_and_escapes_typed_text() -> None:
    page = render_html(report())

    assert page.startswith('<!DOCTYPE html>\n<html lang="pt-BR">')
    assert "<svg" in page
    assert "<script" not in page
    assert "Fazenda &lt;b&gt;Boa&lt;/b&gt; &amp; Vista" in page
    assert "<b>Boa</b>" not in page
    assert 'content="light"' in page
    assert "eletrodo solto" in page
    assert page == render_html(report())  # reproducible


def test_pdf_is_a4_reproducible_and_titled() -> None:
    first = render_pdf(report())

    assert first.startswith(b"%PDF")
    sizes = re.findall(rb"/MediaBox \[ ?0 0 ([\d.]+) ([\d.]+) ?\]", first)
    assert sizes
    assert all(
        (float(w) * 25.4 / 72, float(h) * 25.4 / 72) == pytest.approx((210.0, 297.0))
        for w, h in sizes
    )
    assert b"GeoResistivity " + __version__.encode() in first
    assert b"CreationDate" not in first
    assert first == render_pdf(report())


def test_long_tables_continue_on_more_pages() -> None:
    rows = tuple(
        SheetRow(ab2=str(10 + index), mn="2", delta_v="30", current="50") for index in range(120)
    )

    pdf = render_pdf(report(project=Project(sheet_rows=rows)))

    assert len(re.findall(rb"/Type /Page(?!s)", pdf)) >= 4


def test_report_of_a_sheet_without_readings() -> None:
    content = report(project=Project())

    assert content.summary == ("A folha ainda não tem leituras completas.",)
    assert not content.has_curve
    page = render_html(content)
    assert "Nenhuma posição tem \u03c1a positivo" in page
    assert "<svg" not in page
    assert render_pdf(content).startswith(b"%PDF")


def test_report_files_and_names() -> None:
    content = report()

    assert report_file(content, "html").startswith(b"<!DOCTYPE html>")
    assert report_file(content, "pdf").startswith(b"%PDF")
    with pytest.raises(ValueError, match="unsupported report format"):
        report_file(content, "docx")  # type: ignore[arg-type]
    assert report_file_name(PROJECT, "pdf") == "SEV-01-Fazenda_b_Boa_b_Vista-report.pdf"
    assert report_file_name(Project(), "html") == "georesistivity-report.html"


@pytest.mark.parametrize(
    ("entry", "portuguese", "english"),
    [
        (
            HistoryEntry(TIME, "edit", row="r", field="excluded", old="false", new="true"),
            "Excluir: não → sim",
            "Exclude: no → yes",
        ),
        (
            HistoryEntry(TIME, "edit", row="r", field="marker", old="VD", new=""),
            "Cor: VD → (vazio)",
            "Marker: VD → (empty)",
        ),
        (
            HistoryEntry(
                TIME, "delete_row", row="r", row_number=3, old_row=SheetRow(ab2="1,8", mn="0,5")
            ),
            "Linha apagada (AB/2 1,8 · MN 0,5)",
            "Row deleted (AB/2 1,8 · MN 0,5)",
        ),
        (
            HistoryEntry(TIME, "replace_sheet", source="new_sheet"),
            "Folha substituída por uma folha nova",
            "Sheet replaced by a new sheet",
        ),
        (
            HistoryEntry(TIME, "append_rows", source="import", detail="b.csv", row_ids=("a", "b")),
            "2 linhas acrescentadas pela importação de b.csv",
            "2 rows added by the import of b.csv",
        ),
    ],
)
def test_history_entries_are_described_in_both_languages(
    entry: HistoryEntry, portuguese: str, english: str
) -> None:
    assert describe_change(entry, "pt-BR") == portuguese
    assert describe_change(entry, "en") == english


def test_history_times_follow_the_language() -> None:
    assert history_time(TIME, "pt-BR") == "23/10/2026 09:14:00"
    assert history_time(TIME, "en") == "2026-10-23 09:14:00"


def test_report_with_every_reading_excluded_has_no_range_or_curve() -> None:
    rows = (SheetRow(ab2="1", mn="0,5", delta_v="80", current="40", excluded=True, reason="x"),)

    content = report(project=Project(sheet_rows=rows))

    assert content.summary == ("1 posição em 1 espaçamento AB/2: 0 leituras usadas e 1 excluída.",)
    assert not content.has_curve


def test_curve_moves_to_the_next_page_when_the_details_fill_the_first() -> None:
    survey = SurveyInfo(notes="\n".join(f"Observação {number}" for number in range(40)))
    project = Project(survey=survey, sheet_rows=ROWS)

    pdf = render_pdf(report(project=project))

    assert len(re.findall(rb"/Type /Page(?!s)", pdf)) >= 3
