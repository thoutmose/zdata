from datetime import datetime, timedelta

import polars as pl
from app.data.chat_nlp import top_keywords_per_hour


def _messages(rows: list[tuple[int, str]]) -> pl.DataFrame:
    """Build a minimal messages frame: `(hour_offset, text)` pairs."""
    base = datetime(2026, 9, 4, 20, 0, 0)
    return pl.DataFrame(
        {
            "message_sent_at": [base + timedelta(hours=h) for h, _ in rows],
            "message_text": [text for _, text in rows],
        }
    )


def test_word_spiking_in_one_hour_outranks_a_word_used_every_hour() -> None:
    # "chocolatine" appears once per hour, every hour — no hour distinguishes
    # it. "anniversaire" only appears (repeatedly) in hour 1 — a real spike.
    rows = [(h, "chocolatine") for h in range(5)]
    rows += [(1, "anniversaire") for _ in range(4)]
    df = top_keywords_per_hour(_messages(rows), top_k=1)

    spike_hour = df.filter(pl.col("hour_bucket") == datetime(2026, 9, 4, 21, 0, 0))
    assert spike_hour["keywords"][0] == "anniversaire"


def test_stopwords_and_short_tokens_are_excluded() -> None:
    rows = [(0, "le la de et un vaisseau")]
    df = top_keywords_per_hour(_messages(rows))
    assert df["keywords"][0] == "vaisseau"


def test_empty_after_filtering_returns_empty_frame() -> None:
    rows = [(0, "le la de")]
    df = top_keywords_per_hour(_messages(rows))
    assert df.is_empty()
    assert list(df.columns) == ["hour_bucket", "keywords"]


def test_top_k_limits_keywords_per_hour() -> None:
    rows = [(0, "alpha beta gamma delta epsilon")]
    df = top_keywords_per_hour(_messages(rows), top_k=2)
    assert len(df["keywords"][0].split(", ")) == 2
