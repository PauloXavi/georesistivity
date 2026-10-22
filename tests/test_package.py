"""Tests for the public package surface."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

import georesistivity


def test_version_is_exposed() -> None:
    assert georesistivity.__version__ == "0.2.0"


def test_every_public_name_resolves() -> None:
    for name in georesistivity.__all__:
        assert getattr(georesistivity, name) is not None


def test_unknown_attribute_raises_attribute_error() -> None:
    with pytest.raises(AttributeError, match="no attribute 'missing'"):
        _ = georesistivity.missing  # type: ignore[attr-defined]


def test_public_names_are_listed_by_dir() -> None:
    assert set(georesistivity.__all__) <= set(dir(georesistivity))


def test_core_import_does_not_load_pandas_or_matplotlib() -> None:
    code = (
        "import sys, georesistivity; "
        "from georesistivity import calculate_measurement, parse_number; "
        "print(sorted(m for m in ('pandas', 'matplotlib', 'streamlit') if m in sys.modules))"
    )
    source_dir = Path(__file__).resolve().parents[1] / "src"
    environment = {**os.environ, "PYTHONPATH": str(source_dir)}
    output = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    ).stdout

    assert output.strip() == "[]"
