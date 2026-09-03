"""Streamers page: donations, audience, engagement, correlations, and a profile drill-down.

Note: the real database has no "team" dimension for streamers, so this page
ranks streamers individually rather than grouping/coloring by team.
"""

from __future__ import annotations

import logging

import plotly.graph_objects as go
import polars as pl
import streamlit as st
from app.components.chrome import chart_explainer, page_header
from app.components.search import consume_search_query
from app.components.theme import CATEGORICAL, apply_base_layout
from app.core.i18n import t
from app.core.logging_config import setup_logging
from app.data.repository import get_streamer_breakdown, get_streamer_diurnal_profile

setup_logging()
logger = logging.getLogger(__name__)

page_header(t("streamers.title"), "🎙️", t("streamers.description"))

df = get_streamer_breakdown()
if df.is_empty():
    st.warning(t("streamers.no_data"))
    st.stop()

pending_query = consume_search_query()
if pending_query:
    st.session_state["streamers_search_box"] = pending_query

st.subheader(t("streamers.filters"))
filter_col1, filter_col2, filter_col3 = st.columns(3)
with filter_col1:
    search = st.text_input(t("streamers.search"), key="streamers_search_box")
with filter_col2:
    categories = sorted(df["top_category"].drop_nulls().unique().to_list())
    category_filter = st.multiselect(t("streamers.category_filter"), options=categories, default=[])
with filter_col3:
    min_viewers = st.number_input(t("streamers.min_viewers"), min_value=0, value=0, step=100)

filtered = df
if search:
    filtered = filtered.filter(
        pl.col("streamer").str.to_lowercase().str.contains(search.lower(), literal=True)
    )
if category_filter:
    filtered = filtered.filter(pl.col("top_category").is_in(category_filter))
filtered = filtered.filter(pl.col("avg_viewers") >= min_viewers)

if filtered.is_empty():
    st.info(t("common.no_data_in_range"))
    st.stop()

RANKINGS = {
    t("streamers.rank.donations"): ("amount_eur", "€"),
    t("streamers.rank.engagement"): ("total_messages", t("common.unit.messages")),
    t("streamers.rank.audience"): ("avg_viewers", t("common.unit.viewers")),
}

rank_by = st.radio(t("streamers.rank_by"), list(RANKINGS.keys()), horizontal=True)
column, unit = RANKINGS[rank_by]
if len(filtered) <= 1:
    top_n = len(filtered)
else:
    top_n = st.slider(
        t("streamers.top_n"),
        min_value=1,
        max_value=len(filtered),
        value=min(15, len(filtered)),
    )
top = filtered.sort(column, descending=True).head(top_n)

kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric(t("streamers.kpi.top", metric=rank_by), top["streamer"][0])
kpi2.metric(t("streamers.kpi.total_raised"), f"{top['amount_eur'].sum():,.0f} €")
kpi3.metric(t("streamers.kpi.total_messages"), f"{top['total_messages'].sum():,.0f}")

# Ranked magnitude across many streamers: one hue for the whole chart, not one
# per bar — a distinct color per bar here would be decorative, not meaningful.
ordered = top.sort(column, descending=False)
bar_fig = go.Figure(
    go.Bar(
        x=ordered[column],
        y=ordered["streamer"],
        orientation="h",
        marker_color=CATEGORICAL[0],
        hovertemplate=f"%{{y}}<br>%{{x:,.0f}} {unit}<extra></extra>",
    )
)
apply_base_layout(
    bar_fig, title=t("streamers.chart.ranked", metric=rank_by), height=max(360, 32 * len(ordered))
)
bar_fig.update_xaxes(title_text=unit)
bar_fig.update_layout(showlegend=False)
st.plotly_chart(bar_fig, width="stretch")
chart_explainer(t("streamers.explain.ranked"))

