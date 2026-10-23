"""Application use cases shared by the interfaces.

This layer turns raw user input into domain objects and decides the outcome of each action.
It does not import Streamlit, pandas, or Matplotlib, so every rule here is testable without
an interface, and the interfaces only render what these functions return.
"""

import dataclasses
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from georesistivity.core import calculate_measurement
from georesistivity.formatting import format_full_precision
from georesistivity.geometry import (
    ARRAY_PARAMETERS,
    SCHLUMBERGER_MIN_RATIO,
    ArrayType,
    GeometryError,
    GeometryParameter,
    geometric_factor,
    schlumberger_geometric_factor,
    schlumberger_spacing_ratio,
)
from georesistivity.messages import Problem, problem_of
from georesistivity.models import (
    Measurement,
    MeasurementField,
    MeasurementFieldError,
    MeasurementResult,
    MeasurementWarning,
)
from georesistivity.units import convert_length_to_meters
from georesistivity.validation import parse_number

GeometricFactorMode = Literal["external", "schlumberger"]
"""``external``: K is typed by the user. ``schlumberger``: K is calculated from AB/2 and MN."""


@dataclass(frozen=True, slots=True)
class MeasurementInput:
    """Raw text and unit selections for one measurement, exactly as entered."""

    delta_v: str
    voltage_unit: str
    current: str
    current_unit: str
    geometric_factor: str = ""
    geometric_factor_unit: str = "m"
    spacing_ab2: str = ""
    spacing_unit: str = "m"
    geometric_factor_source: str = ""
    mn: str = ""
    mn_unit: str = "m"
    geometric_factor_mode: GeometricFactorMode = "external"


@dataclass(frozen=True, slots=True)
class FieldIssue:
    """One input problem attributed to a measurement field.

    ``message`` is English; ``problem`` lets interfaces translate it.
    """

    field: MeasurementField
    message: str
    problem: Problem | None = dataclasses.field(default=None, compare=False)

    @classmethod
    def of(cls, field: MeasurementField, problem: Problem) -> "FieldIssue":
        return cls(field, problem.text(), problem)


@dataclass(frozen=True, slots=True)
class SubmissionOutcome:
    """Outcome of evaluating one measurement submission.

    Exactly one of ``result``, ``field_issues``, or ``error`` describes the outcome.
    ``duplicate_of`` is the 1-based acquisition index of the previous measurement when the
    accepted one is identical to it, which may be an intentional repeated reading.
    """

    result: MeasurementResult | None = None
    field_issues: tuple[FieldIssue, ...] = ()
    error: str | None = None
    duplicate_of: int | None = None
    error_problem: Problem | None = dataclasses.field(default=None, compare=False)

    @property
    def accepted(self) -> bool:
        """Whether the submission produced a measurement result."""
        return self.result is not None


_GEOMETRY_FIELDS: dict[GeometryParameter, MeasurementField] = {
    "ab2": "spacing_ab2",
    "mn": "mn",
}


def _parse_field(field: MeasurementField, raw_value: str, issues: list[FieldIssue]) -> float | None:
    try:
        return parse_number(raw_value)
    except ValueError as exc:
        issues.append(FieldIssue.of(field, problem_of(exc)))
        return None


def _parse_optional_field(
    field: MeasurementField,
    raw_value: str,
    issues: list[FieldIssue],
) -> float | None:
    return _parse_field(field, raw_value, issues) if raw_value.strip() else None


def _length_in_meters(
    field: MeasurementField,
    value: float,
    unit: str,
    issues: list[FieldIssue],
) -> float | None:
    try:
        return convert_length_to_meters(value, unit)
    except ValueError as exc:
        issues.append(FieldIssue.of(field, problem_of(exc)))
        return None


def schlumberger_source(ab2: float, ab2_unit: str, mn: float, mn_unit: str) -> str:
    """Describe a calculated Schlumberger K for the "K source" column."""
    ab2_text = format_full_precision(ab2, number_format="en")
    mn_text = format_full_precision(mn, number_format="en")
    return f"calculated: schlumberger (AB/2 = {ab2_text} {ab2_unit}, MN = {mn_text} {mn_unit})"


