"""Community page: who's chatting, how loyal they are, and which channels share audiences."""

from __future__ import annotations

import logging

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
from app.components.filters import (
    apply_global_chatter_filter,
    apply_global_date_filter,
    apply_global_streamer_filter,
    get_global_date_range,
    get_global_streamer_filter,
)
from app.components.network_graph import build_migration_sankey, build_network_figure
from app.components.theme import (
    CATEGORICAL,
    CHROME,
    SEQUENTIAL_GREEN,
    apply_base_layout,
    hex_to_rgba,
)
from app.core.i18n import t
from app.core.logging_config import setup_logging
from app.data.bot_heuristic import bot_filter_expr
from app.data.repository import (
    get_channel_network,
    get_chatter_account_age_mix,
    get_chatter_day1_retention,
    get_chatter_growth_timeseries,
    get_chatter_migrations,
    get_chatter_profile_mix,
    get_hourly_network,
    get_hourly_network_hours,
    get_new_chatters_per_channel,
    get_top_chatters,
)

setup_logging()
logger = logging.getLogger(__name__)


def _shared_audience_threshold_picker(
    edges: pl.DataFrame,
    weight_col: str,
    *,
    key: str,
    a_col: str = "channel_a",
    b_col: str = "channel_b",
) -> float:
    """Render a "minimum shared chatters" slider and return the chosen threshold.

    A shared-audience network is close to a *complete* graph — nearly every
    channel pair shares at least a few chatters — so handing every edge to
    `build_network_figure` turns it into an unreadable hairball. Defaulting
    to the 90th percentile of this edge set's own weights keeps roughly its
    strongest tenth without hard-coding a fixed cutoff that would be
    meaningless across weight scales as different as one hour's graph and
    the event-wide one.

    Args:
        edges: DataFrame with at least `weight_col`, `a_col`, `b_col`.
        weight_col: Column holding edge weight.
        key: Unique Streamlit widget key — this is called for two different
            network sections on the same page.
        a_col: Column holding one endpoint of each edge.
        b_col: Column holding the other endpoint of each edge.

    Returns:
        The chosen minimum edge weight to keep, or 0 if every edge already
        shares the same weight (nothing meaningful to threshold).
    """
    weights = edges[weight_col]
    # `shared_chatter_count` is always integer; `jaccard_index` (the
    # alternative weight the overall network can be colored/sized by) is a
    # small float (0-1) — an `int()` cast on that would floor both min and
    # max to 0 and permanently disable the slider, so the step/rounding
    # below branches on the column's actual dtype instead of assuming int.
    is_int_weight = weights.dtype.is_integer()
    cast = int if is_int_weight else float
    float_step = round((float(weights.max()) - float(weights.min())) / 200, 6) or 0.0001
    step = 1 if is_int_weight else float_step
    min_w, max_w = cast(weights.min()), cast(weights.max())
    can_filter = min_w < max_w
    # Rendered on every call, even when this edge set has nothing to
    # threshold (disabled instead) — a widget that appears only for some
    # hours (min_w < max_w) and vanishes for others would change which
    # widgets exist from one hour to the next, which is needless churn for
    # no benefit here, purely to avoid a data-dependent slider.
    slider_max = max_w if can_filter else min_w + step
    default = (
        min(max(cast(weights.quantile(0.9) or min_w), min_w + step), max_w) if can_filter else min_w
    )
    # This widget's own valid range moves with the data (a different hour,
    # or the event-wide graph, has a different max weight) — a value the
    # widget is still holding in `session_state` from a *previous* range can
    # fall outside the new one, which crashes rather than clamping (the same
    # widget-identity issue fixed on the Donation Tracker page's category
    # filter). Reset only when the stored value no longer fits, so a still-
    # valid threshold survives switching hours instead of jumping back to
    # the default every time.
    if key not in st.session_state or not (min_w <= st.session_state[key] <= slider_max):
        st.session_state[key] = default
    threshold = st.slider(
        t("community.network_min_weight"),
        min_value=min_w,
        max_value=slider_max,
        step=step,
        disabled=not can_filter,
        key=key,
    )
    if not can_filter:
        threshold = min_w
    kept = edges.filter(pl.col(weight_col) >= threshold)
    kept_nodes = set(kept[a_col].to_list()) | set(kept[b_col].to_list())
    total_nodes = set(edges[a_col].to_list()) | set(edges[b_col].to_list())
    st.caption(
        t(
            "community.network_filtered_caption",
            edges=len(kept),
            total_edges=len(edges),
            nodes=len(kept_nodes),
            total_nodes=len(total_nodes),
        )
    )
    return threshold


page_header(t("community.title"), "👥", t("community.description"))

profile_mix = get_chatter_profile_mix()
if profile_mix.is_empty():
    st.warning(t("community.no_data"))
    st.stop()

entity_filter_caveat()
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

date_range = get_global_date_range()

