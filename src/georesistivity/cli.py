"""Command-line interface: ``georesistivity``."""

import argparse
import importlib.util
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from georesistivity import __version__
from georesistivity.app import MAIN_SCRIPT
from georesistivity.figures import (
    DECADE_MM_RANGE,
    DEFAULT_DECADE_MM,
    FIGURE_FORMATS,
    FigureFormat,
    FigureOptions,
    check_decade_mm,
    evaluate_project_sheet,
    figure_file_name,
    sounding_figure_file,
)
from georesistivity.formatting import NumberFormat, format_full_precision, format_significant
from georesistivity.geometry import (
    ARRAY_PARAMETERS,
    FIELD_SHEET_AB2_M,
    FIELD_SHEET_MN_M,
    SCHLUMBERGER_MIN_RATIO,
    ArrayType,
    GeometryError,
    GeometryParameter,
    geometric_factor,
    schlumberger_k_table,
    schlumberger_spacing_ratio,
)
from georesistivity.i18n import LANGUAGES, Language
from georesistivity.models import MeasurementField, MeasurementWarning
from georesistivity.project import ProjectFormatError, project_from_json
from georesistivity.services import GeometricFactorMode, MeasurementInput, evaluate_submission
from georesistivity.storage import AUTOSAVE_VARIABLE
from georesistivity.units import convert_length_to_meters, split_quantity
from georesistivity.validation import parse_number

DEFAULT_PORT = 8501

# Applied on every launch, so they hold even when the repository's .streamlit/config.toml is
# not in the working directory. File watching only serves development, where
# `streamlit run app/app.py` keeps reloading on save.
_STREAMLIT_SETTINGS = (
    "--browser.gatherUsageStats",
    "false",
    "--client.toolbarMode",
    "viewer",
    "--server.fileWatcherType",
    "none",
)

LAN_WARNING = (
    "LAN mode: other devices on this network can open the app and see its data. "
    "Use it only on a trusted network, such as this computer's own hotspot."
)
# Output is ASCII-only so that it survives any console or pipe encoding.
WARNING_TEXT: dict[MeasurementWarning, str] = {
    MeasurementWarning.NEGATIVE_APPARENT_RESISTIVITY: (
        "negative apparent resistivity; check electrode polarity, current direction, "
        "and cable connections"
    ),
    MeasurementWarning.SCHLUMBERGER_WIDE_MN: (
        "MN is wide for this AB/2: (AB/2)/(MN/2) is below 4; K is exact, but consider a smaller MN"
    ),
}
CALC_OPTIONS: dict[MeasurementField, str] = {
    "delta_v": "--dv",
    "current": "--i",
    "geometric_factor": "--k",
    "spacing_ab2": "--ab2",
    "mn": "--mn",
}
ARRAY_HELP: dict[ArrayType, str] = {
    "schlumberger": "Schlumberger, from AB/2 and the full MN spacing",
    "wenner": "Wenner-alpha, from the electrode spacing a",
    "dipole-dipole": "dipole-dipole, from the dipole length a and the factor n",
    "pole-dipole": "pole-dipole with remote B, from the dipole length a and the factor n",
    "general": "any four-electrode layout, from the distances AM, BM, AN, and BN",
}
PARAMETER_HELP: dict[GeometryParameter, str] = {
    "ab2": "half the A-B distance, with unit (e.g. 20m)",
    "mn": "full M-N distance, as on the field sheet, with unit (e.g. 2m)",
    "a": "spacing a, with unit (e.g. 10m)",
    "n": "dimensionless factor n (e.g. 2)",
    "am": "distance A-M, with unit",
    "bm": "distance B-M, with unit",
    "an": "distance A-N, with unit",
    "bn": "distance B-N, with unit",
}

MISSING_STREAMLIT = (
    "The interface needs the 'app' extra. Install it with:\n"
    '    python -m pip install "georesistivity[app]"'
)


def _port(text: str) -> int:
    try:
        port = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid port: {text!r}") from None
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError(f"port must be between 1 and 65535, got {port}")
    return port


