"""Donation Tracker page: track a streamer's donation-goal milestones over time.

Every goal category is tracked, not just `"donation"` (the classic
cumulative-total milestone, "reach X€ total") — but since each category's
"start = previous goal's completion" chain only makes sense within that
category, each one is tracked as its own independent chain against the same
timeseries rather than mixed into one sequence — see
`app/data/goal_progress.py::goal_progress_by_category`. The category filter
below lets you look at one chain at a time, since overlaying every
category's bars on one timeline would otherwise show unrelated goals'
time spans crossing each other.
"""

from __future__ import annotations

import logging
from datetime import timedelta

import plotly.graph_objects as go
import polars as pl
import streamlit as st
from app.components.chrome import chart_explainer, date_filter_caveat, page_footer, page_header
from app.components.filters import apply_global_streamer_filter
from app.components.theme import CATEGORICAL, STATUS, apply_base_layout
from app.core.i18n import t
from app.core.logging_config import setup_logging
from app.data.repository import (
    get_donation_goal_tracker,
    get_donation_goal_tracker_global,
    get_streamer_breakdown,
)

setup_logging()
logger = logging.getLogger(__name__)


def _status_counts(df: pl.DataFrame) -> dict[str, int]:
    """Count rows per `status` value.

    Args:
        df: A DataFrame with a `status` column.

    Returns:
        Mapping from status value to row count.
    """
    counts = df["status"].value_counts()
    return dict(zip(counts["status"].to_list(), counts["count"].to_list(), strict=False))


def _format_duration(td: timedelta | None) -> str:
    if not isinstance(td, timedelta):  # None
        return "—"
    total_minutes = int(td.total_seconds() // 60)
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours}h {minutes:02d}m" if hours else f"{minutes}m"


page_header(t("tracker.title"), "🏆", t("tracker.description"))
date_filter_caveat()

st.subheader(t("tracker.global_heading"))
global_progress = apply_global_streamer_filter(
    get_donation_goal_tracker_global(), channel_col="twitch_login"
)
if global_progress.is_empty():
    st.info(t("tracker.no_global_data"))
else:
    global_counts = _status_counts(global_progress)
    gcol1, gcol2, gcol3, gcol4 = st.columns(4)
    gcol1.metric(t("tracker.kpi.total"), f"{len(global_progress):,}")
    gcol2.metric(t("tracker.kpi.done"), f"{global_counts.get('done', 0):,}")
    gcol3.metric(t("tracker.kpi.in_progress"), f"{global_counts.get('in_progress', 0):,}")
    gcol4.metric(t("tracker.kpi.not_started"), f"{global_counts.get('not_started', 0):,}")

    st.caption(t("tracker.global_caption"))
    done_per_streamer = (
        global_progress.filter(pl.col("status") == "done")
        .group_by("twitch_login")
        .agg(pl.len().alias("goals_done"))
        .sort("goals_done", descending=True)
        .head(15)
    )
    if not done_per_streamer.is_empty():
        chart_data = done_per_streamer.sort("goals_done", descending=False)
        top_fig = go.Figure(
            go.Bar(
                x=chart_data["goals_done"],
                y=chart_data["twitch_login"],
                orientation="h",
                marker_color=CATEGORICAL[0],
                hovertemplate="%{y}<br>%{x} " + t("tracker.kpi.done").lower() + "<extra></extra>",
            )
        )
        apply_base_layout(
            top_fig,
            title=t("tracker.chart.top_completers"),
            height=max(320, 28 * len(chart_data)),
        )
        top_fig.update_xaxes(title_text=t("tracker.kpi.done"))
        top_fig.update_layout(showlegend=False)
        st.plotly_chart(top_fig, width="stretch")
        chart_explainer(t("tracker.explain.top_completers"))

st.subheader(t("tracker.per_streamer_heading"))
streamers = apply_global_streamer_filter(get_streamer_breakdown())
if streamers.is_empty():
    st.warning(t("tracker.no_streamers"))
    st.stop()

streamer_options = streamers["streamer"].to_list()
if len(streamer_options) == 1:
    # The global streamer filter already narrowed this to exactly one —
    # nothing left to pick, so skip the selectbox and go straight to it.
    selected = streamer_options[0]
    st.caption(t("tracker.pick_streamer_single", streamer=selected))
else:
    selected = st.selectbox(t("tracker.pick_streamer"), options=streamer_options)
channel = streamers.filter(pl.col("streamer") == selected)["channel"][0]

progress = get_donation_goal_tracker(channel)
if progress.is_empty():
    st.info(t("tracker.no_goals"))
    st.stop()

available_categories = sorted(progress["goal_category"].unique().to_list())
# A `key`'d widget with no upfront session-state check crashes when a
# streamer switch changes `options` out from under a value Streamlit is
# still holding from the *previous* streamer (a category that streamer
# doesn't have) — reproducible via `st.testing.v1.AppTest` by stepping
# through streamers, and the same widget-identity issue applies to a real
# session. Resetting the stored value to "every current category" whenever
# it no longer fits (not just on every switch) preserves a still-valid
# selection across streamers that happen to share categories.
_category_filter_key = "tracker_category_filter"
if _category_filter_key not in st.session_state or not set(
    st.session_state[_category_filter_key]
).issubset(available_categories):
    st.session_state[_category_filter_key] = available_categories
