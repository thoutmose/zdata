"""Chat Intelligence page: lightweight, dependency-free NLP analysis of live chat text.

Real ZEvent chat (confirmed against the live warehouse, not assumed from the
schema) is short — median ~20 characters — dominated by emote-code spam and
copypasta, almost entirely French, and has no labeled data at all. A generic
sentiment/topic model trained on other text wouldn't fit this corpus well,
and — more importantly — a plain regex over `stg.stg_bronze__live_chat`'s
~7.7M unindexed rows reliably blows past `Settings.db_statement_timeout_ms`
(confirmed: even a single simple `~` match times out at full scale). So every
analysis here is lexicon/heuristic ("NLP-lite") rather than a trained model,
and every event-wide one runs over a random *sample* of the window rather
than a full scan — see `app/data/repository.py::PostgresDataSource._chat_sample_rate`
and `app/data/chat_nlp.py` for the exact methods. Sampling alone doesn't
avoid the underlying cost, though: confirmed via `EXPLAIN (ANALYZE,
BUFFERS)` against the real warehouse, the table has no index at all, so
every query scans it in full regardless of the sample rate — cutting the
sample target 50x changed query time by under 5%. Narrowing the *date
window* does help, since Postgres can skip a row's expensive regex/
aggregate work the moment its timestamp fails the (still fully-scanned)
date check — confirmed: a 66-hour window took ~3s, a 1-hour one ~0.4s.
That's why every per-message section below defaults to a short recent
window rather than the sidebar's full selected range, with an explicit
control to widen it.

Sentiment and toxicity share one lexicon (`PostgresDataSource._HOSTILE_WORD_CASE`)
for their "negative" side — both were curated by testing candidate words
individually against real chat, not assumed from a generic list (several
common first guesses — "con", "cretin", "stupide", "pourri" — turned out to
mostly hit unrelated words, Twitch emote codes, or a game title; see that
constant's docstring for what was dropped and why). Toxicity is deliberately
a *channel-level* trend, not a per-chatter "who is toxic" tracker: attaching
a heuristic toxicity label to a real, on-screen chatter name risks enabling
harassment of anyone the heuristic misclassifies — a channel's line rising
then falling as another's rises already shows hostility moving between
communities over the event, without naming anyone.
"""

from __future__ import annotations

import logging
from datetime import timedelta

import plotly.graph_objects as go
import polars as pl
import streamlit as st
from app.components.chrome import (
    bounded_top_n_slider,
    chart_explainer,
    entity_filter_caveat,
    page_footer,
    page_header,
)
from app.components.filters import (
    apply_global_date_filter,
    apply_global_streamer_filter,
    get_global_chatter_names,
    get_global_date_range,
)
from app.components.theme import CATEGORICAL, apply_base_layout, build_race_figure
from app.core.i18n import t
from app.core.logging_config import setup_logging
from app.data.chat_lexicons import HOSTILE_WORDS, HYPE_EMOTE_WORDS, POSITIVE_WORDS
from app.data.repository import (
    get_channel_sentiment_leaderboard_timeseries,
    get_channel_toxicity_leaderboard_timeseries,
    get_chat_hype_components_timeseries,
    get_chat_mood_timeseries,
    get_chat_toxicity_examples,
    get_chat_trending_keywords,
    get_chat_trending_phrases,
    get_donation_timeseries,
    get_streamer_breakdown,
)

setup_logging()
logger = logging.getLogger(__name__)

page_header(t("chatintel.title"), "🧠", t("chatintel.description"))

