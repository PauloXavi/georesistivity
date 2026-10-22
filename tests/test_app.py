"""Interface tests for the Streamlit application using Streamlit's AppTest."""

from pathlib import Path

import pandas as pd
import pytest

pytest.importorskip("streamlit")

from streamlit.testing.v1 import AppTest

from georesistivity.app import MAIN_SCRIPT
from georesistivity.app.field_sheet_view import rows_from_dataframe, rows_to_dataframe
from georesistivity.field_sheet import SheetRow
from georesistivity.models import Measurement
from georesistivity.project import (
    Project,
    SheetSettings,
    SurveyInfo,
    project_from_json,
    project_to_json,
)
from georesistivity.storage import write_autosave

COMPATIBILITY_SCRIPT = Path(__file__).resolve().parents[1] / "app" / "app.py"


@pytest.fixture
def app() -> AppTest:
    app_test = AppTest.from_file(str(MAIN_SCRIPT), default_timeout=30)
    app_test.run()
    return app_test


def submit(
    app: AppTest,
    *,
    delta_v: str = "",
    current: str = "",
    geometric_factor: str = "",
    spacing: str = "",
    source: str | None = None,
) -> AppTest:
    app.text_input(key="delta_v_raw").set_value(delta_v)
    app.text_input(key="current_raw").set_value(current)
    app.text_input(key="geometric_factor_raw").set_value(geometric_factor)
    app.text_input(key="spacing_raw").set_value(spacing)
    if source is not None:
        app.text_input(key="geometric_factor_source").set_value(source)
    return app.button(key="submit_measurement").click().run()


def measurement_count(app: AppTest) -> int:
    return len(app.session_state["measurements"])


def error_text(app: AppTest) -> str:
    return "\n".join(str(error.value) for error in app.error)


def test_valid_measurement_is_added_and_formatted_in_pt_br(app: AppTest) -> None:
    submit(app, delta_v="125", current="35", geometric_factor="625", spacing="20")

    assert not app.exception
    assert measurement_count(app) == 1
    assert app.metric[0].value == "2.232 \u03a9\u00b7m"
    assert [success.value for success in app.success] == ["Measurement #1 added."]


def test_en_number_format_changes_the_displayed_result(app: AppTest) -> None:
    app.selectbox(key="number_format").set_value("en").run()
    submit(app, delta_v="125", current="35", geometric_factor="625")

    assert app.metric[0].value == "2,232 \u03a9\u00b7m"


def test_ambiguous_thousands_value_is_rejected_with_field_name(app: AppTest) -> None:
    submit(app, delta_v="125", current="35", geometric_factor="1,000")

    assert measurement_count(app) == 0
    assert "Geometric factor K" in error_text(app)
    assert "ambiguous" in error_text(app)
    assert not app.metric


def test_empty_field_error_names_the_field(app: AppTest) -> None:
    submit(app, delta_v="125", current="", geometric_factor="625")

    assert measurement_count(app) == 0
    assert "**Current:** value cannot be empty" in error_text(app)


def test_all_invalid_fields_are_reported_together(app: AppTest) -> None:
    submit(app, delta_v="abc", current="", geometric_factor="1_000")

    errors = error_text(app)
    assert "**Delta V:**" in errors
    assert "**Current:**" in errors
    assert "**Geometric factor K:**" in errors


def test_calculation_error_names_the_field(app: AppTest) -> None:
    submit(app, delta_v="125", current="35", geometric_factor="-625")

    assert measurement_count(app) == 0
    assert "**Geometric factor K:** must be positive" in error_text(app)


def test_non_positive_spacing_is_rejected(app: AppTest) -> None:
    submit(app, delta_v="125", current="35", geometric_factor="625", spacing="0")

    assert measurement_count(app) == 0
    assert "**AB/2:** must be positive" in error_text(app)


def test_invalid_input_is_kept_for_correction(app: AppTest) -> None:
    submit(app, delta_v="125", current="abc", geometric_factor="625")

    assert app.text_input(key="delta_v_raw").value == "125"
    assert app.text_input(key="current_raw").value == "abc"


