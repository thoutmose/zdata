"""Donations page: cumulative total, pace, event-phase split, and leaderboard movement."""

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
    apply_global_date_filter,
    apply_global_streamer_filter,
    get_global_date_range,
    get_global_streamer_names,
)
from app.components.theme import (
    CATEGORICAL,
    CHROME,
    apply_base_layout,
    build_podium_figure,
    build_race_figure,
    hex_to_rgba,
)
from app.core.i18n import t
from app.core.logging_config import setup_logging
from app.data.external_donations import (
    KNOWN_EDITION_YEARS,
    get_edition_kickoff_time,
    get_historical_donation_curve,
)
from app.data.repository import (
    get_channel_donations_leaderboard_timeseries,
    get_data_quality_check,
    get_donation_spike_moments,
    get_donation_timeseries,
    get_donations_by_category,
    get_event_phase_breakdown,
    get_leaderboard_movers,
    get_streamer_breakdown,
)

setup_logging()
logger = logging.getLogger(__name__)

page_header(t("donations.title"), "📈", t("donations.description"))

full_event_df = get_donation_timeseries()
if full_event_df.is_empty():
    st.warning(t("donations.no_data"))
    st.stop()

date_range = get_global_date_range()
selected_streamer_names = get_global_streamer_names()
df = apply_global_date_filter(full_event_df, timestamp_col="timestamp")

if df.is_empty():
    st.info(t("common.no_data_in_range"))
    st.stop()

latest = df.row(-1, named=True)
hourly_amount = df["cumulative_amount_eur"].diff().fill_null(df["cumulative_amount_eur"][0])

quality = get_data_quality_check()
divergence = quality.row(0, named=True)["divergence_eur"] if not quality.is_empty() else None
# Divergence is surfaced in the "Data quality" expander below, not as a banner
# here — it's a diagnostic for anyone who goes looking, not something that
# should compete with the KPIs for attention on every page load.

kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric(t("donations.kpi.total_raised"), f"{latest['cumulative_amount_eur']:,.0f} €")
kpi2.metric(t("donations.kpi.active_streamers"), f"{latest['active_streamers']:,}")
kpi3.metric(t("donations.kpi.best_hour"), f"{hourly_amount.max():,.0f} €")

st.subheader(t("donations.podium_heading"))
date_filter_caveat()
top_donors = apply_global_streamer_filter(get_streamer_breakdown())
if len(top_donors) < 3:
    st.info(t("common.no_data_in_range"))
else:
    st.caption(t("donations.podium_caption"))
    top3 = top_donors.sort("amount_eur", descending=True).head(3)
    st.plotly_chart(
        build_podium_figure(
            top3["streamer"].to_list(),
            top3["amount_eur"].to_list(),
            title=t("donations.chart.podium"),
            unit="€",
        ),
        width="stretch",
    )
    chart_explainer(t("donations.explain.podium"))

cumulative_fig = go.Figure(
    go.Scatter(
        x=df["timestamp"],
        y=df["cumulative_amount_eur"],
        mode="lines",
        line={"color": CATEGORICAL[0], "width": 2},
        fill="tozeroy",
        fillcolor=hex_to_rgba(CATEGORICAL[0], 0.12),
        hovertemplate="%{x|%a %H:%M}<br>%{y:,.0f} €<extra></extra>",
        name=t("donations.chart.cumulative"),
    )
)
apply_base_layout(cumulative_fig, title=t("donations.chart.cumulative"))
cumulative_fig.update_yaxes(title_text="€")
st.plotly_chart(cumulative_fig, width="stretch")
chart_explainer(t("donations.explain.cumulative"))

st.subheader(t("donations.editions_heading"))
date_filter_caveat()
# Own event's curve reuses `full_event_df` (loaded above, before the global
# date filter is applied) rather than also fetching this year's *totals*
# from EvenMoreStats — it's the same underlying total, and this app's own
# warehouse is the authoritative source for it. Deliberately NOT the
# filtered `df`: every historical curve below is always the edition's full
# hour-zero-to-end curve, so narrowing the current year's curve to the
# sidebar's date range would make it look artificially low/short next to
# them instead of comparing like with like.
current_year = full_event_df["timestamp"][0].year
# "Hour 0" is anchored to the real event kickoff (from EvenMoreStats, which
# every historical curve below is already anchored to), not to this app's
# own first ingested snapshot — our ingestion starts recording during the
# ~20-hour pre-show/tech-check period, when donations are near-zero and
# barely moving, well before the marathon itself begins. Counting that
# quiet lead-in as part of "hours since start" would make the current
# year look badly behind every past edition at a given hour mark, even
# though it's genuinely on pace once both curves start at the same real
# moment. Falls back to our own first snapshot if EvenMoreStats is
# unreachable — a shifted x-axis is a better failure mode than crashing.
kickoff_time = get_edition_kickoff_time(current_year) or full_event_df["timestamp"][0]
current_curve = (
    full_event_df.filter(pl.col("timestamp") >= kickoff_time)
    .select(
        ((pl.col("timestamp") - kickoff_time).dt.total_seconds() / 3600).alias(
            "hours_since_start"
        ),
        pl.col("cumulative_amount_eur"),
    )
)
# Chronological order (not "current year first") so the legend reads as a
# timeline rather than jumping back and forth — the current edition still
# stands out on its own via color/width/dash, not via list position.
editions: list[tuple[int, pl.DataFrame, bool]] = []
for year in sorted({current_year, *KNOWN_EDITION_YEARS}):
    if year == current_year:
        editions.append((year, current_curve, True))
        continue
    historical_curve = get_historical_donation_curve(year)
    if not historical_curve.is_empty():
        editions.append((year, historical_curve, False))

