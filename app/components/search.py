"""Global cross-page search: one search box, results from every entity type.

The index is built from data the pages already fetch (streamers, categories,
stream titles, emotes, chatters) — all `st.cache_data`-cached, so building it
here doesn't add any database load beyond what's already happening.
"""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from app.core.i18n import t
from app.data.repository import (
    get_category_breakdown,
    get_chatter_breakdown,
    get_event_bounds,
    get_streamer_breakdown,
    get_title_leaderboard,
    get_top_emotes,
)


@dataclass(frozen=True)
class SearchResult:
    """One matchable entity in the global search index."""

    label: str
    entity_type: str
    page: str
    icon: str


def _build_index() -> list[SearchResult]:
    """Assemble the searchable index from every page's already-cached data.

    Always indexes the *full* event span, regardless of the sidebar date
    filter — search is for jumping to a page, not itself a filtered view.

    Returns:
        A flat list of `SearchResult`, one per streamer/category/title/emote/chatter.
    """
    results: list[SearchResult] = []
    bounds = get_event_bounds()
    if bounds is None:
        return results
    start, end = bounds

    streamers = get_streamer_breakdown()
    if not streamers.is_empty():
        results += [
            SearchResult(name, t("search.type.streamer"), "pages/2_🎙️_Streamers.py", "🎙️")
            for name in streamers["streamer"].drop_nulls().unique()
        ]

    categories = get_category_breakdown(start, end)
    if not categories.is_empty():
        results += [
            SearchResult(cat, t("search.type.category"), "pages/3_🎮_Games.py", "🎮")
            for cat in categories["category"].drop_nulls().unique()
        ]

    titles = get_title_leaderboard(start, end)
    if not titles.is_empty():
        results += [
            SearchResult(title, t("search.type.title"), "pages/3_🎮_Games.py", "🎮")
            for title in titles["title"].drop_nulls().unique()
        ]

    emotes = get_top_emotes(start, end)
    if not emotes.is_empty():
        results += [
            SearchResult(emote, t("search.type.emote"), "pages/5_💬_Live_Chat.py", "💬")
            for emote in emotes["emote"].drop_nulls().unique()
        ]

    chatters = get_chatter_breakdown(start, end)
    if not chatters.is_empty() and "chatter" in chatters.columns:
        results += [
            SearchResult(name, t("search.type.chatter"), "pages/8_🗣️_Chatters.py", "🗣️")
            for name in chatters["chatter"].drop_nulls().unique()
        ]

    return results


def render_global_search() -> None:
    """Render the sidebar search box and, if there's a query, its results.

    Selecting a result stores it in `st.session_state["global_search_query"]`
    so the destination page can pre-fill its own local filter/search widget —
    session state persists across page navigation in the same browser session.
    """
    query = st.text_input(
        t("search.label"),
        key="_global_search_input",
        placeholder=t("search.placeholder"),
    )
    if not query:
        return

    index = _build_index()
    if not index:
        return

    query_lower = query.lower()
    matches = [r for r in index if query_lower in r.label.lower()]
    if not matches:
        st.caption(t("search.no_results", query=query))
        return

    seen: set[tuple[str, str]] = set()
    with st.container(border=True):
        for result in matches[:10]:
            key = (result.label, result.entity_type)
            if key in seen:
                continue
            seen.add(key)
            col_link, col_type = st.columns([3, 1])
            with col_link:
                if st.button(
                    f"{result.icon} {result.label}", key=f"search_{result.page}_{result.label}"
                ):
                    st.session_state["global_search_query"] = result.label
                    st.switch_page(result.page)
            with col_type:
                st.caption(result.entity_type)
        if len(matches) > 10:
            st.caption(t("search.more_results", count=len(matches) - 10))


def consume_search_query() -> str:
    """Pop and return a search query set by a global-search result click, if any.

    Call once near the top of a page's own search/filter widget so a click
    from the global search pre-fills it exactly once, without re-forcing the
    value on every later rerun (which would prevent the user from clearing it).

    Returns:
        The pending query string, or `""` if none is pending.
    """
    return st.session_state.pop("global_search_query", "")
