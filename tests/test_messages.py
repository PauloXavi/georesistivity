"""Tests for message codes carried by errors of the scientific core."""

import string

import pytest

from georesistivity.core import calculate_measurement
from georesistivity.field_sheet import SheetRow, evaluate_sheet
from georesistivity.geometry import GeometryError, schlumberger_geometric_factor
from georesistivity.messages import EN, GeoValueError, Problem, problem_of
from georesistivity.models import Measurement, MeasurementFieldError
from georesistivity.project import ProjectFormatError, project_from_json
from georesistivity.services import MeasurementInput, evaluate_submission
from georesistivity.validation import parse_number


def test_problem_renders_english_text() -> None:
    problem = Problem("number.invalid", {"value": "abc"})

    assert problem.text() == "invalid numeric value: 'abc'"
    assert problem.text({"number.invalid": "valor inválido: {value!r}"}) == "valor inválido: 'abc'"
    assert problem.text({}) == "invalid numeric value: 'abc'"


def test_raw_problems_keep_their_text() -> None:
    assert Problem.raw("as written").text() == "as written"
    assert problem_of(ValueError("plain")) == Problem.raw("plain")


def test_geo_value_error_is_a_value_error_with_english_text() -> None:
    error = GeoValueError("unit.missing", text="125")

    assert isinstance(error, ValueError)
    assert str(error) == "missing unit in '125'; write it like 20m or 125mV"
    assert problem_of(error) == Problem("unit.missing", {"text": "125"})


@pytest.mark.parametrize("code", sorted(EN))
def test_every_message_has_only_named_placeholders(code: str) -> None:
    fields = [name for _, name, _, _ in string.Formatter().parse(EN[code]) if name is not None]

    assert all(fields), f"{code} uses a positional placeholder"


def test_input_errors_carry_codes() -> None:
    with pytest.raises(GeoValueError) as number_error:
        parse_number("1,000")
    assert number_error.value.problem.code == "number.ambiguous"
    assert number_error.value.problem.params["integer"] == "1000"

    with pytest.raises(GeometryError) as geometry_error:
        schlumberger_geometric_factor(1.0, 3.0)
    assert geometry_error.value.problem == Problem("geometry.mn_too_wide")

    measurement = Measurement(1.0, "V", 0.0, "A", 1.0, "m")
    with pytest.raises(MeasurementFieldError) as field_error:
        calculate_measurement(measurement)
    assert field_error.value.problem == Problem("field.zero")
    assert field_error.value.reason == "cannot be zero"

    with pytest.raises(ProjectFormatError) as project_error:
        project_from_json("{")
    assert project_error.value.problem.code == "project.invalid_json"


def test_outcomes_carry_codes_for_translation() -> None:
    entry = MeasurementInput("abc", "mV", "", "mA", "625", "m")
    issues = evaluate_submission(entry, []).field_issues

    assert [issue.problem.code for issue in issues if issue.problem] == [
        "number.invalid",
        "number.empty",
    ]

    rows = evaluate_sheet(
        [SheetRow(ab2="1", mn="0,5", delta_v="80", current="40", excluded=True)],
        voltage_unit="mV",
        current_unit="mA",
    ).rows
    assert rows[0].issues[0].problem == Problem("sheet.reason_required")