st.subheader(t("streamers.correlation_heading"))
st.caption(t("streamers.correlation_caption"))
scatter_fig = go.Figure(
    go.Scatter(
        x=filtered["avg_viewers"],
        y=filtered["total_messages"],
        mode="markers",
        marker={
            "color": CATEGORICAL[0],
            "size": (filtered["amount_eur"].clip(lower_bound=1) ** 0.5) / 3 + 6,
            "opacity": 0.75,
            "line": {"width": 1, "color": "white"},
        },
        text=filtered["streamer"],
        hovertemplate="%{text}<br>viewers: %{x:,.0f}<br>messages: %{y:,.0f}<extra></extra>",
    )
)
apply_base_layout(scatter_fig, title=t("streamers.chart.correlation"), height=420)
scatter_fig.update_xaxes(title_text=t("common.unit.viewers"))
scatter_fig.update_yaxes(title_text=t("common.unit.messages"))
scatter_fig.update_layout(showlegend=False)
st.plotly_chart(scatter_fig, width="stretch")
chart_explainer(t("streamers.explain.correlation"))

st.subheader(t("streamers.profile_heading"))
selected = st.selectbox(t("streamers.pick_streamer"), options=filtered["streamer"].to_list())
profile = filtered.filter(pl.col("streamer") == selected).row(0, named=True)

pcol1, pcol2, pcol3, pcol4 = st.columns(4)
pcol1.metric(t("streamers.kpi.peak_viewers"), f"{profile['peak_viewers']:,.0f}")
uptime_display = (
    f"{min(profile['uptime_pct'], 100):.0f}%"
    if profile["uptime_pct"] <= 100
    else t("streamers.uptime_quirk")
)
pcol2.metric(t("streamers.kpi.uptime"), uptime_display)
pcol3.metric(t("streamers.kpi.top_category"), profile["top_category"] or "—")
pcol4.metric(t("streamers.kpi.unique_chatters"), f"{profile['unique_chatters']:,.0f}")

detail_col1, detail_col2 = st.columns(2)
with detail_col1:
    chatter_mix = go.Figure(
        go.Bar(
            x=[
                t("common.chatter_profile.loyal"),
                t("common.chatter_profile.multi_streamer"),
                t("common.chatter_profile.semi_nomad"),
                t("common.chatter_profile.nomad"),
            ],
            y=[
                profile["sedentaire_chatters"],
                profile["multi_streamer_chatters"],
                profile["semi_nomade_chatters"],
                profile["nomade_chatters"],
            ],
            marker_color=CATEGORICAL[:4],
        )
    )
    apply_base_layout(
        chatter_mix, title=t("streamers.chart.loyalty_mix", streamer=selected), height=320
    )
    chatter_mix.update_yaxes(title_text=t("common.unit.chatters"))
    chatter_mix.update_layout(showlegend=False)
    st.plotly_chart(chatter_mix, width="stretch")
    st.caption(t("common.chatter_profile.caption"))
    chart_explainer(t("streamers.explain.loyalty_mix"))
with detail_col2:
    diurnal = get_streamer_diurnal_profile(profile["channel"])
    if diurnal.is_empty():
        st.info(t("streamers.no_diurnal_data"))
    else:
        diurnal_fig = go.Figure()
        diurnal_fig.add_trace(
            go.Scatter(
                x=diurnal["hour_of_day"],
                y=diurnal["streamer_avg_viewer_count"],
                mode="lines",
                name=selected,
                line={"color": CATEGORICAL[0], "width": 2},
            )
        )
        diurnal_fig.add_trace(
            go.Scatter(
                x=diurnal["hour_of_day"],
                y=diurnal["event_avg_viewer_count"],
                mode="lines",
                name=t("streamers.event_average"),
                line={"color": CATEGORICAL[7], "width": 2, "dash": "dot"},
            )
        )
        apply_base_layout(diurnal_fig, title=t("streamers.chart.diurnal"), height=320)
        diurnal_fig.update_xaxes(title_text=t("streamers.hour_of_day"))
        diurnal_fig.update_yaxes(title_text=t("common.unit.avg_viewers"))
        st.plotly_chart(diurnal_fig, width="stretch")
        chart_explainer(t("streamers.explain.diurnal"))

with st.expander(t("common.view_data")):
    st.dataframe(filtered, width="stretch", hide_index=True)
    st.download_button(
        t("common.download_csv"), filtered.write_csv(), file_name="streamers.csv", mime="text/csv"
    )

logger.info(
    "Streamers page rendered (rows=%s, rank_by=%s, top_n=%s)", len(filtered), rank_by, top_n
)
