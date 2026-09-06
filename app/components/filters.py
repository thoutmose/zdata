"""Global datetime-range filter: one sidebar slider that narrows every page's data.

Rendered once, in `app/🏠_Home.py`'s sidebar block — that file's top-level code
re-executes before every page (Streamlit always runs the entrypoint script
first), so a single call there is enough to put the slider above the nav
links on every page, the same way `render_global_search()` already works.
Bounds come from the event's own timestamps, not wall-clock "now" — the event
is a fixed stretch of its own timeline, and anchoring to real time would
silently break for mock data, or for anyone viewing the app after the event
has ended (the same reasoning `goal_progress.py`'s `elapsed_so_far` follows).

Every timestamp this module touches (`get_event_bounds()`, session state, and
every `timestamp_col` this filters) is naive Europe/Paris wall-clock time —
`repository.py::_run()` converts and strips tzinfo at the source, because
Streamlit's widgets and Plotly's charts render a tz-aware datetime in the
*viewer's browser* timezone rather than the one attached in Python. A naive
value has nothing for any frontend to reinterpret.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import polars as pl
import streamlit as st

from app.core.i18n import t
from app.data.repository import (
    get_chatter_directory,
    get_event_bounds,
    get_streamer_breakdown,
)

_SESSION_KEY = "global_date_range"
_STREAMER_SESSION_KEY = "global_streamer_filter"
_CHATTER_SESSION_KEY = "global_chatter_filter"


def render_global_date_filter() -> None:
    """Render the sidebar date-range slider, seeding/resetting its session state first.

    The event is live, so `get_event_bounds()`'s `max` grows over its ~56
    hours. If a previously stored selection no longer fits the current
    `[min, max]` (stale from an earlier, narrower fetch), `st.slider` raises
    rather than clamping it — so the stored value is reset to the full
    current range whenever that happens, before the widget is created.
    """
    bounds = get_event_bounds()
    if bounds is None:
        return
    min_ts, max_ts = bounds
    if min_ts >= max_ts:
        return

    current = st.session_state.get(_SESSION_KEY)
    if current is None or current[0] < min_ts or current[1] > max_ts or current[0] > current[1]:
        st.session_state[_SESSION_KEY] = (min_ts, max_ts)

    st.sidebar.slider(
        t("filter.date_range_label"),
        min_value=min_ts,
        max_value=max_ts,
        key=_SESSION_KEY,
        format="ddd D MMM, HH:mm",
        # st.slider defaults an all-datetime range to a 1-day step, which
        # leaves next to no room to drag within a live event whose data
        # (bucketed hourly at the source, see repository.py) can span as
        # little as a couple of hours early on — the handles would just
        # snap back to the endpoints. 15 minutes stays well under that
        # hourly grain without being pointlessly finer than the data.
        step=timedelta(minutes=15),
    )


def get_global_date_range() -> tuple[datetime, datetime] | None:
    """Return the currently selected global date range, if the slider has rendered.

    Returns:
        `(start, end)` as naive Europe/Paris wall-clock datetimes (matching
        every timestamp column in the app — see `app/core/tz.py` and
        `repository.py::_run()`), or `None` if the slider hasn't rendered yet
        (no event data) or hasn't been touched this session.
    """
    return st.session_state.get(_SESSION_KEY)


def apply_global_date_filter(df: pl.DataFrame, *, timestamp_col: str) -> pl.DataFrame:
    """Narrow `df` to the currently selected global date range.

    Args:
        df: DataFrame with at least `timestamp_col`. Returned unfiltered if empty.
        timestamp_col: Column holding the timestamps to filter on.

    Returns:
        `df` filtered to rows within the selected range, or `df` unchanged if
        it's empty or no range is set (e.g. the sidebar slider hasn't rendered).
    """
    if df.is_empty():
        return df
    date_range = get_global_date_range()
    if date_range is None:
        return df
    start, end = date_range
    return df.filter(pl.col(timestamp_col).is_between(start, end))


def render_global_entity_filters() -> None:
    """Render the sidebar streamer/chatter multiselects, right below the date filter.

    Replaces every page's own local streamer/channel/chatter *filtering*
    widget (search box, category multiselect, etc.) — see
    `apply_global_streamer_filter`/`apply_global_chatter_filter`. Pages that
    need to pick exactly *one* entity for a drill-down chart keep their own
    selectbox, but constrain its options to whatever is selected here.

    Stores `channel`/`chatter_id` (not the display name) as the selected
    values — that's the join key almost every page's DataFrame actually
    carries, whereas display names exist on fewer of them. `format_func`
    shows the friendly name in the widget without changing what's stored.

    Chatters are capped to the top 500 by activity (`get_chatter_directory`)
    rather than the full chatter universe, which can run into the thousands
    — nobody scrolls a multiselect that deep anyway.
    """
    streamers = get_streamer_breakdown()
    if not streamers.is_empty():
        name_by_channel = dict(zip(streamers["channel"], streamers["streamer"], strict=True))
        st.sidebar.multiselect(
            t("filter.streamer_label"),
            options=sorted(name_by_channel, key=lambda channel: name_by_channel[channel]),
            format_func=lambda channel: name_by_channel.get(channel, channel),
            key=_STREAMER_SESSION_KEY,
        )

    chatters = get_chatter_directory()
    if not chatters.is_empty():
        name_by_chatter_id = dict(zip(chatters["chatter_id"], chatters["chatter"], strict=True))
        st.sidebar.multiselect(
            t("filter.chatter_label"),
            options=list(name_by_chatter_id),
            format_func=lambda chatter_id: name_by_chatter_id.get(chatter_id, chatter_id),
            key=_CHATTER_SESSION_KEY,
        )


def get_global_streamer_filter() -> list[str]:
    """Return the currently selected global streamer `channel` logins (empty = "all")."""
    return st.session_state.get(_STREAMER_SESSION_KEY, [])


def get_global_streamer_names() -> list[str]:
    """Return the selected streamers' display names (empty = "all").

    For the handful of accessors (e.g. `leaderboard_movers`) whose result
    only carries a `streamer` display name, not a `channel` login — resolves
    the selection via `get_streamer_breakdown()`'s channel-to-name mapping
    rather than a second widget.
    """
    selected = get_global_streamer_filter()
    if not selected:
        return []
    streamers = get_streamer_breakdown()
    name_by_channel = dict(zip(streamers["channel"], streamers["streamer"], strict=True))
    return [name_by_channel[channel] for channel in selected if channel in name_by_channel]


def get_global_chatter_filter() -> list[str]:
    """Return the currently selected global `chatter_id`s (empty = "all")."""
    return st.session_state.get(_CHATTER_SESSION_KEY, [])


def get_global_chatter_names() -> list[str]:
    """Return the selected chatters' display names (empty = "all").

    For the handful of accessors (e.g. `chat_message_sample`,
    `chat_toxicity_examples` — both read straight from the raw chat stream,
    which carries a `chatter` username but no stable `chatter_id`) whose
    result can only be narrowed by display name, not by
    `apply_global_chatter_filter`'s `chatter_id` join key. Same
    resolve-via-directory pattern as `get_global_streamer_names`. Chatter
    display names aren't guaranteed globally unique the way a `chatter_id`
    is, so this is a best-effort narrowing for those name-only accessors,
    not a substitute for `apply_global_chatter_filter` wherever a real
    `chatter_id` column is available.
    """
    selected = get_global_chatter_filter()
    if not selected:
        return []
    chatters = get_chatter_directory()
    name_by_id = dict(zip(chatters["chatter_id"], chatters["chatter"], strict=True))
    return [name_by_id[chatter_id] for chatter_id in selected if chatter_id in name_by_id]


def apply_global_streamer_filter(df: pl.DataFrame, *, channel_col: str = "channel") -> pl.DataFrame:
    """Narrow `df` to the globally selected streamers, if any are selected.

    Args:
        df: DataFrame with at least `channel_col`. Returned unfiltered if empty.
        channel_col: Column holding the streamer's `channel` login to filter on.

    Returns:
        `df` filtered to the selected streamers, or `df` unchanged if it's
        empty or nothing is selected (the "all streamers" default).
    """
    if df.is_empty():
        return df
    selected = get_global_streamer_filter()
    if not selected:
        return df
    return df.filter(pl.col(channel_col).is_in(selected))


def apply_global_chatter_filter(
    df: pl.DataFrame, *, chatter_id_col: str = "chatter_id"
) -> pl.DataFrame:
    """Narrow `df` to the globally selected chatters, if any are selected.

    Args:
        df: DataFrame with at least `chatter_id_col`. Returned unfiltered if empty.
        chatter_id_col: Column holding the chatter's `chatter_id` to filter on.

    Returns:
        `df` filtered to the selected chatters, or `df` unchanged if it's
        empty or nothing is selected (the "all chatters" default).
    """
    if df.is_empty():
        return df
    selected = get_global_chatter_filter()
    if not selected:
        return df
    return df.filter(pl.col(chatter_id_col).is_in(selected))
