"""Chatters page: analytics on individual chatters, mirroring the Streamers page.

Chat usernames are real (see `app/data/repository.py::PostgresDataSource.
chatter_breakdown`) and shown on-screen, exactly as on the Streamers and
Community pages. The CSV export is the one place real identifiers must never
leave the app: every download here replaces `chatter_id`/`chatter` with a
stable pseudonym derived from a one-way hash, so a downloaded file can never
be traced back to a real person.
"""

from __future__ import annotations

import hashlib
import logging

import plotly.graph_objects as go
import polars as pl
import streamlit as st
from app.components.chrome import chart_explainer, page_header
from app.components.search import consume_search_query
from app.components.theme import CATEGORICAL, apply_base_layout
from app.core.i18n import t
from app.core.logging_config import setup_logging
from app.data.bot_heuristic import bot_filter_expr
from app.data.repository import get_chatter_breakdown, get_chatter_channel_breakdown

setup_logging()
logger = logging.getLogger(__name__)


def _anonymize(df: pl.DataFrame) -> pl.DataFrame:
    """Replace real chatter identifiers with a stable, one-way pseudonym.

    The pseudonym is derived from a SHA-256 hash of `chatter_id`, truncated —
    deterministic (the same chatter always gets the same pseudonym within a
    download) but not reversible to the real id or username.

    Args:
        df: DataFrame with `chatter_id` and `chatter` columns.

    Returns:
        `df` with those two columns replaced by a single `chatter_pseudonym`
        column, in front.
    """
    pseudonyms = [
        "Chatter_" + hashlib.sha256(cid.encode("utf-8")).hexdigest()[:8]
        for cid in df["chatter_id"].to_list()
    ]
    kept = [c for c in df.columns if c not in ("chatter_id", "chatter")]
    return (
        df.select(kept)
        .with_columns(pl.Series("chatter_pseudonym", pseudonyms))
        .select(["chatter_pseudonym", *kept])
    )


page_header(t("chatters.title"), "🗣️", t("chatters.description"))

df = get_chatter_breakdown()
if df.is_empty():
    st.warning(t("chatters.no_data"))
    st.stop()

pending_query = consume_search_query()
if pending_query:
    st.session_state["chatters_search_box"] = pending_query

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

st.subheader(t("chatters.profile_heading"))
selected = st.selectbox(t("chatters.pick_chatter"), options=filtered["chatter"].to_list())
profile = filtered.filter(pl.col("chatter") == selected).row(0, named=True)

pcol1, pcol2, pcol3, pcol4 = st.columns(4)
pcol1.metric(t("chatters.kpi.channels"), f"{profile['distinct_channel_count']:,}")
pcol2.metric(t("chatters.kpi.top_channel_share"), f"{profile['top_channel_share']:.0%}")
pcol3.metric(t("chatters.kpi.account_age"), age_labels.get(profile["account_age_bucket"], "—"))
gap_cv = profile["gap_coefficient_of_variation"]
pcol4.metric(
    t("chatters.kpi.regularity"),
    f"{gap_cv:.2f}" if gap_cv is not None else "—",
    help=t("chatters.regularity_help"),
)

channel_activity = get_chatter_channel_breakdown(profile["chatter_id"])
if channel_activity.is_empty():
    st.info(t("chatters.no_channel_data"))
else:
    ordered_channels = channel_activity.sort("message_count", descending=False)
    channel_fig = go.Figure(
        go.Bar(
            x=ordered_channels["message_count"],
            y=ordered_channels["channel"],
            orientation="h",
            marker_color=CATEGORICAL[0],
            hovertemplate="%{y}<br>%{x:,.0f} messages<extra></extra>",
        )
    )
    apply_base_layout(
        channel_fig,
        title=t("chatters.chart.channel_breakdown", chatter=selected),
        height=max(280, 32 * len(ordered_channels)),
    )
    channel_fig.update_xaxes(title_text=t("common.unit.messages"))
    channel_fig.update_layout(showlegend=False)
    st.plotly_chart(channel_fig, width="stretch")
    chart_explainer(t("chatters.explain.channel_breakdown"))

with st.expander(t("common.view_data")):
    st.dataframe(filtered, width="stretch", hide_index=True)
    st.caption(t("chatters.anonymize_caption"))
    st.download_button(
        t("common.download_csv"),
        _anonymize(filtered).write_csv(),
        file_name="chatters_anonymized.csv",
        mime="text/csv",
    )

logger.info("Chatters page rendered (rows=%s, rank_by=%s, top_n=%s)", len(filtered), rank_by, top_n)
