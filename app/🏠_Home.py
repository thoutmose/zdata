"""ZEvent Dataviz — Streamlit entrypoint: router + landing page.

Run with `uv run streamlit run app/🏠_Home.py`.

Uses `st.navigation()` with explicit `st.Page(..., title=t(...))` objects
rather than the classic `pages/` filename auto-discovery: the sidebar nav
labels need to be recomputed in the current language on every render, and
filename-derived labels can't do that — they're fixed at parse time,
regardless of `st.session_state["lang"]`. `language_selector()` runs here,
once, before the pages are declared, so a language switch takes effect
immediately, including in the nav itself.

`render_global_search()` also runs here, once, in the sidebar — this file's
top-level code re-executes on every page view (Streamlit always runs the
entrypoint script before handing off to the selected page), so a single call
here is enough to put the search box above the nav links on every page,
without every individual page module needing to render its own copy.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import cast

import streamlit as st

from app.components.search import render_global_search
from app.components.theme import inject_global_css
from app.core.config import get_settings
from app.core.db import check_connection
from app.core.i18n import language_selector, t
from app.core.logging_config import setup_logging
from app.data.repository import (
    get_chat_activity_timeseries,
    get_chatter_breakdown,
    get_donation_timeseries,
    get_streamer_breakdown,
    get_viewership_timeseries,
)

setup_logging()
logger = logging.getLogger(__name__)

_FAVICON = Path(__file__).parent / "static" / "favicon.png"

st.set_page_config(
    page_title="ZEvent Dataviz",
    page_icon=str(_FAVICON) if _FAVICON.exists() else "🎮",
    layout="wide",
    menu_items={
        "About": "ZEvent Dataviz — data-modeling dashboards for the ZEvent charity marathon."
    },
)

language_selector()
with st.sidebar:
    render_global_search()


def _render_home() -> None:
    """Render the landing page: hero image, status, about text, and page cards."""
    inject_global_css()
    settings = get_settings()

    st.image(
        "https://www.lpo.fr/var/site/storage/images/_aliases/detailed_content/9/7/5/0/1910579-1-fre-FR/ZEvent%202026.jpg",
        width="stretch",
    )

    st.title(f"🎮 {t('home.title')}")
    st.caption(t("home.tagline"))

    if settings.use_mock_data:
        st.info(t("common.mock_data_banner"), icon="🧪")
    elif not check_connection():
        st.error(t("home.db_error"), icon="🚨")

    st.subheader(t("home.kpi_heading"))
    donations = get_donation_timeseries()
    streamers = get_streamer_breakdown()
    chatters = get_chatter_breakdown()
    chat_activity = get_chat_activity_timeseries()
    viewership = get_viewership_timeseries()

    if not donations.is_empty():
        max_ts = cast(datetime, donations["timestamp"].max())
        min_ts = cast(datetime, donations["timestamp"].min())
        span_hours = (max_ts - min_ts).total_seconds() / 3600
        duration_display = t("home.kpi.duration_value", hours=f"{span_hours:,.0f}")
    else:
        duration_display = "—"

    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    kpi1.metric(t("home.kpi.duration"), duration_display)
    kpi2.metric(t("home.kpi.streamers"), f"{len(streamers):,}" if not streamers.is_empty() else "—")
    kpi3.metric(t("home.kpi.chatters"), f"{len(chatters):,}" if not chatters.is_empty() else "—")
    kpi4.metric(
        t("home.kpi.messages"),
        f"{chat_activity['message_count'].sum():,.0f}" if not chat_activity.is_empty() else "—",
    )
    kpi5.metric(
        t("home.kpi.peak_viewers"),
        f"{viewership['total_avg_viewer_count'].max():,.0f}" if not viewership.is_empty() else "—",
    )

    st.markdown(t("home.about_body"))

    st.divider()
    st.subheader(t("home.pages_heading"))

    page_cards = [
        (donations_page, "donations.description"),
        (streamers_page, "streamers.description"),
        (games_page, "games.description"),
        (goals_page, "goals.description"),
        (chat_page, "chat.description"),
        (community_page, "community.description"),
        (chatters_page, "chatters.description"),
        (tracker_page, "tracker.description"),
        (activity_page, "activity.description"),
    ]
    for row_start in range(0, len(page_cards), 3):
        row = st.columns(3)
        for col, (page, desc_key) in zip(row, page_cards[row_start : row_start + 3], strict=False):
            with col:
                st.page_link(page, label=page.title, icon=page.icon)
                st.write(t(desc_key))

    st.divider()
    st.markdown(t("home.related_projects"))

    logger.info("Home page rendered (use_mock_data=%s)", settings.use_mock_data)


home_page = st.Page(_render_home, title=t("home.title"), icon="🏠", default=True, url_path="home")
donations_page = st.Page("pages/1_📈_Donations.py", title=t("donations.title"), icon="📈")
streamers_page = st.Page("pages/2_🎙️_Streamers.py", title=t("streamers.title"), icon="🎙️")
games_page = st.Page("pages/3_🎮_Games.py", title=t("games.title"), icon="🎮")
goals_page = st.Page("pages/4_🎯_Donation_Goals.py", title=t("goals.title"), icon="🎯")
chat_page = st.Page("pages/5_💬_Live_Chat.py", title=t("chat.title"), icon="💬")
community_page = st.Page("pages/6_👥_Community.py", title=t("community.title"), icon="👥")
tracker_page = st.Page("pages/7_🏆_Donation_Tracker.py", title=t("tracker.title"), icon="🏆")
chatters_page = st.Page("pages/8_🗣️_Chatters.py", title=t("chatters.title"), icon="🗣️")
activity_page = st.Page("pages/9_📺_Activity.py", title=t("activity.title"), icon="📺")

navigation = st.navigation(
    [
        home_page,
        donations_page,
        streamers_page,
        games_page,
        goals_page,
        chat_page,
        community_page,
        chatters_page,
        tracker_page,
        activity_page,
    ]
)
navigation.run()