with st.expander(t("chatintel.methodology_heading"), expanded=False):
    st.markdown(t("chatintel.methodology_intro"))

    st.markdown(f"**{t('chatintel.methodology_hype_intro')}**")
    st.latex(
        r"H = 100 \times \frac{w_{\text{punct}}\,p_{\text{punct}}"
        r" + w_{\text{caps}}\,p_{\text{caps}} + w_{\text{emote}}\,p_{\text{emote}}}"
        r"{w_{\text{punct}} + w_{\text{caps}} + w_{\text{emote}}}"
    )
    st.caption(t("chatintel.methodology_hype_terms"))
    st.caption(t("chatintel.methodology_hype_tunable"))

    st.markdown(f"**{t('chatintel.methodology_sentiment_intro')}**")
    st.latex(r"S = 100 \times \left(p_{\text{pos}} - p_{\text{hostile}}\right)")

    st.markdown(f"**{t('chatintel.methodology_toxicity_intro')}**")
    st.latex(r"T = 100 \times p_{\text{hostile}}")

    st.markdown(t("chatintel.methodology_words_intro"))
    st.markdown(
        f"- {t('chatintel.methodology_positive_words_label')} `{', '.join(POSITIVE_WORDS)}`\n"
        f"- {t('chatintel.methodology_hype_emote_words_label')} "
        f"`{', '.join(HYPE_EMOTE_WORDS)}`\n"
        f"- {t('chatintel.methodology_hostile_words_label')} `{', '.join(HOSTILE_WORDS)}`"
    )
    st.caption(t("chatintel.methodology_examples_pointer"))

    st.markdown(f"**{t('chatintel.methodology_keywords_intro')}**")
    st.latex(r"\mathrm{tf}(w, h) = \text{number of times } w \text{ appears in hour } h")
    st.latex(r"\mathrm{idf}(w) = \log\!\left(\frac{N_{\text{hours}}}{\mathrm{df}(w)}\right)")
    st.latex(r"\mathrm{tfidf}(w, h) = \mathrm{tf}(w, h) \times \mathrm{idf}(w)")
    st.caption(t("chatintel.methodology_keywords_terms"))

    st.markdown(f"**{t('chatintel.methodology_phrases_intro')}**")

    st.markdown(f"**{t('chatintel.methodology_correlation_intro')}**")
    st.latex(
        r"r = \frac{\sum_i (x_i - \bar{x})(y_i - \bar{y})}"
        r"{\sqrt{\sum_i (x_i - \bar{x})^2}\,\sqrt{\sum_i (y_i - \bar{y})^2}}"
    )

    st.markdown(f"**{t('chatintel.methodology_sampling_intro')}**")
    st.latex(
        r"\text{sample\_rate} = \min\!\left(1,\ \frac{N_{\text{target}}}{N_{\text{total}}}\right)"
    )
    st.caption(t("chatintel.methodology_sampling_terms"))

    st.markdown(t("chatintel.methodology_toxicity_privacy"))

date_range = get_global_date_range()
streamers = apply_global_streamer_filter(get_streamer_breakdown())
if streamers.is_empty():
    st.warning(t("chatintel.no_streamers"))
    st.stop()

# Every section below that reads raw chat text scans the *entire* selected
# window regardless of how few results it returns (see the module
# docstring) — narrowing the window is the one thing that actually cuts
# load time, since Postgres can skip a row's regex/aggregate work the
# moment its timestamp fails the (still full-table-scanned, unindexed)
# date check. Defaults to a recent slice, not the full event, for a fast
# page load by default; widen it explicitly when you want the whole event.
_SCOPE_WINDOWS = {
    t("chatintel.scope.last_1h"): timedelta(hours=1),
    t("chatintel.scope.last_6h"): timedelta(hours=6),
    t("chatintel.scope.last_12h"): timedelta(hours=12),
    t("chatintel.scope.full"): None,
}
scope_choice = st.radio(
    t("chatintel.scope_label"),
    list(_SCOPE_WINDOWS),
    index=0,
    horizontal=True,
    key="chatintel_scope",
)
if date_range is None:
    analysis_range = None
else:
    full_start, full_end = date_range
    window = _SCOPE_WINDOWS[scope_choice]
    analysis_range = (max(full_start, full_end - window), full_end) if window else date_range
    st.caption(
        t(
            "chatintel.scope_caption",
            start=analysis_range[0].strftime("%a %H:%M"),
            end=analysis_range[1].strftime("%a %H:%M"),
        )
    )

# --- Section 1: hype score ---
st.subheader(t("chatintel.hype_heading"))
st.caption(t("chatintel.hype_caption"))
weight_col1, weight_col2, weight_col3 = st.columns(3)
with weight_col1:
    hype_w_punct = st.slider(
        t("chatintel.hype_weight_punct"), 0.0, 1.0, 0.4, 0.05, key="chatintel_hype_w_punct"
    )
with weight_col2:
    hype_w_caps = st.slider(
        t("chatintel.hype_weight_caps"), 0.0, 1.0, 0.3, 0.05, key="chatintel_hype_w_caps"
    )
with weight_col3:
    hype_w_emote = st.slider(
        t("chatintel.hype_weight_emote"), 0.0, 1.0, 0.3, 0.05, key="chatintel_hype_w_emote"
    )
hype_top_n = bounded_top_n_slider(
    label=t("chatintel.hype_top_n"),
    max_value=len(streamers),
    key="chatintel_hype_top_n",
    default_n=8,
)
hype_components = (
    get_chat_hype_components_timeseries(*analysis_range) if analysis_range else pl.DataFrame()
)
hype_components = apply_global_streamer_filter(hype_components)
hype_total_weight = hype_w_punct + hype_w_caps + hype_w_emote
if hype_components.is_empty() or hype_total_weight <= 0:
    hype = pl.DataFrame()
