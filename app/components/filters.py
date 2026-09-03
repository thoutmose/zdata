"""Shared "period" quick-filter: Last hour / Last 6h / Last 24h / All event.

Bounds are computed relative to the latest timestamp actually present in the
data, not wall-clock "now" — the event is a fixed stretch of its own
timeline, and anchoring to real time would silently break for mock data, or
for anyone viewing the app after the event has ended (the same reasoning
`goal_progress.py`'s `elapsed_so_far` already follows).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import cast

import polars as pl
import streamlit as st

from app.core.i18n import t

_PRESET_KEYS = ["period.last_hour", "period.last_6h", "period.last_24h", "period.all"]
_PRESET_SPANS: dict[str, timedelta | None] = {
    "period.last_hour": timedelta(hours=1),
    "period.last_6h": timedelta(hours=6),
    "period.last_24h": timedelta(hours=24),
    "period.all": None,
}


def period_filter(df: pl.DataFrame, *, timestamp_col: str, key: str) -> pl.DataFrame:
    """Render a period quick-filter and return `df` narrowed to the selected window.

    Args:
        df: DataFrame with at least `timestamp_col`. Returned unfiltered if empty.
        timestamp_col: Column holding the timestamps to filter on.
        key: Unique Streamlit widget key — a page with more than one period
            filter on it needs a distinct key per instance.

    Returns:
        `df` filtered to rows within the selected window of its own latest
        timestamp, or `df` unchanged if it's empty or "All event" is picked.
    """
    if df.is_empty():
        return df
    labels = [t(preset_key) for preset_key in _PRESET_KEYS]
    choice = st.radio(t("period.label"), labels, horizontal=True, key=key, index=len(labels) - 1)
    span = _PRESET_SPANS[_PRESET_KEYS[labels.index(choice)]]
    if span is None:
        return df
    max_ts = cast(datetime, df[timestamp_col].max())
    return df.filter(pl.col(timestamp_col) >= max_ts - span)