def _number(text: str) -> float:
    try:
        return parse_number(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


def _add_number_format(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--number-format",
        choices=("pt-BR", "en"),
        default="pt-BR",
        help="decimal separator of the output: pt-BR (comma, default) or en (point)",
    )


def _add_k_parser(subcommands: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    k = subcommands.add_parser(
        "k",
        help="calculate the geometric factor K",
        description="Calculate the geometric factor K in meters.",
    )
    arrays = k.add_subparsers(dest="array", required=True, metavar="ARRAY")
    for array, parameters in ARRAY_PARAMETERS.items():
        array_parser = arrays.add_parser(array, help=ARRAY_HELP[array])
        for parameter in parameters:
            array_parser.add_argument(
                f"--{parameter}",
                required=True,
                metavar="N" if parameter == "n" else "LENGTH",
                help=PARAMETER_HELP[parameter],
            )
        _add_number_format(array_parser)

    table = arrays.add_parser(
        "table",
        help="Schlumberger K table by AB/2 and MN, as on the field sheet",
        description="Print the Schlumberger K table [m]. Rows are AB/2 and columns MN, both in "
        "meters; the defaults are the spacings of the standard field sheet.",
    )
    table.add_argument(
        "--ab2",
        type=_number,
        nargs="+",
        default=list(FIELD_SHEET_AB2_M),
        metavar="M",
        help="AB/2 values in meters",
    )
    table.add_argument(
        "--mn",
        type=_number,
        nargs="+",
        default=list(FIELD_SHEET_MN_M),
        metavar="M",
        help="full MN values in meters",
    )
    table.add_argument(
        "--all",
        action="store_true",
        help=f"also show spacings with (AB/2)/(MN/2) below {SCHLUMBERGER_MIN_RATIO:g}, "
        "marked with *",
    )
    table.add_argument(
        "--digits",
        type=int,
        choices=range(3, 9),
        default=5,
        metavar="3-8",
        help="significant digits (default: 5)",
    )
    _add_number_format(table)


def _add_calc_parser(subcommands: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    calc = subcommands.add_parser(
        "calc",
        help="calculate the apparent resistivity of one reading",
        description="Calculate rho_a = K * DeltaV / I. Give K with --k, or give --ab2 and "
        "--mn to calculate the Schlumberger K. Every value takes its unit, e.g. 125mV. Write "
        "negative values with an equals sign, e.g. --dv=-125mV.",
    )
    calc.add_argument("--dv", required=True, metavar="VOLTAGE", help="DeltaV, e.g. 125mV")
    calc.add_argument("--i", required=True, metavar="CURRENT", help="current, e.g. 35mA")
    calc.add_argument("--k", metavar="LENGTH", help="geometric factor K, e.g. 625m")
    calc.add_argument("--ab2", metavar="LENGTH", help="AB/2, e.g. 20m")
    calc.add_argument("--mn", metavar="LENGTH", help="full MN spacing, e.g. 2m")
    calc.add_argument("--source", default="", help="where the typed K comes from")
    _add_number_format(calc)


def _decade_mm(text: str) -> float:
    try:
        return check_decade_mm(parse_number(text))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


def _add_plot_parser(subcommands: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    low, high = DECADE_MM_RANGE
    plot = subcommands.add_parser(
        "plot",
        help="save the VES curve of a project as PNG, SVG, or PDF",
        description="Draw the field sheet of a project (*.geores.json) as a log-log VES curve "
        "and save it as PNG (300 dpi), SVG, or PDF. The format comes from --format or from the "
        "output name.",
    )
    plot.add_argument("project", type=Path, help="project file (*.geores.json)")
    plot.add_argument(
        "-o",
        "--output",
        type=Path,
        help="figure file to write (default: named after the SEV number and place, e.g. "
        "SEV-01-Fazenda-ves-curve.pdf, in the current directory)",
    )
    plot.add_argument("--format", choices=FIGURE_FORMATS, help="png, svg, or pdf (default: pdf)")
    plot.add_argument(
        "--decade-mm",
        type=_decade_mm,
        nargs="?",
        const=DEFAULT_DECADE_MM,
        metavar="MM",
        help="draw to bilog paper scale with MM millimetres per decade on both axes "
        f"({low:g} to {high:g}; {DEFAULT_DECADE_MM:g} if MM is left out, a provisional default)",
    )
    plot.add_argument("--no-error-bars", action="store_true", help="leave out the error bars")
    plot.add_argument(
        "--no-title-details",
        action="store_true",
        help="leave the SEV number, place, and date out of the title",
    )
    plot.add_argument(
        "--language",
        choices=tuple(LANGUAGES),
        default="pt-BR",
        help="language of the figure texts: pt-BR (default) or en",
    )
    plot.add_argument(
        "--number-format",
        choices=("pt-BR", "en"),
        help="decimal separator of the legend (default: the one of --language)",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for all subcommands."""
    parser = argparse.ArgumentParser(
        prog="georesistivity",
        description="Apparent resistivity calculation, validation, and export.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subcommands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    app = subcommands.add_parser(
        "app",
        help="start the interface in the browser",
        description="Start the Streamlit interface. It listens on this computer only unless "
        "--lan is given.",
    )
    app.add_argument(
        "--port",
        type=_port,
        default=DEFAULT_PORT,
        help=f"port to listen on (default: {DEFAULT_PORT})",
    )
    app.add_argument(
        "--lan",
        action="store_true",
        help="also accept connections from other devices on the local network, such as a "
        "tablet connected to this computer's hotspot",
    )
    app.add_argument(
        "--no-browser",
        action="store_true",
        help="do not open a browser window automatically",
    )
    app.add_argument(
        "--no-autosave",
        action="store_true",
        help="do not keep autosave copies (for example on a shared server); save project "
        "files instead",
    )
    _add_k_parser(subcommands)
    _add_calc_parser(subcommands)
    _add_plot_parser(subcommands)
    return parser


def streamlit_command(*, port: int, lan: bool, open_browser: bool) -> list[str]:
    """Return the command that starts the interface with Streamlit."""
    return [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(MAIN_SCRIPT),
        "--server.port",
        str(port),
        "--server.address",
        "0.0.0.0" if lan else "localhost",
        "--server.headless",
        "false" if open_browser else "true",
        *_STREAMLIT_SETTINGS,
    ]


def run_app(*, port: int, lan: bool, open_browser: bool, autosave: bool = True) -> int:
    """Start the interface and return Streamlit's exit code."""
    if importlib.util.find_spec("streamlit") is None:
        print(MISSING_STREAMLIT, file=sys.stderr)
        return 1
    if lan:
        print(LAN_WARNING, file=sys.stderr)
    command = streamlit_command(port=port, lan=lan, open_browser=open_browser)
    environment = {**os.environ}
    if not autosave:
        environment[AUTOSAVE_VARIABLE] = "0"
    try:
        return subprocess.call(command, env=environment)
    except KeyboardInterrupt:
        return 130


def _fail(*messages: str) -> int:
    for message in messages:
        print(f"error: {message}", file=sys.stderr)
    return 1


def _length_in_meters(text: str) -> float:
    number_text, unit = split_quantity(text)
    return convert_length_to_meters(parse_number(number_text), unit)


def run_k(
    array: ArrayType, raw_values: dict[GeometryParameter, str], number_format: NumberFormat
) -> int:
    """Print K for one array and return the exit code."""
    values: dict[GeometryParameter, float] = {}
    errors: list[str] = []
    for parameter, raw_value in raw_values.items():
        try:
            values[parameter] = (
                parse_number(raw_value) if parameter == "n" else _length_in_meters(raw_value)
            )
        except ValueError as exc:
            errors.append(f"--{parameter}: {exc}")
    if errors:
        return _fail(*errors)

    try:
        value = geometric_factor(array, values)
    except GeometryError as exc:
        return _fail(f"--{exc.parameter}: {exc.reason}")
    except ValueError as exc:
        return _fail(str(exc))

    print(f"K = {format_full_precision(value, number_format=number_format)} m")
    if (
        array == "schlumberger"
        and schlumberger_spacing_ratio(values["ab2"], values["mn"]) < SCHLUMBERGER_MIN_RATIO
    ):
        print(f"warning: {WARNING_TEXT[MeasurementWarning.SCHLUMBERGER_WIDE_MN]}")
    return 0


def format_k_table(
    ab2_values: Sequence[float],
    mn_values: Sequence[float],
    *,
    show_all: bool,
    digits: int,
    number_format: NumberFormat,
) -> str:
    """Return the Schlumberger K table as aligned text."""

    def number(value: float, significant_digits: int) -> str:
        return format_significant(
            value,
            number_format=number_format,
            significant_digits=significant_digits,
            grouping=False,
        )

    header = ["AB/2 \\ MN", *(number(mn, 12).rstrip("0").rstrip(".,") for mn in mn_values)]
    rows = [header]
    for ab2, k_row in zip(ab2_values, schlumberger_k_table(ab2_values, mn_values), strict=True):
        cells = [number(ab2, 12).rstrip("0").rstrip(".,")]
        for mn, k_value in zip(mn_values, k_row, strict=True):
            if k_value is None:
                cells.append("")
            elif schlumberger_spacing_ratio(ab2, mn) < SCHLUMBERGER_MIN_RATIO:
                cells.append(f"{number(k_value, digits)}*" if show_all else "")
            else:
                cells.append(number(k_value, digits))
        rows.append(cells)

    widths = [max(len(row[column]) for row in rows) for column in range(len(header))]
    lines = [
        "  ".join(cell.rjust(width) for cell, width in zip(row, widths, strict=True)).rstrip()
        for row in rows
    ]
    notes = ["Schlumberger K [m]; AB/2 and MN [m]; MN is the full M-N spacing."]
    if show_all:
        notes.append(f"* (AB/2)/(MN/2) below {SCHLUMBERGER_MIN_RATIO:g}.")
    return "\n".join([*notes, "", *lines])


def run_calc(
    *,
    delta_v: str,
    current: str,
    geometric_factor_text: str | None,
    ab2: str | None,
    mn: str | None,
    source: str,
    number_format: NumberFormat,
) -> int:
    """Print rho_a for one reading and return the exit code."""
    if geometric_factor_text is not None:
        mode: GeometricFactorMode = "external"
    elif ab2 is not None and mn is not None:
        mode = "schlumberger"
    else:
        return _fail("give --k, or --ab2 and --mn to calculate the Schlumberger K")

    raw: dict[MeasurementField, tuple[str, str]] = {}
    errors: list[str] = []
    texts: dict[MeasurementField, str | None] = {
        "delta_v": delta_v,
        "current": current,
        "geometric_factor": geometric_factor_text,
        "spacing_ab2": ab2,
        "mn": mn,
    }
    for field, text in texts.items():
        if text is None:
            continue
        try:
            raw[field] = split_quantity(text)
        except ValueError as exc:
            errors.append(f"{CALC_OPTIONS[field]}: {exc}")
    if errors:
        return _fail(*errors)

    def number(field: MeasurementField) -> str:
        return raw[field][0] if field in raw else ""

    def unit(field: MeasurementField, default: str) -> str:
        return raw[field][1] if field in raw else default

    entry = MeasurementInput(
        delta_v=number("delta_v"),
        voltage_unit=unit("delta_v", "V"),
        current=number("current"),
        current_unit=unit("current", "A"),
        geometric_factor=number("geometric_factor"),
        geometric_factor_unit=unit("geometric_factor", "m"),
        spacing_ab2=number("spacing_ab2"),
        spacing_unit=unit("spacing_ab2", "m"),
        geometric_factor_source=source,
        mn=number("mn"),
        mn_unit=unit("mn", "m"),
        geometric_factor_mode=mode,
    )
    outcome = evaluate_submission(entry, [])
    if outcome.result is None:
        if outcome.error is not None:
            return _fail(outcome.error)
        return _fail(
            *(f"{CALC_OPTIONS[issue.field]}: {issue.message}" for issue in outcome.field_issues)
        )

    result = outcome.result

    def full(value: float) -> str:
        return format_full_precision(value, number_format=number_format)

    k_line = f"K = {full(result.geometric_factor_m)} m"
    if result.measurement.geometric_factor_source is not None:
        k_line += f" ({result.measurement.geometric_factor_source})"
    print(f"rho_a = {full(result.apparent_resistivity_ohm_m)} ohm.m")
    print(k_line)
    for warning in result.warnings:
        print(f"warning: {WARNING_TEXT[warning]}")
    return 0


def _figure_format(output: Path | None, requested: FigureFormat | None) -> FigureFormat:
    """The format from --format and the output name, which must end in .png, .svg, or .pdf."""
    if output is None:
        return requested or "pdf"
    suffix = output.suffix.lower().lstrip(".")
    if suffix not in FIGURE_FORMATS:
        raise ValueError(f"the output name {output.name!r} must end in .png, .svg, or .pdf")
    if requested is not None and requested != suffix:
        raise ValueError(f"the output name ends in .{suffix} but --format is {requested}")
    return suffix


def run_plot(
    *,
    project_path: Path,
    output: Path | None,
    file_format: FigureFormat | None,
    decade_mm: float | None,
    error_bars: bool,
    title_details: bool,
    language: Language,
    number_format: NumberFormat | None,
) -> int:
    """Save the VES curve of a project file and return the exit code."""
    try:
        resolved = _figure_format(output, file_format)
    except ValueError as exc:
        return _fail(str(exc))
    try:
        project = project_from_json(project_path.read_text(encoding="utf-8"))
    except OSError as exc:
        return _fail(f"cannot read {project_path}: {exc.strerror or exc}")
    except ProjectFormatError as exc:
        return _fail(f"{project_path}: {exc}")

    outcome = evaluate_project_sheet(project)
    options = FigureOptions(
        file_format=resolved,
        decade_mm=decade_mm,
        error_bars=error_bars,
        title_with_survey=title_details,
        language=language,
        number_format=number_format or ("pt-BR" if language == "pt-BR" else "en"),
    )
    try:
        data = sounding_figure_file(outcome.points, project.survey, options)
    except ValueError as exc:
        return _fail(f"{project_path}: {exc}")

    target = output or Path(figure_file_name(project.survey, resolved))
    try:
        target.write_bytes(data)
    except OSError as exc:
        return _fail(f"cannot write {target}: {exc.strerror or exc}")

    plotted = sum(1 for point in outcome.points if (point.apparent_resistivity_ohm_m or 0.0) > 0)
    size = ""
    if decade_mm is not None:
        from georesistivity.plotting import sounding_decades

        x_decades, y_decades = sounding_decades(outcome.points, error_bars=error_bars)
        size = (
            f", plot area {x_decades * decade_mm:g} x {y_decades * decade_mm:g} mm "
            f"({x_decades} x {y_decades} decades of {decade_mm:g} mm)"
        )
    positions = "1 position" if plotted == 1 else f"{plotted} positions"
    print(f"wrote {target} ({resolved}, {positions}{size})")
    invalid = len(outcome.invalid_rows)
    if invalid:
        rows = (
            "1 row of the field sheet is"
            if invalid == 1
            else f"{invalid} rows of the field sheet are"
        )
        print(f"warning: {rows} invalid and left out; open the project in the app to see why")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point of the ``georesistivity`` command."""
    args = build_parser().parse_args(argv)
    if args.command == "app":
        return run_app(
            port=args.port,
            lan=args.lan,
            open_browser=not args.no_browser,
            autosave=not args.no_autosave,
        )
    if args.command == "k" and args.array == "table":
        print(
            format_k_table(
                args.ab2,
                args.mn,
                show_all=args.all,
                digits=args.digits,
                number_format=args.number_format,
            )
        )
        return 0
    if args.command == "k":
        parameters = ARRAY_PARAMETERS[args.array]
        raw_values = {parameter: getattr(args, parameter) for parameter in parameters}
        return run_k(args.array, raw_values, args.number_format)
    if args.command == "calc":
        return run_calc(
            delta_v=args.dv,
            current=args.i,
            geometric_factor_text=args.k,
            ab2=args.ab2,
            mn=args.mn,
            source=args.source,
            number_format=args.number_format,
        )
    if args.command == "plot":
        return run_plot(
            project_path=args.project,
            output=args.output,
            file_format=args.format,
            decade_mm=args.decade_mm,
            error_bars=not args.no_error_bars,
            title_details=not args.no_title_details,
            language=args.language,
            number_format=args.number_format,
        )
    raise AssertionError(f"unhandled command: {args.command}")  # pragma: no cover
