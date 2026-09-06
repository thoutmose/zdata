"""Shared helper for stripping real chatter identifiers out of exported data.

Chat usernames are real and shown on-screen throughout this app (see
`app/pages/8_🗣️_Chatters.py`'s module docstring) — the CSV export is the one
place a real identifier must never leave the app, so every download that
includes a `chatter`/`chatter_id` column runs it through here first.
"""

from __future__ import annotations

import hashlib

import polars as pl


def anonymize_chatters(df: pl.DataFrame) -> pl.DataFrame:
    """Replace real chatter identifiers with a stable, one-way pseudonym.

    The pseudonym is derived from a SHA-256 hash of `chatter_id`, truncated —
    deterministic (the same chatter always gets the same pseudonym across
    every download, in every page, since it's keyed on the id rather than
    anything download-local) but not reversible to the real id or username.

    Args:
        df: DataFrame with `chatter_id` and `chatter` columns.

    Returns:
        `df` with those two columns replaced by a single `chatter_pseudonym`
        column, in front.
    """
    pseudonyms = [
        "Chatter_" + hashlib.sha256(cid.encode("utf-8")).hexdigest()[:8]
        for cid in df["chatter_id"].to_list()
    ]
    kept = [c for c in df.columns if c not in ("chatter_id", "chatter")]
    return (
        df.select(kept)
        .with_columns(pl.Series("chatter_pseudonym", pseudonyms))
        .select(["chatter_pseudonym", *kept])
    )
