from datetime import datetime, timedelta

import numpy as np
import polars as pl
from app.data.chat_ml import (
    STREAMER_CLUSTER_FEATURES,
    _looks_like_emote_code,
    _looks_like_ner_noise,
    cluster_channel_hours,
    cluster_chatters,
    cluster_streamers,
    dependency_parse,
    detect_chat_mood_outliers,
    detect_chatter_outliers,
    detect_streamer_outliers,
    fit_donation_forecast,
    named_entities,
    pca_projection,
    pos_tag_distribution,
    word_embedding_projection,
)


def _messages(rows: list[tuple[str, int, str]]) -> pl.DataFrame:
    """Build a minimal messages frame: `(channel, hour_offset, text)` triples."""
    base = datetime(2026, 9, 4, 20, 0, 0)
    return pl.DataFrame(
        {
            "channel": [channel for channel, _, _ in rows],
            "message_sent_at": [base + timedelta(hours=h) for _, h, _ in rows],
            "message_text": [text for _, _, text in rows],
        }
    )


def test_cluster_channel_hours_drops_sparse_hours() -> None:
    # Only 2 messages for this channel-hour — below the default min_messages_per_hour.
    rows = [("chan_a", 0, "hello") for _ in range(2)]
    documents, top_terms = cluster_channel_hours(_messages(rows), n_clusters=2)
    assert documents.is_empty()
    assert top_terms == {}


def test_cluster_channel_hours_merges_word_inflections_via_lemma() -> None:
    # "regarde"/"regardait"/"regardent" are all inflections of the same
    # verb — with lemmatization they should collapse into one shared top
    # term rather than splitting a topic's signal three ways.
    text = "il regarde le stream, il regardait hier, ils regardent maintenant"
    rows = []
    for hour in range(4):
        rows += [("chan_a", hour, text) for _ in range(30)]
    for hour in range(4, 8):
        rows += [("chan_b", hour, "la cagnotte des dons pour la bonne cause") for _ in range(30)]
    documents, top_terms = cluster_channel_hours(
        _messages(rows), n_clusters=2, min_messages_per_hour=30
    )
    assert not documents.is_empty()
    all_terms = {term for terms in top_terms.values() for term in terms}
    assert "regarder" in all_terms
    assert "regarde" not in all_terms
    assert "regardait" not in all_terms
    assert "regardent" not in all_terms


def test_cluster_channel_hours_groups_similar_topics() -> None:
    # Two distinct vocabularies, each repeated across several channel-hours,
    # each hour with enough messages to clear the sparsity floor.
    rows = []
    for hour in range(4):
        rows += [("chan_a", hour, "merci super stream") for _ in range(30)]
    for hour in range(4, 8):
        rows += [("chan_b", hour, "cagnotte don zevent") for _ in range(30)]
    documents, _top_terms = cluster_channel_hours(
        _messages(rows), n_clusters=2, min_messages_per_hour=30
    )

    assert not documents.is_empty()
    assert set(documents["cluster"].unique().to_list()) == {0, 1}
    # Every channel_a hour lands in the same cluster, distinct from channel_b's.
    chan_a_clusters = documents.filter(pl.col("channel") == "chan_a")["cluster"].unique().to_list()
    chan_b_clusters = documents.filter(pl.col("channel") == "chan_b")["cluster"].unique().to_list()
    assert len(chan_a_clusters) == 1
    assert len(chan_b_clusters) == 1
    assert chan_a_clusters != chan_b_clusters


def test_cluster_chatters_fills_null_gap_coefficient() -> None:
    chatters = pl.DataFrame(
        {
            "chatter_id": ["1", "2", "3", "4"],
            "distinct_channel_count": [1, 2, 5, 1],
            "total_message_count": [1, 20, 200, 2],
            "lifespan_hours": [0.0, 10.0, 40.0, 1.0],
            "gap_coefficient_of_variation": [None, 0.5, 1.2, None],
            "avg_messages_per_channel": [1.0, 10.0, 40.0, 2.0],
            "top_channel_share": [1.0, 0.8, 0.5, 1.0],
        }
    )
    result = cluster_chatters(chatters, n_clusters=2)
    assert "cluster" in result.columns
    assert len(result) == 4
    assert result["cluster"].null_count() == 0


