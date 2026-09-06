"""Chatters page: analytics on individual chatters, mirroring the Streamers page.

Chat usernames are real (see `app/data/repository.py::PostgresDataSource.
chatter_breakdown`) and shown on-screen, exactly as on the Streamers and
Community pages. The CSV export is the one place real identifiers must never
leave the app: every download here replaces `chatter_id`/`chatter` with a
stable pseudonym derived from a one-way hash, so a downloaded file can never
be traced back to a real person.
"""

from __future__ import annotations

import logging

import plotly.graph_objects as go
import polars as pl
import streamlit as st
from app.components.chrome import chart_explainer, date_filter_caveat, page_footer, page_header
from app.components.filters import (
    apply_global_chatter_filter,
    apply_global_streamer_filter,
    get_global_date_range,
)
from app.components.search import consume_search_query
from app.components.theme import CATEGORICAL, apply_base_layout, build_pie_figure
from app.core.i18n import t
from app.core.logging_config import setup_logging
from app.data.anonymize import anonymize_chatters
from app.data.bot_heuristic import bot_filter_expr
from app.data.repository import (
    get_channel_chatter_breakdown,
    get_chatter_breakdown,
    get_chatter_breakdown_top_n,
    get_chatter_channel_breakdown,
    get_top_chat_channels,
)

setup_logging()
logger = logging.getLogger(__name__)

_DEFAULT_CHATTER_LIMIT = 2000

page_header(t("chatters.title"), "🗣️", t("chatters.description"))

date_range = get_global_date_range()

# Fetching every chatter (up to ~460k, most with a handful of messages) to
# support the search box below is what made this page slow — confirmed
# directly, the query itself is fast, the cost is transferring/parsing that
# many rows. So this only pays that cost once a search is actually active;
# otherwise it fetches just the most active chatters, which is what every
# other control on this page (profile/age/min-messages filters, top-N
# ranking) realistically narrows down to anyway.
pending_query = consume_search_query()
if pending_query:
    st.session_state["chatters_search_box"] = pending_query
search_active = bool(st.session_state.get("chatters_search_box", "").strip())

df = (
    (get_chatter_breakdown(*date_range) if search_active else get_chatter_breakdown_top_n(*date_range, _DEFAULT_CHATTER_LIMIT))
    if date_range
    else pl.DataFrame()
)
df = apply_global_chatter_filter(df)
if df.is_empty():
    st.warning(t("chatters.no_data"))
    st.stop()

if not search_active:
    st.caption(t("chatters.top_n_default_caption", limit=_DEFAULT_CHATTER_LIMIT))

st.subheader(t("chatters.filters"))
filter_col1, filter_col2, filter_col3, filter_col4, filter_col5 = st.columns(5)
with filter_col1:
    search = st.text_input(t("chatters.search"), key="chatters_search_box")
with filter_col2:
    profile_labels = {
        "sedentaire": t("common.chatter_profile.loyal"),
        "multi_streamer": t("common.chatter_profile.multi_streamer"),
        "semi_nomade": t("common.chatter_profile.semi_nomad"),
        "nomade": t("common.chatter_profile.nomad"),
    }
    profile_filter = st.multiselect(
        t("chatters.profile_filter"),
        options=list(profile_labels.keys()),
        format_func=lambda p: profile_labels[p],
        default=[],
    )
with filter_col3:
    age_labels = {
        "new (<30d)": t("community.age.new"),
        "1mo-1yr": t("community.age.month_to_year"),
        "1-3yr": t("community.age.one_to_three"),
        "3yr+": t("community.age.three_plus"),
        "unknown": t("community.age.unknown"),
    }
    age_options = [b for b in age_labels if b in df["account_age_bucket"].unique().to_list()]
    age_filter = st.multiselect(
        t("chatters.age_filter"),
        options=age_options,
        format_func=lambda b: age_labels[b],
        default=[],
    )
