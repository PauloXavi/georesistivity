"""Command-line interface: ``georesistivity``."""

import argparse
import importlib.util
import subprocess
import sys
from collections.abc import Sequence

from georesistivity import __version__
from georesistivity.app import MAIN_SCRIPT

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


def run_app(*, port: int, lan: bool, open_browser: bool) -> int:
    """Start the interface and return Streamlit's exit code."""
    if importlib.util.find_spec("streamlit") is None:
        print(MISSING_STREAMLIT, file=sys.stderr)
        return 1
    if lan:
        print(LAN_WARNING, file=sys.stderr)
    command = streamlit_command(port=port, lan=lan, open_browser=open_browser)
    try:
        return subprocess.call(command)
    except KeyboardInterrupt:
        return 130


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point of the ``georesistivity`` command."""
    args = build_parser().parse_args(argv)
    if args.command == "app":
        return run_app(port=args.port, lan=args.lan, open_browser=not args.no_browser)
    raise AssertionError(f"unhandled command: {args.command}")  # pragma: no cover
