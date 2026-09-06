"""Tests for the global datetime-range filter (`app/components/filters.py`).

`render_global_date_filter()` itself isn't covered here — it renders a real
`st.slider` and needs `get_event_bounds()` wired up, which is an integration
concern better covered by `AppTest` (see `app/data/repository.py`'s docstring
and the AppTest gotcha noted in project memory) than a unit test. What's
tested here is the pure, session-state-driven narrowing logic every page
actually calls: given a selected range (or none), does the right subset of
rows come back.
"""

from __future__ import annotations

from datetime import datetime

import polars as pl
import pytest
import streamlit as st
from app.components.filters import (
    apply_global_chatter_filter,
    apply_global_date_filter,
    apply_global_streamer_filter,
    get_global_chatter_filter,
    get_global_date_range,
    get_global_streamer_filter,
)

_SESSION_KEY = "global_date_range"
_STREAMER_SESSION_KEY = "global_streamer_filter"
_CHATTER_SESSION_KEY = "global_chatter_filter"


@pytest.fixture(autouse=True)
def _clear_session_state():
    for key in (_SESSION_KEY, _STREAMER_SESSION_KEY, _CHATTER_SESSION_KEY):
        st.session_state.pop(key, None)
    yield
    for key in (_SESSION_KEY, _STREAMER_SESSION_KEY, _CHATTER_SESSION_KEY):
        st.session_state.pop(key, None)


def _df(timestamps: list[str]) -> pl.DataFrame:
    return pl.DataFrame({"timestamp": pl.Series(timestamps).str.to_datetime()})


def test_get_global_date_range_is_none_before_slider_has_rendered() -> None:
    assert get_global_date_range() is None


def test_apply_global_date_filter_passes_through_when_no_range_set() -> None:
    df = _df(["2026-09-03T20:00", "2026-09-05T10:00"])

    assert apply_global_date_filter(df, timestamp_col="timestamp").height == 2


def test_apply_global_date_filter_passes_through_empty_df_even_with_range_set() -> None:
    df = pl.DataFrame({"timestamp": pl.Series([], dtype=pl.Datetime)})
    st.session_state[_SESSION_KEY] = (datetime(2026, 9, 3), datetime(2026, 9, 5))

    assert apply_global_date_filter(df, timestamp_col="timestamp").is_empty()


def test_apply_global_date_filter_narrows_to_the_selected_range() -> None:
    df = _df(["2026-09-03T19:00", "2026-09-04T12:00", "2026-09-05T12:00"])
    st.session_state[_SESSION_KEY] = (datetime(2026, 9, 3, 19, 0), datetime(2026, 9, 4, 12, 0))

    result = apply_global_date_filter(df, timestamp_col="timestamp")

    assert result.height == 2
    assert result["timestamp"].max() == datetime(2026, 9, 4, 12, 0)


def test_apply_global_date_filter_default_range_covers_the_full_event() -> None:
    """The whole point of defaulting the slider to `get_event_bounds()`: a
    range spanning the event's own first and last timestamp must keep every
    row, not just the ones strictly between them."""
    df = _df(["2026-09-03T19:00", "2026-09-04T12:00", "2026-09-05T12:00"])
    event_start, event_end = datetime(2026, 9, 3, 19, 0), datetime(2026, 9, 5, 12, 0)
    st.session_state[_SESSION_KEY] = (event_start, event_end)

    result = apply_global_date_filter(df, timestamp_col="timestamp")

    assert result.height == 3


def test_get_global_streamer_filter_is_empty_before_widget_has_rendered() -> None:
    assert get_global_streamer_filter() == []


def test_apply_global_streamer_filter_passes_through_when_nothing_selected() -> None:
    df = pl.DataFrame({"channel": ["zevrix", "auroraline"]})

    assert apply_global_streamer_filter(df).height == 2


def test_apply_global_streamer_filter_passes_through_empty_df_even_with_selection() -> None:
    df = pl.DataFrame({"channel": []}, schema={"channel": pl.Utf8})
    st.session_state[_STREAMER_SESSION_KEY] = ["zevrix"]

    assert apply_global_streamer_filter(df).is_empty()


def test_apply_global_streamer_filter_narrows_to_the_selected_channels() -> None:
    df = pl.DataFrame({"channel": ["zevrix", "auroraline", "streamix"]})
    st.session_state[_STREAMER_SESSION_KEY] = ["zevrix", "streamix"]

    result = apply_global_streamer_filter(df)

    assert sorted(result["channel"].to_list()) == ["streamix", "zevrix"]


def test_get_global_chatter_filter_is_empty_before_widget_has_rendered() -> None:
    assert get_global_chatter_filter() == []


def test_apply_global_chatter_filter_passes_through_when_nothing_selected() -> None:
    df = pl.DataFrame({"chatter_id": ["1", "2"]})

    assert apply_global_chatter_filter(df).height == 2


def test_apply_global_chatter_filter_narrows_to_the_selected_chatter_ids() -> None:
    df = pl.DataFrame({"chatter_id": ["1", "2", "3"]})
    st.session_state[_CHATTER_SESSION_KEY] = ["2"]

    result = apply_global_chatter_filter(df)

    assert result["chatter_id"].to_list() == ["2"]
