"""Interface tests for the Streamlit application using Streamlit's AppTest."""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")

from streamlit.testing.v1 import AppTest

from georesistivity.app import MAIN_SCRIPT

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
