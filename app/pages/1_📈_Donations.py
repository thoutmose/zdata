"""Donations page: cumulative total, pace, event-phase split, and leaderboard movement."""

from __future__ import annotations

import logging

import plotly.graph_objects as go
import polars as pl
import streamlit as st
from app.components.chrome import chart_explainer, page_header
from app.components.filters import period_filter
from app.components.theme import CATEGORICAL, apply_base_layout
from app.core.i18n import t
from app.core.logging_config import setup_logging
from app.data.repository import (
    get_data_quality_check,
    get_donation_timeseries,
    get_donations_by_category,
    get_event_phase_breakdown,
    get_leaderboard_movers,
)

setup_logging()
logger = logging.getLogger(__name__)

page_header(t("donations.title"), "📈", t("donations.description"))

df = get_donation_timeseries()
if df.is_empty():
    st.warning(t("donations.no_data"))
    st.stop()

st.subheader(t("donations.filters"))
df = period_filter(df, timestamp_col="timestamp", key="donations_period")

if df.is_empty():
    st.info(t("common.no_data_in_range"))
    st.stop()

latest = df.row(-1, named=True)
hourly_amount = df["cumulative_amount_eur"].diff().fill_null(df["cumulative_amount_eur"][0])

kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric(t("donations.kpi.total_raised"), f"{latest['cumulative_amount_eur']:,.0f} €")
kpi2.metric(t("donations.kpi.active_streamers"), f"{latest['active_streamers']:,}")
kpi3.metric(t("donations.kpi.best_hour"), f"{hourly_amount.max():,.0f} €")

cumulative_fig = go.Figure(
    go.Scatter(
        x=df["timestamp"],
        y=df["cumulative_amount_eur"],
        mode="lines",
        line={"color": CATEGORICAL[0], "width": 2},
        fill="tozeroy",
        fillcolor="rgba(42, 120, 214, 0.12)",
        hovertemplate="%{x|%a %H:%M}<br>%{y:,.0f} €<extra></extra>",
        name=t("donations.chart.cumulative"),
    )
)
apply_base_layout(cumulative_fig, title=t("donations.chart.cumulative"))
cumulative_fig.update_yaxes(title_text="€")
st.plotly_chart(cumulative_fig, width="stretch")
chart_explainer(t("donations.explain.cumulative"))

pace_fig = go.Figure(
    go.Bar(
        x=df["timestamp"],
        y=hourly_amount,
        marker_color=CATEGORICAL[0],
        hovertemplate="%{x|%a %H:%M}<br>%{y:,.0f} €<extra></extra>",
        name=t("donations.chart.pace"),
    )
)
apply_base_layout(pace_fig, title=t("donations.chart.pace"))
pace_fig.update_yaxes(title_text=t("common.per_hour", unit="€"))
st.plotly_chart(pace_fig, width="stretch")
chart_explainer(t("donations.explain.pace"))

st.subheader(t("donations.phases_heading"))
phases = get_event_phase_breakdown()
if not phases.is_empty():
    col_a, col_b = st.columns(2)
    with col_a:
        phase_fig = go.Figure(
            go.Bar(
                x=phases["phase"],
                y=phases["donations_eur"],
                marker_color=[CATEGORICAL[0], CATEGORICAL[1], CATEGORICAL[2]],
                hovertemplate="%{x}<br>%{y:,.0f} €<extra></extra>",
            )
        )
        apply_base_layout(phase_fig, title=t("donations.chart.by_phase"), height=340)
        phase_fig.update_yaxes(title_text="€")
        phase_fig.update_layout(showlegend=False)
        st.plotly_chart(phase_fig, width="stretch")
        chart_explainer(t("donations.explain.phase"))
    with col_b:
        st.caption(t("donations.phases_caption"))
        st.dataframe(phases, width="stretch", hide_index=True)

st.subheader(t("donations.by_activity_heading"))
by_category = get_donations_by_category()
if by_category.is_empty():
    st.info(t("donations.no_activity_data"))
else:
    st.caption(t("donations.by_activity_caption"))
    ordered_categories = by_category.sort("donations_eur", descending=False)
    activity_fig = go.Figure(
        go.Bar(
            x=ordered_categories["donations_eur"],
            y=ordered_categories["category"],
            orientation="h",
            marker_color=CATEGORICAL[0],
            hovertemplate="%{y}<br>%{x:,.0f} €<extra></extra>",
        )
    )
    apply_base_layout(
        activity_fig,
        title=t("donations.chart.by_activity"),
        height=max(320, 32 * len(ordered_categories)),
    )
    activity_fig.update_xaxes(title_text="€")
    activity_fig.update_layout(showlegend=False)
    st.plotly_chart(activity_fig, width="stretch")
    chart_explainer(t("donations.explain.by_activity"))

st.subheader(t("donations.movers_heading"))
movers = get_leaderboard_movers()
if not movers.is_empty():
    st.caption(t("donations.movers_caption"))
    movers_display = movers.with_columns(
        pl.when(pl.col("rank_change") > 0)
        .then(pl.lit("▲ ") + pl.col("rank_change").cast(pl.Utf8))
        .when(pl.col("rank_change") < 0)
        .then(pl.lit("▼ ") + pl.col("rank_change").abs().cast(pl.Utf8))
        .otherwise(pl.lit("— 0"))
        .alias("rank_change")
    )
    st.dataframe(movers_display, width="stretch", hide_index=True)

with st.expander(t("donations.quality_heading")):
    quality = get_data_quality_check()
    if quality.is_empty():
        st.caption(t("donations.quality_no_data"))
    else:
        quality_row = quality.row(0, named=True)
        divergence = quality_row["divergence_eur"]
        checked_at_str = f"{quality_row['checked_at']:%H:%M} (Europe/Paris)"
        if abs(divergence) < 0.01:
            st.success(
                t("donations.quality_ok", divergence=f"{divergence:,.2f}", time=checked_at_str)
            )
        else:
            st.warning(
                t("donations.quality_bad", divergence=f"{divergence:,.2f}", time=checked_at_str)
            )
        st.caption(t("donations.quality_caption"))

with st.expander(t("common.view_data")):
    st.dataframe(df, width="stretch", hide_index=True)
    st.download_button(
        t("common.download_csv"), df.write_csv(), file_name="donations.csv", mime="text/csv"
    )

logger.info("Donations page rendered (rows=%s)", len(df))
