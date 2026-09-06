"""Live Chat page: message activity, busiest channels, activity heatmap, and emote usage."""

from __future__ import annotations

import logging

import plotly.graph_objects as go
import polars as pl
import streamlit as st
from app.components.chrome import (
    bounded_top_n_slider,
    chart_explainer,
    date_filter_caveat,
    entity_filter_caveat,
    page_footer,
    page_header,
)
from app.components.filters import (
    apply_global_chatter_filter,
    apply_global_date_filter,
    apply_global_streamer_filter,
    get_global_date_range,
)
from app.components.search import consume_search_query
from app.components.theme import (
    CATEGORICAL,
    CHROME,
    SEQUENTIAL_GREEN_HEATMAP_COLORSCALE,
    STATUS,
    apply_base_layout,
    build_pie_figure,
    build_race_figure,
    hex_to_rgba,
)
from app.core.i18n import t
from app.core.logging_config import setup_logging
from app.data.emote_cdn import emote_image_url
from app.data.repository import (
    get_channel_hour_heatmap,
    get_channel_messages_leaderboard_timeseries,
    get_chat_activity_timeseries,
    get_chat_engagement_rate,
    get_chat_spikes,
    get_chatter_channel_breakdown,
    get_emote_catalog_search,
    get_emote_usage_search,
    get_streamer_breakdown,
    get_top_chat_channels,
    get_top_chatters,
    get_top_emotes,
)

setup_logging()
logger = logging.getLogger(__name__)

page_header(t("chat.title"), "💬", t("chat.description"))

activity = get_chat_activity_timeseries()
if activity.is_empty():
    st.warning(t("chat.no_data"))
    st.stop()

date_range = get_global_date_range()
activity = apply_global_date_filter(activity, timestamp_col="timestamp")

if activity.is_empty():
    st.info(t("common.no_data_in_range"))
    st.stop()

entity_filter_caveat()
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
        fillcolor=hex_to_rgba(CATEGORICAL[0], 0.12),
        hovertemplate="%{x|%a %H:%M}<br>%{y:,.0f} messages<extra></extra>",
        name=t("chat.chart.activity"),
    )
)
apply_base_layout(activity_fig, title=t("chat.chart.activity"))
activity_fig.update_yaxes(title_text=t("common.per_hour", unit=t("common.unit.messages")))
st.plotly_chart(activity_fig, width="stretch")
chart_explainer(t("chat.explain.activity"))

st.subheader(t("chat.message_race_heading"))
message_race_top_n = bounded_top_n_slider(
    label=t("chat.message_race_top_n"),
    max_value=len(apply_global_streamer_filter(get_streamer_breakdown())),
    key="chat_message_race_top_n",
    default_n=8,
)
message_race = (
    get_channel_messages_leaderboard_timeseries(*date_range, message_race_top_n)
    if date_range
    else pl.DataFrame()
)
message_race = apply_global_streamer_filter(message_race)
if message_race.is_empty():
    st.info(t("chat.no_message_race"))
else:
    st.caption(t("chat.message_race_caption"))
    message_race_fig = build_race_figure(
        message_race,
        value_col="message_count",
        rank_col="message_rank_at_hour",
        title=t("chat.chart.message_race"),
        unit=t("common.unit.messages"),
    )
    st.plotly_chart(message_race_fig, width="stretch")
    chart_explainer(t("chat.explain.message_race"))

