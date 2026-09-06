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
from app.components.chrome import (
    bounded_top_n_slider,
    chart_explainer,
    entity_filter_caveat,
    page_footer,
    page_header,
)
from app.components.filters import (
    apply_global_date_filter,
    apply_global_streamer_filter,
    get_global_date_range,
)
from app.components.search import consume_search_query
from app.components.theme import (
    CATEGORICAL,
    CHROME,
    STATUS,
    apply_base_layout,
    build_race_figure,
    hex_to_rgba,
)
from app.core.i18n import t
from app.core.logging_config import setup_logging
from app.data.repository import (
    get_category_breakdown,
    get_category_change_impact,
    get_category_popularity_timeseries,
    get_channel_viewership_leaderboard_timeseries,
    get_stream_sessions,
    get_streamer_breakdown,
    get_title_leaderboard,
    get_viewership_timeseries,
)

setup_logging()
logger = logging.getLogger(__name__)

page_header(t("games.title"), "🎮", t("games.description"))

date_range = get_global_date_range()
categories = get_category_breakdown(*date_range) if date_range else pl.DataFrame()
viewership = get_viewership_timeseries()

viewership = apply_global_date_filter(viewership, timestamp_col="timestamp")

entity_filter_caveat()
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
            fillcolor=hex_to_rgba(CATEGORICAL[0], 0.12),
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

    st.subheader(t("games.viewer_race_heading"))
    viewer_race_top_n = bounded_top_n_slider(
        label=t("games.viewer_race_top_n"),
        max_value=len(apply_global_streamer_filter(get_streamer_breakdown())),
        key="games_viewer_race_top_n",
        default_n=8,
    )
    race = (
        get_channel_viewership_leaderboard_timeseries(*date_range, viewer_race_top_n)
        if date_range
        else pl.DataFrame()
    )
    race = apply_global_streamer_filter(race)
    if race.is_empty():
        st.info(t("games.no_viewer_race"))
    else:
        st.caption(t("games.viewer_race_caption"))
        race_fig = build_race_figure(
            race,
            value_col="avg_viewer_count",
            rank_col="viewer_rank_at_hour",
            title=t("games.chart.viewer_race"),
            unit=t("common.unit.viewers"),
        )
        st.plotly_chart(race_fig, width="stretch")
        chart_explainer(t("games.explain.viewer_race"))
else:
    st.info(t("games.no_viewership"))

st.subheader(t("games.categories_heading"))
entity_filter_caveat()
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

    st.subheader(t("games.category_trend_heading"))
    category_trend = (
        get_category_popularity_timeseries(*date_range) if date_range else pl.DataFrame()
    )
    if category_trend.is_empty():
        st.info(t("games.no_category_trend"))
    else:
        st.caption(t("games.category_trend_caption"))
        other_label = t("common.pie_other")
        top_categories = (
            category_trend.group_by("category")
            .agg(pl.col("channel_count_playing").sum())
            .sort("channel_count_playing", descending=True)
            .head(7)["category"]
            .to_list()
        )
        trend = (
            category_trend.with_columns(
                pl.when(pl.col("category").is_in(top_categories))
                .then(pl.col("category"))
                .otherwise(pl.lit(other_label))
                .alias("series")
            )
            .group_by(["timestamp", "series"])
            .agg(pl.col("channel_count_playing").sum())
        )
        series_order = [*top_categories, other_label]
        present_series = set(trend["series"].unique().to_list())
        trend_fig = go.Figure()
        for i, series in enumerate(s for s in series_order if s in present_series):
            subset = trend.filter(pl.col("series") == series).sort("timestamp")
            color = (
                CHROME["baseline"] if series == other_label else CATEGORICAL[i % len(CATEGORICAL)]
            )
            trend_fig.add_trace(
                go.Scatter(
                    x=subset["timestamp"],
                    y=subset["channel_count_playing"],
                    mode="lines",
                    stackgroup="one",
                    name=series,
                    line={"width": 0.5, "color": color},
                    fillcolor=hex_to_rgba(color, 0.75),
                    hovertemplate=f"{series}<br>%{{x|%a %H:%M}}<br>%{{y}} channels<extra></extra>",
                )
            )
        apply_base_layout(trend_fig, title=t("games.chart.category_trend"), height=420)
        trend_fig.update_yaxes(title_text=t("common.unit.channels"))
        st.plotly_chart(trend_fig, width="stretch")
        chart_explainer(t("games.explain.category_trend"))