def _streamers(n_normal: int, *, rng: np.random.Generator) -> pl.DataFrame:
    """A batch of "typical" streamers, for outlier tests to add one extreme row to."""
    return pl.DataFrame(
        {
            "streamer": [f"streamer_{i}" for i in range(n_normal)],
            "amount_eur": rng.uniform(1_000, 5_000, size=n_normal),
            "hours_live": rng.uniform(15, 25, size=n_normal),
            "avg_viewers": rng.uniform(50, 500, size=n_normal),
            "peak_viewers": rng.uniform(100, 1_000, size=n_normal),
            "unique_chatters": rng.uniform(100, 1_000, size=n_normal),
            "total_messages": rng.uniform(1_000, 10_000, size=n_normal),
            "uptime_pct": rng.uniform(20, 40, size=n_normal),
        }
    )


def test_cluster_streamers_assigns_every_row_a_cluster() -> None:
    streamers = _streamers(30, rng=np.random.default_rng(0))
    result = cluster_streamers(streamers, n_clusters=3)
    assert "cluster" in result.columns
    assert result["cluster"].null_count() == 0
    assert set(result["cluster"].unique().to_list()).issubset({0, 1, 2})


def test_detect_streamer_outliers_flags_an_extreme_row() -> None:
    streamers = _streamers(30, rng=np.random.default_rng(1))
    extreme = pl.DataFrame(
        {
            "streamer": ["mega_streamer"],
            "amount_eur": [2_000_000.0],
            "hours_live": [40.0],
            "avg_viewers": [80_000.0],
            "peak_viewers": [100_000.0],
            "unique_chatters": [50_000.0],
            "total_messages": [500_000.0],
            "uptime_pct": [35.0],
        }
    )
    combined = pl.concat([streamers, extreme])
    outliers = detect_streamer_outliers(combined, contamination=0.05)
    assert not outliers.is_empty()
    assert "mega_streamer" in outliers["streamer"].to_list()
    # Sorted most anomalous first.
    assert (outliers["anomaly_score"].diff().drop_nulls() >= 0).all()
    assert set(STREAMER_CLUSTER_FEATURES).issubset(outliers.columns)


def test_detect_chatter_outliers_fills_null_gap_coefficient() -> None:
    rng = np.random.default_rng(2)
    n = 30
    chatters = pl.DataFrame(
        {
            "chatter": [f"chatter_{i}" for i in range(n)],
            "distinct_channel_count": rng.integers(1, 3, size=n),
            "total_message_count": rng.integers(1, 20, size=n),
            "lifespan_hours": rng.uniform(0, 10, size=n),
            "gap_coefficient_of_variation": [None] * n,
            "avg_messages_per_channel": rng.uniform(1, 10, size=n),
            "top_channel_share": rng.uniform(0.5, 1.0, size=n),
        }
    )
    outliers = detect_chatter_outliers(chatters, contamination=0.1)
    assert "anomaly_score" in outliers.columns
    assert not outliers.is_empty()


def test_detect_chat_mood_outliers_handles_negative_sentiment() -> None:
    rng = np.random.default_rng(3)
    n = 30
    mood = pl.DataFrame(
        {
            "timestamp": [datetime(2026, 9, 4, 20, 0, 0) + timedelta(hours=h) for h in range(n)],
            "avg_hype_score": rng.uniform(1, 5, size=n),
            "avg_sentiment_score": rng.uniform(-3, 3, size=n),
        }
    )
    outliers = detect_chat_mood_outliers(mood, contamination=0.1)
    assert "anomaly_score" in outliers.columns
    assert not outliers.is_empty()


def test_pca_projection_returns_two_columns_per_row() -> None:
    streamers = _streamers(20, rng=np.random.default_rng(4))
    coords = pca_projection(streamers, STREAMER_CLUSTER_FEATURES)
    assert coords.shape == (20, 2)