if len(editions) == 1:
    st.info(t("donations.editions_unavailable"))
else:
    st.caption(t("donations.editions_caption"))
    editions_fig = go.Figure()
    # Emphasis, not categorical: the story is "this year vs. its history," so
    # only the current edition gets the brand accent — every past edition
    # shares one muted gray (a different dash style each, since 4 same-color
    # dotted lines would otherwise only be tellable apart by hovering).
    _HISTORICAL_DASHES = ["dot", "dash", "longdash", "dashdot"]
    dash_i = 0
    for year, curve, is_current in editions:
        if is_current:
            line = {"color": CATEGORICAL[0], "width": 3, "dash": "solid"}
        else:
            line = {
                "color": CHROME["text_muted"],
                "width": 2,
                "dash": _HISTORICAL_DASHES[dash_i % len(_HISTORICAL_DASHES)],
            }
            dash_i += 1
        editions_fig.add_trace(
            go.Scatter(
                x=curve["hours_since_start"],
                y=curve["cumulative_amount_eur"],
                mode="lines",
                name=str(year),
                line=line,
                hovertemplate=f"%{{x:.1f}}h<br>%{{y:,.0f}} €<extra>{year}</extra>",
            )
        )
    apply_base_layout(editions_fig, title=t("donations.chart.editions"))
    editions_fig.update_xaxes(title_text=t("donations.hours_since_start"))
    # Log scale: 2025's ~€16.2M final total is over 2x every other edition's,
    # which on a linear axis flattens every other line — including this
    # year's own, still-in-progress one — into the bottom of the chart.
    editions_fig.update_yaxes(
        title_text=t("donations.editions_y_axis"),
        type="log",
        tickmode="array",
        tickvals=[1_000, 10_000, 100_000, 1_000_000, 10_000_000],
        ticktext=["1K €", "10K €", "100K €", "1M €", "10M €"],
    )
    st.plotly_chart(editions_fig, width="stretch")
    chart_explainer(t("donations.explain.editions"))

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

st.subheader(t("donations.donation_race_heading"))
donation_race_top_n = bounded_top_n_slider(
    label=t("donations.donation_race_top_n"),
    max_value=len(top_donors),
    key="donations_donation_race_top_n",
    default_n=8,
)
donation_race = (
    get_channel_donations_leaderboard_timeseries(*date_range, donation_race_top_n)
    if date_range
    else pl.DataFrame()
)
donation_race = apply_global_streamer_filter(donation_race)
if donation_race.is_empty():
    st.info(t("donations.no_donation_race"))
else:
    st.caption(t("donations.donation_race_caption"))
    donation_race_fig = build_race_figure(
        donation_race,
        value_col="amount_eur",
        rank_col="donation_rank_at_hour",
        title=t("donations.chart.donation_race"),
        unit="€",
    )
    st.plotly_chart(donation_race_fig, width="stretch")
    chart_explainer(t("donations.explain.donation_race"))

st.subheader(t("donations.spikes_heading"))
spikes = get_donation_spike_moments(*date_range) if date_range else pl.DataFrame()
if selected_streamer_names and not spikes.is_empty():
    spikes = spikes.filter(pl.col("display_name").is_in(selected_streamer_names))
if spikes.is_empty():
    st.info(t("donations.no_spikes"))
else:
    st.caption(t("donations.spikes_caption"))
    st.dataframe(
        spikes.select(
            "display_name",
            "ingested_at",
            "donation_delta_eur",
            "title",
            "category",
            "chat_messages_that_hour",
        ),
        width="stretch",
        hide_index=True,
    )
    chart_explainer(t("donations.explain.spikes"))

st.subheader(t("donations.phases_heading"))
date_filter_caveat()
entity_filter_caveat()
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
entity_filter_caveat()
by_category = get_donations_by_category(*date_range) if date_range else pl.DataFrame()
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
movers = get_leaderboard_movers(date_range[1]) if date_range else pl.DataFrame()
if selected_streamer_names:
    movers = movers.filter(pl.col("streamer").is_in(selected_streamer_names))
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
    date_filter_caveat()
    entity_filter_caveat()
    if quality.is_empty():
        st.caption(t("donations.quality_no_data"))
    else:
        checked_at_str = f"{quality.row(0, named=True)['checked_at']:%H:%M} (Europe/Paris)"
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

page_footer()

logger.info("Donations page rendered (rows=%s)", len(df))
