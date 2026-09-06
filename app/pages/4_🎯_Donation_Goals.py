"""Donation Goals page: the fun/absurd milestone goals streamers set for donations.

Real goal amounts are streamer-chosen and often intentionally exaggerated for
humor (goals in the hundreds of millions of euros exist as jokes), so this
page charts counts by default and lets an analyst explore the raw amount
distribution (log scale, adjustable cutoff) themselves rather than trusting
one hardcoded threshold — see `app/data/repository.py::PostgresDataSource`.
"""

from __future__ import annotations

import logging

import numpy as np
import plotly.graph_objects as go
import polars as pl
import streamlit as st
from app.components.chrome import (
    chart_explainer,
    date_filter_caveat,
    entity_filter_caveat,
    page_footer,
    page_header,
)
from app.components.filters import apply_global_streamer_filter, get_global_streamer_names
from app.components.theme import CATEGORICAL, apply_base_layout
from app.core.i18n import t
from app.core.logging_config import setup_logging
from app.data.repository import (
    get_goal_ambition_vs_reality,
    get_goal_amount_distribution,
    get_goals_by_category,
    get_top_goal_setters,
)

setup_logging()
logger = logging.getLogger(__name__)

page_header(t("goals.title"), "🎯", t("goals.description"))

by_category = get_goals_by_category()
top_setters = get_top_goal_setters()
amounts = get_goal_amount_distribution()
if by_category.is_empty():
    st.warning(t("goals.no_data"))
    st.stop()

st.caption(t("goals.caveat"))

selected_streamer_names = get_global_streamer_names()
if selected_streamer_names:
    top_setters = top_setters.filter(pl.col("streamer_name").is_in(selected_streamer_names))

kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric(t("goals.kpi.total_goals"), f"{by_category['goal_count'].sum():,}")
kpi2.metric(t("goals.kpi.categories"), f"{len(by_category):,}")
kpi3.metric(
    t("goals.kpi.streamers"),
    f"{top_setters['goal_count'].count():,}" if not top_setters.is_empty() else "—",
)

st.subheader(t("goals.category_heading"))
date_filter_caveat()
entity_filter_caveat()
category_sorted = by_category.sort("goal_count", descending=False)
category_fig = go.Figure(
    go.Bar(
        x=category_sorted["goal_count"],
        y=category_sorted["category"],
        orientation="h",
        marker_color=CATEGORICAL[0],
        hovertemplate="%{y}<br>%{x:,} goals<extra></extra>",
    )
)
apply_base_layout(
    category_fig, title=t("goals.chart.by_category"), height=max(320, 32 * len(category_sorted))
)
category_fig.update_xaxes(title_text=t("common.unit.goals"))
category_fig.update_layout(showlegend=False)
st.plotly_chart(category_fig, width="stretch")
chart_explainer(t("goals.explain.by_category"))

if not top_setters.is_empty():
    setters_sorted = top_setters.sort("goal_count", descending=False)
    setters_fig = go.Figure(
        go.Bar(
            x=setters_sorted["goal_count"],
            y=setters_sorted["streamer_name"],
            orientation="h",
            marker_color=CATEGORICAL[1],
            hovertemplate="%{y}<br>%{x:,} goals<extra></extra>",
        )
    )
    apply_base_layout(
        setters_fig, title=t("goals.chart.top_setters"), height=max(320, 32 * len(setters_sorted))
    )
    setters_fig.update_xaxes(title_text=t("common.unit.goals"))
    setters_fig.update_layout(showlegend=False)
    st.plotly_chart(setters_fig, width="stretch")
    chart_explainer(t("goals.explain.top_setters"))

st.subheader(t("goals.distribution_heading"))
date_filter_caveat()
entity_filter_caveat()
if amounts.is_empty():
    st.info(t("goals.no_amounts"))
else:
    st.caption(t("goals.distribution_caption"))
    cutoff = st.slider(
        t("goals.cutoff_slider"),
        min_value=100,
        max_value=1_000_000,
        value=100_000,
        step=100,
        format="€%d",
    )
    below = amounts.filter(pl.col("goal_amount_eur") < cutoff)
    above_count = len(amounts) - len(below)

    dist_col1, dist_col2 = st.columns([3, 1])
    with dist_col1:
        log_values = np.log10(amounts["goal_amount_eur"].clip(lower_bound=1).to_numpy())
        hist_fig = go.Figure(
            go.Histogram(
                x=log_values,
                marker_color=CATEGORICAL[0],
                nbinsx=40,
                hovertemplate="10^%{x:.1f} €<br>%{y} goals<extra></extra>",
            )
        )
        hist_fig.add_vline(
            x=np.log10(max(cutoff, 1)), line_color=CATEGORICAL[7], line_width=2, line_dash="dash"
        )
        apply_base_layout(hist_fig, title=t("goals.chart.distribution"), height=360)
        hist_fig.update_xaxes(title_text=t("goals.log_amount_axis"))
        hist_fig.update_yaxes(title_text=t("common.unit.goals"))
        hist_fig.update_layout(showlegend=False)
        st.plotly_chart(hist_fig, width="stretch")
        chart_explainer(t("goals.explain.distribution"))
    with dist_col2:
        st.metric(t("goals.kpi.below_cutoff"), f"{len(below):,}")
        st.metric(t("goals.kpi.above_cutoff"), f"{above_count:,}")
        st.caption(t("goals.cutoff_caption"))

st.subheader(t("goals.ambition_heading"))
date_filter_caveat()
ambition = apply_global_streamer_filter(get_goal_ambition_vs_reality(), channel_col="twitch_login")
if ambition.is_empty():
    st.info(t("goals.no_ambition"))
else:
    st.caption(t("goals.ambition_caption"))
    least_covered = ambition.sort("pct_of_goals_covered", descending=False).head(15)
    ambition_fig = go.Figure(
        go.Bar(
            x=least_covered["pct_of_goals_covered"],
            y=least_covered["twitch_login"],
            orientation="h",
            marker_color=CATEGORICAL[2],
            hovertemplate="%{y}<br>%{x:.1f}% covered<extra></extra>",
        )
    )
    apply_base_layout(
        ambition_fig, title=t("goals.chart.ambition"), height=max(360, 28 * len(least_covered))
    )
    ambition_fig.update_xaxes(title_text=t("goals.ambition_axis"))
    ambition_fig.update_layout(showlegend=False, yaxis={"autorange": "reversed"})
    st.plotly_chart(ambition_fig, width="stretch")
    chart_explainer(t("goals.explain.ambition"))

with st.expander(t("common.view_data")):
    st.dataframe(by_category, width="stretch", hide_index=True)
    st.dataframe(top_setters, width="stretch", hide_index=True)
    st.download_button(
        t("common.download_csv"),
        by_category.write_csv(),
        file_name="goals_by_category.csv",
        mime="text/csv",
    )

page_footer()

logger.info("Donation Goals page rendered (categories=%s)", len(by_category))
