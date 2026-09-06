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

from importlib.metadata import PackageNotFoundError, version

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


def bounded_top_n_slider(*, label: str, max_value: int, key: str, default_n: int = 15) -> int:
    """Render a "top N" slider whose upper bound can change across reruns.

    A stable `key` with a stored value that no longer fits a *new*
    `max_value` (e.g. toggling "hide likely bots" or switching the ranking
    metric changes how many rows are even available) crashes rather than
    clamping. Reset only when the stored value no longer fits, so a
    still-valid choice survives across reruns instead of jumping back to the
    default every time.

    Args:
        label: Slider label (already translated by the caller).
        max_value: This rerun's upper bound (rows/channels available to
            rank). With `min_value` fixed at 1, `st.slider` requires
            `max_value` to be strictly greater than 1 — an empty ranking (0)
            or a single eligible row (1, e.g. the global streamer filter
            narrowed to one streamer) would otherwise raise
            `StreamlitInvalidMinMaxError`. There's nothing to *pick* a top-N
            of in either case, so the slider is skipped and `max_value`
            returned as-is.
        key: Unique Streamlit widget key.
        default_n: Preferred default when there's no stored value yet.

    Returns:
        The chosen top-N value.
    """
    if max_value <= 1:
        return max_value
    default = min(default_n, max_value)
    if key not in st.session_state or not (1 <= st.session_state[key] <= max_value):
        st.session_state[key] = default
    return st.slider(label, min_value=1, max_value=max_value, key=key)


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


def date_filter_caveat() -> None:
    """Note that the section right below isn't affected by the sidebar date filter.

    Call once per unaffected section — right after its own subheader, not
    "once per page covering everything below" — since some pages interleave
    sections that do respond to the filter with ones (pre-aggregated,
    event-wide data with no per-row timestamp) that can't. The section may
    still be narrowed by the streamer/chatter filters — see
    `entity_filter_caveat` for sections where those don't apply either.
    """
    st.caption(t("common.date_filter_caveat"))


def entity_filter_caveat() -> None:
    """Note that the section right below isn't affected by the streamer/chatter filters.

    For sections whose data has no per-row `channel`/`chatter_id` at all
    (e.g. a bare category or profile aggregate) — narrower than
    `date_filter_caveat`, which most affected sections also need since a
    mart with no per-row timestamp very often still has an identity column
    the streamer/chatter filters *can* use. Call both together for a
    section with neither.
    """
    st.caption(t("common.entity_filter_caveat"))


def data_source_banner() -> None:
    """Show a visible banner when the page is serving sample data, not the real database.

    Being explicit about mock data prevents anyone from mistaking sample
    figures for real ZEvent numbers before the database is connected.
    """
    settings = get_settings()
    if settings.use_mock_data:
        st.info(t("common.mock_data_banner"), icon="🧪")


def page_footer() -> None:
    """Render the standard footer at the bottom of every page.

    Deliberately part of each page's own scrollable content, not a bar
    pinned to the browser viewport — Streamlit has no public API for a true
    sticky footer, and faking one means injecting CSS against Streamlit's
    internal DOM classes, which aren't a stable contract across versions
    (the same reason `inject_global_css` sticks to documented theming
    hooks). Call once, as the last thing on the page.

    Centered via `st.container(horizontal_alignment="center")` — a public,
    documented layout option — rather than a CSS `text-align` override, for
    the same "don't depend on undocumented internals" reason.
    """
    st.divider()
    try:
        app_version = version("zevent-dataviz")
    except PackageNotFoundError:
        app_version = "dev"
    with st.container(horizontal_alignment="center"):
        st.caption(t("common.footer", version=app_version))
