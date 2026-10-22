"""Application use cases shared by the interfaces.

This layer turns raw user input into domain objects and decides the outcome of each action.
It does not import Streamlit, pandas, or Matplotlib, so every rule here is testable without
an interface, and the interfaces only render what these functions return.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from georesistivity.core import calculate_measurement
from georesistivity.models import (
    Measurement,
    MeasurementField,
    MeasurementFieldError,
    MeasurementResult,
)
from georesistivity.validation import parse_number


@dataclass(frozen=True, slots=True)
class MeasurementInput:
    """Raw text and unit selections for one measurement, exactly as entered."""

    delta_v: str
    voltage_unit: str
    current: str
    current_unit: str
    geometric_factor: str
    geometric_factor_unit: str
    spacing_ab2: str = ""
    spacing_unit: str = "m"
    geometric_factor_source: str = ""


@dataclass(frozen=True, slots=True)
class FieldIssue:
    """One input problem attributed to a measurement field."""

    field: MeasurementField
    message: str


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

    @property
    def accepted(self) -> bool:
        """Whether the submission produced a measurement result."""
        return self.result is not None


def _parse_field(field: MeasurementField, raw_value: str, issues: list[FieldIssue]) -> float | None:
    try:
        return parse_number(raw_value)
    except ValueError as exc:
        issues.append(FieldIssue(field, str(exc)))
        return None


def evaluate_submission(
    entry: MeasurementInput,
    previous: Sequence[MeasurementResult],
) -> SubmissionOutcome:
    """Validate and calculate one measurement without changing ``previous``.

    Every invalid numeric field is reported at once. AB/2 is optional: blank text means no
    spacing. Calculation problems are attributed to their field when possible.
    """
    issues: list[FieldIssue] = []
    delta_v = _parse_field("delta_v", entry.delta_v, issues)
    current = _parse_field("current", entry.current, issues)
    geometric_factor = _parse_field("geometric_factor", entry.geometric_factor, issues)
    spacing_supplied = bool(entry.spacing_ab2.strip())
    spacing = _parse_field("spacing_ab2", entry.spacing_ab2, issues) if spacing_supplied else None

    if issues or delta_v is None or current is None or geometric_factor is None:
        return SubmissionOutcome(field_issues=tuple(issues))

    measurement = Measurement(
        delta_v_original=delta_v,
        voltage_unit=entry.voltage_unit,
        current_original=current,
        current_unit=entry.current_unit,
        geometric_factor_original=geometric_factor,
        geometric_factor_unit=entry.geometric_factor_unit,
        spacing_ab2_original=spacing,
        spacing_unit=entry.spacing_unit if spacing is not None else None,
        geometric_factor_source=entry.geometric_factor_source.strip() or None,
    )
    try:
        result = calculate_measurement(measurement)
    except MeasurementFieldError as exc:
        return SubmissionOutcome(field_issues=(FieldIssue(exc.field, exc.reason),))
    except ValueError as exc:
        return SubmissionOutcome(error=str(exc))

    is_duplicate = bool(previous) and previous[-1].measurement == measurement
    return SubmissionOutcome(result=result, duplicate_of=len(previous) if is_duplicate else None)
