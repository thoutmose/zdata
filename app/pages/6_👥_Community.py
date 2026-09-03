"""Community page: who's chatting, how loyal they are, and which channels share audiences."""

from __future__ import annotations

import logging

import plotly.graph_objects as go
import polars as pl
import streamlit as st
from app.components.chrome import chart_explainer, page_header
from app.components.filters import period_filter
from app.components.network_graph import build_network_figure
from app.components.theme import CATEGORICAL, SEQUENTIAL_BLUE, apply_base_layout
from app.core.i18n import t
from app.core.logging_config import setup_logging
from app.data.bot_heuristic import bot_filter_expr
from app.data.repository import (
    get_channel_network,
    get_chatter_account_age_mix,
    get_chatter_growth_timeseries,
    get_chatter_profile_mix,
    get_hourly_network,
    get_hourly_network_hours,
    get_top_chatters,
)

setup_logging()
logger = logging.getLogger(__name__)

page_header(t("community.title"), "👥", t("community.description"))

profile_mix = get_chatter_profile_mix()
if profile_mix.is_empty():
    st.warning(t("community.no_data"))
    st.stop()

total_chatters = int(profile_mix["chatter_count"].sum())
loyal_chatters = int(profile_mix.filter(pl.col("profile") == "sedentaire")["chatter_count"].sum())
multi_channel = total_chatters - loyal_chatters
kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric(t("community.kpi.total_chatters"), f"{total_chatters:,}")
kpi2.metric(t("community.kpi.multi_channel"), f"{multi_channel:,}")
kpi3.metric(
    t("community.kpi.loyal_share"),
    f"{loyal_chatters / total_chatters:.0%}" if total_chatters else "—",
)

st.subheader(t("community.growth_heading"))
growth = get_chatter_growth_timeseries()
if not growth.is_empty():
    # Cumulative sum computed on the full series *before* the period filter,
    # then windowed for display — filtering first would make the curve
    # restart from zero at the window's start instead of showing the true
    # running total.
    growth = growth.with_columns(pl.col("new_chatters").cum_sum().alias("cumulative_chatters"))
    growth_shown = period_filter(growth, timestamp_col="timestamp", key="community_growth_period")
    if not growth_shown.is_empty():
        st.caption(t("community.growth_caption"))
        growth_fig = go.Figure(
            go.Scatter(
                x=growth_shown["timestamp"],
                y=growth_shown["cumulative_chatters"],
                mode="lines",
                line={"color": CATEGORICAL[0], "width": 2},
                fill="tozeroy",
                fillcolor="rgba(42, 120, 214, 0.12)",
                hovertemplate="%{x|%a %H:%M}<br>%{y:,.0f} chatters<extra></extra>",
            )
        )
        apply_base_layout(growth_fig, title=t("community.chart.growth"), height=340)
        growth_fig.update_yaxes(title_text=t("community.cumulative_chatters"))
        st.plotly_chart(growth_fig, width="stretch")
        chart_explainer(t("community.explain.growth"))

# Fetched early so every channel that ever appears in the event-wide network
# is part of the color universe — a channel keeps the same node color in the
# hourly graph below regardless of which hour (and therefore which subset of
# channels) is selected.
network = get_channel_network()
channel_universe = sorted(set(network["channel_a"].to_list()) | set(network["channel_b"].to_list()))

st.subheader(t("community.hourly_network_heading"))
network_hours = get_hourly_network_hours()
if not network_hours:
    st.info(t("community.no_hourly_network"))
else:
    st.caption(t("community.hourly_network_caption"))
    selected_hour = st.select_slider(
        t("community.hour_picker"),
        options=network_hours,
        value=network_hours[-1],
        format_func=lambda ts: ts.strftime("%a %H:%M"),
    )
    hourly_edges = get_hourly_network(selected_hour)
    if hourly_edges.is_empty():
        st.info(t("community.no_hourly_network"))
    else:
        hourly_universe = sorted(
            set(channel_universe)
            | set(hourly_edges["channel_a"].to_list())
            | set(hourly_edges["channel_b"].to_list())
        )
        network_fig = build_network_figure(
            hourly_edges,
            a_col="channel_a",
            b_col="channel_b",
            weight_col="shared_chatter_count",
            title=t("community.chart.hourly_network", hour=selected_hour.strftime("%a %H:%M")),
            color_universe=hourly_universe,
        )
        st.plotly_chart(network_fig, width="stretch")
        chart_explainer(t("community.explain.hourly_network"))

col_a, col_b = st.columns(2)
with col_a:
    profile_labels = {
        "sedentaire": t("common.chatter_profile.loyal"),
        "multi_streamer": t("common.chatter_profile.multi_streamer"),
        "semi_nomade": t("common.chatter_profile.semi_nomad"),
        "nomade": t("common.chatter_profile.nomad"),
    }
    order = ["sedentaire", "multi_streamer", "semi_nomade", "nomade"]
    counts_by_profile = dict(
        zip(profile_mix["profile"].to_list(), profile_mix["chatter_count"].to_list(), strict=False)
    )
    mix_fig = go.Figure(
        go.Bar(
            x=[profile_labels[p] for p in order],
            y=[counts_by_profile.get(p, 0) for p in order],
            marker_color=CATEGORICAL[:4],
        )
    )
    apply_base_layout(mix_fig, title=t("community.chart.loyalty_mix"), height=340)
    mix_fig.update_yaxes(title_text=t("common.unit.chatters"))
    mix_fig.update_layout(showlegend=False)
    st.plotly_chart(mix_fig, width="stretch")
    st.caption(t("common.chatter_profile.caption"))
    chart_explainer(t("community.explain.loyalty_mix"))