with filter_col4:
    min_messages = st.number_input(t("chatters.min_messages"), min_value=0, value=0, step=10)
with filter_col5:
    hide_bots = st.checkbox(t("chatters.hide_bots"), value=True)

filtered = df
if search:
    filtered = filtered.filter(
        pl.col("chatter").str.to_lowercase().str.contains(search.lower(), literal=True)
    )
if profile_filter:
    filtered = filtered.filter(pl.col("chatter_profile").is_in(profile_filter))
if age_filter:
    filtered = filtered.filter(pl.col("account_age_bucket").is_in(age_filter))
filtered = filtered.filter(pl.col("total_message_count") >= min_messages)
if hide_bots:
    filtered = filtered.filter(~bot_filter_expr())

if filtered.is_empty():
    st.info(t("common.no_data_in_range"))
    st.stop()

RANKINGS = {
    t("chatters.rank.messages"): ("total_message_count", t("common.unit.messages")),
    t("chatters.rank.channels"): ("distinct_channel_count", t("common.unit.channels")),
}
rank_by = st.radio(t("chatters.rank_by"), list(RANKINGS.keys()), horizontal=True)
column, unit = RANKINGS[rank_by]
if len(filtered) <= 1:
    top_n = len(filtered)
else:
    top_n = st.slider(
        t("chatters.top_n"), min_value=1, max_value=len(filtered), value=min(15, len(filtered))
    )
top = filtered.sort(column, descending=True).head(top_n)

kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric(t("chatters.kpi.total"), f"{len(filtered):,}")
kpi2.metric(t("chatters.kpi.top", metric=rank_by), top["chatter"][0])
kpi3.metric(t("chatters.kpi.total_messages"), f"{filtered['total_message_count'].sum():,.0f}")

# Ranked magnitude across many chatters: one hue for the whole chart, not one
# per bar (color-per-bar would be decorative here, not meaningful).
ordered = top.sort(column, descending=False)
bar_fig = go.Figure(
    go.Bar(
        x=ordered[column],
        y=ordered["chatter"],
        orientation="h",
        marker_color=CATEGORICAL[0],
        hovertemplate=f"%{{y}}<br>%{{x:,.0f}} {unit}<extra></extra>",
    )
)
apply_base_layout(
    bar_fig, title=t("chatters.chart.ranked", metric=rank_by), height=max(360, 28 * len(ordered))
)
bar_fig.update_xaxes(title_text=unit)
bar_fig.update_layout(showlegend=False)
st.plotly_chart(bar_fig, width="stretch")
chart_explainer(t("chatters.explain.ranked"))

st.subheader(t("chatters.correlation_heading"))
st.caption(t("chatters.correlation_caption"))
# As on the Streamers page: name a "correlation" without the coefficient and
# the reader is left eyeballing scatter. `None` (too few chatters shown, or
# no variation in one axis) renders as "—" rather than a fabricated number.
breadth_volume_r = (
    filtered.select(pl.corr("distinct_channel_count", "total_message_count")).item()
    if len(filtered) >= 2
    else None
)
st.caption(
    t("chatters.correlation_stat", r=f"{breadth_volume_r:.2f}")
    if breadth_volume_r is not None
    else t("chatters.correlation_stat_na")
)
scatter_fig = go.Figure()
profile_order = ["sedentaire", "multi_streamer", "semi_nomade", "nomade"]
for i, profile in enumerate(profile_order):
    subset = filtered.filter(pl.col("chatter_profile") == profile)
    if subset.is_empty():
        continue
    scatter_fig.add_trace(
        go.Scatter(
            x=subset["distinct_channel_count"],
            y=subset["total_message_count"],
            mode="markers",
            name=profile_labels[profile],
            marker={"color": CATEGORICAL[i], "size": 9, "opacity": 0.75},
            text=subset["chatter"],
            hovertemplate="%{text}<br>channels: %{x}<br>messages: %{y:,.0f}<extra></extra>",
        )
    )
