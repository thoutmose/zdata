"""Games page: categories played, concurrent viewership, and recent stream sessions.

Uses the Twitch-metadata pipeline (`marts.mart_streams__*`), not the donations
pipeline's `game` field, which isn't populated pre-event — see
`app/data/repository.py::PostgresDataSource.category_breakdown`.
"""

from __future__ import annotations

import logging

import plotly.graph_objects as go
import polars as pl
import streamlit as st
from app.components.chrome import chart_explainer, page_header
from app.components.filters import period_filter
from app.components.search import consume_search_query
from app.components.theme import CATEGORICAL, apply_base_layout
from app.core.i18n import t
from app.core.logging_config import setup_logging
from app.data.repository import (
    get_category_breakdown,
    get_stream_sessions,
    get_title_leaderboard,
    get_viewership_timeseries,
)

setup_logging()
logger = logging.getLogger(__name__)

page_header(t("games.title"), "🎮", t("games.description"))

categories = get_category_breakdown()
viewership = get_viewership_timeseries()

st.subheader(t("games.filters"))
viewership = period_filter(viewership, timestamp_col="timestamp", key="games_period")

if not viewership.is_empty():
    latest = viewership.row(-1, named=True)
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric(t("games.kpi.concurrent_now"), f"{latest['total_avg_viewer_count']:,.0f}")
    kpi2.metric(t("games.kpi.channels_now"), f"{latest['live_channel_count']:,}")
    kpi3.metric(
        t("games.kpi.peak_concurrent"), f"{viewership['total_avg_viewer_count'].max():,.0f}"
    )

    view_fig = go.Figure(
        go.Scatter(
            x=viewership["timestamp"],
            y=viewership["total_avg_viewer_count"],
            mode="lines",
            line={"color": CATEGORICAL[0], "width": 2},
            fill="tozeroy",
            fillcolor="rgba(42, 120, 214, 0.12)",
            hovertemplate="%{x|%a %H:%M}<br>%{y:,.0f} viewers<extra></extra>",
        )
    )
    apply_base_layout(view_fig, title=t("games.chart.viewership"))
    view_fig.update_yaxes(title_text=t("common.unit.viewers"))
    st.plotly_chart(view_fig, width="stretch")
    chart_explainer(t("games.explain.viewership"))

    channels_fig = go.Figure(
        go.Bar(
            x=viewership["timestamp"],
            y=viewership["live_channel_count"],
            marker_color=CATEGORICAL[1],
            hovertemplate="%{x|%a %H:%M}<br>%{y} channels live<extra></extra>",
        )
    )
    apply_base_layout(channels_fig, title=t("games.chart.live_channels"), height=320)
    channels_fig.update_yaxes(title_text=t("common.unit.channels"))
    channels_fig.update_layout(showlegend=False)
    st.plotly_chart(channels_fig, width="stretch")
    chart_explainer(t("games.explain.live_channels"))
else:
    st.info(t("games.no_viewership"))

st.subheader(t("games.categories_heading"))
if categories.is_empty():
    st.info(t("games.no_categories"))
else:
    all_categories = sorted(categories["category"].unique().to_list())
    pending_query = consume_search_query()
    if pending_query in all_categories:
        st.session_state["games_category_filter"] = [pending_query]
    category_filter = st.multiselect(
        t("games.category_filter"), options=all_categories, key="games_category_filter"
    )
    shown = (
        categories.filter(pl.col("category").is_in(category_filter))
        if category_filter
        else categories
    )

    sorted_categories = shown.sort("channel_hours", descending=False)
    cat_fig = go.Figure(
        go.Bar(
            x=sorted_categories["channel_hours"],
            y=sorted_categories["category"],
            orientation="h",
            marker_color=CATEGORICAL[0],
            hovertemplate="%{y}<br>%{x:,.1f} channel-hours<extra></extra>",
        )
    )
    apply_base_layout(
        cat_fig, title=t("games.chart.by_category"), height=max(360, 32 * len(sorted_categories))
    )
    cat_fig.update_xaxes(title_text=t("common.unit.channel_hours"))
    cat_fig.update_layout(showlegend=False)
    st.plotly_chart(cat_fig, width="stretch")
    chart_explainer(t("games.explain.by_category"))

st.subheader(t("games.sessions_heading"))
sessions = get_stream_sessions()
if sessions.is_empty():
    st.info(t("games.no_sessions"))
else:
    st.dataframe(sessions, width="stretch", hide_index=True)

st.subheader(t("games.titles_heading"))
titles = get_title_leaderboard()
if titles.is_empty():
    st.info(t("games.no_titles"))
else:
    st.caption(t("games.titles_caption"))
    rank_metric = st.radio(
        t("games.titles_rank_by"),
        [t("games.titles_by_messages"), t("games.titles_by_donations")],
        horizontal=True,
    )
    metric_col = (
        "message_count" if rank_metric == t("games.titles_by_messages") else "donations_eur"
    )
    top_titles = titles.sort(metric_col, descending=False).tail(10)
    titles_fig = go.Figure(
        go.Bar(
            x=top_titles[metric_col],
            y=top_titles["title"],
            orientation="h",
            marker_color=CATEGORICAL[3],
            hovertemplate="%{y}<br>%{x:,.0f}<extra></extra>",
        )
    )
    apply_base_layout(
        titles_fig, title=t("games.chart.titles"), height=max(360, 32 * len(top_titles))
    )
    titles_fig.update_layout(showlegend=False)
    st.plotly_chart(titles_fig, width="stretch")
    chart_explainer(t("games.explain.titles"))

with st.expander(t("common.view_data")):
    st.caption(t("games.categories_heading"))
    st.dataframe(categories, width="stretch", hide_index=True)
    st.caption(t("games.chart.viewership"))
    st.dataframe(viewership, width="stretch", hide_index=True)
    st.caption(t("games.titles_heading"))
    st.dataframe(titles, width="stretch", hide_index=True)
    st.download_button(
        t("common.download_csv"),
        categories.write_csv(),
        file_name="categories.csv",
        mime="text/csv",
    )

logger.info(
    "Games page rendered (categories=%s, viewership_rows=%s, sessions=%s)",
    len(categories),
    len(viewership),
    len(sessions),
)
