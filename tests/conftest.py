"""Shared test configuration."""

from pathlib import Path

import pytest

from georesistivity.storage import AUTOSAVE_VARIABLE, HOME_VARIABLE


@pytest.fixture(autouse=True)
def isolated_data_home(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Keep autosave copies and templates of every test out of the user's real folder."""
    home = tmp_path_factory.mktemp("georesistivity_home")
    monkeypatch.setenv(HOME_VARIABLE, str(home))
    monkeypatch.delenv(AUTOSAVE_VARIABLE, raising=False)
    return home