st.subheader(t("chat.engagement_heading"))
st.caption(t("chat.engagement_caption"))
entity_filter_caveat()
engagement = apply_global_date_filter(get_chat_engagement_rate(), timestamp_col="timestamp")
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
heatmap = apply_global_date_filter(get_channel_hour_heatmap(), timestamp_col="timestamp")
heatmap = apply_global_streamer_filter(heatmap)
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
    # None (not 0) for a channel/hour with no row at all — a channel that
    # simply wasn't active that hour is a *missing* cell, not a measured
    # zero, and should render as the chart's background rather than the
    # colorscale's own floor color, or every quiet hour would look like it
    # had a little activity everywhere.
    z = [[counts_by_cell.get((ch, ts)) for ts in heatmap_hours] for ch in heatmap_channels]

    heat_fig = go.Figure(
        go.Heatmap(
            z=z,
            x=[ts.strftime("%a %H:%M") for ts in heatmap_hours],
            y=heatmap_channels,
            colorscale=SEQUENTIAL_GREEN_HEATMAP_COLORSCALE,
            hovertemplate="%{y}<br>%{x}<br>%{z:,.0f} messages<extra></extra>",
            hoverongaps=False,
            xgap=2,
            ygap=2,
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

st.subheader(t("chat.spikes_heading"))
spikes = get_chat_spikes(*date_range) if date_range else pl.DataFrame()
spikes = apply_global_streamer_filter(spikes)
if spikes.is_empty():
    st.info(t("chat.no_spikes"))
else:
    st.caption(t("chat.spikes_caption"))
    spikes_ordered = spikes.sort("message_count_zscore", descending=False).with_columns(
        (pl.col("channel") + " — " + pl.col("hour_bucket").dt.strftime("%a %H:%M")).alias(
            "spike_label"
        )
    )

    def _spike_color(zscore: float) -> str:
        if zscore >= 4:
            return STATUS["critical"]
        if zscore >= 3:
            return STATUS["warning"]
        return STATUS["good"]

    spikes_fig = go.Figure(
        go.Bar(
            x=spikes_ordered["message_count_zscore"],
            y=spikes_ordered["spike_label"],
            orientation="h",
            marker_color=[_spike_color(z) for z in spikes_ordered["message_count_zscore"]],
            hovertemplate="%{y}<br>z-score %{x:.1f}<extra></extra>",
        )
    )
    apply_base_layout(
        spikes_fig, title=t("chat.chart.spikes"), height=max(360, 28 * len(spikes_ordered))
    )
    spikes_fig.update_xaxes(title_text=t("chat.spikes_axis"))
    spikes_fig.update_layout(showlegend=False)
    st.plotly_chart(spikes_fig, width="stretch")
    chart_explainer(t("chat.explain.spikes"))

date_filter_caveat()
st.subheader(t("chat.channels_heading"))
channels = apply_global_streamer_filter(get_top_chat_channels())
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

    st.subheader(t("chat.verbosity_heading"))
    st.caption(t("chat.verbosity_caption"))
    verbosity_ordered = channels.sort("avg_message_length", descending=False)
    verbosity_fig = go.Figure(
        go.Bar(
            x=verbosity_ordered["avg_message_length"],
            y=verbosity_ordered["channel"],
            orientation="h",
            marker_color=CATEGORICAL[4],
            hovertemplate="%{y}<br>%{x:.0f} characters/message<extra></extra>",
        )
    )
    apply_base_layout(
        verbosity_fig, title=t("chat.chart.verbosity"), height=max(360, 32 * len(verbosity_ordered))
    )
    verbosity_fig.update_xaxes(title_text=t("chat.verbosity_axis"))
    verbosity_fig.update_layout(showlegend=False)
    st.plotly_chart(verbosity_fig, width="stretch")
    chart_explainer(t("chat.explain.verbosity"))

st.subheader(t("chat.emotes_heading"))
entity_filter_caveat()
emotes = get_top_emotes(*date_range) if date_range else pl.DataFrame()
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

st.subheader(t("chat.emote_search_heading"))
st.caption(t("chat.emote_search_caption"))
pending_emote_query = consume_search_query()
if pending_emote_query:
    st.session_state["emote_search_box"] = pending_emote_query
emote_query = st.text_input(t("chat.emote_search_label"), key="emote_search_box")
if emote_query:
    catalog_matches = get_emote_catalog_search(emote_query)
    if catalog_matches.is_empty():
        st.info(t("chat.emote_search_no_matches"))
    else:
        option_labels = [
            f"{row['emote_code']} ({row['service']})"
            for row in catalog_matches.iter_rows(named=True)
        ]
        selected_label = st.selectbox(t("chat.emote_search_pick"), options=option_labels)
        selected_row = catalog_matches.row(option_labels.index(selected_label), named=True)

        img_col, label_col = st.columns([1, 8])
        with img_col:
            image_url = emote_image_url(selected_row["service"], selected_row["emote_id"])
            if image_url:
                st.image(image_url, width=40)
        with label_col:
            st.caption(selected_label)

        results = (
            get_emote_usage_search(selected_row["emote_id"], *date_range)
            if date_range
            else pl.DataFrame()
        )
        if results.is_empty():
            st.info(t("chat.emote_search_no_usage"))
        else:
            st.caption(t("chat.emote_search_results_caption", count=len(results)))
            st.dataframe(
                results.select("message_sent_at", "channel", "chatter", "message_text"),
                width="stretch",
                hide_index=True,
            )


def _top_n_plus_other(
    frame: pl.DataFrame, label_col: str, value_col: str, n: int = 7
) -> tuple[list[str], list[float], list[str]]:
    """Collapse a long-tail distribution into its top N slices plus one "Other" slice.

    A pie/donut with more slices than that stops being readable — this keeps
    every breakdown legible regardless of how many distinct channels,
    chatters, or emotes exist, without silently hiding how much volume the
    tail represents.
    """
    ordered = frame.sort(value_col, descending=True)
    top = ordered.head(n)
    rest_total = ordered.tail(max(0, len(ordered) - n))[value_col].sum()
    labels = top[label_col].to_list()
    values = top[value_col].to_list()
    colors = [CATEGORICAL[i % len(CATEGORICAL)] for i in range(len(labels))]
    if rest_total:
        labels.append(t("common.pie_other"))
        values.append(rest_total)
        colors.append(CHROME["baseline"])
    return labels, values, colors


st.subheader(t("chat.breakdown_heading"))
st.caption(t("chat.breakdown_caption"))
breakdown_options = {
    t("chat.breakdown.by_channel"): "channel",
    t("chat.breakdown.by_chatter"): "chatter",
    t("chat.breakdown.by_time"): "time",
    t("chat.breakdown.by_emote"): "emote",
}
breakdown_choice = st.radio(
    t("chat.breakdown_dimension"), list(breakdown_options.keys()), horizontal=True
)
breakdown_dimension = breakdown_options[breakdown_choice]

if breakdown_dimension == "channel":
    if channels.is_empty():
        st.info(t("common.no_data_in_range"))
    else:
        pie_labels, pie_values, pie_colors = _top_n_plus_other(
            channels, "channel", "message_count"
        )
        st.plotly_chart(
            build_pie_figure(
                pie_labels,
                pie_values,
                title=t("chat.chart.breakdown_channel"),
                colors=pie_colors,
                unit=t("common.unit.messages"),
            ),
            width="stretch",
        )
elif breakdown_dimension == "chatter":
    chatters_for_breakdown = get_top_chatters(*date_range) if date_range else pl.DataFrame()
    chatters_for_breakdown = apply_global_chatter_filter(
        apply_global_streamer_filter(chatters_for_breakdown)
    )
    if chatters_for_breakdown.is_empty():
        st.info(t("common.no_data_in_range"))
    else:
        by_chatter = chatters_for_breakdown.group_by("chatter").agg(
            pl.col("message_count").sum()
        )
        pie_labels, pie_values, pie_colors = _top_n_plus_other(
            by_chatter, "chatter", "message_count"
        )
        st.plotly_chart(
            build_pie_figure(
                pie_labels,
                pie_values,
                title=t("chat.chart.breakdown_chatter"),
                colors=pie_colors,
                unit=t("common.unit.messages"),
            ),
            width="stretch",
        )
elif breakdown_dimension == "time":
    if activity.is_empty():
        st.info(t("common.no_data_in_range"))
    else:
        daypart_hour = pl.col("timestamp").dt.hour()
        by_daypart = (
            activity.with_columns(
                pl.when(daypart_hour.is_between(6, 11))
                .then(pl.lit("morning"))
                .when(daypart_hour.is_between(12, 17))
                .then(pl.lit("afternoon"))
                .when(daypart_hour.is_between(18, 23))
                .then(pl.lit("evening"))
                .otherwise(pl.lit("night"))
                .alias("daypart")
            )
            .group_by("daypart")
            .agg(pl.col("message_count").sum())
        )
        daypart_order = ["morning", "afternoon", "evening", "night"]
        daypart_labels = {
            "morning": t("chat.daypart.morning"),
            "afternoon": t("chat.daypart.afternoon"),
            "evening": t("chat.daypart.evening"),
            "night": t("chat.daypart.night"),
        }
        counts_by_daypart = dict(
            zip(
                by_daypart["daypart"].to_list(),
                by_daypart["message_count"].to_list(),
                strict=False,
            )
        )
        present = [d for d in daypart_order if counts_by_daypart.get(d, 0)]
        pie_labels = [daypart_labels[d] for d in present]
        pie_values = [counts_by_daypart[d] for d in present]
        pie_colors = [CATEGORICAL[i % len(CATEGORICAL)] for i in range(len(pie_labels))]
        st.plotly_chart(
            build_pie_figure(
                pie_labels,
                pie_values,
                title=t("chat.chart.breakdown_time"),
                colors=pie_colors,
                unit=t("common.unit.messages"),
            ),
            width="stretch",
        )
else:  # emote
    if emotes.is_empty():
        st.info(t("chat.no_emotes"))
    else:
        pie_labels, pie_values, pie_colors = _top_n_plus_other(emotes, "emote", "usage_count")
        st.plotly_chart(
            build_pie_figure(
                pie_labels,
                pie_values,
                title=t("chat.chart.breakdown_emote"),
                colors=pie_colors,
                unit=t("chat.uses_axis"),
            ),
            width="stretch",
        )
chart_explainer(t("chat.explain.breakdown"))

st.subheader(t("chat.drilldown_heading"))
st.caption(t("chat.drilldown_caption"))
chatters_for_drilldown = get_top_chatters(*date_range) if date_range else pl.DataFrame()
chatters_for_drilldown = apply_global_chatter_filter(
    apply_global_streamer_filter(chatters_for_drilldown)
)
drilldown_col1, drilldown_col2 = st.columns(2)
with drilldown_col1:
    st.markdown(f"**{t('chat.drilldown_chatter_heading')}**")
    if chatters_for_drilldown.is_empty():
        st.info(t("common.no_data_in_range"))
    else:
        chatter_options = chatters_for_drilldown.sort("message_count", descending=True)[
            "chatter"
        ].to_list()
        picked_chatter = st.selectbox(
            t("chat.drilldown_pick_chatter"), options=chatter_options, key="chat_drilldown_chatter"
        )
        picked_chatter_id = chatters_for_drilldown.filter(pl.col("chatter") == picked_chatter).row(
            0, named=True
        )["chatter_id"]
        chatter_channels = get_chatter_channel_breakdown(picked_chatter_id)
        if chatter_channels.is_empty():
            st.info(t("chatters.no_channel_data"))
        else:
            pie_labels, pie_values, pie_colors = _top_n_plus_other(
                chatter_channels, "channel", "message_count"
            )
            st.plotly_chart(
                build_pie_figure(
                    pie_labels,
                    pie_values,
                    title=t("chat.chart.drilldown_chatter", chatter=picked_chatter),
                    height=360,
                    colors=pie_colors,
                    unit=t("common.unit.messages"),
                ),
                width="stretch",
            )
with drilldown_col2:
    st.markdown(f"**{t('chat.drilldown_channel_heading')}**")
    # Only offer channels actually represented in the (global, top-60)
    # chatter leaderboard — the leaderboard tracks one primary channel per
    # chatter, so a high-traffic channel whose audience is mostly casual
    # (not among the event's top individual posters) can legitimately have
    # zero entries; offering it here would always be a dead end regardless
    # of which one is picked by default.
    channels_with_leaderboard_entries = (
        set(chatters_for_drilldown["channel"].to_list())
        if not chatters_for_drilldown.is_empty()
        else set()
    )
    channel_options = [
        c
        for c in channels.sort("message_count", descending=True)["channel"].to_list()
        if c in channels_with_leaderboard_entries
    ]
    if not channel_options:
        st.info(t("common.no_data_in_range"))
    else:
        picked_channel = st.selectbox(
            t("chat.drilldown_pick_channel"), options=channel_options, key="chat_drilldown_channel"
        )
        channel_chatters = chatters_for_drilldown.filter(pl.col("channel") == picked_channel)
        pie_labels, pie_values, pie_colors = _top_n_plus_other(
            channel_chatters, "chatter", "message_count"
        )
        st.plotly_chart(
            build_pie_figure(
                pie_labels,
                pie_values,
                title=t("chat.chart.drilldown_channel", channel=picked_channel),
                height=360,
                colors=pie_colors,
                unit=t("common.unit.messages"),
            ),
            width="stretch",
        )
chart_explainer(t("chat.explain.drilldown"))

with st.expander(t("common.view_data")):
    st.dataframe(activity, width="stretch", hide_index=True)
    st.dataframe(channels, width="stretch", hide_index=True)
    st.download_button(
        t("common.download_csv"),
        activity.write_csv(),
        file_name="chat_activity.csv",
        mime="text/csv",
    )

page_footer()

logger.info("Live Chat page rendered (activity_rows=%s, channels=%s)", len(activity), len(channels))