def test_values_are_cleared_after_success_but_units_and_source_are_kept(app: AppTest) -> None:
    app.selectbox(key="voltage_unit").set_value("V")
    submit(app, delta_v="0,125", current="35", geometric_factor="625", source="field sheet")

    assert measurement_count(app) == 1
    assert app.text_input(key="delta_v_raw").value == ""
    assert app.text_input(key="current_raw").value == ""
    assert app.text_input(key="geometric_factor_raw").value == ""
    assert app.selectbox(key="voltage_unit").value == "V"
    assert app.text_input(key="geometric_factor_source").value == "field sheet"


def test_double_submit_does_not_duplicate_the_measurement(app: AppTest) -> None:
    submit(app, delta_v="125", current="35", geometric_factor="625")
    app.button(key="submit_measurement").click().run()

    assert measurement_count(app) == 1
    assert "value cannot be empty" in error_text(app)


def test_identical_consecutive_measurement_is_added_with_a_warning(app: AppTest) -> None:
    submit(app, delta_v="125", current="35", geometric_factor="625")
    submit(app, delta_v="125", current="35", geometric_factor="625")

    assert measurement_count(app) == 2
    assert any("identical to #1" in str(warning.value) for warning in app.warning)


def test_negative_apparent_resistivity_is_added_with_a_polarity_warning(app: AppTest) -> None:
    submit(app, delta_v="-125", current="35", geometric_factor="625")

    assert measurement_count(app) == 1
    assert app.metric[0].value == "-2.232 \u03a9\u00b7m"
    assert any("polarity" in str(warning.value) for warning in app.warning)


def test_remove_last_measurement(app: AppTest) -> None:
    submit(app, delta_v="125", current="35", geometric_factor="625")
    submit(app, delta_v="100", current="35", geometric_factor="625")

    remove = next(button for button in app.button if button.label == "Remove last measurement")
    remove.click().run()

    assert measurement_count(app) == 1
    assert app.metric[0].value == "2.232 \u03a9\u00b7m"


def test_clear_all_requires_confirmation(app: AppTest) -> None:
    submit(app, delta_v="125", current="35", geometric_factor="625")

    next(button for button in app.button if button.label == "Clear all measurements").click().run()
    assert measurement_count(app) == 1

    next(button for button in app.button if button.label == "Confirm clear").click().run()
    assert measurement_count(app) == 0
    assert not app.metric


def test_spacing_plot_appears_with_two_spaced_measurements(app: AppTest) -> None:
    submit(app, delta_v="125", current="35", geometric_factor="625", spacing="20")
    assert any("at least two measurements" in str(info.value) for info in app.info)

    submit(app, delta_v="100", current="35", geometric_factor="900", spacing="25")

    assert not app.exception
    assert any(subheader.value == "Spacing Plot" for subheader in app.subheader)


def test_compatibility_script_runs_the_same_interface() -> None:
    app_test = AppTest.from_file(str(COMPATIBILITY_SCRIPT), default_timeout=30)
    app_test.run()
    submit(app_test, delta_v="125", current="35", geometric_factor="625")

    assert not app_test.exception
    assert app_test.metric[0].value == "2.232 \u03a9\u00b7m"


def submit_schlumberger(app: AppTest, *, ab2: str, mn: str) -> AppTest:
    app.radio(key="geometric_factor_mode").set_value("schlumberger").run()
    app.text_input(key="delta_v_raw").set_value("125")
    app.text_input(key="current_raw").set_value("35")
    app.text_input(key="spacing_raw").set_value(ab2)
    app.text_input(key="mn_raw").set_value(mn)
    return app.button(key="submit_measurement").click().run()


def test_schlumberger_mode_calculates_k_and_records_its_source(app: AppTest) -> None:
    submit_schlumberger(app, ab2="20", mn="2")

    assert not app.exception
    assert measurement_count(app) == 1
    assert app.metric[0].value == "2.238 \u03a9\u00b7m"
    assert any(
        "calculated: schlumberger (AB/2 = 20 m, MN = 2 m)" in str(caption.value)
        for caption in app.caption
    )
    # MN stays filled for the next reading of the same segment; AB/2 is cleared.
    assert app.text_input(key="mn_raw").value == "2"
    assert app.text_input(key="spacing_raw").value == ""


def test_schlumberger_mode_hides_the_typed_k_field(app: AppTest) -> None:
    app.radio(key="geometric_factor_mode").set_value("schlumberger").run()

    assert "Geometric Factor K" not in [text_input.label for text_input in app.text_input]


