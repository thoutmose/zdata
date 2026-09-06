"""Streamers page: donations, audience, engagement, correlations, and a profile drill-down.

Note: the real database has no "team" dimension for streamers, so this page
ranks streamers individually rather than grouping/coloring by team.
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
from app.components.theme import (
    CATEGORICAL,
    CHROME,
    SEQUENTIAL_GOLD_COLORSCALE,
    STATUS,
    apply_base_layout,
    build_radar_figure,
)
from app.core.i18n import t
from app.core.logging_config import setup_logging
from app.data.bot_heuristic import bot_filter_expr
from app.data.repository import (
    get_event_bounds,
    get_streamer_breakdown,
    get_streamer_diurnal_profile,
    get_streamer_night_shift,
    get_top_chatters_for_channels,
)

setup_logging()
logger = logging.getLogger(__name__)

page_header(t("streamers.title"), "🎙️", t("streamers.description"))
date_filter_caveat()

full_df = get_streamer_breakdown()
if full_df.is_empty():
    st.warning(t("streamers.no_data"))
    st.stop()
df = apply_global_streamer_filter(full_df)
if df.is_empty():
    st.info(t("common.no_data_in_range"))
    st.stop()

pending_query = consume_search_query()
if pending_query:
    st.session_state["streamers_search_box"] = pending_query

st.subheader(t("streamers.filters"))
filter_col1, filter_col2, filter_col3 = st.columns(3)
with filter_col1:
    search = st.text_input(t("streamers.search"), key="streamers_search_box")
with filter_col2:
    categories = sorted(df["top_category"].drop_nulls().unique().to_list())
    category_filter = st.multiselect(t("streamers.category_filter"), options=categories, default=[])
with filter_col3:
    min_viewers = st.number_input(t("streamers.min_viewers"), min_value=0, value=0, step=100)

filtered = df
if search:
    filtered = filtered.filter(
        pl.col("streamer").str.to_lowercase().str.contains(search.lower(), literal=True)
    )
if category_filter:
    filtered = filtered.filter(pl.col("top_category").is_in(category_filter))
filtered = filtered.filter(pl.col("avg_viewers") >= min_viewers)

if filtered.is_empty():
    st.info(t("common.no_data_in_range"))
    st.stop()

RANKINGS = {
    t("streamers.rank.donations"): ("amount_eur", "€"),
    t("streamers.rank.engagement"): ("total_messages", t("common.unit.messages")),
    t("streamers.rank.audience"): ("avg_viewers", t("common.unit.viewers")),
    t("streamers.rank.efficiency"): ("donation_eur_per_avg_viewer", "€"),
}

rank_by = st.radio(t("streamers.rank_by"), list(RANKINGS.keys()), horizontal=True)
column, unit = RANKINGS[rank_by]
if len(filtered) <= 1:
    top_n = len(filtered)
else:
    top_n = st.slider(
        t("streamers.top_n"),
        min_value=1,
        max_value=len(filtered),
        value=min(15, len(filtered)),
    )
top = filtered.sort(column, descending=True).head(top_n)

kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric(t("streamers.kpi.top", metric=rank_by), top["streamer"][0])
kpi2.metric(t("streamers.kpi.total_raised"), f"{top['amount_eur'].sum():,.0f} €")
kpi3.metric(t("streamers.kpi.total_messages"), f"{top['total_messages'].sum():,.0f}")

# Ranked magnitude across many streamers: one hue for the whole chart, not one
# per bar — a distinct color per bar here would be decorative, not meaningful.
ordered = top.sort(column, descending=False)
bar_fig = go.Figure(
    go.Bar(
        x=ordered[column],
        y=ordered["streamer"],
        orientation="h",
        marker_color=CATEGORICAL[0],
        hovertemplate=f"%{{y}}<br>%{{x:,.0f}} {unit}<extra></extra>",
    )
)
apply_base_layout(
    bar_fig, title=t("streamers.chart.ranked", metric=rank_by), height=max(360, 32 * len(ordered))
)
bar_fig.update_xaxes(title_text=unit)
bar_fig.update_layout(showlegend=False)
st.plotly_chart(bar_fig, width="stretch")
chart_explainer(t("streamers.explain.ranked"))

st.subheader(t("streamers.correlation_heading"))
st.caption(t("streamers.correlation_caption"))
# Naming a "correlation" section without stating the actual coefficient
# leaves the reader to eyeball scatter, which is imprecise and easy to
# over- or under-read. `None` (too few points, or one axis constant) is
# shown as "—" rather than a fabricated number.
audience_engagement_r = (
    filtered.select(pl.corr("avg_viewers", "total_messages")).item() if len(filtered) >= 2 else None
)
st.caption(
    t("streamers.correlation_stat", r=f"{audience_engagement_r:.2f}")
    if audience_engagement_r is not None
    else t("streamers.correlation_stat_na")
)
# Four variables at once: x/y are the audience-vs-engagement position, bubble
# size is donations raised, and color is donation *efficiency* (€ per
# viewer) — a streamer can be big on all three of the first variables while
# still converting audience to donations worse than a smaller one, and that
# only shows up once it has its own visual channel instead of being folded
# into a single flat marker color.
efficiency = filtered["donation_eur_per_avg_viewer"].fill_null(0)
scatter_fig = go.Figure(
    go.Scatter(
        x=filtered["avg_viewers"],
        y=filtered["total_messages"],
        mode="markers",
        marker={
            "color": efficiency,
            "colorscale": SEQUENTIAL_GOLD_COLORSCALE,
            "colorbar": {"title": t("streamers.efficiency_axis")},
            "size": (filtered["amount_eur"].clip(lower_bound=1) ** 0.5) / 3 + 6,
            "opacity": 0.85,
            "line": {"width": 1, "color": CHROME["page"]},
        },
        text=filtered["streamer"],
        customdata=efficiency,
        hovertemplate=(
            "%{text}<br>viewers: %{x:,.0f}<br>messages: %{y:,.0f}"
            "<br>%{customdata:.2f} €/viewer<extra></extra>"
        ),
    )
)
apply_base_layout(scatter_fig, title=t("streamers.chart.correlation"), height=420)
scatter_fig.update_xaxes(title_text=t("common.unit.viewers"))
scatter_fig.update_yaxes(title_text=t("common.unit.messages"))
scatter_fig.update_layout(showlegend=False)
st.plotly_chart(scatter_fig, width="stretch")
chart_explainer(t("streamers.explain.correlation"))

st.subheader(t("streamers.top_chatters_heading"))
filtered_channels = sorted(filtered["channel"].unique().to_list())
all_channels = sorted(df["channel"].unique().to_list())
is_streamer_filtered = filtered_channels != all_channels
st.caption(
    t("streamers.top_chatters_caption_filtered", n=len(filtered_channels))
    if is_streamer_filtered
    else t("streamers.top_chatters_caption_all", n=len(filtered_channels))
)
date_range = get_global_date_range() or get_event_bounds()
chatters_for_streamers = (
    get_top_chatters_for_channels(filtered_channels, *date_range)
    if date_range
    else pl.DataFrame()
)
chatters_for_streamers = apply_global_chatter_filter(chatters_for_streamers)
if chatters_for_streamers.is_empty():
    st.info(t("common.no_data_in_range"))
else:
    tc_col1, tc_col2 = st.columns([1, 3])
    with tc_col1:
        hide_bots_chatters = st.checkbox(
            t("chatters.hide_bots"), value=True, key="streamers_chatters_hide_bots"
        )
    shown_top_chatters = (
        chatters_for_streamers.filter(~bot_filter_expr())
        if hide_bots_chatters
        else chatters_for_streamers
    )
    if shown_top_chatters.is_empty():
        st.info(t("common.no_data_in_range"))
    else:
        with tc_col2:
            if len(shown_top_chatters) <= 1:
                chatters_top_n = len(shown_top_chatters)
            else:
                chatters_top_n = st.slider(
                    t("chatters.top_n"),
                    min_value=1,
                    max_value=len(shown_top_chatters),
                    value=min(15, len(shown_top_chatters)),
                    key="streamers_chatters_top_n",
                )
        top_chatters_ordered = (
            shown_top_chatters.sort("message_count", descending=True)
            .head(chatters_top_n)
            .sort("message_count", descending=False)
        )
        top_chatters_fig = go.Figure(
            go.Bar(
                x=top_chatters_ordered["message_count"],
                y=top_chatters_ordered["chatter"],
                orientation="h",
                marker_color=CATEGORICAL[0],
                customdata=top_chatters_ordered["channels_in_filter"],
                hovertemplate=(
                    "%{y}<br>%{x:,.0f} messages<br>in %{customdata} of the channels above"
                    "<extra></extra>"
                ),
            )
        )
        apply_base_layout(
            top_chatters_fig,
            title=t("streamers.chart.top_chatters", n=chatters_top_n),
            height=max(360, 28 * len(top_chatters_ordered)),
        )
        top_chatters_fig.update_xaxes(title_text=t("common.unit.messages"))
        top_chatters_fig.update_layout(showlegend=False)
        st.plotly_chart(top_chatters_fig, width="stretch")
        chart_explainer(t("streamers.explain.top_chatters"))

st.subheader(t("streamers.profile_heading"))
compare_options = filtered["streamer"].to_list()
# Same guard as the Donation Tracker's category multiselect: the local
# search/category/min-viewers filters above can narrow `compare_options`
# out from under a previously selected streamer, and `st.multiselect`
# crashes if its stored value isn't a subset of `options` — so drop only
# the entries that fell out. Only the very first load (no stored value
# yet) seeds a default; once the user has made a choice, an empty result
# after pruning is left empty (they'll see "pick at least one" below)
# rather than silently swapped back in for a streamer they didn't pick.
_compare_key = "streamers_compare_select"
_stored_compare = st.session_state.get(_compare_key)
if _stored_compare is None:
    st.session_state[_compare_key] = compare_options[:1]
else:
    _valid_compare = [s for s in _stored_compare if s in compare_options][:4]
    if _valid_compare != _stored_compare:
        st.session_state[_compare_key] = _valid_compare
selected = st.multiselect(
    t("streamers.pick_streamer"), options=compare_options, key=_compare_key, max_selections=4
)

if not selected:
    st.info(t("streamers.pick_at_least_one"))
else:
    comparing = len(selected) > 1
    profiles = {s: filtered.filter(pl.col("streamer") == s).row(0, named=True) for s in selected}

    if comparing:
        compare_rows = []
        for s in selected:
            p = profiles[s]
            uptime_display = (
                f"{min(p['uptime_pct'], 100):.0f}%"
                if p["uptime_pct"] <= 100
                else t("streamers.uptime_quirk")
            )
            compare_rows.append(
                {
                    t("streamers.column.streamer"): s,
                    t("streamers.kpi.peak_viewers"): f"{p['peak_viewers']:,.0f}",
                    t("streamers.kpi.uptime"): uptime_display,
                    t("streamers.kpi.top_category"): p["top_category"] or "—",
                    t("streamers.kpi.unique_chatters"): f"{p['unique_chatters']:,.0f}",
                }
            )
        st.dataframe(pl.DataFrame(compare_rows), width="stretch", hide_index=True)
    else:
        profile = profiles[selected[0]]
        pcol1, pcol2, pcol3, pcol4 = st.columns(4)
        pcol1.metric(t("streamers.kpi.peak_viewers"), f"{profile['peak_viewers']:,.0f}")
        uptime_display = (
            f"{min(profile['uptime_pct'], 100):.0f}%"
            if profile["uptime_pct"] <= 100
            else t("streamers.uptime_quirk")
        )
        pcol2.metric(t("streamers.kpi.uptime"), uptime_display)
        pcol3.metric(t("streamers.kpi.top_category"), profile["top_category"] or "—")
        pcol4.metric(t("streamers.kpi.unique_chatters"), f"{profile['unique_chatters']:,.0f}")

    st.caption(t("streamers.radar_caption"))
    # Percentile rank (0-100) against *every* streamer event-wide — deliberately
    # `full_df`, not `df` (already narrowed by the global streamer filter above)
    # or `filtered` (this page's own local search/category/min-viewers filters):
    # same "compare to the whole field" reasoning as the diurnal chart's
    # event-average line, and computed once per metric column, not per streamer,
    # since a rank only means anything against the full, unfiltered field.
    RADAR_METRICS = [
        ("amount_eur", t("streamers.radar.donations")),
        ("avg_viewers", t("streamers.radar.audience")),
        ("total_messages", t("streamers.radar.engagement")),
        ("donation_eur_per_avg_viewer", t("streamers.radar.efficiency")),
        ("uptime_pct", t("streamers.radar.uptime")),
    ]
    percentile_df = full_df.with_columns(
        [
            (pl.col(col).fill_null(0).rank(method="average") / len(full_df) * 100).alias(
                f"{col}_pctl"
            )
            for col, _ in RADAR_METRICS
        ]
    )
    radar_series = [
        (
            s,
            [
                percentile_df.filter(pl.col("streamer") == s).row(0, named=True)[f"{col}_pctl"]
                for col, _ in RADAR_METRICS
            ],
        )
        for s in selected
    ]
    radar_title = (
        t("streamers.chart.radar_compare")
        if comparing
        else t("streamers.chart.radar", streamer=selected[0])
    )
    st.plotly_chart(
        build_radar_figure(
            [label for _, label in RADAR_METRICS],
            radar_series,
            title=radar_title,
            reference_value=50,
            reference_name=t("streamers.radar.median"),
        ),
        width="stretch",
    )
    chart_explainer(t("streamers.explain.radar"))

    detail_col1, detail_col2 = st.columns(2)
    with detail_col1:
        loyalty_categories = [
            t("common.chatter_profile.loyal"),
            t("common.chatter_profile.multi_streamer"),
            t("common.chatter_profile.semi_nomad"),
            t("common.chatter_profile.nomad"),
        ]
        if comparing:
            chatter_mix = go.Figure()
            for i, s in enumerate(selected):
                p = profiles[s]
                chatter_mix.add_trace(
                    go.Bar(
                        x=loyalty_categories,
                        y=[
                            p["sedentaire_chatters"],
                            p["multi_streamer_chatters"],
                            p["semi_nomade_chatters"],
                            p["nomade_chatters"],
                        ],
                        name=s,
                        marker_color=CATEGORICAL[i % len(CATEGORICAL)],
                    )
                )
            apply_base_layout(
                chatter_mix, title=t("streamers.chart.loyalty_mix_compare"), height=320
            )
            chatter_mix.update_layout(barmode="group")
        else:
            profile = profiles[selected[0]]
            chatter_mix = go.Figure(
                go.Bar(
                    x=loyalty_categories,
                    y=[
                        profile["sedentaire_chatters"],
                        profile["multi_streamer_chatters"],
                        profile["semi_nomade_chatters"],
                        profile["nomade_chatters"],
                    ],
                    marker_color=CATEGORICAL[:4],
                )
            )
            apply_base_layout(
                chatter_mix,
                title=t("streamers.chart.loyalty_mix", streamer=selected[0]),
                height=320,
            )
            chatter_mix.update_layout(showlegend=False)
        chatter_mix.update_yaxes(title_text=t("common.unit.chatters"))
        st.plotly_chart(chatter_mix, width="stretch")
        st.caption(t("common.chatter_profile.caption"))
        chart_explainer(t("streamers.explain.loyalty_mix"))
    with detail_col2:
        # One loop handles 1 or N streamers alike — the single-streamer case
        # is just this loop running once. The event-average line is added
        # only once (it's the same series regardless of which streamer's
        # diurnal query returned it) rather than once per streamer.
        diurnal_fig = go.Figure()
        event_avg_added = False
        for i, s in enumerate(selected):
            diurnal = get_streamer_diurnal_profile(profiles[s]["channel"])
            if diurnal.is_empty():
                continue
            diurnal_fig.add_trace(
                go.Scatter(
                    x=diurnal["hour_of_day"],
                    y=diurnal["streamer_avg_viewer_count"],
                    mode="lines",
                    name=s,
                    line={"color": CATEGORICAL[i % len(CATEGORICAL)], "width": 2},
                )
            )
            if not event_avg_added:
                diurnal_fig.add_trace(
                    go.Scatter(
                        x=diurnal["hour_of_day"],
                        y=diurnal["event_avg_viewer_count"],
                        mode="lines",
                        name=t("streamers.event_average"),
                        line={"color": CATEGORICAL[7], "width": 2, "dash": "dot"},
                    )
                )
                event_avg_added = True
        if not diurnal_fig.data:
            st.info(t("streamers.no_diurnal_data"))
        else:
            apply_base_layout(diurnal_fig, title=t("streamers.chart.diurnal"), height=320)
            diurnal_fig.update_xaxes(title_text=t("streamers.hour_of_day"))
            diurnal_fig.update_yaxes(title_text=t("common.unit.avg_viewers"))
            st.plotly_chart(diurnal_fig, width="stretch")
            chart_explainer(t("streamers.explain.diurnal"))

    if comparing:
        # The overnight-highlighting bar chart's whole visual meaning (muted
        # vs. bright bars) is per-single-streamer — mixing several
        # streamers' bars together would just be noise, so it's skipped
        # rather than forced into a shape it doesn't fit.
        st.caption(t("streamers.night_shift_compare_note"))
    else:
        night_shift = get_streamer_night_shift(profiles[selected[0]]["channel"])
        if not night_shift.is_empty():
            st.caption(t("streamers.night_shift_caption"))
            night_colors = [
                STATUS["muted"] if overnight else CATEGORICAL[0]
                for overnight in night_shift["is_overnight"]
            ]
            night_fig = go.Figure(
                go.Bar(
                    x=night_shift["hour_of_day"],
                    y=night_shift["donation_eur_per_viewer"],
                    marker_color=night_colors,
                    hovertemplate="%{x}h<br>%{y:.3f} €/viewer<extra></extra>",
                )
            )
            apply_base_layout(
                night_fig, title=t("streamers.chart.night_shift", streamer=selected[0]), height=300
            )
            night_fig.update_xaxes(title_text=t("streamers.hour_of_day"), dtick=2)
            night_fig.update_yaxes(title_text=t("streamers.night_shift_axis"))
            night_fig.update_layout(showlegend=False)
            st.plotly_chart(night_fig, width="stretch")
            chart_explainer(t("streamers.explain.night_shift"))

with st.expander(t("common.view_data")):
    st.dataframe(filtered, width="stretch", hide_index=True)
    st.download_button(
        t("common.download_csv"), filtered.write_csv(), file_name="streamers.csv", mime="text/csv"
    )

page_footer()

logger.info(
    "Streamers page rendered (rows=%s, rank_by=%s, top_n=%s)", len(filtered), rank_by, top_n
)