apply_base_layout(scatter_fig, title=t("chatters.chart.correlation"), height=420)
scatter_fig.update_xaxes(title_text=t("common.unit.channels"))
scatter_fig.update_yaxes(title_text=t("common.unit.messages"))
st.plotly_chart(scatter_fig, width="stretch")
chart_explainer(t("chatters.explain.correlation"))

st.subheader(t("chatters.lifespan_heading"))
st.caption(t("chatters.lifespan_caption"))
lifespan_hours = pl.col("lifespan_hours")
lifespan_buckets = (
    filtered.with_columns(
        pl.when(lifespan_hours <= 0)
        .then(pl.lit("single_message"))
        .when(lifespan_hours < 1)
        .then(pl.lit("under_1h"))
        .when(lifespan_hours < 6)
        .then(pl.lit("1_to_6h"))
        .when(lifespan_hours < 24)
        .then(pl.lit("6_to_24h"))
        .otherwise(pl.lit("24h_plus"))
        .alias("lifespan_bucket")
    )
    .group_by("lifespan_bucket")
    .agg(pl.len().alias("chatter_count"))
)
lifespan_order = ["single_message", "under_1h", "1_to_6h", "6_to_24h", "24h_plus"]
lifespan_labels = {
    "single_message": t("chatters.lifespan.single_message"),
    "under_1h": t("chatters.lifespan.under_1h"),
    "1_to_6h": t("chatters.lifespan.1_to_6h"),
    "6_to_24h": t("chatters.lifespan.6_to_24h"),
    "24h_plus": t("chatters.lifespan.24h_plus"),
}
counts_by_bucket = dict(
    zip(
        lifespan_buckets["lifespan_bucket"].to_list(),
        lifespan_buckets["chatter_count"].to_list(),
        strict=False,
    )
)
lifespan_fig = go.Figure(
    go.Bar(
        x=[lifespan_labels[b] for b in lifespan_order],
        y=[counts_by_bucket.get(b, 0) for b in lifespan_order],
        marker_color=CATEGORICAL[5],
        hovertemplate="%{x}<br>%{y:,} chatters<extra></extra>",
    )
)
apply_base_layout(lifespan_fig, title=t("chatters.chart.lifespan"), height=360)
lifespan_fig.update_yaxes(title_text=t("common.unit.chatters"))
lifespan_fig.update_layout(showlegend=False)
st.plotly_chart(lifespan_fig, width="stretch")
chart_explainer(t("chatters.explain.lifespan"))

st.subheader(t("chatters.profile_heading"))
selected = st.selectbox(t("chatters.pick_chatter"), options=filtered["chatter"].to_list())
profile = filtered.filter(pl.col("chatter") == selected).row(0, named=True)

pcol0, pcol1, pcol2, pcol3, pcol4 = st.columns(5)
pcol0.metric(t("chatters.kpi.global_total"), f"{profile['total_message_count']:,.0f}")
pcol1.metric(t("chatters.kpi.channels"), f"{profile['distinct_channel_count']:,}")
pcol2.metric(t("chatters.kpi.top_channel_share"), f"{profile['top_channel_share']:.0%}")
pcol3.metric(t("chatters.kpi.account_age"), age_labels.get(profile["account_age_bucket"], "—"))
gap_cv = profile["gap_coefficient_of_variation"]
pcol4.metric(
    t("chatters.kpi.regularity"),
    f"{gap_cv:.2f}" if gap_cv is not None else "—",
    help=t("chatters.regularity_help"),
)

date_filter_caveat()
channel_activity = get_chatter_channel_breakdown(profile["chatter_id"])
if channel_activity.is_empty():
    st.info(t("chatters.no_channel_data"))
