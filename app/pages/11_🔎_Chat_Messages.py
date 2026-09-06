"""Chat Messages page: browse and search individual chat messages.

Chat usernames are real and shown on-screen, exactly as on the Chatters,
Streamers, and Community pages (see `app/pages/8_🗣️_Chatters.py`'s module
docstring) — the CSV export is the one place a real identifier must never
leave the app, so it goes through `anonymize_chatters` first, same as there.
"""

from __future__ import annotations

import logging

import plotly.graph_objects as go
import polars as pl
import streamlit as st
from app.components.chrome import chart_explainer, page_footer, page_header
from app.components.filters import (
    apply_global_chatter_filter,
    apply_global_streamer_filter,
    get_global_date_range,
    get_global_streamer_filter,
)
from app.components.theme import CATEGORICAL, apply_base_layout, build_pie_figure, hex_to_rgba
from app.core.i18n import t
from app.core.logging_config import setup_logging
from app.data.anonymize import anonymize_chatters
from app.data.bot_heuristic import bot_filter_expr
from app.data.repository import get_chat_channel_list, get_chat_message_search

setup_logging()
logger = logging.getLogger(__name__)

page_header(t("messages.title"), "🔎", t("messages.description"))

date_range = get_global_date_range()
if date_range is None:
    st.warning(t("messages.no_data"))
    st.stop()

st.subheader(t("messages.filters"))
filter_col1, filter_col2, filter_col3, filter_col4, filter_col5 = st.columns([2, 2, 2, 1, 1])
with filter_col1:
    channel_options = get_chat_channel_list()
    selected_streamers = get_global_streamer_filter()
    if selected_streamers:
        channel_options = [c for c in channel_options if c in selected_streamers]
    channel_pick = st.selectbox(
        t("messages.channel_filter"),
        options=[t("messages.all_channels"), *channel_options],
    )
    channel = None if channel_pick == t("messages.all_channels") else channel_pick
with filter_col2:
    chatter_query = st.text_input(t("messages.chatter_search"))
with filter_col3:
    text_query = st.text_input(t("messages.text_search"))
with filter_col4:
    limit = st.selectbox(t("messages.limit_label"), options=[100, 250, 500, 1000], index=2)
with filter_col5:
    hide_bots = st.checkbox(t("chatters.hide_bots"), value=True)

messages = get_chat_message_search(
    *date_range,
    channel=channel,
    chatter_query=chatter_query or None,
    text_query=text_query or None,
    limit=limit,
)
fetched_count = len(messages)
# The global streamer/chatter filters narrow client-side, same as bot-hiding
# below — `chat_message_search` takes at most one `channel`, not a list, so
# a multi-streamer global selection can't be pushed into the query itself.
messages = apply_global_chatter_filter(apply_global_streamer_filter(messages))
# Bot-hiding happens after the fetch, same as the Chatters/Community/Streamers
# pages — the underlying query already applied `limit`, so hiding bots can
# only ever *shrink* what's shown here, never reveal more real rows than the
# limit fetched. The "hit the limit" caveat below is checked against the
# fetch count, not the post-filter one, since it's warning about the fetch
# being truncated, not about how many survived the bot filter.
if hide_bots:
    messages = messages.filter(~bot_filter_expr())

if messages.is_empty():
    st.info(t("common.no_data_in_range"))
    st.stop()

kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric(t("messages.kpi.shown"), f"{len(messages):,}")
kpi2.metric(t("messages.kpi.channels"), f"{messages['channel'].n_unique():,}")
kpi3.metric(t("messages.kpi.chatters"), f"{messages['chatter'].n_unique():,}")
if fetched_count == limit:
    st.caption(t("messages.limit_caveat", limit=f"{limit:,}"))

st.subheader(t("messages.time_heading"))
st.caption(t("messages.time_caption"))
by_hour = (
    messages.with_columns(pl.col("message_sent_at").dt.truncate("1h").alias("hour"))
    .group_by("hour")
    .agg(pl.len().alias("message_count"))
    .sort("hour")
)
time_fig = go.Figure(
    go.Scatter(
        x=by_hour["hour"],
        y=by_hour["message_count"],
        mode="lines",
        line={"color": CATEGORICAL[0], "width": 2},
        fill="tozeroy",
        fillcolor=hex_to_rgba(CATEGORICAL[0], 0.12),
        hovertemplate="%{x|%a %H:%M}<br>%{y:,.0f} messages<extra></extra>",
    )
)
apply_base_layout(time_fig, title=t("messages.chart.time"), height=320)
time_fig.update_yaxes(title_text=t("common.unit.messages"))
st.plotly_chart(time_fig, width="stretch")
chart_explainer(t("messages.explain.time"))

