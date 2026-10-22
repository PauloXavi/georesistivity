"""Tests for the ``georesistivity`` command line."""

import runpy
import subprocess
import sys

import pytest

from georesistivity import __version__, cli
from georesistivity.app import MAIN_SCRIPT


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--version"])

    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"georesistivity {__version__}"


def test_a_command_is_required(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        cli.main([])

    assert exit_info.value.code == 2
    assert "required" in capsys.readouterr().err


@pytest.mark.parametrize("port", ["0", "65536", "http"])
def test_invalid_port_is_rejected(port: str, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        cli.main(["app", "--port", port])

    assert "--port" in capsys.readouterr().err


def test_app_listens_on_this_computer_only_by_default() -> None:
    command = cli.streamlit_command(port=8501, lan=False, open_browser=True)

    assert command[:5] == [sys.executable, "-m", "streamlit", "run", str(MAIN_SCRIPT)]
    assert _option(command, "--server.address") == "localhost"
    assert _option(command, "--server.port") == "8501"
    assert _option(command, "--server.headless") == "false"
    assert _option(command, "--browser.gatherUsageStats") == "false"
    assert _option(command, "--client.toolbarMode") == "viewer"
    assert _option(command, "--server.fileWatcherType") == "none"


def test_lan_mode_listens_on_all_interfaces() -> None:
    command = cli.streamlit_command(port=9000, lan=True, open_browser=False)

    assert _option(command, "--server.address") == "0.0.0.0"
    assert _option(command, "--server.port") == "9000"
    assert _option(command, "--server.headless") == "true"


def test_main_script_exists() -> None:
    assert MAIN_SCRIPT.is_file()


def test_app_command_runs_streamlit(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[list[str]] = []

    def fake_call(command: list[str]) -> int:
        calls.append(command)
        return 0

    monkeypatch.setattr(subprocess, "call", fake_call)

    assert cli.main(["app", "--lan", "--port", "8600", "--no-browser"]) == 0
    assert calls == [cli.streamlit_command(port=8600, lan=True, open_browser=False)]
    assert "LAN mode" in capsys.readouterr().err


def test_app_command_without_streamlit_explains_the_extra(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli.importlib.util, "find_spec", lambda name: None)

    assert cli.main(["app"]) == 1
    assert "georesistivity[app]" in capsys.readouterr().err


def test_interrupting_the_app_exits_cleanly(monkeypatch: pytest.MonkeyPatch) -> None:
    def interrupted(command: list[str]) -> int:
        raise KeyboardInterrupt

    monkeypatch.setattr(subprocess, "call", interrupted)

    assert cli.main(["app"]) == 130


def _option(command: list[str], name: str) -> str:
    return command[command.index(name) + 1]


def test_python_dash_m_entry_point(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["georesistivity", "--version"])

    with pytest.raises(SystemExit) as exit_info:
        runpy.run_module("georesistivity", run_name="__main__")

    assert exit_info.value.code == 0
    assert __version__ in capsys.readouterr().out