def _forecast_features(n: int, *, rng: np.random.Generator) -> pl.DataFrame:
    """Mid-event snapshots that scale toward a known final total, plus noise."""
    final = rng.uniform(5_000, 500_000, size=n)
    progress = rng.uniform(0.2, 0.8, size=n)
    noise = rng.normal(1.0, 0.05, size=n)
    return pl.DataFrame(
        {
            "channel": [f"chan_{i}" for i in range(n)],
            "streamer": [f"Streamer {i}" for i in range(n)],
            "amount_eur_mid": final * progress * noise,
            "avg_viewers_mid": final * progress * rng.normal(1.0, 0.05, size=n) / 10,
            "peak_viewers_mid": (final * progress * rng.normal(1.0, 0.05, size=n) / 5).astype(int),
            "total_messages_mid": final * progress * rng.normal(1.0, 0.05, size=n) / 2,
            "amount_eur": final,
        }
    )


def test_fit_donation_forecast_predicts_final_total_reasonably_well() -> None:
    features = _forecast_features(60, rng=np.random.default_rng(5))
    result = fit_donation_forecast(
        features,
        ["amount_eur_mid", "avg_viewers_mid", "peak_viewers_mid", "total_messages_mid"],
        "amount_eur",
    )
    assert result["r2"] > 0.5
    assert result["mae"] >= 0
    assert len(result["channel"]) == len(result["actual"]) == len(result["predicted"])
    assert set(result["feature_importances"]) == {
        "amount_eur_mid",
        "avg_viewers_mid",
        "peak_viewers_mid",
        "total_messages_mid",
    }
    assert abs(sum(result["feature_importances"].values()) - 1.0) < 1e-6


def test_looks_like_emote_code_flags_interior_case_transitions() -> None:
    assert _looks_like_emote_code("MegaphoneZ")
    assert _looks_like_emote_code("adfaceBZZZ")
    assert _looks_like_emote_code("VoteYea")
    assert not _looks_like_emote_code("Domingo")
    assert not _looks_like_emote_code("ZEVENT")
    assert not _looks_like_emote_code("bonjour")


def test_looks_like_ner_noise_flags_emote_spam_and_shouting() -> None:
    assert _looks_like_ner_noise("MegaphoneZ")
    assert _looks_like_ner_noise("MDRRR")
    assert _looks_like_ner_noise("maryJam axyartDancing")
    assert _looks_like_ner_noise("@someone")
    assert not _looks_like_ner_noise("Domingo")
    assert not _looks_like_ner_noise("Elden Ring")
    assert not _looks_like_ner_noise("GTA 5")


def _text_messages(texts: list[str]) -> pl.DataFrame:
    return pl.DataFrame({"message_text": texts})


def test_pos_tag_distribution_counts_real_tags() -> None:
    dist = pos_tag_distribution(_text_messages(["le stream est genial", "merci pour le don"]))
    assert not dist.is_empty()
    assert "pos" in dist.columns
    assert (dist["count"].diff().drop_nulls() <= 0).all()


def test_named_entities_finds_a_real_person_and_filters_emote_spam() -> None:
    messages = _text_messages(
        [
            "quel beau run de Domingo aujourd'hui",
            "Domingo est le meilleur",
            "MegaphoneZ MegaphoneZ MegaphoneZ",
        ]
        * 5
    )
    entities = named_entities(messages, top_n=10)
    assert not entities.is_empty()
    assert "Domingo" in entities["entity"].to_list()
    assert "MegaphoneZ" not in " ".join(entities["entity"].to_list())


def test_dependency_parse_returns_one_row_per_token() -> None:
    parsed = dependency_parse("le stream est genial")
    assert list(parsed.columns) == ["token", "lemma", "pos", "dependency", "head"]
    assert len(parsed) == 4  # "le", "stream", "est", "genial"


def test_word_embedding_projection_returns_2d_coords_for_frequent_words() -> None:
    messages = _text_messages(["le stream est genial et le jeu est super"] * 20)
    projected = word_embedding_projection(messages, top_k=10)
    if not projected.is_empty():
        assert set(projected.columns) == {"word", "x", "y", "count"}
        assert (projected["count"] > 0).all()
