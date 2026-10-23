"""Messages of the scientific core: stable codes with English text.

Problems caused by user input carry a code and parameters (:class:`Problem`), so interfaces
can show them in another language (see ``georesistivity.i18n``) while ``str(error)``
stays English for programs and logs. Errors that only signal programming mistakes keep plain
exception messages.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

EN: dict[str, str] = {
    # Fallback for text without a code (for example from the standard library).
    "text.raw": "{text}",
    # Numbers typed by the user.
    "number.empty": "value cannot be empty",
    "number.both_separators": (
        "ambiguous decimal separators; thousands separators are not accepted "
        "(type 1234.5 or 1234,5)"
    ),
    "number.ambiguous": (
        "ambiguous value {value!r}: {separator!r} may be a thousands or a decimal separator. "
        "Type {integer} for the integer, or {decimal} for the decimal value"
    ),
    "number.invalid": "invalid numeric value: {value!r}",
    "number.not_finite": "value must be finite",
    "number.wrong_separator": (
        "{value!r} uses {other!r}, but the decimal separator is {separator!r}; "
        "thousands separators are not accepted"
    ),
    "value.named_not_finite": "{name} must be finite",
    # Units.
    "unit.missing": "missing unit in {text!r}; write it like 20m or 125mV",
    "voltage.unsupported_unit": "unsupported voltage unit {unit!r}; supported units: {supported}",
    "current.unsupported_unit": "unsupported current unit {unit!r}; supported units: {supported}",
    "length.unsupported_unit": "unsupported length unit {unit!r}; supported units: {supported}",
    "voltage.too_large": "voltage value is too large to convert to SI units",
    "current.too_large": "current value is too large to convert to SI units",
    "length.too_large": "length value is too large to convert to SI units",
    "voltage.too_small": "voltage value is too small to convert to SI units",
    "current.too_small": "current value is too small to convert to SI units",
    "length.too_small": "length value is too small to convert to SI units",
    # Calculation.
    "core.current_zero": "current_a cannot be zero",
    "core.k_zero": "geometric_factor_m cannot be zero",
    "core.k_negative": "geometric_factor_m must be positive",
    "core.result_not_finite": "apparent resistivity result must be finite",
    "field.zero": "cannot be zero",
    "field.not_positive": "must be positive",
    "field.not_finite": "must be finite",
    "field.required": "is required",
    "field.required_for_k": "is required to calculate K",
    # Geometry.
    "geometry.mn_too_wide": "MN/2 must be smaller than AB/2",
    "geometry.too_large": "geometric factor is too large to represent",
    "geometry.undefined": "electrode layout gives no potential difference; K is undefined",
    # Readings and the field sheet.
    "reading.reason_required": "an excluded reading needs a reason",
    "sheet.reason_required": "is required to exclude a reading",
    "sheet.not_typed": "not typed yet",
    "measurement.spacing_pair": "spacing value and spacing unit must be provided together",
    "measurement.mn_pair": "MN value and MN unit must be provided together",
    # CSV files.
    "csv.bad_utf8": "the file starts like UTF-8 but is not valid UTF-8",
    "csv.invalid": "the file is not valid CSV (line {line}): {detail}",
    "csv.no_header": "the file has no header row",
    "csv.not_flag": "{text!r} is not yes or no",
    "csv.unit_differs": "{text!r} differs from {unit!r}, used by the other rows",
    "csv.other_value_filled": "is empty, but the other value is filled",
    # Project and template files.
    "project.invalid_json": "not valid JSON (line {line}, column {column})",
    "project.not_project": "this is not a GeoResistivity project (expected {expected!r})",
    "project.bad_version": "must be a positive integer",
    "project.newer_version": (
        "the file uses version {version}, newer than this program supports ({supported}); "
        "update GeoResistivity to open it"
    ),
    "project.must_be_object": "must be an object",
    "project.must_be_list": "must be a list",
    "project.must_be_text": "must be text",
    "project.must_be_number": "must be a number",
    "project.must_be_number_or_null": "must be a number or null",
    "project.must_be_flag": "must be true or false",
    "project.unknown_field": "unknown field",
    "project.required": "is required",
    "project.array": "only 'schlumberger' is supported",
    "project.cv_limit": "must be between 0 and 100",
    "project.date": "must be a date written as YYYY-MM-DD",
    "project.range": "{name} must be between {low:g} and {high:g}",
    "project.not_finite": "{name} must be a finite number",
    "project.unsupported_voltage_unit": "unsupported DeltaV unit in the sheet: {unit!r}",
    "project.unsupported_current_unit": "unsupported current unit in the sheet: {unit!r}",
    "project.cv_limit_shown": "the CV limit must be between {low:g} and {high:g}%",
    "template.not_template": "this is not a sheet template (expected {expected!r})",
    "template.bad_version": "must be {version}",
    "template.needs_name": "a template needs a name",
    "template.needs_rows": "a template needs at least one row",
    "template.layout_only": "a template keeps only marker, AB/2, and MN",
}


@dataclass(frozen=True, slots=True)
class Problem:
    """A message code with its parameters, renderable in any catalog."""

    code: str
    params: Mapping[str, object] = field(default_factory=dict)

    def text(self, catalog: Mapping[str, str] = EN) -> str:
        """Render the message, in English unless another catalog is given."""
        template = catalog.get(self.code) or EN[self.code]
        return template.format(**self.params)

    @classmethod
    def raw(cls, text: str) -> "Problem":
        """A problem that only has text (no translation is possible)."""
        return cls("text.raw", {"text": text})


class GeoValueError(ValueError):
    """A ``ValueError`` caused by input, carrying a translatable :class:`Problem`."""

    def __init__(self, code: str, **params: object) -> None:
        self.problem = Problem(code, params)
        super().__init__(self.problem.text())


def problem_of(error: BaseException) -> Problem:
    """The problem carried by ``error``, or its English text as a raw problem."""
    problem = getattr(error, "problem", None)
    return problem if isinstance(problem, Problem) else Problem.raw(str(error))
