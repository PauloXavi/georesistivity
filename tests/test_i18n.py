"""Tests for the text catalogs in Portuguese and English."""

import string

import pytest

from georesistivity.i18n import LANGUAGES, PROBLEMS, TEXTS, text_in
from georesistivity.messages import EN, Problem


def placeholders(template: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


def test_languages_are_portuguese_and_english() -> None:
    assert list(LANGUAGES) == ["pt-BR", "en"]


def test_both_interface_catalogs_have_the_same_keys() -> None:
    assert set(TEXTS["pt-BR"]) == set(TEXTS["en"])


@pytest.mark.parametrize("key", sorted(TEXTS["en"]))
def test_interface_texts_use_the_same_placeholders(key: str) -> None:
    assert placeholders(TEXTS["pt-BR"][key]) == placeholders(TEXTS["en"][key])


def test_every_core_message_is_translated() -> None:
    assert set(PROBLEMS["pt-BR"]) == set(EN)


@pytest.mark.parametrize("code", sorted(EN))
def test_core_messages_use_the_same_placeholders(code: str) -> None:
    assert placeholders(PROBLEMS["pt-BR"][code]) == placeholders(EN[code])


def test_every_counted_text_has_one_and_other_forms() -> None:
    for catalog in TEXTS.values():
        stems = {key.rsplit(".", 1)[0] for key in catalog if key.endswith((".one", ".other"))}
        for stem in stems:
            assert {f"{stem}.one", f"{stem}.other"} <= set(catalog)


def test_texts_and_problems_render_in_both_languages() -> None:
    assert text_in("pt-BR", "form.added", number=3) == "Medição nº 3 adicionada."
    assert text_in("en", "form.added", number=3) == "Measurement #3 added."
    problem = Problem("number.ambiguous", {"value": "1,000", "separator": ",", "integer": "1000",
                                           "decimal": "1,0000"})  # fmt: skip
    assert problem.text(PROBLEMS["pt-BR"]).startswith("valor ambíguo '1,000'")