else:
    hype_scored = hype_components.with_columns(
        (
            100.0
            * (
                hype_w_punct * pl.col("punct_rate")
                + hype_w_caps * pl.col("caps_rate")
                + hype_w_emote * pl.col("emote_rate")
            )
            / hype_total_weight
        ).alias("hype_score")
    )
    hype_ranked = hype_scored.with_columns(
        pl.col("hype_score")
        .rank(method="min", descending=True)
        .over("timestamp")
        .cast(pl.Int64)
        .alias("hype_rank_at_hour")
    )
    hype_top_channels = (
        hype_ranked.group_by("channel")
        .agg(pl.col("hype_score").mean().alias("overall_hype"))
        .sort("overall_hype", descending=True)
        .head(hype_top_n)["channel"]
        .to_list()
    )
    hype = hype_ranked.filter(pl.col("channel").is_in(hype_top_channels)).select(
        "timestamp", "channel", "hype_score", "hype_rank_at_hour"
    )
if hype.is_empty():
    st.info(t("chatintel.no_hype"))
else:
    hype_fig = build_race_figure(
        hype,
        value_col="hype_score",
        rank_col="hype_rank_at_hour",
        title=t("chatintel.chart.hype"),
        unit=t("chatintel.unit.hype_score"),
    )
    st.plotly_chart(hype_fig, width="stretch")
    chart_explainer(t("chatintel.explain.hype"))

# --- Section 2: sentiment ---
st.subheader(t("chatintel.sentiment_heading"))
st.caption(t("chatintel.sentiment_caption"))
sentiment_top_n = bounded_top_n_slider(
    label=t("chatintel.sentiment_top_n"),
    max_value=len(streamers),
    key="chatintel_sentiment_top_n",
    default_n=8,
)
sentiment = (
    get_channel_sentiment_leaderboard_timeseries(*analysis_range, sentiment_top_n)
    if analysis_range
    else pl.DataFrame()
)
sentiment = apply_global_streamer_filter(sentiment)
if sentiment.is_empty():
    st.info(t("chatintel.no_sentiment"))
else:
    sentiment_fig = build_race_figure(
        sentiment,
        value_col="sentiment_score",
        rank_col="sentiment_rank_at_hour",
        title=t("chatintel.chart.sentiment"),
        unit=t("chatintel.unit.sentiment_score"),
    )
    st.plotly_chart(sentiment_fig, width="stretch")
    chart_explainer(t("chatintel.explain.sentiment"))

# --- Section 3: toxicity ---
st.subheader(t("chatintel.toxicity_heading"))
st.caption(t("chatintel.toxicity_caption"))
toxicity_top_n = bounded_top_n_slider(
    label=t("chatintel.toxicity_top_n"),
    max_value=len(streamers),
    key="chatintel_toxicity_top_n",
    default_n=8,
)
toxicity = (
    get_channel_toxicity_leaderboard_timeseries(*analysis_range, toxicity_top_n)
    if analysis_range
    else pl.DataFrame()
)
toxicity = apply_global_streamer_filter(toxicity)
if toxicity.is_empty():
    st.info(t("chatintel.no_toxicity"))
else:
    toxicity_fig = build_race_figure(
        toxicity,
        value_col="toxicity_score",
        rank_col="toxicity_rank_at_hour",
        title=t("chatintel.chart.toxicity"),
        unit=t("chatintel.unit.toxicity_score"),
    )
    st.plotly_chart(toxicity_fig, width="stretch")
    chart_explainer(t("chatintel.explain.toxicity"))

with st.expander(t("chatintel.toxicity_examples_heading"), expanded=True):
    st.caption(t("chatintel.toxicity_examples_caption"))
    toxicity_examples = (
        get_chat_toxicity_examples(*analysis_range, 15) if analysis_range else pl.DataFrame()
    )
    toxicity_examples = apply_global_streamer_filter(toxicity_examples)
    selected_chatter_names = get_global_chatter_names()
    if selected_chatter_names and not toxicity_examples.is_empty():
        toxicity_examples = toxicity_examples.filter(
            pl.col("chatter").is_in(selected_chatter_names)
        )
    if toxicity_examples.is_empty():
        st.info(t("chatintel.no_toxicity_examples"))
    else:
        toxicity_examples = toxicity_examples.select(
            "channel", "chatter", "message_sent_at", "message_text"
        )
        st.dataframe(
            toxicity_examples.rename(
                {
                    "channel": t("chatintel.column.channel"),
                    "chatter": t("chatintel.column.chatter"),
                    "message_sent_at": t("chatintel.column.hour"),
                    "message_text": t("chatintel.column.message"),
                }
            ),
            width="stretch",
            hide_index=True,
        )

# --- Section 4: chat mood vs. donation pace ---
st.subheader(t("chatintel.correlation_heading"))
st.caption(t("chatintel.correlation_caption"))
entity_filter_caveat()
mood = get_chat_mood_timeseries(*analysis_range) if analysis_range else pl.DataFrame()
donation_pace = apply_global_date_filter(get_donation_timeseries(), timestamp_col="timestamp")
if not donation_pace.is_empty():
    donation_pace = donation_pace.with_columns(
        pl.col("cumulative_amount_eur")
        .diff()
        .fill_null(donation_pace["cumulative_amount_eur"][0])
        .alias("hourly_amount")
    ).select("timestamp", "hourly_amount")
