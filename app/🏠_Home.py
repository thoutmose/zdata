"""ZData — Streamlit entrypoint: router + landing page.

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

import plotly.graph_objects as go
import polars as pl
import streamlit as st

from app.components.chrome import (
    chart_explainer,
    date_filter_caveat,
    entity_filter_caveat,
    page_footer,
)
from app.components.filters import (
    apply_global_streamer_filter,
    get_global_chatter_filter,
    get_global_date_range,
    render_global_date_filter,
    render_global_entity_filters,
    render_global_streamer_scope,
)
from app.components.search import render_global_search
from app.components.theme import CATEGORICAL, apply_base_layout, inject_global_css
from app.core.config import get_settings
from app.core.db import check_connection
from app.core.i18n import language_selector, t
from app.core.logging_config import setup_logging
from app.data.repository import (
    get_chat_activity_timeseries,
    get_chatter_count,
    get_donation_timeseries,
    get_event_bounds,
    get_event_daily_rollup,
    get_schema_table_stats,
    get_streamer_breakdown,
    get_viewership_timeseries,
)

setup_logging()
logger = logging.getLogger(__name__)

_FAVICON = Path(__file__).parent / "static" / "favicon.png"

_APP_PAGE_COUNT = 14


def _format_bytes(n: int | None) -> str:
    """Format a byte count as a human-readable size (e.g. "1.9 GB"), or "—" if unknown."""
    if n is None:
        return "—"
    value = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:,.0f} {unit}" if unit == "B" else f"{value:,.1f} {unit}"
        value /= 1024
    return f"{value:,.1f} TB"

st.set_page_config(
    page_title="ZData",
    page_icon=str(_FAVICON) if _FAVICON.exists() else "🎮",
    layout="wide",
    menu_items={
        "About": "ZData — data-modeling dashboards for the ZEvent charity marathon."
    },
)

language_selector()
with st.sidebar:
    render_global_search()
    render_global_date_filter()
    render_global_streamer_scope()
    render_global_entity_filters()


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
    streamers = apply_global_streamer_filter(get_streamer_breakdown())
    date_range = get_global_date_range() or get_event_bounds()
    # An explicit chatter pick in the sidebar is exactly how many chatters
    # to count — no query needed. Otherwise, count active chatters directly
    # rather than fetching all ~416,000 rows of the full per-chatter
    # breakdown just to call `len()` on it: confirmed directly, that cost
    # ~4.9s for a number nobody looks past; `get_chatter_count` runs the
    # same underlying join without the enrichment joins/columns/sort a
    # count never needed, in ~0.2s.
    selected_chatter_ids = get_global_chatter_filter()
    if selected_chatter_ids:
        chatter_count = len(selected_chatter_ids)
    else:
        chatter_count = get_chatter_count(*date_range) if date_range else 0
    # Donations/chat-activity/viewership below are event-wide totals with no
    # per-row timestamp or channel column — unaffected by any sidebar filter.
    date_filter_caveat()
    entity_filter_caveat()
    donations = get_donation_timeseries()
    chat_activity = get_chat_activity_timeseries()
    viewership = get_viewership_timeseries()

    if not donations.is_empty():
        max_ts = cast(datetime, donations["timestamp"].max())
        min_ts = cast(datetime, donations["timestamp"].min())
        span_hours = (max_ts - min_ts).total_seconds() / 3600
        duration_display = t("home.kpi.duration_value", hours=f"{span_hours:,.0f}")
    else:
        duration_display = "—"

    # Two rows of 3, not one row of 6 — a formatted total like "1,032,223 €"
    # needs more than a sixth of the page width to read comfortably.
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi4, kpi5, kpi6 = st.columns(3)
    kpi1.metric(
        t("home.kpi.total_raised"),
        f"{donations['cumulative_amount_eur'][-1]:,.0f} €" if not donations.is_empty() else "—",
    )
    kpi2.metric(t("home.kpi.duration"), duration_display)
    kpi3.metric(t("home.kpi.streamers"), f"{len(streamers):,}" if not streamers.is_empty() else "—")
    kpi4.metric(t("home.kpi.chatters"), f"{chatter_count:,}" if chatter_count else "—")
    kpi5.metric(
        t("home.kpi.messages"),
        f"{chat_activity['message_count'].sum():,.0f}" if not chat_activity.is_empty() else "—",
    )
    kpi6.metric(
        t("home.kpi.peak_viewers"),
        f"{viewership['total_avg_viewer_count'].max():,.0f}" if not viewership.is_empty() else "—",
    )

    with st.expander(t("home.tech_expander_label"), expanded=False):
        st.caption(t("home.tech_caption"))
        table_stats = get_schema_table_stats()
        if table_stats.is_empty():
            st.info(t("home.tech_no_data"))
        else:
            stage_counts = (
                table_stats.group_by("schema").agg(pl.len().alias("n_tables")).sort("schema")
            )
            counts_by_schema = dict(
                zip(stage_counts["schema"], stage_counts["n_tables"], strict=True)
            )

            tkpi1, tkpi2, tkpi3 = st.columns(3)
            tkpi1.metric(t("home.tech_kpi.tables"), f"{len(table_stats):,}")
            total_rows = table_stats["row_estimate"].sum()
            tkpi2.metric(t("home.tech_kpi.rows"), f"{total_rows:,.0f}" if total_rows else "—")
            tkpi3.metric(t("home.tech_kpi.size"), _format_bytes(table_stats["size_bytes"].sum()))

            stage_keys = ["raw", "stg", "int", "marts"]
            stage_labels = [t(f"home.tech_stage.{stage}") for stage in stage_keys] + [
                t("home.tech_stage.pages")
            ]
            stage_values = [counts_by_schema.get(stage, 0) for stage in stage_keys]
            lineage_fig = go.Figure(
                go.Sankey(
                    node={
                        "label": stage_labels,
                        "color": CATEGORICAL[: len(stage_labels)],
                        "pad": 20,
                    },
                    link={
                        "source": list(range(len(stage_keys))),
                        "target": list(range(1, len(stage_keys) + 1)),
                        "value": [*stage_values[1:], _APP_PAGE_COUNT],
                        "color": "rgba(150, 150, 150, 0.3)",
                    },
                )
            )
            apply_base_layout(lineage_fig, title=t("home.tech_chart.lineage"), height=280)
            st.plotly_chart(lineage_fig, width="stretch")
            chart_explainer(t("home.explain.tech_lineage"))
            if settings.dbt_docs_url:
                st.link_button(t("home.tech_dbt_docs_button"), settings.dbt_docs_url)
            else:
                st.caption(t("home.tech_dbt_docs_hint"))

            # `map_elements` silently skips `null` cells (never calls the
            # mapping function, just re-emits `null`) — without the
            # explicit `is_null()` branch below, every view and
            # never-analyzed table (see `schema_table_stats`'s docstring)
            # would render as the literal text "None" rather than "—",
            # since Streamlit's dataframe widget shows missing values in a
            # string column that way.
            table_stats_display = table_stats.with_columns(
                pl.when(pl.col("size_bytes").is_null())
                .then(pl.lit("—"))
                .otherwise(
                    pl.col("size_bytes").map_elements(_format_bytes, return_dtype=pl.Utf8)
                )
                .alias("size"),
                pl.when(pl.col("row_estimate").is_null())
                .then(pl.lit("—"))
                .otherwise(
                    pl.col("row_estimate").map_elements(lambda n: f"{n:,}", return_dtype=pl.Utf8)
                )
                .alias("rows"),
                pl.col("kind").map_elements(
                    lambda k: t(f"home.tech_table.kind.{k}"), return_dtype=pl.Utf8
                ),
            ).select("schema", "table", "kind", "rows", "size")
            st.dataframe(
                table_stats_display.rename(
                    {
                        "schema": t("home.tech_table.column.schema"),
                        "table": t("home.tech_table.column.table"),
                        "kind": t("home.tech_table.column.kind"),
                        "rows": t("home.tech_table.column.rows"),
                        "size": t("home.tech_table.column.size"),
                    }
                ),
                width="stretch",
                hide_index=True,
            )

    date_range = get_global_date_range()
    daily_rollup = get_event_daily_rollup(*date_range) if date_range else pl.DataFrame()
    if not daily_rollup.is_empty():
        st.subheader(t("home.daily_heading"))
        st.caption(t("home.daily_caption"))
        daily_fig = go.Figure(
            go.Bar(
                x=daily_rollup["day_bucket"],
                y=daily_rollup["donation_delta_eur"],
                marker_color=CATEGORICAL[0],
                hovertemplate="%{x|%a %d %b}<br>%{y:,.0f} €<extra></extra>",
            )
        )
        apply_base_layout(daily_fig, title=t("home.chart.daily"), height=300)
        daily_fig.update_xaxes(dtick=86_400_000)
        daily_fig.update_yaxes(title_text="€")
        daily_fig.update_layout(showlegend=False)
        st.plotly_chart(daily_fig, width="stretch")
        chart_explainer(t("home.explain.daily"))
        st.dataframe(
            daily_rollup.select(
                "day_bucket",
                "message_count",
                "active_channels",
                "avg_total_viewer_count",
                "total_donation_amount_eur_end_of_day",
            ),
            width="stretch",
            hide_index=True,
        )

    st.markdown(t("home.about_body"))
    st.page_link(about_page, label=t("home.about_link"), icon=about_page.icon)

    st.divider()
    st.subheader(t("home.pages_heading"))

    # Same order as the sidebar nav (`content_pages`, alphabetized by the
    # current-language title) rather than a separately hand-maintained
    # list — the two would otherwise drift out of sync, and did.
    page_cards = [(page, _PAGE_DESCRIPTIONS[page]) for page in content_pages]
    for row_start in range(0, len(page_cards), 3):
        row = st.columns(3)
        for col, (page, desc_key) in zip(row, page_cards[row_start : row_start + 3], strict=False):
            with col:
                st.page_link(page, label=page.title, icon=page.icon)
                st.write(t(desc_key))

    page_footer()

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
about_page = st.Page("pages/10_ℹ️_About.py", title=t("about.title"), icon="ℹ️")  # noqa: RUF001
messages_page = st.Page("pages/11_🔎_Chat_Messages.py", title=t("messages.title"), icon="🔎")
leaderboard_page = st.Page("pages/12_🥇_Leaderboard.py", title=t("leaderboard.title"), icon="🥇")
chatintel_page = st.Page(
    "pages/13_🧠_Chat_Intelligence.py", title=t("chatintel.title"), icon="🧠"
)
chatml_page = st.Page("pages/14_🔬_Chat_ML_Lab.py", title=t("chatml.title"), icon="🔬")

_PAGE_DESCRIPTIONS = {
    donations_page: "donations.description",
    streamers_page: "streamers.description",
    games_page: "games.description",
    goals_page: "goals.description",
    chat_page: "chat.description",
    community_page: "community.description",
    chatters_page: "chatters.description",
    tracker_page: "tracker.description",
    activity_page: "activity.description",
    messages_page: "messages.description",
    leaderboard_page: "leaderboard.description",
    chatintel_page: "chatintel.description",
    chatml_page: "chatml.description",
}

content_pages = sorted(
    [
        donations_page,
        streamers_page,
        games_page,
        goals_page,
        chat_page,
        community_page,
        chatters_page,
        tracker_page,
        activity_page,
        messages_page,
        leaderboard_page,
        chatintel_page,
        chatml_page,
    ],
    key=lambda page: page.title,
)

navigation = st.navigation(
    {
        # An untitled first section, not a flat list: `st.navigation` always
        # inserts a small section-label caption above a *labeled* group, so
        # putting About in its own second group is what visually pins it to
        # the bottom of the nav (a divider-like gap plus its own label)
        # instead of just being the last row in one continuous list, which
        # reads as "somewhere in the middle" once there are a dozen pages.
        # Home is pinned first (it's the app's landing/index, not a content
        # page); every other page is alphabetized by its current-language
        # title, same as About is pinned outside the sort in its own section.
        "": [home_page, *content_pages],
        t("nav.info_section"): [about_page],
    },
    # `expanded` defaults to `False` once the sidebar has other elements
    # below the nav menu (it does here: nothing below it, but Streamlit
    # applies the same collapsed-with-"View more"/"View less" treatment to
    # a sectioned nav with enough pages) — every page should always be one
    # click away, not hidden behind an extra expand/collapse control.
    expanded=True,
)
navigation.run()