st.subheader(t("games.switches_heading"))
changes = get_category_change_impact(*date_range) if date_range else pl.DataFrame()
changes = apply_global_streamer_filter(changes)
if changes.is_empty():
    st.info(t("games.no_switches"))
else:
    st.caption(t("games.switches_caption"))
    changes = changes.with_columns(
        (pl.col("avg_viewer_count_hour_after") - pl.col("viewer_count_at_change")).alias(
            "viewer_delta"
        )
    )
    ordered_changes = changes.sort(pl.col("viewer_delta").abs(), descending=False).with_columns(
        (pl.col("channel") + ": " + pl.col("prev_category") + " → " + pl.col("new_category")).alias(
            "switch_label"
        )
    )
    switch_fig = go.Figure(
        go.Bar(
            x=ordered_changes["viewer_delta"],
            y=ordered_changes["switch_label"],
            orientation="h",
            marker_color=[
                STATUS["good"] if d >= 0 else STATUS["critical"]
                for d in ordered_changes["viewer_delta"]
            ],
            hovertemplate="%{y}<br>%{x:+,.0f} viewers<extra></extra>",
        )
    )
    apply_base_layout(
        switch_fig, title=t("games.chart.switches"), height=max(360, 32 * len(ordered_changes))
    )
    switch_fig.update_xaxes(title_text=t("games.switches_axis"))
    switch_fig.update_layout(showlegend=False)
    st.plotly_chart(switch_fig, width="stretch")
    chart_explainer(t("games.explain.switches"))

st.subheader(t("games.sessions_heading"))
sessions = apply_global_date_filter(get_stream_sessions(), timestamp_col="stream_started_at")
sessions = apply_global_streamer_filter(sessions)
if sessions.is_empty():
    st.info(t("games.no_sessions"))
else:
    st.caption(t("games.sessions_caption"))
    sessions_ordered = sessions.with_columns(
        (
            pl.col("channel") + " — " + pl.col("stream_started_at").dt.strftime("%a %H:%M")
        ).alias("session_label")
    ).sort("peak_viewer_count", descending=False)
    sessions_fig = go.Figure(
        go.Bar(
            x=sessions_ordered["peak_viewer_count"],
            y=sessions_ordered["session_label"],
            orientation="h",
            marker_color=[
                STATUS["good"] if d >= 0 else STATUS["critical"]
                for d in sessions_ordered["viewer_change"]
            ],
            customdata=sessions_ordered["viewer_change"],
            hovertemplate=(
                "%{y}<br>%{x:,.0f} peak viewers<br>%{customdata:+,.0f} vs. session start"
                "<extra></extra>"
            ),
        )
    )
    apply_base_layout(
        sessions_fig,
        title=t("games.chart.sessions"),
        height=max(360, 32 * len(sessions_ordered)),
    )
    sessions_fig.update_xaxes(title_text=t("common.unit.viewers"))
    sessions_fig.update_layout(showlegend=False)
    st.plotly_chart(sessions_fig, width="stretch")
    chart_explainer(t("games.explain.sessions"))
    with st.expander(t("common.view_data")):
        st.dataframe(sessions, width="stretch", hide_index=True)

st.subheader(t("games.titles_heading"))
entity_filter_caveat()
titles = get_title_leaderboard(*date_range) if date_range else pl.DataFrame()
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

page_footer()

logger.info(
    "Games page rendered (categories=%s, viewership_rows=%s, sessions=%s)",
    len(categories),
    len(viewership),
    len(sessions),
)
