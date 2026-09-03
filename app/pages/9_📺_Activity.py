"""Stream Activity page: per-streamer title/category timeline.

Streamers change their stream title — and sometimes their Twitch category —
as they move between activities during the event. This page turns that raw
metadata-snapshot stream into a segmented timeline per streamer, using
`app/data/repository.py::PostgresDataSource.stream_activity_log`.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import cast

import plotly.graph_objects as go
import polars as pl
import streamlit as st
from app.components.chrome import chart_explainer, page_header
from app.components.filters import period_filter
from app.components.theme import apply_base_layout, node_palette
from app.core.i18n import t
from app.core.logging_config import setup_logging
from app.data.repository import get_stream_activity_log, get_streamer_breakdown

setup_logging()
logger = logging.getLogger(__name__)


def _format_duration(td: timedelta | None) -> str:
    if not isinstance(td, timedelta):  # None
        return "—"
    total_minutes = int(td.total_seconds() // 60)
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours}h {minutes:02d}m" if hours else f"{minutes}m"


page_header(t("activity.title"), "📺", t("activity.description"))

streamers = get_streamer_breakdown()
if streamers.is_empty():
    st.warning(t("activity.no_streamers"))
    st.stop()

selected = st.selectbox(t("activity.pick_streamer"), options=streamers["streamer"].to_list())
channel = streamers.filter(pl.col("streamer") == selected)["channel"][0]

activity = get_stream_activity_log(channel)
if activity.is_empty():
    st.info(t("activity.no_data"))
    st.stop()

activity = activity.with_columns((pl.col("ended_at") - pl.col("started_at")).alias("duration"))

st.subheader(t("activity.filters"))
activity = period_filter(activity, timestamp_col="started_at", key="activity_period")
if activity.is_empty():
    st.info(t("common.no_data_in_range"))
    st.stop()

kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric(t("activity.kpi.segments"), f"{len(activity):,}")
kpi2.metric(t("activity.kpi.categories"), f"{activity['category'].n_unique():,}")
total_duration = cast("timedelta | None", activity["duration"].sum())
kpi3.metric(t("activity.kpi.tracked_duration"), _format_duration(total_duration))

st.subheader(t("activity.timeline_heading"))
st.caption(t("activity.timeline_caption", streamer=selected))
categories = sorted(activity["category"].unique().to_list())
palette = node_palette(categories)
timeline_fig = go.Figure()
for cat in categories:
    subset = activity.filter(pl.col("category") == cat)
    timeline_fig.add_trace(
        go.Bar(
            x=[d.total_seconds() * 1000 for d in subset["duration"]],
            y=[t("activity.timeline_row")] * len(subset),
            base=subset["started_at"],
            orientation="h",
            name=cat,
            marker_color=palette[cat],
            customdata=subset["title"],
            hovertemplate="%{customdata}<br>" + cat + "<extra></extra>",
        )
    )
apply_base_layout(timeline_fig, title=t("activity.chart.timeline"), height=260)
timeline_fig.update_xaxes(title_text=t("activity.timeline_axis"), type="date")
timeline_fig.update_layout(barmode="overlay")
st.plotly_chart(timeline_fig, width="stretch")
chart_explainer(t("activity.explain.timeline"))

st.subheader(t("activity.breakdown_heading"))
by_category = (
    activity.group_by("category")
    .agg(pl.col("duration").sum().alias("total_duration"))
    .with_columns((pl.col("total_duration").dt.total_seconds() / 3600).alias("hours"))
    .sort("hours", descending=False)
)
breakdown_fig = go.Figure(
    go.Bar(
        x=by_category["hours"],
        y=by_category["category"],
        orientation="h",
        marker_color=[palette[c] for c in by_category["category"]],
        hovertemplate="%{y}<br>%{x:.1f} h<extra></extra>",
    )
)
apply_base_layout(
    breakdown_fig,
    title=t("activity.chart.breakdown", streamer=selected),
    height=max(280, 32 * len(by_category)),
)
breakdown_fig.update_xaxes(title_text=t("activity.hours_axis"))
breakdown_fig.update_layout(showlegend=False)
st.plotly_chart(breakdown_fig, width="stretch")
chart_explainer(t("activity.explain.breakdown"))

with st.expander(t("common.view_data")):
    display = activity.with_columns(
        pl.col("duration")
        .map_elements(_format_duration, return_dtype=pl.Utf8)
        .alias("duration_display")
    ).select(["title", "category", "started_at", "ended_at", "duration_display", "snapshot_count"])
    st.dataframe(display, width="stretch", hide_index=True)
    st.download_button(
        t("common.download_csv"),
        display.write_csv(),
        file_name="stream_activity.csv",
        mime="text/csv",
    )

logger.info("Activity page rendered (channel=%s, segments=%s)", channel, len(activity))
