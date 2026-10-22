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


def run(capsys: pytest.CaptureFixture[str], *arguments: str) -> tuple[int, str, str]:
    code = cli.main(list(arguments))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        (("schlumberger", "--ab2", "20m", "--mn", "2m"), "K = 626,747734391 m"),
        (("schlumberger", "--ab2", "2000cm", "--mn", "0,002km"), "K = 626,747734391 m"),
        (("wenner", "--a", "10m", "--number-format", "en"), "K = 62.8318530718 m"),
        (("dipole-dipole", "--a", "10m", "--n", "2"), "K = 753,982236862 m"),
        (("pole-dipole", "--a", "10m", "--n", "2"), "K = 376,991118431 m"),
        (
            ("general", "--am", "4m", "--bm", "6m", "--an", "6m", "--bn", "4m"),
            "K = 37,6991118431 m",
        ),
    ],
)
def test_k_command(
    capsys: pytest.CaptureFixture[str],
    arguments: tuple[str, ...],
    expected: str,
) -> None:
    code, out, err = run(capsys, "k", *arguments)

    assert code == 0
    assert out.splitlines() == [expected]
    assert err == ""


def test_k_command_warns_about_wide_mn(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys, "k", "schlumberger", "--ab2", "1m", "--mn", "0,8m")

    assert code == 0
    assert "warning: MN is wide" in out


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (("schlumberger", "--ab2", "1m", "--mn", "3m"), "--mn: MN/2 must be smaller than AB/2"),
        (("schlumberger", "--ab2", "20", "--mn", "2m"), "--ab2: missing unit"),
        (("wenner", "--a", "1,000m"), "--a: ambiguous value"),
        (("dipole-dipole", "--a", "10ft", "--n", "x"), "--a: unsupported length unit"),
        (("wenner", "--a", "1e308m"), "error: geometric factor is too large"),
    ],
)
def test_k_command_errors(
    capsys: pytest.CaptureFixture[str],
    arguments: tuple[str, ...],
    message: str,
) -> None:
    code, out, err = run(capsys, "k", *arguments)

    assert code == 1
    assert out == ""
    assert message in err


def test_k_command_reports_every_invalid_parameter(capsys: pytest.CaptureFixture[str]) -> None:
    _, _, err = run(capsys, "k", "dipole-dipole", "--a", "10ft", "--n", "x")

    assert err.count("error:") == 2


def test_k_table_reproduces_the_field_sheet(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys, "k", "table")
    lines = out.splitlines()

    assert code == 0
    assert lines[2].split() == ["AB/2", "\\", "MN", "0,5", "2", "5", "20", "50", "100"]
    rows = {line.split()[0]: line.split()[1:] for line in lines[3:]}
    assert len(rows) == 21
    assert rows["1"] == ["5,8905"]
    assert rows["18"] == ["2035,4", "507,37", "199,65"]
    assert rows["240"] == ["361910", "90476", "36187", "9032,1", "3579,8", "1731,0"]


def test_k_table_marks_wide_mn_only_with_all(capsys: pytest.CaptureFixture[str]) -> None:
    _, default, _ = run(capsys, "k", "table", "--ab2", "1,3", "--mn", "0,5", "2")
    _, everything, _ = run(
        capsys, "k", "table", "--ab2", "1,3", "--mn", "0,5", "2", "--all", "--number-format", "en"
    )

    assert default.splitlines()[-1].split() == ["1,3", "10,226"]
    assert everything.splitlines()[-1].split() == ["1.3", "10.226", "1.0838*"]
    assert "* (AB/2)/(MN/2) below 4." in everything


def test_k_table_rejects_invalid_numbers(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        cli.main(["k", "table", "--ab2", "1,000"])

    assert "ambiguous" in capsys.readouterr().err


def test_calc_with_typed_k(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys, "calc", "--dv", "125mV", "--i", "35mA", "--k", "625m")

    assert code == 0
    assert out.splitlines() == ["rho_a = 2232,14285714 ohm.m", "K = 625 m"]


def test_calc_with_schlumberger_geometry(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(
        capsys, "calc", "--dv", "125mV", "--i", "35mA", "--ab2", "20m", "--mn", "2m",
        "--number-format", "en",
    )  # fmt: skip

    assert code == 0
    assert out.splitlines() == [
        "rho_a = 2238.38476568 ohm.m",
        "K = 626.747734391 m (calculated: schlumberger (AB/2 = 20 m, MN = 2 m))",
    ]


def test_calc_records_typed_k_source(capsys: pytest.CaptureFixture[str]) -> None:
    _, out, _ = run(
        capsys, "calc", "--dv", "1V", "--i", "1A", "--k", "5m", "--source", "field sheet"
    )

    assert out.splitlines()[1] == "K = 5 m (field sheet)"


def test_calc_warns_about_negative_rho_a(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys, "calc", "--dv=-125mV", "--i", "35mA", "--k", "625m")

    assert code == 0
    assert out.splitlines()[0] == "rho_a = -2232,14285714 ohm.m"
    assert "warning: negative apparent resistivity" in out


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (("--dv", "125mV", "--i", "35mA"), "give --k, or --ab2 and --mn"),
        (("--dv", "125mV", "--i", "35mA", "--ab2", "20m"), "give --k, or --ab2 and --mn"),
        (("--dv", "125", "--i", "35mA", "--k", "625m"), "--dv: missing unit"),
        (("--dv", "125mV", "--i", "0mA", "--k", "625m"), "--i: cannot be zero"),
        (("--dv", "125mV", "--i", "35mA", "--k", "1,000m"), "--k: ambiguous value"),
        (("--dv", "125mV", "--i", "35mA", "--ab2", "1m", "--mn", "3m"), "--mn: MN/2 must be"),
        (("--dv", "1e306V", "--i", "1e-306A", "--k", "5m"), "error: apparent resistivity"),
    ],
)
def test_calc_errors(
    capsys: pytest.CaptureFixture[str],
    arguments: tuple[str, ...],
    message: str,
) -> None:
    code, out, err = run(capsys, "calc", *arguments)

    assert code == 1
    assert out == ""
    assert message in err
