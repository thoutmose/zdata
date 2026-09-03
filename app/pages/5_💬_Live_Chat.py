"""Live Chat page: message activity, busiest channels, activity heatmap, and emote usage."""

from __future__ import annotations

import logging

import plotly.graph_objects as go
import polars as pl
import streamlit as st
from app.components.chrome import chart_explainer, page_header
from app.components.filters import period_filter
from app.components.theme import CATEGORICAL, SEQUENTIAL_BLUE_COLORSCALE, apply_base_layout
from app.core.i18n import t
from app.core.logging_config import setup_logging
from app.data.repository import (
    get_channel_hour_heatmap,
    get_chat_activity_timeseries,
    get_chat_engagement_rate,
    get_top_chat_channels,
    get_top_emotes,
)

setup_logging()
logger = logging.getLogger(__name__)

page_header(t("chat.title"), "💬", t("chat.description"))

activity = get_chat_activity_timeseries()
if activity.is_empty():
    st.warning(t("chat.no_data"))
    st.stop()

st.subheader(t("chat.filters"))
activity = period_filter(activity, timestamp_col="timestamp", key="chat_period")

if activity.is_empty():
    st.info(t("common.no_data_in_range"))
    st.stop()

latest = activity.row(-1, named=True)
kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric(t("chat.kpi.messages_this_hour"), f"{latest['message_count']:,.0f}")
kpi2.metric(t("chat.kpi.chatters_this_hour"), f"{latest['unique_chatters']:,.0f}")
kpi3.metric(t("chat.kpi.total_messages"), f"{activity['message_count'].sum():,.0f}")

activity_fig = go.Figure(
    go.Scatter(
        x=activity["timestamp"],
        y=activity["message_count"],
        mode="lines",
        line={"color": CATEGORICAL[0], "width": 2},
        fill="tozeroy",
        fillcolor="rgba(42, 120, 214, 0.12)",
        hovertemplate="%{x|%a %H:%M}<br>%{y:,.0f} messages<extra></extra>",
        name=t("chat.chart.activity"),
    )
)
apply_base_layout(activity_fig, title=t("chat.chart.activity"))
activity_fig.update_yaxes(title_text=t("common.per_hour", unit=t("common.unit.messages")))
st.plotly_chart(activity_fig, width="stretch")
chart_explainer(t("chat.explain.activity"))

st.subheader(t("chat.engagement_heading"))
st.caption(t("chat.engagement_caption"))
engagement = get_chat_engagement_rate()
if engagement.is_empty():
    st.info(t("chat.no_engagement"))
else:
    engagement_fig = go.Figure(
        go.Scatter(
            x=engagement["timestamp"],
            y=engagement["avg_engagement_rate"],
            mode="lines+markers",
            line={"color": CATEGORICAL[2], "width": 2},
            hovertemplate="%{x|%a %H:%M}<br>%{y:.1f}<extra></extra>",
        )
    )
    apply_base_layout(engagement_fig, title=t("chat.chart.engagement"), height=340)
    engagement_fig.update_yaxes(title_text=t("chat.engagement_axis"))
    st.plotly_chart(engagement_fig, width="stretch")
    chart_explainer(t("chat.explain.engagement"))

st.subheader(t("chat.heatmap_heading"))
heatmap = get_channel_hour_heatmap()
if heatmap.is_empty():
    st.info(t("chat.no_heatmap"))