mood_vs_donations = (
    mood.join(donation_pace, on="timestamp", how="inner").drop_nulls()
    if not mood.is_empty() and not donation_pace.is_empty()
    else pl.DataFrame()
)
if len(mood_vs_donations) < 5:
    st.info(t("chatintel.no_correlation"))
else:
    hype_corr = mood_vs_donations.select(pl.corr("avg_hype_score", "hourly_amount")).item()
    sentiment_corr = mood_vs_donations.select(
        pl.corr("avg_sentiment_score", "hourly_amount")
    ).item()
    st.caption(
        t(
            "chatintel.correlation_summary",
            hype_corr=f"{hype_corr:+.2f}",
            sentiment_corr=f"{sentiment_corr:+.2f}",
            n=len(mood_vs_donations),
        )
    )
    correlation_fig = go.Figure(
        go.Scatter(
            x=mood_vs_donations["avg_hype_score"],
            y=mood_vs_donations["hourly_amount"],
            mode="markers",
            marker={"color": CATEGORICAL[0], "size": 9},
            customdata=mood_vs_donations["timestamp"],
            hovertemplate="%{customdata|%a %H:%M}<br>%{x:.1f} hype, %{y:,.0f} €<extra></extra>",
        )
    )
    apply_base_layout(correlation_fig, title=t("chatintel.chart.correlation"), height=380)
    correlation_fig.update_layout(showlegend=False)
    correlation_fig.update_xaxes(title_text=t("chatintel.unit.hype_score"))
    correlation_fig.update_yaxes(title_text=t("common.per_hour", unit="€"))
    st.plotly_chart(correlation_fig, width="stretch")
    chart_explainer(t("chatintel.explain.correlation"))

# --- Section 5: trending phrases / copypasta ---
st.subheader(t("chatintel.phrases_heading"))
st.caption(t("chatintel.phrases_caption"))
phrases = (
    get_chat_trending_phrases(*analysis_range, 100) if analysis_range else pl.DataFrame()
)
phrases = apply_global_streamer_filter(phrases)
if phrases.is_empty():
    st.info(t("chatintel.no_phrases"))
else:
    phrases_top_n = bounded_top_n_slider(
        label=t("chatintel.phrases_top_n"),
        max_value=len(phrases),
        key="chatintel_phrases_top_n",
        default_n=min(20, len(phrases)),
    )
    phrases_table = (
        phrases.sort("repeat_count", descending=True)
        .head(phrases_top_n)
        .select("hour_bucket", "channel", "phrase", "repeat_count")
        .rename(
            {
                "hour_bucket": t("chatintel.column.hour"),
                "channel": t("chatintel.column.channel"),
                "phrase": t("chatintel.column.phrase"),
                "repeat_count": t("chatintel.column.repeat_count"),
            }
        )
    )
    st.dataframe(phrases_table, width="stretch", hide_index=True)
    chart_explainer(t("chatintel.explain.phrases"))

# --- Section 6: trending keywords per channel ---
st.subheader(t("chatintel.keywords_heading"))
st.caption(t("chatintel.keywords_caption"))
streamer_options = streamers["streamer"].to_list()
if len(streamer_options) == 1:
    selected_streamer = streamer_options[0]
    st.caption(t("tracker.pick_streamer_single", streamer=selected_streamer))
else:
    selected_streamer = st.selectbox(
        t("chatintel.pick_channel"), options=streamer_options, key="chatintel_channel_pick"
    )
selected_channel = streamers.filter(pl.col("streamer") == selected_streamer)["channel"][0]

keywords = (
    get_chat_trending_keywords(selected_channel, *date_range) if date_range else pl.DataFrame()
)
if keywords.is_empty():
    st.info(t("chatintel.no_keywords"))
else:
    keywords_table = keywords.rename(
        {"hour_bucket": t("chatintel.column.hour"), "keywords": t("chatintel.column.keywords")}
    )
    st.dataframe(keywords_table, width="stretch", hide_index=True)
    chart_explainer(t("chatintel.explain.keywords"))

page_footer()

logger.info(
    "Chat Intelligence page rendered (hype_rows=%s, sentiment_rows=%s, toxicity_rows=%s, "
    "toxicity_examples=%s, correlation_rows=%s, phrases_rows=%s, keyword_rows=%s)",
    len(hype),
    len(sentiment),
    len(toxicity),
    len(toxicity_examples),
    len(mood_vs_donations),
    len(phrases),
    len(keywords),
)
