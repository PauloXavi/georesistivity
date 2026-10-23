"""Interface texts in Brazilian Portuguese (default) and English.

Texts are looked up by key in Python catalogs (``pt_br.py`` and ``en.py``); a test checks
that both catalogs have the same keys and placeholders. Errors of the scientific core are
translated by their message code (:class:`georesistivity.messages.Problem`), never by their
English text. CSV headers and project files stay in English, so files are the same whatever
the interface language.
"""

from collections.abc import Callable
from typing import Literal, cast

import streamlit as st

from georesistivity.app.i18n import en, pt_br
from georesistivity.messages import EN as EN_PROBLEMS
from georesistivity.messages import Problem, problem_of

Language = Literal["pt-BR", "en"]
DEFAULT_LANGUAGE: Language = "pt-BR"
LANGUAGES: dict[Language, str] = {"pt-BR": "Português (Brasil)", "en": "English"}
LANGUAGE_KEY = "language"

TEXTS: dict[Language, dict[str, str]] = {"pt-BR": pt_br.TEXT, "en": en.TEXT}
PROBLEMS: dict[Language, dict[str, str]] = {"pt-BR": pt_br.PROBLEMS, "en": EN_PROBLEMS}


def current_language() -> Language:
    """Language selected in this session (Portuguese by default)."""
    value = st.session_state.get(LANGUAGE_KEY, DEFAULT_LANGUAGE)
    return cast(Language, value) if value in LANGUAGES else DEFAULT_LANGUAGE


def text_in(language: Language, key: str, **params: object) -> str:
    """The text of ``key`` in ``language``, with its placeholders filled in."""
    return TEXTS[language][key].format(**params)


def t(key: str, **params: object) -> str:
    """The text of ``key`` in the current language."""
    return text_in(current_language(), key, **params)


def translator() -> Callable[..., str]:
    """``t`` bound to the language of this run.

    Use it in ``format_func`` callbacks: Streamlit may call them outside the script run, where
    the session language cannot be read.
    """
    language = current_language()

    def translate(key: str, **params: object) -> str:
        return text_in(language, key, **params)

    return translate


def count(key: str, n: int) -> str:
    """``1 linha`` / ``2 linhas``: the count with the right form, in the current language."""
    return t(f"{key}.{'one' if n == 1 else 'other'}", n=n)


def t_for(n: int, key: str, **params: object) -> str:
    """The singular (``key.one``) or plural (``key.other``) form of a sentence about ``n``."""
    return t(f"{key}.{'one' if n == 1 else 'other'}", **params)


def problem_text(problem: Problem | None, fallback: str = "") -> str:
    """A core problem in the current language (``fallback`` when there is none)."""
    if problem is None:
        return fallback
    return problem.text(PROBLEMS[current_language()])


def error_text(error: BaseException) -> str:
    """An exception in the current language, keeping a JSON path when there is one."""
    message = problem_text(problem_of(error))
    path = getattr(error, "path", "")
    return f"{path}: {message}" if isinstance(path, str) and path else message
