"""Interface texts in the language selected in the Streamlit session.

The catalogs and the language list live in :mod:`georesistivity.i18n`, which does not import
Streamlit; this module adds the session language and the helpers used by the pages.
"""

from collections.abc import Callable
from typing import cast

import streamlit as st

from georesistivity.i18n import (
    DEFAULT_LANGUAGE,
    LANGUAGES,
    PROBLEMS,
    TEXTS,
    Language,
    text_in,
)
from georesistivity.messages import Problem, problem_of

__all__ = [
    "DEFAULT_LANGUAGE",
    "LANGUAGES",
    "LANGUAGE_KEY",
    "PROBLEMS",
    "TEXTS",
    "Language",
    "count",
    "current_language",
    "error_text",
    "problem_text",
    "t",
    "t_for",
    "text_in",
    "translator",
]

LANGUAGE_KEY = "language"


def current_language() -> Language:
    """Language selected in this session (Portuguese by default)."""
    value = st.session_state.get(LANGUAGE_KEY, DEFAULT_LANGUAGE)
    return cast(Language, value) if value in LANGUAGES else DEFAULT_LANGUAGE


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
