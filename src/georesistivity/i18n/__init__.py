"""Texts for people, in Brazilian Portuguese (default) and English.

Texts are looked up by key in Python catalogs (``pt_br.py`` and ``en.py``); a test checks
that both catalogs have the same keys and placeholders. Errors of the scientific core are
translated by their message code (:class:`georesistivity.messages.Problem`), never by their
English text. This package does not import Streamlit, so the command line and the reports use
the same texts as the interface (``georesistivity.app.i18n``). CSV headers and project files
stay in English, so files are the same whatever the language.
"""

from typing import Literal

from georesistivity.i18n import en, pt_br
from georesistivity.messages import EN as EN_PROBLEMS

Language = Literal["pt-BR", "en"]
DEFAULT_LANGUAGE: Language = "pt-BR"
LANGUAGES: dict[Language, str] = {"pt-BR": "Português (Brasil)", "en": "English"}

TEXTS: dict[Language, dict[str, str]] = {"pt-BR": pt_br.TEXT, "en": en.TEXT}
PROBLEMS: dict[Language, dict[str, str]] = {"pt-BR": pt_br.PROBLEMS, "en": EN_PROBLEMS}


def text_in(language: Language, key: str, **params: object) -> str:
    """The text of ``key`` in ``language``, with its placeholders filled in."""
    return TEXTS[language][key].format(**params)
