"""Real, trained-model ML for the Chat ML Lab page — heavier than Chat Intelligence's lexicons.

Everything here depends on `scikit-learn` and/or `transformers`/`torch`,
unlike every other `app/data/chat_*` module, which is deliberately
dependency-light. Keeping the heavy imports confined to this one module
means every other page (and every test that doesn't touch Chat ML Lab)
never pays for loading `torch` at all.

Two real machine-learning techniques, chosen and verified against real
ZEvent chat, not assumed to work from documentation:

- **Clustering** (`sklearn.cluster.KMeans`) for both message/topic discovery
  and chatter behavioral segmentation. Clustering *individual* messages was
  tried first and rejected: real Twitch chat is so short and sparse that raw
  per-message TF-IDF vectors barely overlap, and KMeans collapsed 92% of a
  channel's messages into one meaningless catch-all cluster. Pooling all of
  one channel-hour's messages into a single "document" first (the same
  trick `app/data/chat_nlp.py` uses for trending keywords) gives each vector
  enough signal to cluster properly — confirmed against real data: one
  cluster's top terms were literally "haut/bas/gauche/droite/commande/votée"
  (a Twitch-plays-style channel voting on directional game inputs), a
  genuine, distinct topic a human would recognize immediately.
- **Pretrained transformer classifiers** (via `transformers.pipeline`) for
  sentiment and toxicity, as a real-model comparison against Chat
  Intelligence's word-list heuristics. Model choice was verified, not
  assumed: a smaller multilingual toxicity model
  (`citizenlab/distilbert-base-multilingual-cased-toxicity`) confidently
  mislabeled "gg les gars, quel beau run" (a friendly, wholesome message) as
  99% toxic and missed a genuine insult entirely — swapped for
  `textdetox/xlmr-large-toxicity-classifier`, which got every real test
  message right, including correctly reading "TA GUEULE ADRIEN" as mostly
  playful banter between friends rather than hostile — a distinction the
  word-list heuristic, which flags "ta gueule" unconditionally, cannot make.
  Sentiment uses `cardiffnlp/twitter-xlm-roberta-base-sentiment`, trained on
  multilingual social-media text (a good fit for Twitch chat's register).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import polars as pl
import streamlit as st
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from app.data.chat_nlp import STOPWORDS

if TYPE_CHECKING:
    from collections.abc import Sequence

    from transformers import Pipeline

_TOKEN_PATTERN = r"[a-zà-öø-ÿ']{3,}"

_SENTIMENT_MODEL = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
_TOXICITY_MODEL = "textdetox/xlmr-large-toxicity-classifier"

CHATTER_CLUSTER_FEATURES = (
    "distinct_channel_count",
    "total_message_count",
    "lifespan_hours",
    "gap_coefficient_of_variation",
    "avg_messages_per_channel",
    "top_channel_share",
)

STREAMER_CLUSTER_FEATURES = (
    "amount_eur",
    "hours_live",
    "avg_viewers",
    "peak_viewers",
    "unique_chatters",
    "total_messages",
    "uptime_pct",
)


def _log_scaled(df: pl.DataFrame, features: Sequence[str]) -> np.ndarray:
    """Log1p + standard-scale a set of non-negative numeric features.

    Shared by every clustering/outlier function below whose features are
    activity *counts* — confirmed against real data that these are heavily
    right-skewed (`avg_messages_per_channel` ranges from 1 to 18,824), and
    without the log transform a handful of extreme accounts would dominate
    the fit entirely rather than the shape of the bulk of the population.
    Not used for signed/bounded scores (e.g. sentiment, which can be
    negative) — see `detect_chat_mood_outliers`.
    """
    values = df.select(list(features)).to_numpy()
    return StandardScaler().fit_transform(np.log1p(np.clip(values, 0, None)))


def _flag_outliers(df: pl.DataFrame, x_scaled: np.ndarray, *, contamination: float) -> pl.DataFrame:
    """Fit an Isolation Forest over `x_scaled` and return `df`'s flagged rows.

    Args:
        df: The rows `x_scaled` was computed from, in the same order.
        x_scaled: Already-scaled numeric features (see `_log_scaled`, or a
            plain `StandardScaler` for signed/bounded scores).
        contamination: Expected fraction of rows to flag — Isolation
            Forest's one tuning knob; the UI exposes it as a slider.

    Returns:
        Only the flagged rows, with an added `anomaly_score` column
        (sklearn's `decision_function` output — more negative is more
        anomalous), sorted most anomalous first.
    """
    forest = IsolationForest(contamination=contamination, random_state=42)
    is_outlier = forest.fit_predict(x_scaled) == -1
    scores = forest.decision_function(x_scaled)
    return (
        df.with_columns(pl.Series("_is_outlier", is_outlier), pl.Series("anomaly_score", scores))
        .filter(pl.col("_is_outlier"))
        .drop("_is_outlier")
        .sort("anomaly_score")
    )


def pca_projection(df: pl.DataFrame, features: Sequence[str]) -> np.ndarray:
    """Project log1p+standard-scaled features onto their first two principal components.

    Lets a cluster fit in the (5-7-dimensional) feature space `cluster_streamers`/
    `cluster_chatters` actually used be *seen*, not just tabulated — a 2D
    scatter, colored by cluster, is a genuinely different chart shape from
    every other visualization on this page. Uses the same `_log_scaled`
    transform clustering itself fits on, so the 2D layout reflects the same
    geometry the cluster assignments came from, rather than a separately
    chosen projection that might disagree with them.

    Args:
        df: Rows to project (any DataFrame with `features` present, already
            filled — see `cluster_chatters`'s `gap_coefficient_of_variation`
            fill for the one feature set that needs it).
        features: Numeric feature columns to project.

    Returns:
        An `(n_rows, 2)` array of principal-component coordinates.
    """
    return PCA(n_components=2, random_state=42).fit_transform(_log_scaled(df, features))


def cluster_channel_hours(
    messages: pl.DataFrame, *, n_clusters: int, min_messages_per_hour: int = 30
) -> tuple[pl.DataFrame, dict[int, list[str]]]:
    """Discover topic clusters by pooling each (channel, hour)'s messages into one document.

    Args:
        messages: Columns `channel`, `message_sent_at`, `message_text` (any
            mix of channels — each channel-hour becomes its own document, so
            mixing is fine, unlike `chat_nlp.top_keywords_per_hour`).
        n_clusters: How many topic clusters to fit.
        min_messages_per_hour: Channel-hours with fewer sampled messages than
            this are dropped — too few words to form a meaningful document
            (same "don't trust a thin sample" reasoning as
            `PostgresDataSource.chat_hype_components_timeseries`'s
            `HAVING COUNT(*) >= 20`).

    Returns:
        A `(documents, top_terms)` pair: `documents` has columns `channel`,
        `hour_bucket`, `message_count`, `cluster`; `top_terms` maps each
        cluster id to its top 8 distinguishing words (by TF-IDF centroid
        weight), for labeling the cluster in the UI.
    """
    pooled = (
        messages.with_columns(pl.col("message_sent_at").dt.truncate("1h").alias("hour_bucket"))
        .group_by("channel", "hour_bucket")
        .agg(
            pl.col("message_text").str.join(" ").alias("text"),
            pl.len().alias("message_count"),
        )
        .filter(pl.col("message_count") >= min_messages_per_hour)
    )
    if len(pooled) < n_clusters:
        return pooled.drop("text").with_columns(pl.lit(None).alias("cluster")), {}

    vectorizer = TfidfVectorizer(
        max_features=3000, min_df=3, stop_words=list(STOPWORDS), token_pattern=_TOKEN_PATTERN
    )
    vectors = vectorizer.fit_transform(pooled["text"].to_list())
    kmeans = KMeans(n_clusters=n_clusters, n_init=5, random_state=42)
    labels = kmeans.fit_predict(vectors)

    terms = vectorizer.get_feature_names_out()
    term_order = kmeans.cluster_centers_.argsort()[:, ::-1]
    top_terms = {i: [terms[j] for j in term_order[i, :8]] for i in range(n_clusters)}

    documents = pooled.drop("text").with_columns(pl.Series("cluster", labels))
    return documents, top_terms


def cluster_chatters(chatters: pl.DataFrame, *, n_clusters: int) -> pl.DataFrame:
    """Discover behavioral chatter segments from their activity-shape features.

    Log-transforms every feature before scaling: real chatter activity is
    heavily right-skewed (confirmed against real data — `avg_messages_per_channel`
    ranges from 1 to 18,824), and without a log transform a handful of
    extreme accounts would dominate cluster formation entirely rather than
    the shape of the bulk of the population. `chatters` should already be
    filtered to likely-human accounts (`~bot_filter_expr()`) — bot traffic
    would otherwise form its own extreme, uninformative cluster.

    Args:
        chatters: A `chatter_breakdown()`-shaped DataFrame — needs
            `distinct_channel_count`, `total_message_count`, `lifespan_hours`,
            `gap_coefficient_of_variation`, `avg_messages_per_channel`,
            `top_channel_share`.
        n_clusters: How many behavioral segments to fit.

    Returns:
        `chatters` with a new `cluster` column (int, 0-based).
    """
    filled = chatters.with_columns(pl.col("gap_coefficient_of_variation").fill_null(0.0))
    scaled = _log_scaled(filled, CHATTER_CLUSTER_FEATURES)
    labels = KMeans(n_clusters=n_clusters, n_init=10, random_state=42).fit_predict(scaled)
    return filled.with_columns(pl.Series("cluster", labels))


def cluster_streamers(streamers: pl.DataFrame, *, n_clusters: int) -> pl.DataFrame:
    """Discover streamer segments from their performance-shape features.

    Same log-transform reasoning as `cluster_chatters` — real streamer
    donation/audience figures are heavily right-skewed (confirmed against
    real data: `amount_eur` ranges from 0 to over €2M against a €3.3k
    median).

    Args:
        streamers: A `streamer_breakdown()`-shaped DataFrame — needs
            `amount_eur`, `hours_live`, `avg_viewers`, `peak_viewers`,
            `unique_chatters`, `total_messages`, `uptime_pct`.
        n_clusters: How many performance segments to fit.

    Returns:
        `streamers` with a new `cluster` column (int, 0-based).
    """
    scaled = _log_scaled(streamers, STREAMER_CLUSTER_FEATURES)
    labels = KMeans(n_clusters=n_clusters, n_init=10, random_state=42).fit_predict(scaled)
    return streamers.with_columns(pl.Series("cluster", labels))


def detect_streamer_outliers(streamers: pl.DataFrame, *, contamination: float) -> pl.DataFrame:
    """Flag streamers whose performance shape is statistically unusual (Isolation Forest).

    Args:
        streamers: Same shape `cluster_streamers` needs.
        contamination: Expected fraction of streamers to flag (e.g. `0.05`
            for the most unusual ~5%) — the one tuning knob Isolation Forest
            has; the UI exposes it as a slider.

    Returns:
        Only the flagged rows, with an added `anomaly_score` column (more
        negative = more anomalous), sorted most anomalous first. Confirmed
        against real data to surface *both* extremes at once — the event's
        biggest fundraisers (millions of euros, tens of thousands of
        viewers) and near-inactive placeholder entries (zero viewers, zero
        uptime) are both "statistically unlike a typical streamer."
    """
    scaled = _log_scaled(streamers, STREAMER_CLUSTER_FEATURES)
    return _flag_outliers(streamers, scaled, contamination=contamination)


def detect_chatter_outliers(chatters: pl.DataFrame, *, contamination: float) -> pl.DataFrame:
    """Flag chatters whose activity shape is statistically unusual (Isolation Forest).

    Same reasoning and return shape as `detect_streamer_outliers`, over
    `cluster_chatters`'s feature set.
    """
    filled = chatters.with_columns(pl.col("gap_coefficient_of_variation").fill_null(0.0))
    scaled = _log_scaled(filled, CHATTER_CLUSTER_FEATURES)
    return _flag_outliers(filled, scaled, contamination=contamination)


def detect_chat_mood_outliers(mood: pl.DataFrame, *, contamination: float) -> pl.DataFrame:
    """Flag hours whose event-wide chat mood is statistically unusual (Isolation Forest).

    Unlike the streamer/chatter outlier detectors, features here are *not*
    log-transformed: `avg_sentiment_score` can be negative (`log1p` would be
    undefined), and hype/sentiment are already bounded scores rather than
    heavy-tailed counts, so a plain standard-scale is enough.

    Args:
        mood: A `chat_mood_timeseries()`-shaped DataFrame — needs
            `avg_hype_score`, `avg_sentiment_score`.
        contamination: Expected fraction of hours to flag.

    Returns:
        Only the flagged rows, with an added `anomaly_score` column (more
        negative = more anomalous), sorted most anomalous first.
    """
    features = ("avg_hype_score", "avg_sentiment_score")
    scaled = StandardScaler().fit_transform(mood.select(list(features)).to_numpy())
    return _flag_outliers(mood, scaled, contamination=contamination)


@st.cache_resource(show_spinner="Loading sentiment model (first load only, ~1GB download)...")
def _sentiment_pipeline() -> Pipeline:
    from transformers import pipeline

    return pipeline("sentiment-analysis", model=_SENTIMENT_MODEL)


@st.cache_resource(show_spinner="Loading toxicity model (first load only, ~2GB download)...")
def _toxicity_pipeline() -> Pipeline:
    from transformers import pipeline

    return pipeline("text-classification", model=_TOXICITY_MODEL)


def classify_messages_ml(messages: pl.DataFrame) -> pl.DataFrame:
    """Run real pretrained sentiment and toxicity classifiers over a batch of messages.

    Both models are loaded once per app process (`st.cache_resource`) — the
    ~1-2GB download only happens the first time either is used, not on every
    call. Meant for a small batch (dozens to a few hundred messages): CPU
    inference for the toxicity model, confirmed against real data, takes
    ~35ms/message even in a batch, which adds up fast at chat-wide sample
    sizes (250k) the lexicon-based Chat Intelligence page uses.

    Args:
        messages: Must have a `message_text` column.

    Returns:
        `messages` with four new columns: `ml_sentiment_label`,
        `ml_sentiment_score`, `ml_toxicity_label`, `ml_toxicity_score`.
    """
    texts = messages["message_text"].to_list()
    sentiment = _sentiment_pipeline()(texts, truncation=True, max_length=64, batch_size=16)
    toxicity = _toxicity_pipeline()(texts, truncation=True, max_length=64, batch_size=16)
    return messages.with_columns(
        pl.Series("ml_sentiment_label", [r["label"] for r in sentiment]),
        pl.Series("ml_sentiment_score", [r["score"] for r in sentiment]),
        pl.Series("ml_toxicity_label", [r["label"] for r in toxicity]),
        pl.Series("ml_toxicity_score", [r["score"] for r in toxicity]),
    )


def fit_donation_forecast(
    features: pl.DataFrame, feature_cols: Sequence[str], target_col: str
) -> dict:
    """Fit a Random Forest forecasting a streamer's final donation total from a mid-event snapshot.

    Every streamer contributes one row: their own cumulative donations,
    viewer counts and message volume as of some earlier cutoff, and their
    eventual final total as the label — genuinely forecasting an unknown
    future from a known past, not predicting a number from itself (see
    `DataSource.donation_forecast_features`). Features and target are both
    log1p-transformed before fitting (all heavily right-skewed, like every
    other count/currency feature in this module — see `_log_scaled`), then
    predictions are inverse-transformed back to euros before scoring, so
    R²/MAE are reported in the same units the chart shows.

    Args:
        features: One row per streamer, with `channel`, `streamer`,
            `feature_cols` and `target_col`.
        feature_cols: Column names to use as predictors.
        target_col: Column name of the value to predict.

    Returns:
        A dict with `channel`/`streamer`/`actual`/`predicted` (test-set
        only, euros), `r2`, `mae` (euros), and `feature_importances`
        (feature name -> importance, sorted most important first).
    """
    x = np.log1p(features.select(list(feature_cols)).to_numpy())
    y_log = np.log1p(features[target_col].to_numpy())
    channels = features["channel"].to_numpy()
    streamers = features["streamer"].to_numpy()
    x_train, x_test, y_train, y_test, _, ch_test, _, name_test = train_test_split(
        x, y_log, channels, streamers, test_size=0.25, random_state=42
    )
    model = RandomForestRegressor(n_estimators=200, max_depth=6, random_state=42)
    model.fit(x_train, y_train)
    actual = np.expm1(y_test)
    predicted = np.expm1(model.predict(x_test))
    importances = dict(
        sorted(
            zip(feature_cols, model.feature_importances_, strict=True),
            key=lambda kv: -kv[1],
        )
    )
    return {
        "channel": ch_test,
        "streamer": name_test,
        "actual": actual,
        "predicted": predicted,
        "r2": r2_score(actual, predicted),
        "mae": mean_absolute_error(actual, predicted),
        "feature_importances": importances,
    }