st.subheader(t("community.growth_heading"))
entity_filter_caveat()
growth = get_chatter_growth_timeseries()
if not growth.is_empty():
    # Cumulative sum computed on the full series *before* the period filter,
    # then windowed for display — filtering first would make the curve
    # restart from zero at the window's start instead of showing the true
    # running total.
    growth = growth.with_columns(pl.col("new_chatters").cum_sum().alias("cumulative_chatters"))
    growth_shown = apply_global_date_filter(growth, timestamp_col="timestamp")
    if not growth_shown.is_empty():
        st.caption(t("community.growth_caption"))
        growth_fig = go.Figure(
            go.Scatter(
                x=growth_shown["timestamp"],
                y=growth_shown["cumulative_chatters"],
                mode="lines",
                line={"color": CATEGORICAL[0], "width": 2},
                fill="tozeroy",
                fillcolor=hex_to_rgba(CATEGORICAL[0], 0.12),
                hovertemplate="%{x|%a %H:%M}<br>%{y:,.0f} chatters<extra></extra>",
            )
        )
        apply_base_layout(growth_fig, title=t("community.chart.growth"), height=340)
        growth_fig.update_yaxes(title_text=t("community.cumulative_chatters"))
        st.plotly_chart(growth_fig, width="stretch")
        chart_explainer(t("community.explain.growth"))

st.subheader(t("community.retention_heading"))
date_filter_caveat()
entity_filter_caveat()
retention = get_chatter_day1_retention()
if len(retention) < 2:
    st.info(t("community.no_retention"))
else:
    st.caption(t("community.retention_caption"))
    day_labels = [
        t("community.retention_day_label", day=day) for day in retention["day_index"].to_list()
    ]
    retention_fig = go.Figure(
        go.Funnel(
            y=day_labels,
            x=retention["retained_chatters"].to_list(),
            marker={"color": CATEGORICAL[0]},
            textinfo="value+percent initial",
        )
    )
    apply_base_layout(
        retention_fig, title=t("community.chart.retention"), height=max(280, 90 * len(retention))
    )
    st.plotly_chart(retention_fig, width="stretch")
    # The event may still be live — its most recent day bucket can still be
    # partway through, so that stage's retained-count is a floor, not a
    # final figure, regardless of whether the event has actually wrapped by
    # the time this renders.
    st.caption(t("community.retention_live_caveat"))
    chart_explainer(t("community.explain.retention"))

st.subheader(t("community.new_by_channel_heading"))
new_by_channel = get_new_chatters_per_channel(*date_range) if date_range else pl.DataFrame()
new_by_channel = apply_global_streamer_filter(new_by_channel)
if new_by_channel.is_empty():
    st.info(t("community.no_new_by_channel"))
else:
    # Capped to the top 15 (of potentially hundreds of channels with any new
    # chatters at all) — an uncapped `height = 28px * len(channels)` chart
    # was rendering at several thousand pixels tall by default, well past
    # the point of being readable in one screen.
    all_totals_by_channel = (
        new_by_channel.group_by("channel")
        .agg(pl.col("new_chatters_to_channel").sum())
        .sort("new_chatters_to_channel", descending=True)
    )
    totals_by_channel = all_totals_by_channel.head(15).sort(
        "new_chatters_to_channel", descending=False
    )
    st.caption(
        t(
            "community.new_by_channel_caption",
            shown=len(totals_by_channel),
            total=len(all_totals_by_channel),
        )
    )
    new_by_channel_fig = go.Figure(
        go.Bar(
            x=totals_by_channel["new_chatters_to_channel"],
            y=totals_by_channel["channel"],
            orientation="h",
            marker_color=CATEGORICAL[0],
            hovertemplate="%{y}<br>%{x:,} new chatters<extra></extra>",
        )
    )
    apply_base_layout(
        new_by_channel_fig,
        title=t("community.chart.new_by_channel"),
        height=max(320, 28 * len(totals_by_channel)),
    )
    new_by_channel_fig.update_xaxes(title_text=t("common.unit.chatters"))
    new_by_channel_fig.update_layout(showlegend=False)
    st.plotly_chart(new_by_channel_fig, width="stretch")
    chart_explainer(t("community.explain.new_by_channel"))

network = get_channel_network()
selected_streamers = get_global_streamer_filter()
if selected_streamers:
    # An edge belongs to the filtered graph if *either* endpoint is
    # selected — unlike a plain row filter, a network's identity column is
    # split across two endpoint columns, so `apply_global_streamer_filter`
    # (single-column `is_in`) doesn't fit; this is the OR-across-both-
    # endpoints equivalent, used here and for the migrations Sankey below.
    network = network.filter(
        pl.col("channel_a").is_in(selected_streamers)
        | pl.col("channel_b").is_in(selected_streamers)
    )

st.subheader(t("community.hourly_network_heading"))
network_hours = get_hourly_network_hours()
if date_range is not None:
    start, end = date_range
    network_hours = [hour for hour in network_hours if start <= hour <= end]
if not network_hours:
    st.info(t("community.no_hourly_network"))
