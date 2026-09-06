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
- **spaCy's French pipeline** (`fr_core_news_md`) for linguistic structure —
  lemmatization, part-of-speech tagging, dependency parsing, named-entity
  recognition, and static word vectors — all from one model, real and
  verified against ZEvent chat, caveats included. Lemmatization measurably
  improves topic clustering: pooling `jouait`/`joue`/`jouer` into one lemma
  before TF-IDF means a topic isn't split across a word's inflections. NER
  is the one technique here that's honestly weak on this text: a generic
  French model trained on formal text reads Twitch emote codes and chat
  slang as entities (`"LUL"` as a place, `"MegaphoneZ"` — a hype-train emote
  — as a person, repeated dozens of times) — verified, not assumed, and
  filtered for the most obvious cases (see `named_entities`), not silently
  hidden.

Every function below expensive enough to notice (spaCy over thousands of
messages, KMeans/IsolationForest/RandomForest fits) is wrapped in
`st.cache_data`. This isn't optional polish: Streamlit reruns a page's
*entire* script top-to-bottom on any widget interaction anywhere on the
page, not just the widget's own section — without caching, moving the
outlier-contamination slider would silently also re-run topic clustering,
POS tagging, NER, and word-embedding projection from scratch every time,
each taking several seconds, which reads to a user as the whole page
having frozen. `st.cache_data` keys on the function's actual arguments
(including DataFrame content), so it only re-executes when the input
genuinely changed, not on every unrelated rerun.
"""

from __future__ import annotations

import re
from itertools import pairwise
from typing import TYPE_CHECKING

import numpy as np
import polars as pl
import spacy
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

_SENTIMENT_MODEL = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
_TOXICITY_MODEL = "textdetox/xlmr-large-toxicity-classifier"
_SPACY_MODEL = "fr_core_news_md"

# Content-bearing POS tags kept for topic clustering, the word-embedding map,
# and POS-distribution reporting — determiners/pronouns/adpositions carry
# almost no topical signal on their own and would otherwise dominate purely
# by frequency (French "de"/"le"/"la" appear in nearly every message).
_CONTENT_POS = frozenset({"NOUN", "PROPN", "VERB", "ADJ"})

# A generic French model — for NER below, and for lemmatized topic-cluster
# tokens above — wasn't trained on Twitch emote codes or chat slang, and
# confidently treats both as real words/entities — verified against real
# ZEvent chat (see module docstring; "MegaphoneZ", a hype-train emote,
# dominated topic clusters before this filter existed). Emote codes almost
# never follow real French/English capitalization (one capital, only ever
# at the start): `"MegaphoneZ"`, `"VoteYea"`, `"adfaceBZZZ"` all have an
# interior lowercase-then-uppercase transition instead, which is what
# `_EMOTE_CODE_PATTERN` catches, checked against the token's *original*
# casing before any lowercasing — a cheap, real-data-verified filter
# without a hand-maintained emote blocklist. Common chat interjections
# that read as capitalized enough to pass as a name/place ("GG", "LUL",
# "mdr") are caught separately, by an explicit small list.
_EMOTE_CODE_PATTERN = re.compile(r"[a-z][A-Z]")
_REPEATED_CHAR_PATTERN = re.compile(r"(.)\1{2,}")
_NER_NOISE_WORDS = frozenset({"gg", "mdr", "lul", "kekw", "xd", "lol", "ptdr", "ca", "ça", "pog"})


def _looks_like_emote_code(text: str) -> bool:
    """Return whether `text` (original casing) reads as a Twitch emote code, not a real word."""
    return " " not in text and bool(_EMOTE_CODE_PATTERN.search(text))


def _is_noise_token(tok: spacy.tokens.Token) -> bool:
    """Return whether a parsed token is noise for topic/vocabulary analysis, not real content.

    Beyond `_looks_like_emote_code`: a URL (`tok.like_url` — Twitch donation
    links appear constantly and would otherwise show up as a "topic" on
    their own), a token containing a digit (real French/English content
    words essentially never do; channel-prefixed handles like
    `"anyme023gg"` do), or 3+ of the same character in a row
    (`"wwwww"`, `"mdrrrrr"` — laugh/spam text, not a word) — all verified
    against real chat before adding, same as `_looks_like_emote_code`.
    """
    text = tok.text
    return (
        tok.like_url
        or not text.isprintable()
        or any(char.isdigit() for char in text)
        or bool(_REPEATED_CHAR_PATTERN.search(text))
        or _looks_like_emote_code(text)
    )


def _looks_like_ner_noise(text: str) -> bool:
    """Return whether a spaCy-recognized entity is likely emote-code/slang noise, not real.

    Repeated-char spam ("MDRRR", one letter 3+ times running) is checked
    here too — chat shouting in ALL CAPS reads as a plausible-looking
    entity to a model trained on formally-capitalized proper nouns just as
    readily as an emote code does. A digit only disqualifies a single-word
    span outright (`"voidth9Rave1"` isn't a word) — a real multi-word
    entity can legitimately contain one ("GTA 5"), so a multi-word span is
    instead rejected only if one of its *individual* words looks like an
    emote code on its own — verified against real chat: spaCy often merges
    several adjacent emote-code tokens with no punctuation between them
    into a single entity span (`"maryJam axyartDancing"`), which a
    no-space-only check would otherwise miss entirely.
    """
    if "@" in text or len(text) < 2 or _REPEATED_CHAR_PATTERN.search(text):
        return True
    if text.lower() in _NER_NOISE_WORDS:
        return True
    words = text.split(" ")
    if len(words) == 1:
        return _looks_like_emote_code(text) or any(char.isdigit() for char in text)
    return any(_looks_like_emote_code(word) for word in words)


@st.cache_resource(show_spinner="Loading French NLP model (first load only)...")
def _nlp_pipeline() -> spacy.language.Language:
    return spacy.load(_SPACY_MODEL)


def _lemmatized_ngram_tokens(doc: spacy.tokens.Doc) -> list[str]:
    """Turn a parsed message into lemmatized unigram+bigram tokens for TF-IDF.

    Keeps only content words (see `_CONTENT_POS`) at least 3 characters
    after lemmatization, excluding `STOPWORDS` (the same curated list
    `chat_nlp.py`'s dependency-free keyword extraction uses, for the
    domain-generic filler it already excludes — "http", "twitch", etc.).
    Bigrams are added as `"word_word"` — a topic like "hype train" as two
    unigrams loses the phrase itself; joined into one bigram token, TF-IDF
    can score the phrase on its own.
    """
    unigrams = [
        tok.lemma_.lower()
        for tok in doc
        if tok.pos_ in _CONTENT_POS
        and len(tok.lemma_) >= 3
        and tok.lemma_.lower() not in STOPWORDS
        and not _is_noise_token(tok)
    ]
    bigrams = [f"{a}_{b}" for a, b in pairwise(unigrams)]
    return unigrams + bigrams


def _lemmatize_documents(texts: Sequence[str]) -> list[list[str]]:
    """Lemmatize+POS-filter a batch of documents in one spaCy pipe (much faster than per-call).

    `disable=["parser", "ner"]`: only lemma and POS tag are used (see
    `_lemmatized_ngram_tokens`) — measured directly against real chat, the
    dependency parser alone accounted for ~40% of this function's runtime
    on pooled channel-hour documents (some exceeding 100k characters after
    joining an hour's messages together), for output this function never
    reads.
    """
    nlp = _nlp_pipeline()
    docs = nlp.pipe(texts, batch_size=32, disable=["parser", "ner"])
    return [_lemmatized_ngram_tokens(doc) for doc in docs]


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


@st.cache_data(ttl=300, show_spinner=False)
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


@st.cache_data(ttl=300, show_spinner=False)
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
        weight — lemmatized, so "jouer"/"joue"/"jouait" contribute to one
        term instead of splitting a topic's signal across inflections; a
        `word_word` term is a bigram, not two separate words), for labeling
        the cluster in the UI.
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

    tokenized_docs = _lemmatize_documents(pooled["text"].to_list())
    # A pre-tokenized `analyzer` (identity function) replaces TfidfVectorizer's
    # own tokenizing/stop-word/n-gram logic entirely — lemmatization and
    # n-grams already happened in `_lemmatize_documents`, once per document,
    # via spaCy's batched `nlp.pipe` rather than sklearn re-tokenizing text
    # sklearn was never going to lemmatize correctly on its own.
    vectorizer = TfidfVectorizer(max_features=3000, min_df=3, analyzer=lambda tokens: tokens)
    vectors = vectorizer.fit_transform(tokenized_docs)
    kmeans = KMeans(n_clusters=n_clusters, n_init=5, random_state=42)
    labels = kmeans.fit_predict(vectors)

    terms = vectorizer.get_feature_names_out()
    term_order = kmeans.cluster_centers_.argsort()[:, ::-1]
    # "_" -> " " only for display: a bigram like "hype_train" was joined with
    # an underscore so TF-IDF treats it as one atomic feature distinct from
    # the unigrams "hype" and "train" (see `_lemmatized_ngram_tokens`).
    top_terms = {
        i: [terms[j].replace("_", " ") for j in term_order[i, :8]] for i in range(n_clusters)
    }

    documents = pooled.drop("text").with_columns(pl.Series("cluster", labels))
    return documents, top_terms


@st.cache_data(ttl=300, show_spinner=False)
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


@st.cache_data(ttl=300, show_spinner=False)
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


@st.cache_data(ttl=300, show_spinner=False)
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


@st.cache_data(ttl=300, show_spinner=False)
def detect_chatter_outliers(chatters: pl.DataFrame, *, contamination: float) -> pl.DataFrame:
    """Flag chatters whose activity shape is statistically unusual (Isolation Forest).

    Same reasoning and return shape as `detect_streamer_outliers`, over
    `cluster_chatters`'s feature set.
    """
    filled = chatters.with_columns(pl.col("gap_coefficient_of_variation").fill_null(0.0))
    scaled = _log_scaled(filled, CHATTER_CLUSTER_FEATURES)
    return _flag_outliers(filled, scaled, contamination=contamination)


@st.cache_data(ttl=300, show_spinner=False)
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


@st.cache_data(ttl=300, show_spinner=False)
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


@st.cache_data(ttl=300, show_spinner=False)
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


@st.cache_data(ttl=300, show_spinner=False)
def pos_tag_distribution(messages: pl.DataFrame, *, sample_size: int = 3000) -> pl.DataFrame:
    """Count how often each part-of-speech tag appears across a sample of messages.

    Args:
        messages: Must have a `message_text` column.
        sample_size: Cap on messages parsed — spaCy is fast (~1ms/message
            batched) but there's no reason to parse a 200k-message sample
            just to get a stable POS distribution; a few thousand already
            gives stable proportions.

    Returns:
        DataFrame with columns `pos` (spaCy's universal POS tag, e.g.
        `NOUN`, `VERB`, `PUNCT`) and `count`, sorted most common first.
    """
    texts = messages["message_text"].to_list()[:sample_size]
    nlp = _nlp_pipeline()
    counts: dict[str, int] = {}
    # POS tags come from tok2vec/morphologizer, not the parser or NER —
    # disabling both here is a pure speedup with no effect on the result.
    for doc in nlp.pipe(texts, batch_size=128, disable=["parser", "ner"]):
        for tok in doc:
            if tok.is_space:
                continue
            counts[tok.pos_] = counts.get(tok.pos_, 0) + 1
    if not counts:
        return pl.DataFrame({"pos": [], "count": []})
    return pl.DataFrame({"pos": list(counts.keys()), "count": list(counts.values())}).sort(
        "count", descending=True
    )


@st.cache_data(ttl=300, show_spinner=False)
def named_entities(
    messages: pl.DataFrame, *, sample_size: int = 4000, top_n: int = 20
) -> pl.DataFrame:
    """Extract the most frequently mentioned named entities across a sample of messages.

    A generic French NER model wasn't trained on Twitch emote codes or chat
    slang and will still misclassify some of it as a real entity even after
    `_looks_like_ner_noise`'s filter (see the module docstring for verified
    real examples) — real signal (a streamer's name, a game title) is
    usually still findable because it recurs far more often than any one
    misclassified emote code, which is why this ranks by frequency rather
    than showing every raw hit.

    Args:
        messages: Must have a `message_text` column.
        sample_size: Cap on messages parsed (see `pos_tag_distribution`).
        top_n: How many (entity, label) pairs to return.

    Returns:
        DataFrame with columns `entity`, `label` (spaCy's entity type —
        `PER`, `LOC`, `ORG`, `MISC`), `count`, sorted most frequent first.
    """
    texts = messages["message_text"].to_list()[:sample_size]
    nlp = _nlp_pipeline()
    counts: dict[tuple[str, str], int] = {}
    # The dependency parser's output isn't read here — only NER — so it's
    # disabled for speed; NER itself has to stay enabled, obviously.
    for doc in nlp.pipe(texts, batch_size=128, disable=["parser"]):
        for ent in doc.ents:
            if _looks_like_ner_noise(ent.text):
                continue
            key = (ent.text, ent.label_)
            counts[key] = counts.get(key, 0) + 1
    if not counts:
        return pl.DataFrame({"entity": [], "label": [], "count": []})
    ranked = sorted(counts.items(), key=lambda kv: -kv[1])[:top_n]
    return pl.DataFrame(
        {
            "entity": [key[0] for key, _ in ranked],
            "label": [key[1] for key, _ in ranked],
            "count": [count for _, count in ranked],
        }
    )


@st.cache_data(ttl=300, show_spinner=False)
def dependency_parse(text: str) -> pl.DataFrame:
    """Parse one message's grammatical structure, token by token.

    Args:
        text: A single message to parse.

    Returns:
        DataFrame with columns `token`, `lemma`, `pos`, `dependency` (the
        token's grammatical relation to its head, e.g. `nsubj`, `amod`),
        and `head` (the token it depends on — its own text for the ROOT).
    """
    nlp = _nlp_pipeline()
    doc = nlp(text)
    return pl.DataFrame(
        {
            "token": [tok.text for tok in doc],
            "lemma": [tok.lemma_ for tok in doc],
            "pos": [tok.pos_ for tok in doc],
            "dependency": [tok.dep_ for tok in doc],
            "head": [tok.head.text for tok in doc],
        }
    )


@st.cache_data(ttl=300, show_spinner=False)
def word_embedding_projection(
    messages: pl.DataFrame, *, sample_size: int = 6000, top_k: int = 150
) -> pl.DataFrame:
    """Project the most frequent content words' static word vectors down to 2D.

    spaCy's `fr_core_news_md` ships pretrained static (non-contextual) word
    vectors — the classic "word embeddings" sense of the term, one fixed
    vector per word regardless of context, unlike `contextual_message_embeddings`
    below. Words that co-occur in similar contexts across the training corpus
    end up nearby after the projection, independent of anything specific to
    ZEvent chat.

    Args:
        messages: Must have a `message_text` column.
        sample_size: Cap on messages parsed (see `pos_tag_distribution`).
        top_k: How many of the most frequent content words to project —
            capped since a semantic map of thousands of words stops being
            readable as a scatter plot.

    Returns:
        DataFrame with columns `word`, `x`, `y` (2D PCA projection of the
        300-dim static vector), `count` (frequency in the sample) — empty
        if fewer than 3 distinct words had vectors.
    """
    texts = messages["message_text"].to_list()[:sample_size]
    nlp = _nlp_pipeline()
    freq: dict[str, int] = {}
    vectors: dict[str, np.ndarray] = {}
    # Static vectors + POS come straight from tok2vec/morphologizer — the
    # parser and NER are never consulted below, so disabled for speed.
    for doc in nlp.pipe(texts, batch_size=128, disable=["parser", "ner"]):
        for tok in doc:
            if tok.pos_ not in _CONTENT_POS or not tok.has_vector or tok.is_stop:
                continue
            if _is_noise_token(tok):
                continue
            lemma = tok.lemma_.lower()
            if len(lemma) < 3 or lemma in STOPWORDS:
                continue
            freq[lemma] = freq.get(lemma, 0) + 1
            vectors.setdefault(lemma, tok.vector)
    top_words = sorted(freq, key=lambda word: -freq[word])[:top_k]
    if len(top_words) < 3:
        return pl.DataFrame({"word": [], "x": [], "y": [], "count": []})
    matrix = np.stack([vectors[word] for word in top_words])
    coords = PCA(n_components=2, random_state=42).fit_transform(matrix)
    return pl.DataFrame(
        {
            "word": top_words,
            "x": coords[:, 0],
            "y": coords[:, 1],
            "count": [freq[word] for word in top_words],
        }
    )


@st.cache_resource(show_spinner="Loading embedding model (first load only)...")
def _embedding_model() -> tuple:
    from transformers import AutoModel, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(_TOXICITY_MODEL)
    model = AutoModel.from_pretrained(_TOXICITY_MODEL)
    model.eval()
    return tokenizer, model


@st.cache_data(ttl=300, show_spinner=False)
def contextual_message_embeddings(
    messages: pl.DataFrame, *, sample_size: int = 150
) -> tuple[list[str], np.ndarray]:
    """Compute one contextual embedding per message, mean-pooled from a transformer's hidden states.

    Unlike `word_embedding_projection`'s static, context-free word vectors,
    the same word here gets a different vector depending on the sentence
    around it — "avocat" the fruit and "avocat" the lawyer would land in
    different places. Reuses the toxicity classifier's own encoder
    (`_TOXICITY_MODEL`, an XLM-R model, rather than downloading yet another
    model) purely as a general-purpose multilingual text encoder — its
    classification head isn't used here. Mean-pooling the last hidden
    state over real (non-padding) tokens is the standard way to turn a
    transformer's per-token output into one fixed-size vector per message.

    Args:
        messages: Must have a `message_text` column.
        sample_size: Small on purpose — a large XLM-R model doing full
            forward passes on CPU is far slower than the lexicon/sklearn
            paths elsewhere in this module (same reasoning as
            `classify_messages_ml`'s docstring).

    Returns:
        A `(texts, embeddings)` pair: `texts` are the sampled messages in
        order, `embeddings` is an `(n, hidden_size)` array, one row per text.
    """
    import torch

    texts = messages["message_text"].to_list()[:sample_size]
    tokenizer, model = _embedding_model()
    encoded = tokenizer(texts, padding=True, truncation=True, max_length=64, return_tensors="pt")
    with torch.no_grad():
        output = model(**encoded)
    mask = encoded["attention_mask"].unsqueeze(-1).float()
    summed = (output.last_hidden_state * mask).sum(dim=1)
    token_counts = mask.sum(dim=1).clamp(min=1e-9)
    embeddings = (summed / token_counts).numpy()
    return texts, embeddings


def project_2d(matrix: np.ndarray) -> np.ndarray:
    """PCA-project an already-dense, reasonably-scaled matrix (e.g. embeddings) down to 2D.

    Unlike `pca_projection`, no log1p/standardize step — embeddings from a
    trained model are already dense floats on a comparable scale, not
    heavily-skewed raw counts.
    """
    return PCA(n_components=2, random_state=42).fit_transform(matrix)