with col_b:
    age_mix = get_chatter_account_age_mix()
    if not age_mix.is_empty():
        age_order = ["new (<30d)", "1mo-1yr", "1-3yr", "3yr+", "unknown"]
        age_labels = {
            "new (<30d)": t("community.age.new"),
            "1mo-1yr": t("community.age.month_to_year"),
            "1-3yr": t("community.age.one_to_three"),
            "3yr+": t("community.age.three_plus"),
            "unknown": t("community.age.unknown"),
        }
        age_colors = [
            SEQUENTIAL_BLUE[0],
            SEQUENTIAL_BLUE[2],
            SEQUENTIAL_BLUE[3],
            SEQUENTIAL_BLUE[5],
            "#c3c2b7",
        ]
        counts_by_age = dict(
            zip(age_mix["age_bucket"].to_list(), age_mix["chatter_count"].to_list(), strict=False)
        )
        age_fig = go.Figure(
            go.Bar(
                x=[age_labels[b] for b in age_order],
                y=[counts_by_age.get(b, 0) for b in age_order],
                marker_color=age_colors,
            )
        )
        apply_base_layout(age_fig, title=t("community.chart.account_age"), height=340)
        age_fig.update_yaxes(title_text=t("common.unit.chatters"))
        age_fig.update_layout(showlegend=False)
        st.plotly_chart(age_fig, width="stretch")
        st.caption(t("community.age_caption"))
        chart_explainer(t("community.explain.account_age"))

st.subheader(t("community.chatters_heading"))
top_chatters = get_top_chatters()
if top_chatters.is_empty():
    st.info(t("community.no_chatters"))
else:
    st.caption(t("community.chatters_caption"))
    filter_col1, filter_col2 = st.columns([2, 1])
    with filter_col1:
        channel_options = sorted(top_chatters["channel"].unique().to_list())
        channel_filter = st.multiselect(
            t("community.channel_filter"), options=channel_options, default=[]
        )
    with filter_col2:
        hide_bots = st.checkbox(t("community.hide_bots"), value=True)

    shown_chatters = top_chatters
    if channel_filter:
        shown_chatters = shown_chatters.filter(pl.col("channel").is_in(channel_filter))
    if hide_bots:
        shown_chatters = shown_chatters.filter(~bot_filter_expr())

    if shown_chatters.is_empty():
        st.info(t("common.no_data_in_range"))
    else:
        if len(shown_chatters) <= 1:
            top_n = len(shown_chatters)
        else:
            top_n = st.slider(
                t("community.top_n"),
                min_value=1,
                max_value=len(shown_chatters),
                value=min(15, len(shown_chatters)),
            )
        ordered_chatters = shown_chatters.sort("message_count", descending=True).head(top_n)
        ordered_chatters = ordered_chatters.sort("message_count", descending=False)
        chatters_fig = go.Figure(
            go.Bar(
                x=ordered_chatters["message_count"],
                y=ordered_chatters["chatter"],
                orientation="h",
                marker_color=CATEGORICAL[0],
                hovertemplate="%{y}<br>%{x:,.0f} messages<extra></extra>",
            )
        )
        apply_base_layout(
            chatters_fig,
            title=t("community.chart.top_chatters"),
            height=max(360, 28 * len(ordered_chatters)),
        )
        chatters_fig.update_yaxes(type="category", title_text="")
        chatters_fig.update_xaxes(title_text=t("common.unit.messages"))
        chatters_fig.update_layout(showlegend=False)
        st.plotly_chart(chatters_fig, width="stretch")
        chart_explainer(t("community.explain.top_chatters"))

st.subheader(t("community.network_heading"))
if network.is_empty():
    st.info(t("community.no_network"))
else:
    st.caption(t("community.network_caption"))
    overall_network_fig = build_network_figure(
        network,
        a_col="channel_a",
        b_col="channel_b",
        weight_col="shared_chatter_count",
        title=t("community.chart.network"),
        height=520,
        color_universe=channel_universe,
    )
    st.plotly_chart(overall_network_fig, width="stretch")
    chart_explainer(t("community.explain.network"))

with st.expander(t("common.view_data")):
    st.dataframe(profile_mix, width="stretch", hide_index=True)
    st.dataframe(network, width="stretch", hide_index=True)
    st.download_button(
        t("common.download_csv"),
        network.write_csv(),
        file_name="channel_network.csv",
        mime="text/csv",
    )

logger.info("Community page rendered (chatters=%s, network_pairs=%s)", total_chatters, len(network))