else:
    # The "Global (all channels)" bar is included by default alongside the
    # per-channel ones, not just implied by the KPI above — it's this
    # chatter's own total (`total_message_count`, event-wide, unaffected by
    # the sidebar date filter same as the rest of this section), given a
    # distinct color since it isn't one more channel to compare against the
    # others but the sum of all of them.
    # Global bar last (Plotly draws the first array entry at the *bottom* of
    # a horizontal bar chart) so it lands at the top as the most prominent
    # bar, above the per-channel ones sorted ascending below it.
    ordered_channels = channel_activity.sort("message_count", descending=False)
    global_label = t("chatters.chart.global_bar_label")
    bar_labels = [*ordered_channels["channel"].to_list(), global_label]
    bar_values = [*ordered_channels["message_count"].to_list(), profile["total_message_count"]]
    bar_colors = [*([CATEGORICAL[0]] * len(ordered_channels)), CATEGORICAL[1]]
    channel_fig = go.Figure(
        go.Bar(
            x=bar_values,
            y=bar_labels,
            orientation="h",
            marker_color=bar_colors,
            hovertemplate="%{y}<br>%{x:,.0f} messages<extra></extra>",
        )
    )
    apply_base_layout(
        channel_fig,
        title=t("chatters.chart.channel_breakdown", chatter=selected),
        height=max(280, 32 * len(bar_labels)),
    )
    channel_fig.update_xaxes(title_text=t("common.unit.messages"))
    channel_fig.update_yaxes(type="category")
    channel_fig.update_layout(showlegend=False)
    st.plotly_chart(channel_fig, width="stretch")
    chart_explainer(t("chatters.explain.channel_breakdown"))

st.subheader(t("chatters.by_channel_heading"))
st.caption(t("chatters.by_channel_caption"))
channel_options = sorted(
    apply_global_streamer_filter(get_top_chat_channels())["channel"].unique().to_list()
)
if not channel_options:
    st.info(t("common.no_data_in_range"))
