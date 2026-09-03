"""Shared page chrome: header and data-source banner.

The language selector and the global search box both live solely in
`app/🏠_Home.py` (the router), not here — they must run once, before
`st.navigation()` declares the pages, so a language switch is reflected in
the nav labels too, and so the search box sits in the sidebar above the nav
links on every page. Calling either again per-page would also register a
second `key="lang"` / `key="_global_search_input"` widget in the same
render, which Streamlit rejects as a duplicate.
"""

from __future__ import annotations

import streamlit as st

from app.components.theme import inject_global_css
from app.core.config import get_settings
from app.core.i18n import t


def page_header(title: str, icon: str, description: str) -> None:
    """Render the standard title block used at the top of every page.

    Args:
        title: Page title (already translated by the caller).
        icon: A single emoji used as the page icon.
        description: One or two sentences describing what the page shows
            (already translated by the caller).
    """
    inject_global_css()
    st.title(f"{icon} {title}")
    st.caption(description)
    data_source_banner()
    st.divider()


def chart_explainer(text: str) -> None:
    """Render a collapsed "how to read this chart" note right under a chart.

    Collapsed by default so it doesn't compete with the chart itself, but a
    click away for anyone unsure how to read it — every chart in the app gets
    one of these rather than relying on a chart title alone.

    Args:
        text: Explanation text (already translated by the caller).
    """
    with st.expander(t("common.how_to_read"), expanded=False):
        st.caption(text)


def data_source_banner() -> None:
    """Show a visible banner when the page is serving sample data, not the real database.

    Being explicit about mock data prevents anyone from mistaking sample
    figures for real ZEvent numbers before the database is connected.
    """
    settings = get_settings()
    if settings.use_mock_data:
        st.info(t("common.mock_data_banner"), icon="🧪")