st.subheader(t("messages.breakdown_heading"))
st.caption(t("messages.breakdown_caption"))
# A "top channels" bar is a single, trivial bar when one specific streamer is
# already selected above — only worth its own column when the search spans
# every streamer, otherwise it just repeats the streamer filter as a chart.
if channel is None:
    breakdown_col1, breakdown_col2 = st.columns(2)
else:
    breakdown_col2 = st.container()
    breakdown_col1 = None

if breakdown_col1 is not None:
    with breakdown_col1:
        top_channels = (
            messages.group_by("channel")
            .agg(pl.len().alias("message_count"))
            .sort("message_count", descending=True)
            .head(15)
            .sort("message_count", descending=False)
        )
        channels_fig = go.Figure(
            go.Bar(
                x=top_channels["message_count"],
                y=top_channels["channel"],
                orientation="h",
                marker_color=CATEGORICAL[0],
                hovertemplate="%{y}<br>%{x:,.0f} messages<extra></extra>",
            )
        )
        apply_base_layout(
            channels_fig,
            title=t("messages.chart.top_channels"),
            height=max(280, 28 * len(top_channels)),
        )
        channels_fig.update_xaxes(title_text=t("common.unit.messages"))
        channels_fig.update_layout(showlegend=False)
        st.plotly_chart(channels_fig, width="stretch")

with breakdown_col2:
    top_chatters = (
        messages.group_by("chatter")
        .agg(pl.len().alias("message_count"))
        .sort("message_count", descending=True)
        .head(15)
        .sort("message_count", descending=False)
    )
    chatters_fig = go.Figure(
        go.Bar(
            x=top_chatters["message_count"],
            y=top_chatters["chatter"],
            orientation="h",
            marker_color=CATEGORICAL[1],
            hovertemplate="%{y}<br>%{x:,.0f} messages<extra></extra>",
        )
    )
    apply_base_layout(
        chatters_fig,
        title=t("messages.chart.top_chatters"),
        height=max(280, 28 * len(top_chatters)),
    )
    chatters_fig.update_xaxes(title_text=t("common.unit.messages"))
    chatters_fig.update_layout(showlegend=False)
    st.plotly_chart(chatters_fig, width="stretch")
chart_explainer(t("messages.explain.breakdown"))

st.subheader(t("messages.table_heading"))
st.caption(t("messages.table_caption"))
display_columns = {
    "message_sent_at": t("messages.column.datetime"),
    "channel": t("messages.column.streamer"),
    "chatter": t("messages.column.chatter"),
    "message_text": t("messages.column.message"),
    "badge": t("messages.column.badge"),
}
display_table = messages.select(list(display_columns.keys())).rename(display_columns)
st.dataframe(
    display_table,
    width="stretch",
    hide_index=True,
    column_config={
        t("messages.column.datetime"): st.column_config.DatetimeColumn(format="ddd D MMM, HH:mm:ss")
    },
)

badge_labels = {
    "moderator": t("common.badge.moderator"),
    "vip": t("common.badge.vip"),
    "subscriber": t("common.badge.subscriber"),
    "plain_viewer": t("common.badge.plain_viewer"),
}
badge_counts = messages["badge"].value_counts()
counts_by_badge = dict(
    zip(badge_counts["badge"].to_list(), badge_counts["count"].to_list(), strict=False)
)
pie_labels = [badge_labels[b] for b in badge_labels if counts_by_badge.get(b, 0) > 0]
pie_values = [counts_by_badge[b] for b in badge_labels if counts_by_badge.get(b, 0) > 0]
if pie_values:
    pie_colors = [CATEGORICAL[i % len(CATEGORICAL)] for i in range(len(pie_labels))]
    st.plotly_chart(
        build_pie_figure(
            pie_labels,
            pie_values,
            title=t("messages.chart.badge_mix"),
            colors=pie_colors,
            unit=t("common.unit.messages"),
        ),
        width="stretch",
    )
    chart_explainer(t("messages.explain.badge_mix"))

with st.expander(t("common.view_data")):
    st.caption(t("chatters.anonymize_caption"))
    st.download_button(
        t("common.download_csv"),
        anonymize_chatters(messages).write_csv(),
        file_name="chat_messages_anonymized.csv",
        mime="text/csv",
    )

page_footer()

logger.info(
    "Chat Messages page rendered (rows=%s, channel=%s, chatter_query=%s, text_query=%s)",
    len(messages),
    channel,
    bool(chatter_query),
    bool(text_query),
)