def test_schlumberger_mode_requires_mn(app: AppTest) -> None:
    submit_schlumberger(app, ab2="20", mn="")

    assert measurement_count(app) == 0
    assert "**MN:** is required to calculate K" in error_text(app)


def test_schlumberger_mode_rejects_mn_wider_than_ab(app: AppTest) -> None:
    submit_schlumberger(app, ab2="1", mn="3")

    assert measurement_count(app) == 0
    assert "**MN:** MN/2 must be smaller than AB/2" in error_text(app)


def test_wide_mn_shows_a_warning(app: AppTest) -> None:
    submit_schlumberger(app, ab2="1", mn="0,8")

    assert measurement_count(app) == 1
    assert any("MN is wide" in str(warning.value) for warning in app.warning)


def test_k_calculator_for_wenner(app: AppTest) -> None:
    app.selectbox(key="k_calculator_array").set_value("wenner").run()
    app.text_input(key="k_calculator_wenner_a").set_value("10")
    app.button(key="calculate_k").click().run()

    assert [success.value for success in app.success] == ["K = 62,8318530718 m"]


def test_k_calculator_reports_invalid_parameters(app: AppTest) -> None:
    app.selectbox(key="k_calculator_array").set_value("dipole-dipole").run()
    app.text_input(key="k_calculator_dipole-dipole_a").set_value("5")
    app.text_input(key="k_calculator_dipole-dipole_n").set_value("0")
    app.button(key="calculate_k").click().run()

    assert "**n (dimensionless):** must be positive" in error_text(app)


def sheet_app(*rows: SheetRow) -> AppTest:
    app_test = AppTest.from_file(str(MAIN_SCRIPT), default_timeout=30)
    app_test.session_state["sheet_rows"] = list(rows)
    app_test.run()
    return app_test


RHO_COLUMN = "\u03c1a [\u03a9\u00b7m]"


def points_table(app_test: AppTest) -> pd.DataFrame:
    # The editor is also a Dataframe element; the points table is the one without a key.
    return next(frame.value for frame in app_test.dataframe if frame.key is None)


def test_field_sheet_starts_from_the_45_template_positions(app: AppTest) -> None:
    rows = app.session_state["sheet_rows"]

    assert len(rows) == 45
    assert rows[0] == SheetRow(ab2="1", mn="0,5")
    assert any("Type ΔV and I in a row" in str(info.value) for info in app.info)


def test_field_sheet_shows_points_and_the_curve() -> None:
    app_test = sheet_app(
        SheetRow(marker="VD", ab2="1", mn="0,5", delta_v="80", current="40"),
        SheetRow(ab2="5,5", mn="0,5", delta_v="9", current="50"),
        SheetRow(ab2="5,5", mn="2", delta_v="33", current="50"),
        SheetRow(ab2="7,5", mn="2"),
    )

    assert not app_test.exception
    assert not app_test.error
    assert any("3 positions read at 2 AB/2 spacings" in str(c.value) for c in app_test.caption)
    table = points_table(app_test)
    assert table["AB/2 [m]"].tolist() == ["1", "5,5", "5,5"]
    assert table["MN [m]"].tolist() == ["0,5", "0,5", "2"]
    assert table["Marker"].tolist() == ["VD", "", ""]
    assert table[RHO_COLUMN].tolist()[0] == "11,78"
    assert len(app_test.get("image")) == 1


def test_field_sheet_reports_invalid_rows_by_number() -> None:
    app_test = sheet_app(
        SheetRow(ab2="1", mn="0,5", delta_v="1,000", current="40"),
        SheetRow(ab2="1,3", mn="0,5", delta_v="80", current="40", excluded=True),
    )

    errors = error_text(app_test)
    assert "**Row 1** — ΔV: ambiguous value" in errors
    assert "**Row 2** — Exclusion reason: is required to exclude a reading" in errors


def test_field_sheet_flags_high_variation_with_the_selected_limit() -> None:
    app_test = sheet_app(
        SheetRow(ab2="10", mn="2", delta_v="80", current="40"),
        SheetRow(ab2="10", mn="2", delta_v="88", current="40"),
    )

    assert points_table(app_test)["Warnings"].tolist() == ["CV above limit"]

    app_test.number_input(key="sheet_cv_limit_percent").set_value(10.0).run()

    assert points_table(app_test)["Warnings"].tolist() == [""]