else:
    picked_channel = st.selectbox(
        t("chatters.pick_channel"), options=channel_options, key="chatters_channel_pick"
    )
    channel_chatters = (
        get_channel_chatter_breakdown(picked_channel, *date_range) if date_range else pl.DataFrame()
    )
    channel_chatters = apply_global_chatter_filter(channel_chatters)
    if channel_chatters.is_empty():
        st.info(t("common.no_data_in_range"))
    else:
        cf_col1, cf_col2, cf_col3 = st.columns(3)
        with cf_col1:
            channel_search = st.text_input(t("chatters.search"), key="channel_chatters_search")
        with cf_col2:
            badge_labels = {
                "moderator": t("common.badge.moderator"),
                "vip": t("common.badge.vip"),
                "subscriber": t("common.badge.subscriber"),
                "plain_viewer": t("common.badge.plain_viewer"),
            }
            badge_filter = st.multiselect(
                t("chatters.badge_filter"),
                options=list(badge_labels.keys()),
                format_func=lambda b: badge_labels[b],
                default=[],
            )
        with cf_col3:
            channel_min_messages = st.number_input(
                t("chatters.min_messages"), min_value=0, value=0, step=5, key="channel_min_messages"
            )

        cshown = channel_chatters
        if channel_search:
            cshown = cshown.filter(
                pl.col("chatter")
                .str.to_lowercase()
                .str.contains(channel_search.lower(), literal=True)
            )
        if badge_filter:
            badge_columns = {
                "moderator": "moderator_message_count",
                "vip": "vip_message_count",
                "subscriber": "subscriber_message_count",
                "plain_viewer": "plain_viewer_message_count",
            }
            badge_mask = pl.any_horizontal(
                [pl.col(badge_columns[b]) > 0 for b in badge_filter]
            )
            cshown = cshown.filter(badge_mask)
        cshown = cshown.filter(
            pl.col("message_count") >= channel_min_messages
        )

        if cshown.is_empty():
            st.info(t("common.no_data_in_range"))
        else:
            ckpi1, ckpi2, ckpi3, ckpi4 = st.columns(4)
            ckpi1.metric(t("chatters.kpi.total"), f"{len(cshown):,}")
            ckpi2.metric(
                t("chatters.kpi.total_messages"), f"{cshown['message_count'].sum():,.0f}"
            )
            ckpi3.metric(
                t("chatters.kpi.moderators"),
                f"{(cshown['moderator_message_count'] > 0).sum():,}",
            )
            ckpi4.metric(
                t("chatters.kpi.subscribers"),
                f"{(cshown['subscriber_message_count'] > 0).sum():,}",
            )

            badge_totals = {
                t("common.badge.moderator"): cshown["moderator_message_count"].sum(),
                t("common.badge.vip"): cshown["vip_message_count"].sum(),
                t("common.badge.subscriber"): cshown["subscriber_message_count"].sum(),
                t("common.badge.plain_viewer"): cshown[
                    "plain_viewer_message_count"
                ].sum(),
            }
            pie_labels = [label for label, total in badge_totals.items() if total > 0]
            pie_values = [badge_totals[label] for label in pie_labels]
            if pie_values:
                pie_colors = [CATEGORICAL[i % len(CATEGORICAL)] for i in range(len(pie_labels))]
                st.plotly_chart(
                    build_pie_figure(
                        pie_labels,
                        pie_values,
                        title=t("chatters.chart.badge_mix", channel=picked_channel),
                        colors=pie_colors,
                        unit=t("common.unit.messages"),
                    ),
                    width="stretch",
                )
                chart_explainer(t("chatters.explain.badge_mix"))

            channel_rank_by = st.radio(
                t("chatters.rank_by"),
                [t("chatters.rank.messages"), t("chatters.rank.emotes")],
                horizontal=True,
                key="channel_rank_by",
            )
            channel_rank_col = (
                "message_count"
                if channel_rank_by == t("chatters.rank.messages")
                else "emote_usage_count"
            )
            if len(cshown) <= 1:
                channel_top_n = len(cshown)
            else:
                channel_top_n = st.slider(
                    t("chatters.top_n"),
                    min_value=1,
                    max_value=len(cshown),
                    value=min(15, len(cshown)),
                    key="channel_top_n",
                )
            channel_top = (
                cshown.sort(channel_rank_col, descending=True)
                .head(channel_top_n)
                .sort(channel_rank_col, descending=False)
            )
            channel_rank_fig = go.Figure(
                go.Bar(
                    x=channel_top[channel_rank_col],
                    y=channel_top["chatter"],
                    orientation="h",
                    marker_color=CATEGORICAL[0],
                    hovertemplate="%{y}<br>%{x:,.0f}<extra></extra>",
                )
            )
            apply_base_layout(
                channel_rank_fig,
                title=t(
                    "chatters.chart.channel_ranked", channel=picked_channel, metric=channel_rank_by
                ),
                height=max(360, 28 * len(channel_top)),
            )
            channel_rank_fig.update_layout(showlegend=False)
            st.plotly_chart(channel_rank_fig, width="stretch")
            chart_explainer(t("chatters.explain.channel_ranked"))

            with st.expander(t("common.view_data")):
                st.caption(t("chatters.by_channel_table_caption"))
                st.dataframe(cshown, width="stretch", hide_index=True)
                st.caption(t("chatters.anonymize_caption"))
                st.download_button(
                    t("common.download_csv"),
                    anonymize_chatters(cshown).write_csv(),
                    file_name=f"chatters_{picked_channel}.csv",
                    mime="text/csv",
                    key="channel_chatters_download",
                )

with st.expander(t("common.view_data")):
    st.dataframe(filtered, width="stretch", hide_index=True)
    st.caption(t("chatters.anonymize_caption"))
    st.download_button(
        t("common.download_csv"),
        anonymize_chatters(filtered).write_csv(),
        file_name="chatters_anonymized.csv",
        mime="text/csv",
    )

page_footer()

logger.info("Chatters page rendered (rows=%s, rank_by=%s, top_n=%s)", len(filtered), rank_by, top_n)
