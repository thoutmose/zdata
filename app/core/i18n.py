"""Minimal i18n: a flat translation dict keyed by dotted string keys.

`t("donations.kpi.total_raised")` looks up the current language's string,
falling back to English and then to the raw key if a translation is missing
— so a missing key degrades to visible-but-ugly rather than crashing a page.

The language choice lives in `st.session_state["lang"]` (persists across
reruns and page navigation for the session) and is rendered once, in the
sidebar, by `language_selector()`.
"""

from __future__ import annotations

import streamlit as st

from app.core.translations import TRANSLATIONS

_DEFAULT_LANG = "en"
_LANGUAGES = {"en": "English", "fr": "Français"}


def get_language() -> str:
    """Return the current session's language code.

    Returns:
        `"en"` or `"fr"`.
    """
    return st.session_state.get("lang", _DEFAULT_LANG)


def language_selector() -> None:
    """Render the language picker in the sidebar.

    Call once per page (idempotent — it just re-renders the same widget,
    bound to the same session-state key, on every rerun).
    """
    if "lang" not in st.session_state:
        st.session_state["lang"] = _DEFAULT_LANG
    st.sidebar.selectbox(
        "🌐 Language / Langue",
        options=list(_LANGUAGES.keys()),
        format_func=lambda code: _LANGUAGES[code],
        key="lang",
    )


def t(key: str, **kwargs: object) -> str:
    """Translate a key into the current session's language.

    Args:
        key: Dotted translation key, e.g. `"donations.kpi.total_raised"`.
        **kwargs: Values to interpolate into the string via `str.format`.

    Returns:
        The translated (and formatted) string. Falls back to the English
        string, then to the raw key, if no translation is found.
    """
    lang = get_language()
    text = TRANSLATIONS.get(lang, {}).get(key) or TRANSLATIONS["en"].get(key, key)
    return text.format(**kwargs) if kwargs else text