def test_field_sheet_uses_the_selected_units() -> None:
    app_test = sheet_app(SheetRow(ab2="1", mn="0,5", delta_v="80", current="40"))
    millivolts = points_table(app_test)[RHO_COLUMN].tolist()[0]

    app_test.selectbox(key="sheet_voltage_unit").set_value("V").run()

    assert millivolts == "11,78"
    assert points_table(app_test)[RHO_COLUMN].tolist()[0] == "11.780"  # 11 780.97 to 4 digits


def test_field_sheet_warns_about_points_left_off_the_log_curve() -> None:
    app_test = sheet_app(
        SheetRow(ab2="1", mn="0,5", delta_v="-80", current="40"),
        SheetRow(ab2="1,3", mn="0,5", delta_v="80", current="40"),
    )

    assert any("not positive: AB/2 = 1 m" in str(w.value) for w in app_test.warning)
    assert len(app_test.get("image")) == 1


def test_field_sheet_without_positive_points_draws_no_curve() -> None:
    app_test = sheet_app(SheetRow(ab2="1", mn="0,5", delta_v="-80", current="40"))

    assert not app_test.exception
    assert app_test.get("image") == []


def test_new_sheet_requires_confirmation() -> None:
    app_test = sheet_app(SheetRow(ab2="1", mn="0,5", delta_v="80", current="40"))

    app_test.button(key="sheet_new").click().run()
    app_test.button(key="sheet_new_cancel").click().run()
    assert len(app_test.session_state["sheet_rows"]) == 1

    app_test.button(key="sheet_new").click().run()
    app_test.button(key="sheet_new_confirm").click().run()

    assert len(app_test.session_state["sheet_rows"]) == 45
    assert app_test.session_state["sheet_version"] == 1
    assert [frame.key for frame in app_test.dataframe] == ["sheet_editor_1"]


def test_rows_from_editor_treat_missing_cells_as_blank() -> None:
    edited = rows_to_dataframe([SheetRow(ab2="1", mn="0,5", delta_v="80", current="40")])
    added = pd.DataFrame(
        [
            {
                "Marker": None,
                "AB/2 [m]": "10",
                "MN [m]": "2",
                "ΔV": float("nan"),
                "I": None,
                "Exclude": None,
                "Exclusion reason": None,
            }
        ]
    )

    rows = rows_from_dataframe(pd.concat([edited, added], ignore_index=True))

    assert rows == [
        SheetRow(ab2="1", mn="0,5", delta_v="80", current="40"),
        SheetRow(ab2="10", mn="2"),
    ]


def test_field_sheet_summary_uses_singular_for_one_position() -> None:
    app_test = sheet_app(SheetRow(ab2="1", mn="0,5", delta_v="80", current="40"))

    assert any(
        str(caption.value) == "1 position read at 1 AB/2 spacing." for caption in app_test.caption
    )


def autosave_files(home: Path) -> list[Path]:
    directory = home / "autosave"
    return sorted(directory.glob("*.geores.json")) if directory.exists() else []


def test_empty_session_is_not_autosaved(app: AppTest, isolated_data_home: Path) -> None:
    assert autosave_files(isolated_data_home) == []
    assert any("Autosave starts with the first value" in str(c.value) for c in app.caption)


def test_sheet_and_survey_details_are_autosaved(isolated_data_home: Path) -> None:
    app_test = sheet_app(SheetRow(marker="VD", ab2="1", mn="0,5", delta_v="80", current="40"))
    app_test.text_input(key="survey_local").set_value("Fazenda Exemplo").run()
    app_test.number_input(key="survey_azimuth").set_value(45.0).run()

    (path,) = autosave_files(isolated_data_home)
    saved = project_from_json(path.read_text(encoding="utf-8"))

    assert path.name == f"session-{app_test.session_state['session_id']}.geores.json"
    assert saved.sheet_rows == (
        SheetRow(marker="VD", ab2="1", mn="0,5", delta_v="80", current="40"),
    )
    assert saved.survey.local == "Fazenda Exemplo"
    assert saved.survey.azimuth_deg == 45.0
    assert any("Autosaved at" in str(c.value) for c in app_test.caption)


