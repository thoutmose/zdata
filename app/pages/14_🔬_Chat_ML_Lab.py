"""Chat ML Lab page: real trained machine-learning models over live chat.

Unlike Chat Intelligence (`13_🧠_Chat_Intelligence.py`) — deliberately just
word lists and counting, no ML dependency — this page uses actual
`scikit-learn` clustering and pretrained `transformers` models. Heavier and
slower on purpose, for questions a keyword count can't answer: what topics
does chat actually organize into (not just top words), what behavioral
segments exist among chatters, and does a real trained model even agree
with the lexicon heuristic?

Both techniques were shaped by testing against real ZEvent data, not
assumed from documentation — see `app/data/chat_ml.py`'s module docstring
for what was tried and rejected (clustering raw messages collapsed into one
useless catch-all cluster; a smaller toxicity model confidently
mislabeled a wholesome message as toxic).

Real streamer/chatter names are shown everywhere on this page — same as
every other page in this app (Chatters/Streamers/Community already show
real names). That includes the sentiment/toxicity model-vs-lexicon
comparison table: neither the model nor the lexicon is a certified
classifier (both make real, confirmed mistakes — see `app/data/chat_ml.py`
and `app/data/chat_lexicons.py` for what was tested and got wrong), so
treat a "toxic"/"hostile" flag anywhere on this page as a lead to look at
in context, not a verdict about the person who sent it.
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
    get_global_chatter_names,
    get_global_date_range,
)
from app.components.theme import CATEGORICAL, apply_base_layout
from app.core.i18n import t
from app.core.logging_config import setup_logging
from app.data.bot_heuristic import bot_filter_expr
from app.data.chat_lexicons import HOSTILE_WORDS, contains_any
from app.data.chat_ml import (
    CHATTER_CLUSTER_FEATURES,
    STREAMER_CLUSTER_FEATURES,
    classify_messages_ml,
    cluster_channel_hours,
    cluster_chatters,
    cluster_streamers,
    contextual_message_embeddings,
    dependency_parse,
    detect_chat_mood_outliers,
    detect_chatter_outliers,
    detect_streamer_outliers,
    fit_donation_forecast,
    named_entities,
    pca_projection,
    pos_tag_distribution,
    project_2d,
    word_embedding_projection,
)
from app.data.repository import (
    get_chat_message_sample,
    get_chat_mood_timeseries,
    get_chat_toxicity_examples,
    get_chatter_breakdown,
    get_donation_forecast_features,
    get_streamer_breakdown,
)

setup_logging()
logger = logging.getLogger(__name__)

page_header(t("chatml.title"), "🔬", t("chatml.description"))

date_range = get_global_date_range()

# --- Section 1: message/topic clustering ---
st.subheader(t("chatml.topics_heading"))
st.caption(t("chatml.topics_caption"))
st.caption(t("chatml.data_used.topics"))
topics_k = st.slider(
    t("chatml.topics_n_clusters"), min_value=3, max_value=12, value=8, key="chatml_topics_k"
)
# 40,000, not 200,000: this sample feeds spaCy (topic-cluster lemmatization,
# POS tagging, NER, word embeddings below) — measured directly against real
# chat, 200k messages took over a minute even with unneeded pipeline
# components disabled, while 40k comfortably finishes in single-digit
# seconds with no less real diversity across channel-hours to cluster.
messages_for_topics = (
    get_chat_message_sample(*date_range, 40_000) if date_range else pl.DataFrame()
)
messages_for_topics = apply_global_streamer_filter(messages_for_topics)
selected_chatter_names = get_global_chatter_names()
if selected_chatter_names and not messages_for_topics.is_empty():
    messages_for_topics = messages_for_topics.filter(
        pl.col("chatter").is_in(selected_chatter_names)
    )
if messages_for_topics.is_empty():
    st.info(t("chatml.no_topics"))
else:
    documents, top_terms = cluster_channel_hours(messages_for_topics, n_clusters=topics_k)
    if documents.is_empty() or not top_terms:
        st.info(t("chatml.no_topics"))
    else:
        sizes = documents.group_by("cluster").len().sort("len", descending=True)
        topics_table = sizes.with_columns(
            pl.col("cluster")
            .map_elements(lambda c: ", ".join(top_terms[c]), return_dtype=pl.Utf8)
            .alias("top_terms")
        ).rename(
            {
                "cluster": t("chatml.column.cluster"),
                "len": t("chatml.column.channel_hours"),
                "top_terms": t("chatml.column.top_terms"),
            }
        )
        topics_fig = go.Figure(
            go.Bar(
                x=[f"#{c}" for c in sizes["cluster"].to_list()],
                y=sizes["len"],
                marker_color=CATEGORICAL[0],
                customdata=[", ".join(top_terms[c]) for c in sizes["cluster"].to_list()],
                hovertemplate="%{customdata}<br>%{y} channel-hours<extra></extra>",
            )
        )
        apply_base_layout(topics_fig, title=t("chatml.chart.topics"), height=360)
        topics_fig.update_layout(showlegend=False)
        topics_fig.update_xaxes(title_text=t("chatml.column.cluster"))
        st.plotly_chart(topics_fig, width="stretch")
        st.dataframe(topics_table, width="stretch", hide_index=True)
        chart_explainer(t("chatml.explain.topics"))

# --- Section 1b: linguistic analysis (POS, NER, dependency parse, embeddings) ---
st.subheader(t("chatml.linguistics_heading"))
st.caption(t("chatml.linguistics_caption"))
st.caption(t("chatml.data_used.linguistics"))
if messages_for_topics.is_empty():
    st.info(t("chatml.no_linguistics"))
else:
    st.markdown(f"**{t('chatml.pos_heading')}**")
    pos_dist = pos_tag_distribution(messages_for_topics)
    pos_fig = go.Figure(
        go.Bar(x=pos_dist["pos"], y=pos_dist["count"], marker_color=CATEGORICAL[0])
    )
    apply_base_layout(pos_fig, title=t("chatml.chart.pos_distribution"), height=320)
    pos_fig.update_layout(showlegend=False)
    pos_fig.update_xaxes(title_text=t("chatml.column.pos"))
    st.plotly_chart(pos_fig, width="stretch")
    chart_explainer(t("chatml.explain.pos"))

    st.markdown(f"**{t('chatml.ner_heading')}**")
    entities = named_entities(messages_for_topics)
    if entities.is_empty():
        st.info(t("chatml.no_linguistics"))
    else:
        entities_table = entities.rename(
            {
                "entity": t("chatml.column.entity"),
                "label": t("chatml.column.label"),
                "count": t("chatml.column.count"),
            }
        )
        st.dataframe(entities_table, width="stretch", hide_index=True)
        chart_explainer(t("chatml.explain.ner"))

    st.markdown(f"**{t('chatml.parse_heading')}**")
    st.caption(t("chatml.parse_caption"))
    all_texts = messages_for_topics["message_text"].to_list()
    default_message = next((m for m in all_texts if 15 <= len(m) <= 80), all_texts[0])
    parse_input = st.text_input(
        t("chatml.parse_input_label"), value=default_message, key="chatml_parse_input"
    )
    if parse_input.strip():
        parsed_table = dependency_parse(parse_input).rename(
            {
                "token": t("chatml.column.token"),
                "lemma": t("chatml.column.lemma"),
                "pos": t("chatml.column.pos"),
                "dependency": t("chatml.column.dependency"),
                "head": t("chatml.column.head"),
            }
        )
        st.dataframe(parsed_table, width="stretch", hide_index=True)
        chart_explainer(t("chatml.explain.parse"))

    st.markdown(f"**{t('chatml.word_embeddings_heading')}**")
    word_vectors = word_embedding_projection(messages_for_topics)
    if word_vectors.is_empty():
        st.info(t("chatml.no_word_embeddings"))
    else:
        marker_sizes = 6 + 14 * (word_vectors["count"] / word_vectors["count"].max())
        we_fig = go.Figure(
            go.Scatter(
                x=word_vectors["x"],
                y=word_vectors["y"],
                mode="markers+text",
                text=word_vectors["word"],
                textposition="top center",
                textfont={"size": 10},
                marker={"size": marker_sizes, "color": CATEGORICAL[2], "opacity": 0.75},
                customdata=word_vectors["count"],
                hovertemplate="%{text}<br>count=%{customdata}<extra></extra>",
            )
        )
        apply_base_layout(we_fig, title=t("chatml.chart.word_embeddings"), height=520)
        we_fig.update_layout(showlegend=False)
        we_fig.update_xaxes(title_text=t("chatml.column.pca1"))
        we_fig.update_yaxes(title_text=t("chatml.column.pca2"))
        st.plotly_chart(we_fig, width="stretch")
        chart_explainer(t("chatml.explain.word_embeddings"))

    st.markdown(f"**{t('chatml.contextual_embeddings_heading')}**")
    st.caption(t("chatml.contextual_embeddings_caption"))
    if st.button(t("chatml.contextual_embeddings_button"), key="chatml_run_contextual"):
        with st.spinner(t("chatml.contextual_embeddings_spinner")):
            embed_sample = (
                get_chat_message_sample(*date_range, 150) if date_range else pl.DataFrame()
            )
            embed_sample = apply_global_streamer_filter(embed_sample)
            if selected_chatter_names and not embed_sample.is_empty():
                embed_sample = embed_sample.filter(
                    pl.col("chatter").is_in(selected_chatter_names)
                )
            if embed_sample.is_empty():
                st.info(t("chatml.no_linguistics"))
            else:
                embed_texts, embeddings = contextual_message_embeddings(embed_sample)
                embed_coords = project_2d(embeddings)
                ce_fig = go.Figure(
                    go.Scatter(
                        x=embed_coords[:, 0],
                        y=embed_coords[:, 1],
                        mode="markers",
                        marker={"color": CATEGORICAL[3], "size": 8},
                        text=embed_texts,
                        hovertemplate="%{text}<extra></extra>",
                    )
                )
                apply_base_layout(
                    ce_fig, title=t("chatml.chart.contextual_embeddings"), height=480
                )
                ce_fig.update_layout(showlegend=False)
                ce_fig.update_xaxes(title_text=t("chatml.column.pca1"))
                ce_fig.update_yaxes(title_text=t("chatml.column.pca2"))
                st.plotly_chart(ce_fig, width="stretch")
    else:
        st.caption(t("chatml.contextual_embeddings_hint"))

# --- Section 2: streamer behavioral clustering ---
st.subheader(t("chatml.streamers_heading"))
st.caption(t("chatml.streamers_caption"))
st.caption(t("chatml.data_used.streamers"))
streamers_k = st.slider(
    t("chatml.streamers_n_clusters"), min_value=2, max_value=8, value=5, key="chatml_streamers_k"
)
streamers_for_clustering = apply_global_streamer_filter(get_streamer_breakdown())
if len(streamers_for_clustering) < streamers_k:
    st.info(t("chatml.no_streamers_ml"))
else:
    clustered_streamers = cluster_streamers(streamers_for_clustering, n_clusters=streamers_k)
    streamers_summary = (
        clustered_streamers.group_by("cluster")
        .agg(
            pl.len().alias("n"),
            pl.col("amount_eur").mean().round(0).alias("avg_amount"),
            pl.col("avg_viewers").mean().round(0).alias("avg_avg_viewers"),
            pl.col("hours_live").mean().round(1).alias("avg_hours_live"),
            pl.col("uptime_pct").mean().round(1).alias("avg_uptime_pct"),
        )
        .sort("n", descending=True)
        .rename(
            {
                "cluster": t("chatml.column.cluster"),
                "n": t("chatml.column.streamers"),
                "avg_amount": t("chatml.column.avg_amount"),
                "avg_avg_viewers": t("chatml.column.avg_avg_viewers"),
                "avg_hours_live": t("chatml.column.avg_hours_live"),
                "avg_uptime_pct": t("chatml.column.avg_uptime_pct"),
            }
        )
    )
    st.dataframe(streamers_summary, width="stretch", hide_index=True)

    streamers_pca = pca_projection(clustered_streamers, STREAMER_CLUSTER_FEATURES)
    all_streamer_cluster_ids = sorted(clustered_streamers["cluster"].unique().to_list())
    pca_search_col, pca_clusters_col = st.columns([2, 1])
    with pca_search_col:
        streamer_search = st.text_input(
            t("chatml.streamers_pca_search_label"), key="chatml_streamers_pca_search"
        )
    with pca_clusters_col:
        shown_streamer_clusters = st.multiselect(
            t("chatml.streamers_pca_clusters_label"),
            options=all_streamer_cluster_ids,
            default=all_streamer_cluster_ids,
            format_func=lambda c: f"#{c}",
            key="chatml_streamers_pca_clusters",
        )
    streamers_scatter = go.Figure()
    for cluster_id in all_streamer_cluster_ids:
        if cluster_id not in shown_streamer_clusters:
            continue
        mask = (clustered_streamers["cluster"] == cluster_id).to_numpy()
        cluster_rows = clustered_streamers.filter(pl.col("cluster") == cluster_id)
        streamers_scatter.add_trace(
            go.Scatter(
                x=streamers_pca[mask, 0],
                y=streamers_pca[mask, 1],
                mode="markers",
                name=f"#{cluster_id}",
                marker={"color": CATEGORICAL[cluster_id % len(CATEGORICAL)], "size": 9},
                text=cluster_rows["streamer"],
                customdata=cluster_rows["channel"],
                hovertemplate="%{text} (%{customdata})<extra></extra>",
            )
        )
    streamer_search_query = streamer_search.strip().lower()
    if streamer_search_query:
        shown_mask = clustered_streamers["cluster"].is_in(shown_streamer_clusters).to_numpy()
        name_hit = clustered_streamers["streamer"].str.to_lowercase().str.contains(
            streamer_search_query, literal=True
        )
        channel_hit = clustered_streamers["channel"].str.to_lowercase().str.contains(
            streamer_search_query, literal=True
        )
        match_mask = (name_hit | channel_hit).to_numpy() & shown_mask
        n_streamer_matches = int(match_mask.sum())
        if n_streamer_matches:
            matched_streamers = clustered_streamers.filter(pl.Series(match_mask))
            # A dedicated highlight trace, added last (drawn on top): bigger,
            # gold, black-outlined markers with the name always shown, not
            # just on hover — the whole point of "find X in the crowd".
            streamers_scatter.add_trace(
                go.Scatter(
                    x=streamers_pca[match_mask, 0],
                    y=streamers_pca[match_mask, 1],
                    mode="markers+text",
                    name=t("chatml.streamers_pca_search_label"),
                    marker={"size": 16, "color": "#FFD700", "line": {"color": "black", "width": 2}},
                    text=matched_streamers["streamer"],
                    textposition="top center",
                    textfont={"size": 11, "color": "#FFD700"},
                    customdata=matched_streamers["channel"],
                    hovertemplate="%{text} (%{customdata})<extra></extra>",
                    showlegend=False,
                )
            )
            st.caption(t("chatml.streamers_pca_match_count", n=n_streamer_matches))
        else:
            st.caption(t("chatml.streamers_pca_no_match", query=streamer_search))
    apply_base_layout(streamers_scatter, title=t("chatml.chart.streamers_pca"), height=440)
    streamers_scatter.update_xaxes(title_text=t("chatml.column.pca1"))
    streamers_scatter.update_yaxes(title_text=t("chatml.column.pca2"))
    streamers_scatter.update_layout(
        hovermode="closest",
        legend={
            "orientation": "v",
            "yanchor": "top",
            "y": 1,
            "xanchor": "left",
            "x": 1.02,
            "title": {"text": t("chatml.column.cluster")},
        },
        margin={"r": 110},
    )
    st.plotly_chart(streamers_scatter, width="stretch")
    st.caption(t("chatml.streamers_pca_caption"))
    chart_explainer(t("chatml.explain.streamers_pca"))

    st.markdown(f"**{t('chatml.streamers_examples_heading')}**")
    streamers_examples = (
        clustered_streamers.sort("cluster", "amount_eur", descending=[False, True])
        .group_by("cluster", maintain_order=True)
        .head(5)
        .select("cluster", "streamer", "amount_eur", "avg_viewers")
        .rename(
            {
                "cluster": t("chatml.column.cluster"),
                "streamer": t("chatml.column.streamer"),
                "amount_eur": t("chatml.column.amount"),
                "avg_viewers": t("chatml.column.avg_viewers_short"),
            }
        )
    )
    st.dataframe(streamers_examples, width="stretch", hide_index=True)
    chart_explainer(t("chatml.explain.streamers"))

# --- Section 3: chatter behavioral clustering ---
st.subheader(t("chatml.chatters_heading"))
st.caption(t("chatml.chatters_caption"))
st.caption(t("chatml.data_used.chatters"))
chatters_k = st.slider(
    t("chatml.chatters_n_clusters"), min_value=2, max_value=8, value=5, key="chatml_chatters_k"
)
chatters = get_chatter_breakdown(*date_range) if date_range else pl.DataFrame()
chatters = apply_global_chatter_filter(chatters)
if not chatters.is_empty():
    chatters = chatters.filter(~bot_filter_expr())
if len(chatters) < chatters_k:
    st.info(t("chatml.no_chatters"))
else:
    clustered_chatters = cluster_chatters(chatters, n_clusters=chatters_k)
    chatters_summary = (
        clustered_chatters.group_by("cluster")
        .agg(
            pl.len().alias("n"),
            pl.col("distinct_channel_count").mean().round(1).alias("avg_channels"),
            pl.col("total_message_count").mean().round(1).alias("avg_messages"),
            pl.col("lifespan_hours").mean().round(1).alias("avg_lifespan_hours"),
            pl.col("avg_messages_per_channel").mean().round(1),
        )
        .sort("n", descending=True)
        .rename(
            {
                "cluster": t("chatml.column.cluster"),
                "n": t("chatml.column.chatters"),
                "avg_channels": t("chatml.column.avg_channels"),
                "avg_messages": t("chatml.column.avg_messages"),
                "avg_lifespan_hours": t("chatml.column.avg_lifespan_hours"),
                "avg_messages_per_channel": t("chatml.column.avg_messages_per_channel"),
            }
        )
    )
    st.dataframe(chatters_summary, width="stretch", hide_index=True)

    chatters_pca = pca_projection(clustered_chatters, CHATTER_CLUSTER_FEATURES)
    all_chatter_cluster_ids = sorted(clustered_chatters["cluster"].unique().to_list())
    chatter_pca_search_col, chatter_pca_clusters_col = st.columns([2, 1])
    with chatter_pca_search_col:
        chatter_search = st.text_input(
            t("chatml.chatters_pca_search_label"), key="chatml_chatters_pca_search"
        )
    with chatter_pca_clusters_col:
        shown_chatter_clusters = st.multiselect(
            t("chatml.chatters_pca_clusters_label"),
            options=all_chatter_cluster_ids,
            default=all_chatter_cluster_ids,
            format_func=lambda c: f"#{c}",
            key="chatml_chatters_pca_clusters",
        )
    chatters_scatter = go.Figure()
    for cluster_id in all_chatter_cluster_ids:
        if cluster_id not in shown_chatter_clusters:
            continue
        mask = (clustered_chatters["cluster"] == cluster_id).to_numpy()
        chatters_scatter.add_trace(
            go.Scatter(
                x=chatters_pca[mask, 0],
                y=chatters_pca[mask, 1],
                mode="markers",
                name=f"#{cluster_id}",
                marker={"color": CATEGORICAL[cluster_id % len(CATEGORICAL)], "size": 6},
                text=clustered_chatters.filter(pl.col("cluster") == cluster_id)["chatter"],
                hovertemplate="%{text}<extra></extra>",
            )
        )
    chatter_search_query = chatter_search.strip().lower()
    if chatter_search_query:
        shown_mask = clustered_chatters["cluster"].is_in(shown_chatter_clusters).to_numpy()
        name_hit = clustered_chatters["chatter"].str.to_lowercase().str.contains(
            chatter_search_query, literal=True
        )
        match_mask = name_hit.to_numpy() & shown_mask
        n_chatter_matches = int(match_mask.sum())
        if n_chatter_matches:
            matched_chatters = clustered_chatters.filter(pl.Series(match_mask))
            chatters_scatter.add_trace(
                go.Scatter(
                    x=chatters_pca[match_mask, 0],
                    y=chatters_pca[match_mask, 1],
                    mode="markers+text",
                    name=t("chatml.chatters_pca_search_label"),
                    marker={"size": 12, "color": "#FFD700", "line": {"color": "black", "width": 2}},
                    text=matched_chatters["chatter"],
                    textposition="top center",
                    textfont={"size": 11, "color": "#FFD700"},
                    hovertemplate="%{text}<extra></extra>",
                    showlegend=False,
                )
            )
            st.caption(t("chatml.chatters_pca_match_count", n=n_chatter_matches))
        else:
            st.caption(t("chatml.chatters_pca_no_match", query=chatter_search))
    apply_base_layout(chatters_scatter, title=t("chatml.chart.chatters_pca"), height=440)
    chatters_scatter.update_xaxes(title_text=t("chatml.column.pca1"))
    chatters_scatter.update_yaxes(title_text=t("chatml.column.pca2"))
    chatters_scatter.update_layout(
        hovermode="closest",
        legend={
            "orientation": "v",
            "yanchor": "top",
            "y": 1,
            "xanchor": "left",
            "x": 1.02,
            "title": {"text": t("chatml.column.cluster")},
        },
        margin={"r": 110},
    )
    st.plotly_chart(chatters_scatter, width="stretch")
    st.caption(t("chatml.chatters_pca_caption"))
    chart_explainer(t("chatml.explain.chatters_pca"))

    st.markdown(f"**{t('chatml.chatters_examples_heading')}**")
    chatters_examples = (
        clustered_chatters.sort("cluster", "total_message_count", descending=[False, True])
        .group_by("cluster", maintain_order=True)
        .head(5)
        .select("cluster", "chatter", "distinct_channel_count", "total_message_count")
        .rename(
            {
                "cluster": t("chatml.column.cluster"),
                "chatter": t("chatml.column.chatter"),
                "distinct_channel_count": t("chatml.column.avg_channels"),
                "total_message_count": t("chatml.column.avg_messages"),
            }
        )
    )
    st.dataframe(chatters_examples, width="stretch", hide_index=True)
    chart_explainer(t("chatml.explain.chatters"))

# --- Section 4: outlier detection ---
st.subheader(t("chatml.outliers_heading"))
st.caption(t("chatml.outliers_caption"))
st.caption(t("chatml.data_used.outliers"))
outliers_target_streamers = t("chatml.outliers_target_streamers")
outliers_target_chatters = t("chatml.outliers_target_chatters")
outliers_target_hours = t("chatml.outliers_target_hours")
outliers_target = st.radio(
    t("chatml.outliers_target_label"),
    [outliers_target_streamers, outliers_target_chatters, outliers_target_hours],
    key="chatml_outliers_target",
    horizontal=True,
)
outliers_contamination = st.slider(
    t("chatml.outliers_contamination"),
    min_value=0.01,
    max_value=0.2,
    value=0.05,
    step=0.01,
    key="chatml_outliers_contamination",
)
if outliers_target == outliers_target_streamers:
    streamers_for_outliers = apply_global_streamer_filter(get_streamer_breakdown())
    if len(streamers_for_outliers) < 10:
        st.info(t("chatml.no_outliers"))
    else:
        streamer_outliers = detect_streamer_outliers(
            streamers_for_outliers, contamination=outliers_contamination
        )
        st.dataframe(
            streamer_outliers.select(
                "streamer", "amount_eur", "avg_viewers", "uptime_pct", "anomaly_score"
            ).rename(
                {
                    "streamer": t("chatml.column.streamer"),
                    "amount_eur": t("chatml.column.amount"),
                    "avg_viewers": t("chatml.column.avg_viewers_short"),
                    "uptime_pct": t("chatml.column.uptime_pct"),
                    "anomaly_score": t("chatml.column.anomaly_score"),
                }
            ),
            width="stretch",
            hide_index=True,
        )
elif outliers_target == outliers_target_chatters:
    chatters_for_outliers = get_chatter_breakdown(*date_range) if date_range else pl.DataFrame()
    chatters_for_outliers = apply_global_chatter_filter(chatters_for_outliers)
    if not chatters_for_outliers.is_empty():
        chatters_for_outliers = chatters_for_outliers.filter(~bot_filter_expr())
    if len(chatters_for_outliers) < 10:
        st.info(t("chatml.no_outliers"))
    else:
        chatter_outliers = detect_chatter_outliers(
            chatters_for_outliers, contamination=outliers_contamination
        )
        st.dataframe(
            chatter_outliers.select(
                "chatter", "distinct_channel_count", "total_message_count", "anomaly_score"
            ).rename(
                {
                    "chatter": t("chatml.column.chatter"),
                    "distinct_channel_count": t("chatml.column.avg_channels"),
                    "total_message_count": t("chatml.column.avg_messages"),
                    "anomaly_score": t("chatml.column.anomaly_score"),
                }
            ),
            width="stretch",
            hide_index=True,
        )
else:
    mood_for_outliers = get_chat_mood_timeseries(*date_range) if date_range else pl.DataFrame()
    if len(mood_for_outliers) < 10:
        st.info(t("chatml.no_outliers"))
    else:
        mood_outliers = detect_chat_mood_outliers(
            mood_for_outliers, contamination=outliers_contamination
        )
        st.dataframe(
            mood_outliers.rename(
                {
                    "timestamp": t("chatml.column.hour"),
                    "avg_hype_score": t("chatml.column.avg_hype"),
                    "avg_sentiment_score": t("chatml.column.avg_sentiment"),
                    "anomaly_score": t("chatml.column.anomaly_score"),
                }
            ),
            width="stretch",
            hide_index=True,
        )
chart_explainer(t("chatml.explain.outliers"))

# --- Section 5: ML sentiment/toxicity vs. lexicon heuristic ---
st.subheader(t("chatml.classify_heading"))
st.caption(t("chatml.classify_caption"))
st.caption(t("chatml.data_used.classify"))
if st.button(t("chatml.classify_button"), key="chatml_run_classify"):
    with st.spinner(t("chatml.classify_spinner")):
        toxic_sample = (
            get_chat_toxicity_examples(*date_range, 20) if date_range else pl.DataFrame()
        )
        random_sample = (
            get_chat_message_sample(*date_range, 30) if date_range else pl.DataFrame()
        )
        combined = (
            pl.concat([toxic_sample, random_sample])
            if not toxic_sample.is_empty()
            else random_sample
        )
        combined = apply_global_streamer_filter(combined)
        if selected_chatter_names and not combined.is_empty():
            combined = combined.filter(pl.col("chatter").is_in(selected_chatter_names))
        if combined.is_empty():
            st.info(t("chatml.no_classify"))
        else:
            classified = classify_messages_ml(combined).with_columns(
                pl.col("message_text")
                .map_elements(
                    lambda text: contains_any(text, HOSTILE_WORDS), return_dtype=pl.Boolean
                )
                .alias("lexicon_hostile")
            )
            matches = classified["lexicon_hostile"] == (classified["ml_toxicity_label"] == "toxic")
            agreement = float(matches.mean())
            st.caption(t("chatml.classify_agreement", pct=f"{agreement * 100:.0f}"))
            classify_table = classified.select(
                "channel",
                "chatter",
                "message_text",
                "lexicon_hostile",
                "ml_sentiment_label",
                "ml_toxicity_label",
            ).rename(
                {
                    "channel": t("chatml.column.channel_short"),
                    "chatter": t("chatml.column.chatter"),
                    "message_text": t("chatml.column.message"),
                    "lexicon_hostile": t("chatml.column.lexicon_verdict"),
                    "ml_sentiment_label": t("chatml.column.ml_sentiment"),
                    "ml_toxicity_label": t("chatml.column.ml_toxicity"),
                }
            )
            st.dataframe(classify_table, width="stretch", hide_index=True)
            chart_explainer(t("chatml.explain.classify"))
else:
    st.caption(t("chatml.classify_hint"))

# --- Section 6: donation forecasting from a mid-event snapshot ---
st.subheader(t("chatml.forecast_heading"))
st.caption(t("chatml.forecast_caption"))
st.caption(t("chatml.data_used.forecast"))
if date_range is None:
    st.info(t("chatml.no_forecast"))
else:
    forecast_start, forecast_end = date_range
    forecast_span = forecast_end - forecast_start
    if forecast_span.total_seconds() <= 0:
        st.info(t("chatml.no_forecast"))
    else:
        cutoff_fraction = st.slider(
            t("chatml.forecast_cutoff"),
            min_value=0.05,
            max_value=0.95,
            value=0.5,
            step=0.05,
            key="chatml_forecast_cutoff",
        )
        forecast_cutoff = forecast_start + forecast_span * cutoff_fraction
        cutoff_label = forecast_cutoff.strftime("%a %d %b, %H:%M")
        st.caption(t("chatml.forecast_cutoff_caption", cutoff=cutoff_label))
        forecast_features = get_donation_forecast_features(
            forecast_start, forecast_end, forecast_cutoff
        )
        forecast_features = apply_global_streamer_filter(forecast_features)
        if len(forecast_features) < 10:
            st.info(t("chatml.no_forecast"))
        else:
            forecast_cols = [
                "amount_eur_mid",
                "avg_viewers_mid",
                "peak_viewers_mid",
                "total_messages_mid",
            ]
            forecast_result = fit_donation_forecast(forecast_features, forecast_cols, "amount_eur")
            metric_r2, metric_mae, metric_n = st.columns(3)
            metric_r2.metric(t("chatml.forecast_r2"), f"{forecast_result['r2']:.2f}")
            metric_mae.metric(t("chatml.forecast_mae"), f"€{forecast_result['mae']:,.0f}")
            metric_n.metric(t("chatml.forecast_n_test"), len(forecast_result["channel"]))

            max_val = max(forecast_result["actual"].max(), forecast_result["predicted"].max())
            forecast_scatter = go.Figure()
            forecast_scatter.add_trace(
                go.Scatter(
                    x=[0, max_val],
                    y=[0, max_val],
                    mode="lines",
                    line={"color": "gray", "dash": "dash"},
                    name=t("chatml.forecast_perfect_line"),
                    hoverinfo="skip",
                )
            )
            forecast_scatter.add_trace(
                go.Scatter(
                    x=forecast_result["actual"],
                    y=forecast_result["predicted"],
                    mode="markers",
                    marker={"color": CATEGORICAL[0], "size": 9},
                    text=forecast_result["streamer"],
                    customdata=forecast_result["channel"],
                    hovertemplate=(
                        "%{text} (%{customdata})<br>actual=%{x:.0f} €"
                        "<br>predicted=%{y:.0f} €<extra></extra>"
                    ),
                    name=t("chatml.forecast_scatter_name"),
                )
            )
            apply_base_layout(
                forecast_scatter, title=t("chatml.chart.forecast_scatter"), height=420
            )
            forecast_scatter.update_xaxes(title_text=t("chatml.forecast_axis_actual"))
            forecast_scatter.update_yaxes(title_text=t("chatml.forecast_axis_predicted"))
            forecast_scatter.update_layout(hovermode="closest")
            st.plotly_chart(forecast_scatter, width="stretch")

            importance_labels = {
                "amount_eur_mid": t("chatml.forecast_feature_amount"),
                "avg_viewers_mid": t("chatml.forecast_feature_avg_viewers"),
                "peak_viewers_mid": t("chatml.forecast_feature_peak_viewers"),
                "total_messages_mid": t("chatml.forecast_feature_messages"),
            }
            importances = forecast_result["feature_importances"]
            importance_fig = go.Figure(
                go.Bar(
                    x=list(importances.values()),
                    y=[importance_labels[f] for f in importances],
                    orientation="h",
                    marker_color=CATEGORICAL[1],
                )
            )
            apply_base_layout(
                importance_fig, title=t("chatml.chart.forecast_importance"), height=280
            )
            importance_fig.update_layout(showlegend=False)
            importance_fig.update_yaxes(autorange="reversed")
            st.plotly_chart(importance_fig, width="stretch")
            chart_explainer(t("chatml.explain.forecast"))

page_footer()

logger.info(
    "Chat ML Lab page rendered (topic_messages=%s, streamers=%s, chatters=%s)",
    len(messages_for_topics),
    len(streamers_for_clustering),
    len(chatters),
)