else:
    all_channels = sorted(heatmap["channel"].unique().to_list())
    channel_filter = st.multiselect(t("chat.channel_filter"), options=all_channels, default=[])
    shown_heatmap = (
        heatmap.filter(pl.col("channel").is_in(channel_filter)) if channel_filter else heatmap
    )
    st.caption(t("chat.heatmap_caption"))

    heatmap_channels = sorted(shown_heatmap["channel"].unique().to_list())
    heatmap_hours = sorted(shown_heatmap["timestamp"].unique().to_list())
    counts_by_cell = {
        (row["channel"], row["timestamp"]): row["message_count"]
        for row in shown_heatmap.iter_rows(named=True)
    }
    z = [[counts_by_cell.get((ch, ts), 0) for ts in heatmap_hours] for ch in heatmap_channels]

    heat_fig = go.Figure(
        go.Heatmap(
            z=z,
            x=[ts.strftime("%a %H:%M") for ts in heatmap_hours],
            y=heatmap_channels,
            colorscale=SEQUENTIAL_BLUE_COLORSCALE,
            hovertemplate="%{y}<br>%{x}<br>%{z:,.0f} messages<extra></extra>",
            colorbar={"title": t("common.unit.messages")},
        )
    )
    apply_base_layout(
        heat_fig, title=t("chat.chart.heatmap"), height=max(360, 24 * len(heatmap_channels))
    )
    heat_fig.update_xaxes(showgrid=False)
    heat_fig.update_yaxes(showgrid=False)
    st.plotly_chart(heat_fig, width="stretch")
    chart_explainer(t("chat.explain.heatmap"))

st.subheader(t("chat.channels_heading"))
channels = get_top_chat_channels()
if channels.is_empty():
    st.info(t("chat.no_channels"))
else:
    st.caption(t("chat.channels_caption"))
    ordered = channels.sort("message_count", descending=False)
    comp_fig = go.Figure()
    segments = [
        ("subscriber_message_count", t("common.badge.subscriber"), CATEGORICAL[0]),
        ("vip_message_count", t("common.badge.vip"), CATEGORICAL[1]),
        ("moderator_message_count", t("common.badge.moderator"), CATEGORICAL[2]),
        ("plain_viewer_message_count", t("common.badge.plain_viewer"), CATEGORICAL[3]),
    ]
    for col, label, color in segments:
        comp_fig.add_trace(
            go.Bar(
                x=ordered[col],
                y=ordered["channel"],
                orientation="h",
                name=label,
                marker_color=color,
                hovertemplate="%{y}<br>%{x:,.0f} " + label.lower() + " messages<extra></extra>",
            )
        )
    apply_base_layout(
        comp_fig, title=t("chat.chart.composition"), height=max(360, 32 * len(ordered))
    )
    comp_fig.update_xaxes(title_text=t("common.unit.messages"))
    comp_fig.update_layout(barmode="stack")
    st.plotly_chart(comp_fig, width="stretch")
    chart_explainer(t("chat.explain.composition"))

st.subheader(t("chat.emotes_heading"))
emotes = get_top_emotes()
if emotes.is_empty():
    st.info(t("chat.no_emotes"))
else:
    if not emotes["is_named"].any():
        st.caption(t("chat.emotes_unnamed_caveat"))
    # A Plotly axis can't render an image as a tick label, and the whole
    # point here is to show the actual emote — so this is a native leaderboard
    # (image + a proportional bar) rather than a bar chart with a text label.
    emotes_sorted = emotes.sort("usage_count", descending=True)
    max_usage = emotes_sorted["usage_count"].max() or 1
    for row in emotes_sorted.iter_rows(named=True):
        img_col, bar_col = st.columns([1, 6])
        with img_col:
            if row.get("image_url"):
                st.image(row["image_url"], width=40)
            else:
                st.markdown(f"**{row['emote']}**")
        with bar_col:
            st.caption(f"{row['emote']} — {row['usage_count']:,.0f} {t('chat.uses_axis')}")
            st.progress(min(row["usage_count"] / max_usage, 1.0))
    chart_explainer(t("chat.explain.emotes"))

with st.expander(t("common.view_data")):
    st.dataframe(activity, width="stretch", hide_index=True)
    st.dataframe(channels, width="stretch", hide_index=True)
    st.download_button(
        t("common.download_csv"),
        activity.write_csv(),
        file_name="chat_activity.csv",
        mime="text/csv",
    )

logger.info("Live Chat page rendered (activity_rows=%s, channels=%s)", len(activity), len(channels))