def test_single_measurements_are_autosaved(app: AppTest, isolated_data_home: Path) -> None:
    submit(app, delta_v="125", current="35", geometric_factor="625", source="table")

    (path,) = autosave_files(isolated_data_home)
    saved = project_from_json(path.read_text(encoding="utf-8"))

    assert len(saved.measurements) == 1
    assert saved.measurements[0].geometric_factor_source == "table"


def earlier_session_project() -> Project:
    return Project(
        survey=SurveyInfo(local="Fazenda Exemplo", sev_number="07", operator="P."),
        sheet_settings=SheetSettings(voltage_unit="V", current_unit="A", cv_limit_percent=3.0),
        sheet_rows=(
            SheetRow(marker="AZ", ab2="1", mn="0,5", delta_v="0,08", current="0,04"),
            SheetRow(ab2="1,3", mn="0,5"),
        ),
        measurements=(
            Measurement(
                delta_v_original=125.0,
                voltage_unit="mV",
                current_original=35.0,
                current_unit="mA",
                geometric_factor_original=625.0,
                geometric_factor_unit="m",
            ),
        ),
    )


def test_work_from_an_earlier_session_can_be_restored(isolated_data_home: Path) -> None:
    write_autosave("earlier", earlier_session_project())
    app_test = AppTest.from_file(str(MAIN_SCRIPT), default_timeout=30)
    app_test.run()

    assert any("Work from an earlier session" in str(info.value) for info in app_test.info)
    assert any("Fazenda Exemplo · 1 reading ·" in str(c.value) for c in app_test.caption)

    app_test.button(key="restore_earlier").click().run()

    assert not app_test.exception
    assert [s.value for s in app_test.success] == ["Opened the autosave copy."]
    assert app_test.session_state["sheet_rows"] == list(earlier_session_project().sheet_rows)
    assert app_test.session_state["survey_local"] == "Fazenda Exemplo"
    assert app_test.session_state["sheet_voltage_unit"] == "V"
    assert app_test.session_state["sheet_cv_limit_percent"] == 3.0
    assert len(app_test.session_state["measurements"]) == 1
    assert app_test.metric[0].value == "2.232 \u03a9\u00b7m"
    table = points_table(app_test)
    assert table["Marker"].tolist() == ["AZ"]
    # The restored work continues in this session's own autosave file.
    assert len(autosave_files(isolated_data_home)) == 2


def test_project_that_cannot_be_shown_leaves_the_session_unchanged(
    isolated_data_home: Path,
) -> None:
    unsupported = Project(
        sheet_settings=SheetSettings(voltage_unit="uV"),
        sheet_rows=(SheetRow(ab2="1", mn="0,5", delta_v="80", current="40"),),
    )
    write_autosave("other", unsupported)
    app_test = AppTest.from_file(str(MAIN_SCRIPT), default_timeout=30)
    app_test.run()

    app_test.button(key="restore_other").click().run()

    assert "unsupported DeltaV unit in the sheet: 'uV'" in error_text(app_test)
    assert len(app_test.session_state["sheet_rows"]) == 45


def test_autosave_can_be_switched_off(
    monkeypatch: pytest.MonkeyPatch,
    isolated_data_home: Path,
) -> None:
    monkeypatch.setenv("GEORESISTIVITY_AUTOSAVE", "0")
    app_test = sheet_app(SheetRow(ab2="1", mn="0,5", delta_v="80", current="40"))

    assert autosave_files(isolated_data_home) == []
    assert any("Autosave is off" in str(info.value) for info in app_test.info)


def test_save_project_is_enabled_only_with_content(app: AppTest) -> None:
    save = app.get("download_button")
    assert any(button.proto.disabled for button in save if button.proto.label == "Save project")

    submit(app, delta_v="125", current="35", geometric_factor="625")

    buttons = [b for b in app.get("download_button") if b.proto.label == "Save project"]
    assert not buttons[0].proto.disabled


def test_layout_can_be_saved_as_template_and_reused(isolated_data_home: Path) -> None:
    app_test = sheet_app(
        SheetRow(marker="VM", ab2="1", mn="0,5", delta_v="80", current="40"),
        SheetRow(marker="VD", ab2="1,3", mn="0,5"),
    )
    app_test.text_input(key="sheet_template_name").set_value("Meu cabo").run()
    app_test.button(key="save_template").click().run()

    assert any("Template 'Meu cabo' saved" in str(s.value) for s in app_test.success)
    assert (isolated_data_home / "templates" / "Meu_cabo.template.json").exists()

    app_test.selectbox(key="sheet_template_choice").set_value("Meu cabo").run()
    app_test.button(key="sheet_new").click().run()
    app_test.button(key="sheet_new_confirm").click().run()

    assert app_test.session_state["sheet_rows"] == [
        SheetRow(marker="VM", ab2="1", mn="0,5"),
        SheetRow(marker="VD", ab2="1,3", mn="0,5"),
    ]


