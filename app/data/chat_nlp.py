"""Lightweight TF-IDF keyword extraction over raw chat messages.

Shared by the real and mock `chat_trending_keywords` implementations.
No ML library dependency — Twitch chat is short (median ~20 characters) and
dominated by emote-code spam and copypasta (see the Chat Intelligence page's
docstring), so a hand-rolled bag-of-words TF-IDF over per-hour pooled text
already surfaces genuine spikes (verified against real event data: a
streamer's "joyeux anniversaire" birthday moment stood out clearly) without
the cost or complexity of a trained model.
"""

from __future__ import annotations

import polars as pl

# French (the event's dominant language) + English stopwords, plus a handful
# of domain-generic filler ("http"/"www"/"twitch" link boilerplate) that would
# otherwise dominate every hour's top keywords and drown out anything actually
# distinctive to that hour. Public — `app/data/chat_ml.py`'s message/topic
# clustering reuses this same list, for the same reason.
STOPWORDS = frozenset(
    """
    le la les de des du un une et est sont sur pour dans avec mais que qui quoi
    pas plus tout tous toute toutes ça ce cette ces son sa ses mon ma mes ton ta
    tes notre nos votre vos leur leurs je tu il elle on nous vous ils elles se
    ne au aux en y du au fait bien encore comme donc alors ici là peut être vais
    the is are and you to of in it that this a i not me my your his her its our
    their have has had was were be been being will would can could should https
    http www com twitch fr net org
    """.split()  # noqa: SIM905 -- a quoted list literal of ~100 words is far less readable
)

_TOKEN_PATTERN = r"[a-zà-öø-ÿ']{3,}"


def top_keywords_per_hour(messages: pl.DataFrame, *, top_k: int = 5) -> pl.DataFrame:
    """Extract each hour's most distinctive words from one channel's chat messages.

    Treats each hour's pooled messages as one "document" and the channel's
    whole history as the corpus: a word's score is its count that hour times
    `log(total_hours / hours_it_appears_in)` (classic TF-IDF) — this is what
    lets a word that suddenly spikes in one hour (a shoutout, a running joke,
    a donation-goal reveal) outrank words used at a similar low rate every
    hour, which raw frequency alone can't tell apart.

    Args:
        messages: Columns `message_sent_at` (datetime) and `message_text`
            (str), all from a single channel — mixing channels would pollute
            the per-hour "document" with unrelated chat.
        top_k: How many top-scoring words to keep per hour.

    Returns:
        DataFrame with columns `hour_bucket` (datetime) and `keywords` (the
        top-scoring words for that hour, comma-joined, highest first). Hours
        with no token surviving stopword/length filtering are omitted.
    """
    tokens = (
        messages.select(
            pl.col("message_sent_at").dt.truncate("1h").alias("hour_bucket"),
            pl.col("message_text").str.to_lowercase().str.extract_all(_TOKEN_PATTERN).alias("token"),
        )
        .explode("token", empty_as_null=True)
        .drop_nulls("token")
        .filter(~pl.col("token").is_in(STOPWORDS))
    )
    if tokens.is_empty():
        return pl.DataFrame(schema={"hour_bucket": pl.Datetime("us"), "keywords": pl.Utf8})

    total_hours = tokens["hour_bucket"].n_unique()
    term_freq = tokens.group_by("hour_bucket", "token").len("tf")
    doc_freq = tokens.group_by("token").agg(pl.col("hour_bucket").n_unique().alias("df"))
    scored = term_freq.join(doc_freq, on="token").with_columns(
        (pl.col("tf") * (total_hours / pl.col("df")).log()).alias("tfidf")
    )
    return (
        scored.sort("tfidf", descending=True)
        .group_by("hour_bucket", maintain_order=True)
        .agg(pl.col("token").head(top_k).str.join(", ").alias("keywords"))
        .sort("hour_bucket")
    )