def evaluate_submission(
    entry: MeasurementInput,
    previous: Sequence[MeasurementResult],
) -> SubmissionOutcome:
    """Validate and calculate one measurement without changing ``previous``.

    Every invalid numeric field is reported at once. AB/2 and MN are optional when K is
    entered, and required when K is calculated for Schlumberger; the calculated K is stored
    in meters with a "K source" that records the geometry. Calculation problems are
    attributed to their field when possible.
    """
    issues: list[FieldIssue] = []
    calculated = entry.geometric_factor_mode == "schlumberger"

    delta_v = _parse_field("delta_v", entry.delta_v, issues)
    current = _parse_field("current", entry.current, issues)
    typed_factor = (
        None if calculated else _parse_field("geometric_factor", entry.geometric_factor, issues)
    )
    spacing = _parse_optional_field("spacing_ab2", entry.spacing_ab2, issues)
    mn = _parse_optional_field("mn", entry.mn, issues)
    if calculated:
        if not entry.spacing_ab2.strip():
            issues.append(FieldIssue.of("spacing_ab2", Problem("field.required_for_k")))
        if not entry.mn.strip():
            issues.append(FieldIssue.of("mn", Problem("field.required_for_k")))

    if issues or delta_v is None or current is None:
        return SubmissionOutcome(field_issues=tuple(issues))

    if calculated:
        assert spacing is not None and mn is not None
        spacing_m = _length_in_meters("spacing_ab2", spacing, entry.spacing_unit, issues)
        mn_m = _length_in_meters("mn", mn, entry.mn_unit, issues)
        if spacing_m is None or mn_m is None:
            return SubmissionOutcome(field_issues=tuple(issues))
        try:
            factor = schlumberger_geometric_factor(spacing_m, mn_m)
        except GeometryError as exc:
            field = _GEOMETRY_FIELDS[exc.parameter]
            return SubmissionOutcome(field_issues=(FieldIssue.of(field, exc.problem),))
        except ValueError as exc:
            return SubmissionOutcome(error=str(exc), error_problem=problem_of(exc))
        factor_unit = "m"
        source: str | None = schlumberger_source(spacing, entry.spacing_unit, mn, entry.mn_unit)
    else:
        assert typed_factor is not None
        factor = typed_factor
        factor_unit = entry.geometric_factor_unit
        source = entry.geometric_factor_source.strip() or None

    measurement = Measurement(
        delta_v_original=delta_v,
        voltage_unit=entry.voltage_unit,
        current_original=current,
        current_unit=entry.current_unit,
        geometric_factor_original=factor,
        geometric_factor_unit=factor_unit,
        spacing_ab2_original=spacing,
        spacing_unit=entry.spacing_unit if spacing is not None else None,
        geometric_factor_source=source,
        mn_original=mn,
        mn_unit=entry.mn_unit if mn is not None else None,
    )
    try:
        result = calculate_measurement(measurement)
    except MeasurementFieldError as exc:
        return SubmissionOutcome(field_issues=(FieldIssue.of(exc.field, exc.problem),))
    except ValueError as exc:
        return SubmissionOutcome(error=str(exc), error_problem=problem_of(exc))

    if (
        calculated
        and result.spacing_ab2_m is not None
        and result.mn_m is not None
        and schlumberger_spacing_ratio(result.spacing_ab2_m, result.mn_m) < SCHLUMBERGER_MIN_RATIO
    ):
        result = dataclasses.replace(
            result,
            warnings=(*result.warnings, MeasurementWarning.SCHLUMBERGER_WIDE_MN),
        )

    is_duplicate = bool(previous) and previous[-1].measurement == measurement
    return SubmissionOutcome(result=result, duplicate_of=len(previous) if is_duplicate else None)


@dataclass(frozen=True, slots=True)
class ParameterIssue:
    """One problem with one geometry parameter; ``message`` is English."""

    parameter: GeometryParameter
    message: str
    problem: Problem | None = dataclasses.field(default=None, compare=False)

    @classmethod
    def of(cls, parameter: GeometryParameter, problem: Problem) -> "ParameterIssue":
        return cls(parameter, problem.text(), problem)


@dataclass(frozen=True, slots=True)
class GeometricFactorOutcome:
    """Outcome of a stand-alone K calculation: ``value_m`` or the problems found."""

    value_m: float | None = None
    issues: tuple[ParameterIssue, ...] = ()
    error: str | None = None
    error_problem: Problem | None = dataclasses.field(default=None, compare=False)


def calculate_geometric_factor(
    array: ArrayType,
    raw_values: Mapping[GeometryParameter, str],
    length_unit: str,
) -> GeometricFactorOutcome:
    """Calculate K from typed geometry parameters, all lengths in ``length_unit``.

    The dimensionless ``n`` of dipole arrays is not converted.
    """
    issues: list[ParameterIssue] = []
    values: dict[GeometryParameter, float] = {}
    for parameter in ARRAY_PARAMETERS[array]:
        raw_value = raw_values.get(parameter, "")
        try:
            number = parse_number(raw_value)
            values[parameter] = (
                number if parameter == "n" else convert_length_to_meters(number, length_unit)
            )
        except ValueError as exc:
            issues.append(ParameterIssue.of(parameter, problem_of(exc)))
    if issues:
        return GeometricFactorOutcome(issues=tuple(issues))

    try:
        return GeometricFactorOutcome(value_m=geometric_factor(array, values))
    except GeometryError as exc:
        return GeometricFactorOutcome(issues=(ParameterIssue.of(exc.parameter, exc.problem),))
    except ValueError as exc:
        return GeometricFactorOutcome(error=str(exc), error_problem=problem_of(exc))