def test_template_needs_a_name(isolated_data_home: Path) -> None:
    app_test = sheet_app(SheetRow(ab2="1", mn="0,5"))

    app_test.button(key="save_template").click().run()

    assert "The template was not saved: a template needs a name" in error_text(app_test)


def open_upload_script() -> None:
    import streamlit as st

    from georesistivity.app import project_view, state

    class FakeUpload:
        def __init__(self, name: str, data: bytes) -> None:
            self.name = name
            self._data = data

        def getvalue(self) -> bytes:
            return self._data

    state.initialize()
    upload = st.session_state.get("fake_upload")
    st.session_state[state.OPEN_UPLOAD] = None if upload is None else FakeUpload(*upload)
    project_view.open_uploaded_project()
    st.write(repr(state.project_message()))
    st.write(repr(st.session_state[state.META_LOCAL]))


def run_open_upload(name: str, data: bytes | None) -> list[str]:
    app_test = AppTest.from_function(open_upload_script, default_timeout=30)
    if data is not None:
        app_test.session_state["fake_upload"] = (name, data)
    app_test.run()
    assert not app_test.exception
    return [str(markdown.value) for markdown in app_test.markdown]


def test_opening_an_uploaded_project_replaces_the_session() -> None:
    data = project_to_json(earlier_session_project()).encode("utf-8")

    message, local = run_open_upload("SEV-07.geores.json", data)

    assert message == "('success', 'Opened SEV-07.geores.json.')"
    assert local == "'Fazenda Exemplo'"


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (b"\xff\xfe", "not UTF-8 text"),
        (b"{}", "this is not a GeoResistivity project"),
        (b"{", "not valid JSON"),
    ],
)
def test_opening_an_invalid_upload_reports_the_problem(data: bytes, expected: str) -> None:
    message, local = run_open_upload("bad.json", data)

    assert message.startswith("('error', ")
    assert "Could not open bad.json: " in message
    assert expected in message
    assert local == "''"


def test_no_upload_does_nothing() -> None:
    message, _ = run_open_upload("", None)

    assert message == "None"


def test_missing_autosave_copy_reports_a_read_error(isolated_data_home: Path) -> None:
    path = write_autosave("gone", earlier_session_project())
    app_test = AppTest.from_file(str(MAIN_SCRIPT), default_timeout=30)
    app_test.run()
    path.unlink()

    app_test.button(key="restore_gone").click().run()

    assert "Could not read the autosave copy" in error_text(app_test)


def test_autosave_failure_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    from georesistivity.app import project_view

    def failing_write(*args: object, **kwargs: object) -> Path:
        raise OSError("disk full")

    monkeypatch.setattr(project_view, "write_autosave", failing_write)

    app_test = sheet_app(SheetRow(ab2="1", mn="0,5", delta_v="80", current="40"))

    assert "Autosave failed: disk full. Save the project file." in error_text(app_test)


def test_half_typed_row_waits_instead_of_failing() -> None:
    app_test = sheet_app(SheetRow(ab2="1", mn="0,5", delta_v="80"))

    assert not app_test.error
    assert any(str(c.value) == "Waiting for a value in row 1 (I)." for c in app_test.caption)


def test_survey_details_stay_open_while_typing() -> None:
    app_test = AppTest.from_file(str(MAIN_SCRIPT), default_timeout=30)
    app_test.run()
    app_test.text_input(key="survey_local").set_value("Fazenda").run()

    assert app_test.expander[0].label == "Survey details"
    assert app_test.session_state["survey_details_expanded"] is True


def test_restoring_details_collapses_the_survey_panel(isolated_data_home: Path) -> None:
    write_autosave("earlier", earlier_session_project())
    app_test = AppTest.from_file(str(MAIN_SCRIPT), default_timeout=30)
    app_test.run()

    app_test.button(key="restore_earlier").click().run()

    assert app_test.session_state["survey_details_expanded"] is False