else:
    st.caption(t("community.hourly_network_caption"))
    # Default to the latest hour that actually has computed edges, not
    # simply the latest hour in range: this is a live event, and the most
    # recent hour's cross-channel edges can lag a run or two behind — always
    # landing a first-time visitor on a blank graph would look broken. The
    # full range stays pickable, so scrubbing to a genuinely not-yet-computed
    # hour still shows the honest "no data" message below.
    default_hour = network_hours[-1]
    for candidate in reversed(network_hours):
        if not get_hourly_network(candidate).is_empty():
            default_hour = candidate
            break
    selected_hour = st.select_slider(
        t("community.hour_picker"),
        options=network_hours,
        value=default_hour,
        format_func=lambda ts: ts.strftime("%a %H:%M"),
    )
    hourly_edges = get_hourly_network(selected_hour)
    if selected_streamers:
        hourly_edges = hourly_edges.filter(
            pl.col("channel_a").is_in(selected_streamers)
            | pl.col("channel_b").is_in(selected_streamers)
        )
    if hourly_edges.is_empty():
        st.info(t("community.no_hourly_network"))
    else:
        hourly_min_weight = _shared_audience_threshold_picker(
            hourly_edges, "shared_chatter_count", key="hourly_network_min_weight"
        )
        network_fig = build_network_figure(
            hourly_edges,
            a_col="channel_a",
            b_col="channel_b",
            weight_col="shared_chatter_count",
            title=t("community.chart.hourly_network", hour=selected_hour.strftime("%a %H:%M")),
            min_weight=hourly_min_weight,
        )
        st.plotly_chart(network_fig, width="stretch")
        chart_explainer(t("community.explain.hourly_network"))

date_filter_caveat()
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
        # Indices 2-5, not 0-1: those darkest ramp steps are meant to recede
        # into the near-black page for a heatmap's "low magnitude" cells,
        # which would just look like missing bars here.
        age_colors = [
            SEQUENTIAL_GREEN[2],
            SEQUENTIAL_GREEN[3],
            SEQUENTIAL_GREEN[4],
            SEQUENTIAL_GREEN[5],
            CHROME["baseline"],
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
top_chatters = get_top_chatters(*date_range) if date_range else pl.DataFrame()
top_chatters = apply_global_chatter_filter(apply_global_streamer_filter(top_chatters))
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
date_filter_caveat()
if network.is_empty():
    st.info(t("community.no_network"))
else:
    st.caption(t("community.network_caption"))
    NETWORK_WEIGHTS = {
        t("community.weight.shared_count"): "shared_chatter_count",
        t("community.weight.jaccard"): "jaccard_index",
    }
    weight_choice = st.radio(
        t("community.weight_picker"), list(NETWORK_WEIGHTS.keys()), horizontal=True
    )
    weight_col = NETWORK_WEIGHTS[weight_choice]
    if weight_col == "jaccard_index":
        st.caption(t("community.weight.jaccard_caveat"))
    overall_min_weight = _shared_audience_threshold_picker(
        network,
        weight_col,
        # Keyed per metric, not shared: switching metrics swaps the whole
        # weight scale (a handful of shared chatters vs. a 0-1 overlap
        # ratio) out from under the slider, so each gets its own persistent
        # widget instead of one fighting to reinterpret the other's value.
        key=f"overall_network_min_weight_{weight_col}",
    )
    overall_network_fig = build_network_figure(
        network,
        a_col="channel_a",
        b_col="channel_b",
        weight_col=weight_col,
        title=t("community.chart.network"),
        height=520,
        min_weight=overall_min_weight,
        weight_label=(
            t("community.weight.jaccard_hover_label")
            if weight_col == "jaccard_index"
            else t("community.weight.shared_count_hover_label")
        ),
        weight_format=".3f" if weight_col == "jaccard_index" else ",.0f",
    )
    st.plotly_chart(overall_network_fig, width="stretch")
    chart_explainer(t("community.explain.network"))

st.subheader(t("community.migrations_heading"))
date_filter_caveat()
migrations = get_chatter_migrations()
if selected_streamers:
    migrations = migrations.filter(
        pl.col("from_channel").is_in(selected_streamers)
        | pl.col("to_channel").is_in(selected_streamers)
    )
if migrations.is_empty():
    st.info(t("community.no_migrations"))
else:
    st.caption(t("community.migrations_caption"))
    migration_universe = sorted(
        set(migrations["from_channel"].to_list()) | set(migrations["to_channel"].to_list())
    )
    migrations_fig = build_migration_sankey(
        migrations,
        source_col="from_channel",
        target_col="to_channel",
        value_col="hop_count",
        title=t("community.chart.migrations"),
        height=480,
        color_universe=migration_universe,
    )
    st.plotly_chart(migrations_fig, width="stretch")
    chart_explainer(t("community.explain.migrations"))

with st.expander(t("common.view_data")):
    st.dataframe(profile_mix, width="stretch", hide_index=True)
    st.dataframe(network, width="stretch", hide_index=True)
    st.download_button(
        t("common.download_csv"),
        network.write_csv(),
        file_name="channel_network.csv",
        mime="text/csv",
    )

page_footer()

logger.info("Community page rendered (chatters=%s, network_pairs=%s)", total_chatters, len(network))