category_filter = st.multiselect(
    t("tracker.category_filter"),
    options=available_categories,
    help=t("tracker.category_filter_help"),
    key=_category_filter_key,
)
progress = (
    progress.filter(pl.col("goal_category").is_in(category_filter))
    if category_filter
    else progress
)
if progress.is_empty():
    st.info(t("tracker.no_goals"))
    st.stop()

status_counts = _status_counts(progress)
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric(t("tracker.kpi.total"), f"{len(progress):,}")
kpi2.metric(t("tracker.kpi.done"), f"{status_counts.get('done', 0):,}")
kpi3.metric(t("tracker.kpi.in_progress"), f"{status_counts.get('in_progress', 0):,}")
kpi4.metric(t("tracker.kpi.not_started"), f"{status_counts.get('not_started', 0):,}")

STATUS_LABELS = {
    "done": t("tracker.status.done"),
    "in_progress": t("tracker.status.in_progress"),
    "not_started": t("tracker.status.not_started"),
}
STATUS_COLORS = {
    "done": STATUS["good"],
    "in_progress": STATUS["warning"],
    "not_started": STATUS["muted"],
}

ordered = progress.sort("goal_amount_eur", descending=False)
completed = ordered.filter(pl.col("status") == "done")

view = st.radio(
    t("tracker.view_picker"),
    [t("tracker.view.timeline"), t("tracker.view.duration_bar")],
    horizontal=True,
)

if view == t("tracker.view.timeline"):
    st.caption(t("tracker.timeline_caption", streamer=selected))
    timeline_fig = go.Figure()
    for status, color, label in [
        ("done", STATUS_COLORS["done"], STATUS_LABELS["done"]),
        ("in_progress", STATUS_COLORS["in_progress"], STATUS_LABELS["in_progress"]),
    ]:
        subset = ordered.filter(pl.col("status") == status)
        if subset.is_empty():
            continue
        span = subset["duration"] if status == "done" else subset["elapsed_so_far"]
        timeline_fig.add_trace(
            go.Bar(
                x=[d.total_seconds() * 1000 if d is not None else 0 for d in span],
                y=subset["goal_name"],
                base=subset["started_at"],
                orientation="h",
                name=label,
                marker_color=color,
                hovertemplate="%{y}<br>" + label + "<extra></extra>",
            )
        )
    if timeline_fig.data:
        apply_base_layout(
            timeline_fig, title=t("tracker.chart.timeline"), height=max(360, 36 * len(ordered))
        )
        timeline_fig.update_xaxes(title_text=t("tracker.timeline_axis"), type="date")
        st.plotly_chart(timeline_fig, width="stretch")
        chart_explainer(t("tracker.explain.timeline"))
    else:
        st.info(t("tracker.no_timeline"))
else:
    st.caption(t("tracker.duration_bar_caption"))
    if completed.is_empty():
        st.info(t("tracker.no_completed_goals"))
    else:
        duration_hours = completed["duration"].dt.total_seconds() / 3600
        duration_fig = go.Figure(
            go.Bar(
                x=duration_hours,
                y=completed["goal_name"],
                orientation="h",
                marker_color=STATUS["good"],
                hovertemplate="%{y}<br>%{x:.1f} h<extra></extra>",
            )
        )
        apply_base_layout(
            duration_fig,
            title=t("tracker.chart.duration_bar"),
            height=max(320, 32 * len(completed)),
        )
        duration_fig.update_xaxes(title_text=t("tracker.duration_axis"))
        duration_fig.update_layout(showlegend=False)
        st.plotly_chart(duration_fig, width="stretch")
        chart_explainer(t("tracker.explain.duration_bar"))

st.subheader(t("tracker.table_heading"))
st.caption(t("tracker.table_caption"))
table = ordered.with_columns(
    pl.col("status").replace(STATUS_LABELS).alias("status_label"),
    pl.col("duration")
    .map_elements(_format_duration, return_dtype=pl.Utf8)
    .alias("duration_display"),
    (pl.col("duration").dt.total_seconds() / 3600).alias("duration_hours"),
    pl.col("duration").dt.total_seconds().alias("duration_seconds"),
    pl.col("goal_amount_eur")
    .map_elements(lambda v: f"{v:,.0f} €", return_dtype=pl.Utf8)
    .alias("goal_amount_eur"),
)
display_columns = {
    "goal_category": t("tracker.column.category"),
    "goal_name": t("tracker.column.goal"),
    "goal_amount_eur": t("tracker.column.amount"),
    "status_label": t("tracker.column.status"),
    "started_at": t("tracker.column.started"),
    "completed_at": t("tracker.column.completed"),
    "duration_display": t("tracker.column.duration"),
    "duration_hours": t("tracker.column.duration_hours"),
    "duration_seconds": t("tracker.column.duration_seconds"),
}
display_table = table.select(list(display_columns.keys())).rename(display_columns)
st.dataframe(
    display_table,
    width="stretch",
    hide_index=True,
    column_config={
        t("tracker.column.duration_hours"): st.column_config.NumberColumn(format="%.2f h"),
        t("tracker.column.duration_seconds"): st.column_config.NumberColumn(format="%.0f s"),
    },
)
st.download_button(
    t("common.download_csv"),
    display_table.write_csv(),
    file_name="donation_tracker.csv",
    mime="text/csv",
)

page_footer()

logger.info("Donation Tracker page rendered (channel=%s, goals=%s)", channel, len(progress))
