"""Deterministic sample data, shaped like the real ZEvent dataset.

Used whenever no database credentials are configured (`Settings.use_mock_data`)
so every page works end to end offline. Every function here is seeded and
pure — same input, same output — so pages and tests behave predictably.

Column shapes mirror `app/data/repository.py::PostgresDataSource`, which
queries the real dbt-modeled warehouse (`raw` -> `stg` -> `int` -> `marts`
schemas). Notably, the real warehouse has no "team" dimension for streamers.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import polars as pl

from app.core.tz import PARIS
from app.data.chat_lexicons import HOSTILE_WORDS, contains_any
from app.data.chat_nlp import top_keywords_per_hour
from app.data.emote_cdn import emote_image_url
from app.data.goal_progress import goal_progress_by_category

_SEED = 42
_EVENT_START = datetime(2026, 9, 4, 20, 0, 0)  # Europe/Paris wall-clock, naive (see `_run`)
_EVENT_DURATION_HOURS = 56

_STREAMERS = [
    "Zevrix",
    "Auroraline",
    "Marathonix",
    "Solidarine",
    "Nightowl_fr",
    "Petitpixel",
    "Longrun92",
    "Coeurdejeu",
    "Streamix",
    "Luciole_tv",
]
_CATEGORIES = [
    "Just Chatting",
    "Minecraft",
    "Geoguessr",
    "Mario Kart 8",
    "Fall Guys",
    "Valorant",
    "Overcooked 2",
    "Trackmania",
    "Chess",
    "Among Us",
]
_GOAL_CATEGORIES = [
    "donation",
    "recurent",
    "donation_equal",
    "donation_more_than",
    "incentive",
    "donation_largest",
    "global",
]
# Weights for `rng.choice(_GOAL_CATEGORIES, ...)`: 'donation' (the classic
# cumulative-total milestone) and 'global' (event-wide goals, e.g. the
# official ZEvent channel's own) dominate in the real data; the rest are
# rarer, which is also why each is tracked as its own independent chain
# rather than folded into one (see `app.data.goal_progress`).
_GOAL_CATEGORY_WEIGHTS = [0.55, 0.06, 0.06, 0.06, 0.06, 0.06, 0.15]
_EVENT_PHASES = ["opening", "middle", "final_push"]
_ACCOUNT_AGE_BUCKETS = ["new (<30d)", "1mo-1yr", "1-3yr", "3yr+", "unknown"]
_CHATTER_PROFILES = ["sedentaire", "multi_streamer", "semi_nomade", "nomade"]


def _hours() -> np.ndarray:
    return np.arange(_EVENT_DURATION_HOURS + 1)


def _timestamps(hours: np.ndarray) -> list[datetime]:
    """Turn hour offsets into absolute event timestamps.

    Args:
        hours: Hour offsets from the event start.

    Returns:
        One timezone-aware `datetime` per offset.
    """
    return [_EVENT_START + timedelta(hours=int(h)) for h in hours]


def donation_timeseries() -> pl.DataFrame:
    """Generate an hourly cumulative-donations curve for a full event.

    Returns:
        DataFrame with columns `timestamp` (datetime), `cumulative_amount_eur`
        (float, monotonically increasing) and `active_streamers` (int).
    """
    rng = np.random.default_rng(_SEED)
    hours = _hours()

    base_rate = 8_000 + 4_000 * np.sin(hours / 12) ** 2
    night_dip = np.where((hours % 24 >= 2) & (hours % 24 <= 8), 0.4, 1.0)
    final_surge = np.where(hours >= _EVENT_DURATION_HOURS - 4, 2.5, 1.0)
    hourly_amount = base_rate * night_dip * final_surge * rng.uniform(0.85, 1.15, size=hours.size)
    cumulative_amount = np.cumsum(hourly_amount)

    active_streamers = rng.integers(20, len(_STREAMERS) * 6, size=hours.size)

    return pl.DataFrame(
        {
            "timestamp": _timestamps(hours),
            "cumulative_amount_eur": cumulative_amount.round(2),
            "active_streamers": active_streamers,
        }
    )


def event_phase_breakdown() -> pl.DataFrame:
    """Generate donations and streamer counts by event phase.

    Returns:
        DataFrame with columns `phase`, `donations_eur`, `streamers`.
    """
    rng = np.random.default_rng(_SEED + 10)
    weights = np.array([0.2, 0.35, 0.45])  # final push raises disproportionately more
    total = donation_timeseries()["cumulative_amount_eur"][-1]
    return pl.DataFrame(
        {
            "phase": _EVENT_PHASES,
            "donations_eur": (total * weights).round(2),
            "streamers": rng.integers(30, len(_STREAMERS) * 6, size=len(_EVENT_PHASES)),
        }
    )


def leaderboard_movers() -> pl.DataFrame:
    """Generate the streamers with the biggest recent donation-rank swings.

    Returns:
        DataFrame with columns `streamer`, `donation_rank`, `rank_change`.
    """
    rng = np.random.default_rng(_SEED + 11)
    n = len(_STREAMERS)
    return pl.DataFrame(
        {
            "streamer": _STREAMERS,
            "donation_rank": rng.permutation(n) + 1,
            "rank_change": rng.integers(-5, 6, size=n),
        }
    ).sort(pl.col("rank_change").abs(), descending=True)


def data_quality_check() -> pl.DataFrame:
    """Generate a (clean) donation-total reconciliation check.

    Returns:
        DataFrame with one row: `checked_at`, `divergence_eur`.
    """
    checked_at = datetime.now(PARIS).replace(tzinfo=None)
    return pl.DataFrame({"checked_at": [checked_at], "divergence_eur": [0.0]})


def streamer_breakdown() -> pl.DataFrame:
    """Generate per-streamer donation, audience and engagement figures.

    `donation_eur_per_avg_viewer`/`donation_eur_per_unique_chatter` mirror
    `marts.mart_donations__normalized`'s efficiency metrics.

    Returns:
        DataFrame with columns `channel`, `streamer`, `amount_eur`,
        `hours_live`, `avg_viewers`, `peak_viewers`, `unique_chatters`,
        `total_messages`, `sedentaire_chatters`, `multi_streamer_chatters`,
        `semi_nomade_chatters`, `nomade_chatters`, `top_category`,
        `uptime_pct`, `donation_eur_per_avg_viewer`,
        `donation_eur_per_unique_chatter`.
    """
    rng = np.random.default_rng(_SEED + 1)
    n = len(_STREAMERS)
    amounts = rng.pareto(a=2.0, size=n) * 15_000 + 5_000
    avg_viewers = rng.integers(1_500, 45_000, size=n)
    unique_chatters = rng.integers(200, 2_000, size=n)
    sedentaire = (unique_chatters * rng.uniform(0.85, 0.95, size=n)).astype(int)
    multi_streamer = (unique_chatters * rng.uniform(0.02, 0.08, size=n)).astype(int)
    semi_nomade = (unique_chatters * rng.uniform(0.0, 0.03, size=n)).astype(int)
    nomade = np.maximum(unique_chatters - sedentaire - multi_streamer - semi_nomade, 0)
    return pl.DataFrame(
        {
            "channel": [s.lower() for s in _STREAMERS],
            "streamer": _STREAMERS,
            "amount_eur": amounts.round(2),
            "hours_live": rng.uniform(30, _EVENT_DURATION_HOURS, size=n).round(1),
            "avg_viewers": avg_viewers,
            "peak_viewers": rng.integers(2_000, 60_000, size=n),
            "unique_chatters": unique_chatters,
            "total_messages": unique_chatters * rng.integers(3, 15, size=n),
            "sedentaire_chatters": sedentaire,
            "multi_streamer_chatters": multi_streamer,
            "semi_nomade_chatters": semi_nomade,
            "nomade_chatters": nomade,
            "top_category": rng.choice(_CATEGORIES, size=n),
            "uptime_pct": rng.uniform(40, 99, size=n).round(1),
            "donation_eur_per_avg_viewer": (amounts / avg_viewers).round(4),
            "donation_eur_per_unique_chatter": (amounts / unique_chatters).round(4),
        }
    ).sort("amount_eur", descending=True)


def streamer_diurnal_profile(channel: str) -> pl.DataFrame:
    """Generate one streamer's hourly viewer pattern vs. the event average.

    Args:
        channel: The streamer's channel/login (used only to seed variation).

    Returns:
        DataFrame with columns `hour_of_day`, `streamer_avg_viewer_count`,
        `event_avg_viewer_count`.
    """
    seed = _SEED + sum(map(ord, channel))
    rng = np.random.default_rng(seed)
    hour_of_day = np.arange(24)
    event_avg = 3_000 + 2_000 * np.sin((hour_of_day - 14) / 24 * 2 * np.pi)
    streamer_avg = event_avg * rng.uniform(0.5, 1.8) + rng.normal(0, 200, size=24)
    return pl.DataFrame(
        {
            "hour_of_day": hour_of_day,
            "streamer_avg_viewer_count": np.clip(streamer_avg, 0, None).round(1),
            "event_avg_viewer_count": np.clip(event_avg, 0, None).round(1),
        }
    )


def donation_forecast_features(cutoff: datetime) -> pl.DataFrame:
    """Generate each streamer's mid-event snapshot plus their eventual final total.

    Mirrors `PostgresDataSource.donation_forecast_features`: scales each
    streamer's final `streamer_breakdown` stats down to a `cutoff`-implied
    progress fraction, plus noise and a random per-streamer growth-curve
    exponent, so some streamers' donations/viewers/messages accumulate
    steadily while others stay flat then surge late — the same
    late-donation-surge shape real ZEvent data shows — even though every
    streamer's final total is unchanged.

    Args:
        cutoff: The mid-event point in time to snapshot features at.

    Returns:
        DataFrame with columns `channel`, `streamer`, `amount_eur_mid`,
        `avg_viewers_mid`, `peak_viewers_mid`, `total_messages_mid`,
        `amount_eur` (the final, eventual total — the regression target).
    """
    cutoff_naive = cutoff.replace(tzinfo=None) if cutoff.tzinfo else cutoff
    rng = np.random.default_rng(_SEED + 40)
    final = streamer_breakdown()
    n = len(final)
    progress = np.clip(
        (cutoff_naive - _EVENT_START).total_seconds() / 3600 / _EVENT_DURATION_HOURS,
        0.05,
        1.0,
    )
    growth_exponent = rng.uniform(0.6, 1.8, size=n)
    fraction = progress**growth_exponent
    amount_final = final["amount_eur"].to_numpy()
    avg_viewers_final = final["avg_viewers"].to_numpy()
    peak_viewers_final = final["peak_viewers"].to_numpy()
    messages_final = final["total_messages"].to_numpy()
    amount_mid = amount_final * fraction * rng.normal(1.0, 0.05, size=n)
    avg_viewers_mid = avg_viewers_final * fraction * rng.normal(1.0, 0.05, size=n)
    peak_viewers_mid = np.minimum(
        peak_viewers_final * np.clip(fraction * rng.uniform(0.9, 1.05, size=n), 0, 1),
        peak_viewers_final,
    )
    messages_mid = messages_final * fraction * rng.normal(1.0, 0.05, size=n)
    return pl.DataFrame(
        {
            "channel": final["channel"],
            "streamer": final["streamer"],
            "amount_eur_mid": np.maximum(amount_mid, 0).round(2),
            "avg_viewers_mid": np.maximum(avg_viewers_mid, 0).round(1),
            "peak_viewers_mid": np.maximum(peak_viewers_mid, 0).astype(int),
            "total_messages_mid": np.maximum(messages_mid, 0).round(0),
            "amount_eur": final["amount_eur"],
        }
    )


def category_breakdown() -> pl.DataFrame:
    """Generate channel-hours played per Twitch category.

    Returns:
        DataFrame with columns `category`, `channel_hours`.
    """
    rng = np.random.default_rng(_SEED + 2)
    n = len(_CATEGORIES)
    channel_hours = rng.dirichlet(np.ones(n)) * (_EVENT_DURATION_HOURS * len(_STREAMERS))
    return pl.DataFrame({"category": _CATEGORIES, "channel_hours": channel_hours.round(1)}).sort(
        "channel_hours", descending=True
    )


def viewership_timeseries() -> pl.DataFrame:
    """Generate event-wide concurrent viewership over time.

    Returns:
        DataFrame with columns `timestamp`, `total_avg_viewer_count`,
        `live_channel_count`.
    """
    rng = np.random.default_rng(_SEED + 12)
    hours = _hours()
    base = 20_000 + 15_000 * np.sin(hours / 12) ** 2
    night_dip = np.where((hours % 24 >= 2) & (hours % 24 <= 8), 0.5, 1.0)
    total_avg_viewer_count = base * night_dip * rng.uniform(0.9, 1.1, size=hours.size)
    live_channel_count = (
        len(_STREAMERS) * night_dip * rng.uniform(0.7, 1.0, size=hours.size)
    ).astype(int)
    return pl.DataFrame(
        {
            "timestamp": _timestamps(hours),
            "total_avg_viewer_count": total_avg_viewer_count.round(1),
            "live_channel_count": np.maximum(live_channel_count, 1),
        }
    )


def stream_sessions() -> pl.DataFrame:
    """Generate a handful of recent individual stream sessions.

    Returns:
        DataFrame with columns `channel`, `stream_started_at`,
        `duration_hours`, `avg_viewer_count`, `peak_viewer_count`, `viewer_change`.
    """
    rng = np.random.default_rng(_SEED + 13)
    n = 12
    offsets = rng.uniform(0, _EVENT_DURATION_HOURS, size=n)
    started = [_EVENT_START + timedelta(hours=float(h)) for h in offsets]
    avg_viewers = rng.integers(500, 30_000, size=n)
    return pl.DataFrame(
        {
            "channel": rng.choice([s.lower() for s in _STREAMERS], size=n),
            "stream_started_at": started,
            "duration_hours": rng.uniform(1, 10, size=n).round(1),
            "avg_viewer_count": avg_viewers,
            "peak_viewer_count": (avg_viewers * rng.uniform(1.1, 1.8, size=n)).astype(int),
            "viewer_change": rng.integers(-500, 2_000, size=n),
        }
    ).sort("stream_started_at", descending=True)


def goals_by_category() -> pl.DataFrame:
    """Generate per-category donation-goal figures.

    Returns:
        DataFrame with columns `category`, `goal_count`, `streamer_count`,
        `avg_goal_amount_eur`.
    """
    rng = np.random.default_rng(_SEED + 3)
    n = len(_GOAL_CATEGORIES)
    goal_count = rng.integers(2, 400, size=n)
    return pl.DataFrame(
        {
            "category": _GOAL_CATEGORIES,
            "goal_count": goal_count,
            "streamer_count": np.minimum(goal_count, rng.integers(2, 140, size=n)),
            "avg_goal_amount_eur": rng.uniform(50, 5_000, size=n).round(2),
        }
    ).sort("goal_count", descending=True)


def top_goal_setters() -> pl.DataFrame:
    """Generate the streamers with the most donation goals set.

    Returns:
        DataFrame with columns `streamer_name`, `goal_count`,
        `realistic_goal_amount_eur`.
    """
    rng = np.random.default_rng(_SEED + 4)
    n = len(_STREAMERS)
    goal_count = rng.integers(1, 30, size=n)
    return pl.DataFrame(
        {
            "streamer_name": _STREAMERS,
            "goal_count": goal_count,
            "realistic_goal_amount_eur": (goal_count * rng.uniform(50, 400, size=n)).round(2),
        }
    ).sort("goal_count", descending=True)


def chat_activity_timeseries() -> pl.DataFrame:
    """Generate event-wide chat message volume over time.

    Returns:
        DataFrame with columns `timestamp`, `message_count`, `unique_chatters`.
    """
    rng = np.random.default_rng(_SEED + 20)
    hours = _hours()
    base = 3_000 + 2_500 * np.sin(hours / 12) ** 2
    night_dip = np.where((hours % 24 >= 2) & (hours % 24 <= 8), 0.4, 1.0)
    message_count = (base * night_dip * rng.uniform(0.85, 1.15, size=hours.size)).astype(int)
    return pl.DataFrame(
        {
            "timestamp": _timestamps(hours),
            "message_count": message_count,
            "unique_chatters": (message_count / rng.uniform(3, 6)).astype(int),
        }
    )


def top_chat_channels() -> pl.DataFrame:
    """Generate the busiest channels by chat message composition.

    Returns:
        DataFrame with columns `channel`, `message_count`,
        `subscriber_message_count`, `vip_message_count`,
        `moderator_message_count`, `plain_viewer_message_count`,
        `avg_message_length`.
    """
    rng = np.random.default_rng(_SEED + 21)
    n = len(_STREAMERS)
    message_count = rng.integers(500, 5_000, size=n)
    subscriber = (message_count * rng.uniform(0.2, 0.4, size=n)).astype(int)
    vip = (message_count * rng.uniform(0.0, 0.02, size=n)).astype(int)
    moderator = (message_count * rng.uniform(0.02, 0.1, size=n)).astype(int)
    plain = np.maximum(message_count - subscriber - vip - moderator, 0)
    return pl.DataFrame(
        {
            "channel": [s.lower() for s in _STREAMERS],
            "message_count": message_count,
            "subscriber_message_count": subscriber,
            "vip_message_count": vip,
            "moderator_message_count": moderator,
            "plain_viewer_message_count": plain,
            "avg_message_length": rng.uniform(20, 70, size=n).round(1),
        }
    ).sort("message_count", descending=True)


def chat_channel_list() -> list[str]:
    """Generate the full list of channels with chat activity.

    Returns:
        Every mock streamer's channel login, sorted.
    """
    return sorted(s.lower() for s in _STREAMERS)


def top_emotes() -> pl.DataFrame:
    """Generate the most-used emotes across the event.

    Uses real Twitch global emote ids (Kappa, 4Head, ...) so the mock image
    actually resolves, same as production — see `app.data.emote_cdn`.

    Returns:
        DataFrame with columns `service`, `emote_id`, `emote`, `is_named`,
        `usage_count`, `image_url`.
    """
    rng = np.random.default_rng(_SEED + 22)
    names_and_ids = [
        ("Kappa", "25"),
        ("4Head", "354"),
        ("DansGame", "33"),
        ("SwiftRage", "34"),
        ("ResidentSleeper", "245"),
        ("NotLikeThis", "58765"),
        ("ANELE", "43"),
        ("BloodTrail", "76"),
        ("PJSalt", "36"),
        ("Kreygasm", "41"),
    ]
    names = [n for n, _ in names_and_ids]
    ids = [i for _, i in names_and_ids]
    return pl.DataFrame(
        {
            "service": ["twitch"] * len(names),
            "emote_id": ids,
            "emote": names,
            "is_named": [True] * len(names),
            "usage_count": rng.integers(50, 700, size=len(names)),
            "image_url": [emote_image_url("twitch", i) for i in ids],
        }
    ).sort("usage_count", descending=True)


def chatter_profile_mix() -> pl.DataFrame:
    """Generate the breakdown of chatters by loyalty profile.

    Returns:
        DataFrame with columns `profile`, `chatter_count`.
    """
    rng = np.random.default_rng(_SEED + 23)
    total = 3_000
    shares = np.array([0.93, 0.04, 0.02, 0.01])
    counts = (total * shares * rng.uniform(0.9, 1.1, size=4)).astype(int)
    return pl.DataFrame({"profile": _CHATTER_PROFILES, "chatter_count": counts}).sort(
        "chatter_count", descending=True
    )


def chatter_account_age_mix() -> pl.DataFrame:
    """Generate the breakdown of chatters by Twitch account age.

    Returns:
        DataFrame with columns `age_bucket`, `chatter_count`.
    """
    shares = np.array([0.01, 0.05, 0.1, 0.44, 0.4])
    counts = (3_000 * shares).astype(int)
    return pl.DataFrame({"age_bucket": _ACCOUNT_AGE_BUCKETS, "chatter_count": counts})


def top_chatters() -> pl.DataFrame:
    """Generate the most active chatters by message count.

    A couple of entries are named/flagged like real moderation bots so the
    "hide likely bots" filter has something to demonstrate against mock data.

    Returns:
        DataFrame with columns `chatter_id`, `chatter`, `channel`,
        `message_count`, `distinct_channel_count`, `has_long_digit_suffix`.
    """
    rng = np.random.default_rng(_SEED + 25)
    n = 15
    names = [f"Chatter{i}" for i in range(1, n + 1)]
    names[0] = "Nightbot"
    names[1] = "StreamElements"
    has_long_digit_suffix = [False] * n
    has_long_digit_suffix[2] = True
    return pl.DataFrame(
        {
            "chatter_id": [str(rng.integers(10_000_000, 999_999_999)) for _ in range(n)],
            "chatter": names,
            "channel": rng.choice([s.lower() for s in _STREAMERS], size=n),
            "message_count": np.sort(rng.integers(50, 500, size=n))[::-1],
            "distinct_channel_count": rng.integers(1, 3, size=n),
            "has_long_digit_suffix": has_long_digit_suffix,
        }
    )


def top_chatters_for_channels(channels: list[str]) -> pl.DataFrame:
    """Generate the most active chatters across a set of channels.

    Reuses `channel_chatter_breakdown` per channel and sums by chatter.
    Mock chatter ids are generated independently per channel (seeded by
    channel name), so unlike the real data, a mock chatter won't naturally
    show up in more than one requested channel — `channels_in_filter` is
    always 1 here, whereas real chatters often span several.

    Args:
        channels: The channels to include.

    Returns:
        DataFrame with columns `chatter_id`, `chatter`, `message_count`,
        `channels_in_filter`, `has_long_digit_suffix`.
    """
    schema = {
        "chatter_id": pl.Utf8,
        "chatter": pl.Utf8,
        "message_count": pl.Int64,
        "channels_in_filter": pl.UInt32,
        "has_long_digit_suffix": pl.Boolean,
    }
    if not channels:
        return pl.DataFrame(schema=schema)

    combined = pl.concat(
        channel_chatter_breakdown(channel)
        .select("chatter_id", "chatter", "message_count")
        .with_columns(channel=pl.lit(channel))
        for channel in channels
    )
    grouped = (
        combined.group_by("chatter_id")
        .agg(
            pl.col("chatter").first(),
            pl.col("message_count").sum(),
            pl.col("channel").n_unique().alias("channels_in_filter"),
        )
        .sort("message_count", descending=True)
        .head(200)
    )
    seed = _SEED + 90 + sum(ord(c) for name in channels for c in name)
    rng = np.random.default_rng(seed)
    return grouped.with_columns(
        pl.Series("has_long_digit_suffix", rng.uniform(size=len(grouped)) < 0.05)
    )


def top_chatter_per_channel() -> pl.DataFrame:
    """Generate each channel's single most active chatter ("#1 fan").

    Reuses `channel_chatter_breakdown` per channel (only 10 in mock data,
    unlike the real ~300+ channels) and keeps its single busiest row.

    Returns:
        DataFrame with columns `channel`, `chatter_id`, `chatter`,
        `message_count`, `has_long_digit_suffix`.
    """
    rows = [
        {
            "channel": channel,
            **channel_chatter_breakdown(channel)
            .sort("message_count", descending=True)
            .select("chatter_id", "chatter", "message_count")
            .row(0, named=True),
        }
        for channel in (s.lower() for s in _STREAMERS)
    ]
    df = pl.DataFrame(rows)
    rng = np.random.default_rng(_SEED + 96)
    return df.with_columns(pl.Series("has_long_digit_suffix", rng.uniform(size=len(df)) < 0.05))


def channel_network() -> pl.DataFrame:
    """Generate channel pairs ranked by shared chat audience.

    Returns:
        DataFrame with columns `channel_a`, `channel_b`,
        `shared_chatter_count`, `jaccard_index`.
    """
    rng = np.random.default_rng(_SEED + 26)
    channels = [s.lower() for s in _STREAMERS]
    pairs = [(channels[i], channels[i + 1]) for i in range(0, len(channels) - 1, 2)]
    shared = rng.integers(2, 30, size=len(pairs))
    return pl.DataFrame(
        {
            "channel_a": [p[0] for p in pairs],
            "channel_b": [p[1] for p in pairs],
            "shared_chatter_count": shared,
            "jaccard_index": rng.uniform(0.005, 0.05, size=len(pairs)).round(4),
        }
    ).sort("shared_chatter_count", descending=True)


def chatter_growth_timeseries() -> pl.DataFrame:
    """Generate new-chatter counts per quarter-hour, event-wide.

    Quarter-hour grain mirrors `marts.mart_chatters__retention`'s
    `is_new_this_quarter_hour` flag — finer than the previous hourly grain,
    and matches the sidebar date filter's own 15-minute step.

    Returns:
        DataFrame with columns `timestamp`, `new_chatters`.
    """
    rng = np.random.default_rng(_SEED + 27)
    quarter_hours = np.arange(_EVENT_DURATION_HOURS * 4 + 1) / 4
    base = 40 * np.exp(-quarter_hours / 30) + 5  # most new chatters arrive early
    timestamps = [_EVENT_START + timedelta(hours=float(h)) for h in quarter_hours]
    return pl.DataFrame(
        {
            "timestamp": timestamps,
            "new_chatters": (base * rng.uniform(0.8, 1.2, size=quarter_hours.size)).astype(int),
        }
    )


def chatter_day1_retention() -> pl.DataFrame:
    """Generate day-N retention of the event's first-day chatters.

    Returns:
        DataFrame with columns `day_index` (0-based, relative to the
        event's own start), `retained_chatters`.
    """
    n_days = int(_EVENT_DURATION_HOURS // 24) + 1
    rng = np.random.default_rng(_SEED + 28)
    day0_chatters = int(rng.integers(15_000, 25_000))
    # Typical day-N retention decay for a multi-day live event: a large
    # first-day drop-off, then a shallower decline each day after.
    decay = [1.0, *[0.55 * (0.75**i) for i in range(n_days - 1)]]
    return pl.DataFrame(
        {
            "day_index": list(range(n_days)),
            "retained_chatters": [int(day0_chatters * d) for d in decay],
        }
    )


def channel_hour_heatmap() -> pl.DataFrame:
    """Generate per-channel, per-hour message counts for a heatmap.

    Returns:
        DataFrame with columns `channel`, `timestamp`, `message_count`.
    """
    rng = np.random.default_rng(_SEED + 28)
    hours = _hours()
    timestamps = _timestamps(hours)
    frames = []
    for streamer in _STREAMERS:
        base = rng.uniform(50, 400)
        night_dip = np.where((hours % 24 >= 2) & (hours % 24 <= 8), 0.3, 1.0)
        counts = (base * night_dip * rng.uniform(0.7, 1.3, size=hours.size)).astype(int)
        frames.append(
            pl.DataFrame(
                {
                    "channel": [streamer.lower()] * hours.size,
                    "timestamp": timestamps,
                    "message_count": counts,
                }
            )
        )
    return pl.concat(frames)


def goal_amount_distribution() -> pl.DataFrame:
    """Generate a right-skewed distribution of donation-goal amounts, across every category.

    A few large (joke) amounts alongside many small, realistic ones — matches
    the shape of the real data, which is why callers can't just sum this.

    Returns:
        DataFrame with columns `goal_category`, `goal_amount_eur`.
    """
    rng = np.random.default_rng(_SEED + 29)
    n = 400
    realistic = rng.pareto(a=1.5, size=int(n * 0.97)) * 300 + 10
    jokes = rng.uniform(1_000_000, 1_000_000_000, size=n - int(n * 0.97))
    amounts = np.concatenate([realistic, jokes])
    categories = rng.choice(_GOAL_CATEGORIES, size=len(amounts), p=_GOAL_CATEGORY_WEIGHTS)
    return pl.DataFrame({"goal_category": categories, "goal_amount_eur": amounts})


def donation_goal_tracker(twitch_login: str) -> pl.DataFrame:
    """Generate one streamer's donation-goal progress (start/complete/duration).

    Every goal category is included, each tracked as its own independent
    chain against the same timeseries — see
    `app.data.goal_progress.goal_progress_by_category`.

    Args:
        twitch_login: The streamer's channel/login (used only to seed variation).

    Returns:
        See `app.data.goal_progress.goal_progress_by_category`.
    """
    seed = _SEED + 30 + sum(map(ord, twitch_login))
    rng = np.random.default_rng(seed)

    hours = _hours()
    final_total = rng.uniform(5_000, 60_000)
    progress_curve = final_total * (1 - np.exp(-hours / 20))
    timeseries = pl.DataFrame(
        {"ingested_at": _timestamps(hours), "total_donation_amount_eur": progress_curve}
    )

    n_goals = rng.integers(5, 12)
    amounts = np.sort(rng.uniform(200, final_total * 1.6, size=n_goals))
    categories = rng.choice(_GOAL_CATEGORIES, size=n_goals, p=_GOAL_CATEGORY_WEIGHTS)
    goals = pl.DataFrame(
        {
            "goal_category": categories,
            "goal_name": [f"Goal #{i + 1}" for i in range(n_goals)],
            "goal_amount_eur": amounts.round(0),
        }
    )
    return goal_progress_by_category(goals, timeseries)


def donation_goal_tracker_global() -> pl.DataFrame:
    """Generate donation-goal progress across every streamer.

    Returns:
        Concatenation of `donation_goal_tracker` for every mock streamer,
        with a `twitch_login` column added.
    """
    frames = [
        donation_goal_tracker(streamer.lower()).with_columns(twitch_login=pl.lit(streamer.lower()))
        for streamer in _STREAMERS
    ]
    return pl.concat(frames)


def chat_engagement_rate() -> pl.DataFrame:
    """Generate the event-wide average chat-messages-per-100-viewers rate over time.

    Returns:
        DataFrame with columns `timestamp`, `avg_engagement_rate`.
    """
    rng = np.random.default_rng(_SEED + 31)
    hours = _hours()
    base = 8 + 3 * np.sin(hours / 12) ** 2
    return pl.DataFrame(
        {
            "timestamp": _timestamps(hours),
            "avg_engagement_rate": (base * rng.uniform(0.85, 1.15, size=hours.size)).round(2),
        }
    )


def hourly_network_hours() -> list[datetime]:
    """Generate the list of hours with a mock hourly network available.

    Returns:
        A list of hourly timestamps covering the mock event.
    """
    return _timestamps(_hours()[:12])  # a representative slice, not the whole event


def hourly_network(hour: datetime) -> pl.DataFrame:
    """Generate the chatter-community network (channel pairs) for one hour.

    Args:
        hour: The hour bucket to generate a network for (seeds variation).

    Returns:
        DataFrame with columns `channel_a`, `channel_b`, `shared_chatter_count`.
    """
    seed = _SEED + 32 + int(hour.timestamp()) % 1_000
    rng = np.random.default_rng(seed)
    channels = [s.lower() for s in _STREAMERS]
    n_edges = rng.integers(4, len(channels))
    pairs: set[tuple[str, str]] = set()
    while len(pairs) < n_edges:
        a, b = rng.choice(channels, size=2, replace=False)
        pairs.add((min(a, b), max(a, b)))
    pairs_list = list(pairs)
    return pl.DataFrame(
        {
            "channel_a": [p[0] for p in pairs_list],
            "channel_b": [p[1] for p in pairs_list],
            "shared_chatter_count": rng.integers(2, 25, size=len(pairs_list)),
        }
    )


def title_leaderboard() -> pl.DataFrame:
    """Generate stream titles ranked by chat messages and donations.

    Returns:
        DataFrame with columns `title`, `category`, `channels`,
        `message_count`, `donations_eur`.
    """
    rng = np.random.default_rng(_SEED + 33)
    titles = [
        "ZEvent J-1 : on prépare le setup !",
        "Marathon caritatif, 48h non-stop !",
        "Objectif final atteint ?! Sprint de fin",
        "Blabla + dons en direct",
        "Nuit blanche pour la bonne cause",
        "On tente le record de dons !",
        "Retour de la pause, on repart fort",
        "Chill stream, discussion et dons",
    ]
    n = len(titles)
    message_count = rng.integers(200, 8_000, size=n)
    return pl.DataFrame(
        {
            "title": titles,
            "category": rng.choice(_CATEGORIES, size=n),
            "channels": rng.integers(1, 4, size=n),
            "message_count": message_count,
            "donations_eur": (message_count * rng.uniform(0.5, 4.0, size=n)).round(2),
        }
    ).sort("message_count", descending=True)


def chatter_breakdown() -> pl.DataFrame:
    """Generate per-chatter loyalty, activity and bot-signal figures.

    `first_message_at`/`last_message_at`/`lifespan_hours`/
    `avg_messages_per_channel` mirror `marts.mart_chatters__breadth_depth_lifespan`
    — mock data needs its own activity window so `MockDataSource.chatter_breakdown`
    can filter by the same first/last-message overlap the real query does.

    Returns:
        DataFrame with columns `chatter_id`, `chatter`, `distinct_channel_count`,
        `total_message_count`, `top_channel_share`, `chatter_profile`,
        `account_created_at`, `has_long_digit_suffix`,
        `gap_coefficient_of_variation`, `account_age_bucket`,
        `first_message_at`, `last_message_at`, `lifespan_hours`,
        `avg_messages_per_channel`.
    """
    rng = np.random.default_rng(_SEED + 40)
    n = 400
    profiles = rng.choice(_CHATTER_PROFILES, size=n, p=[0.93, 0.04, 0.02, 0.01])
    distinct_channels = np.where(profiles == "sedentaire", 1, rng.integers(2, 6, size=n))
    total_messages = rng.lognormal(mean=3.2, sigma=1.1, size=n).astype(int) + 1
    top_channel_share = np.where(distinct_channels == 1, 1.0, rng.uniform(0.3, 0.9, size=n)).round(
        3
    )
    age_buckets = rng.choice(_ACCOUNT_AGE_BUCKETS, size=n, p=[0.01, 0.05, 0.1, 0.44, 0.4])
    account_created = [_EVENT_START - timedelta(days=int(rng.uniform(1, 3650))) for _ in range(n)]
    has_long_digit_suffix = rng.uniform(size=n) < 0.08
    gap_cv = rng.uniform(0.3, 2.5, size=n).round(4)
    first_offset_hours = rng.uniform(0, _EVENT_DURATION_HOURS * 0.8, size=n)
    lifespan_hours = rng.uniform(0.5, _EVENT_DURATION_HOURS * 0.3, size=n)
    first_message_at = [_EVENT_START + timedelta(hours=float(h)) for h in first_offset_hours]
    last_message_at = [
        start + timedelta(hours=float(span))
        for start, span in zip(first_message_at, lifespan_hours, strict=True)
    ]
    return pl.DataFrame(
        {
            "chatter_id": [str(rng.integers(10_000_000, 999_999_999)) for _ in range(n)],
            "chatter": [f"Chatter{i}" for i in range(1, n + 1)],
            "distinct_channel_count": distinct_channels,
            "total_message_count": total_messages,
            "top_channel_share": top_channel_share,
            "chatter_profile": profiles,
            "account_created_at": account_created,
            "has_long_digit_suffix": has_long_digit_suffix,
            "gap_coefficient_of_variation": gap_cv,
            "account_age_bucket": age_buckets,
            "first_message_at": first_message_at,
            "last_message_at": last_message_at,
            "lifespan_hours": lifespan_hours.round(2),
            "avg_messages_per_channel": (total_messages / distinct_channels).round(1),
        }
    ).sort("total_message_count", descending=True)


def chatter_directory() -> pl.DataFrame:
    """Generate the chatter-picker population for the global chatter filter.

    Reuses `chatter_breakdown()` (already the full 400-chatter mock
    population, sorted by activity) rather than generating a separate
    population — the global filter just needs `chatter_id`/`chatter`/
    `total_message_count`, all already there.

    Returns:
        DataFrame with columns `chatter_id`, `chatter`, `total_message_count`.
    """
    return chatter_breakdown().select("chatter_id", "chatter", "total_message_count")


def chatter_channel_breakdown(chatter_id: str) -> pl.DataFrame:
    """Generate one chatter's per-channel message activity.

    Args:
        chatter_id: The chatter's id to look up — seeds the RNG so the same
            id always returns the same shape (same pattern as
            `streamer_diurnal_profile`).

    Returns:
        DataFrame with columns `channel`, `message_count`, `first_message_at`,
        `last_message_at`, `active_hours`.
    """
    seed = _SEED + sum(map(ord, chatter_id))
    rng = np.random.default_rng(seed)
    n_channels = int(rng.integers(1, 4))
    channels = rng.choice([s.lower() for s in _STREAMERS], size=n_channels, replace=False)
    message_count = np.sort(rng.integers(5, 300, size=n_channels))[::-1]
    starts = [_EVENT_START + timedelta(hours=float(rng.uniform(0, 40))) for _ in range(n_channels)]
    active_hours = rng.integers(1, 20, size=n_channels)
    return pl.DataFrame(
        {
            "channel": channels,
            "message_count": message_count,
            "first_message_at": starts,
            "last_message_at": [
                s + timedelta(hours=float(h)) for s, h in zip(starts, active_hours, strict=False)
            ],
            "active_hours": active_hours,
        }
    ).sort("message_count", descending=True)


def channel_chatter_breakdown(channel: str) -> pl.DataFrame:
    """Generate every chatter active in one channel, with badge mix and emote usage.

    Mirrors `stg.stg_bronze__live_chat` badge-tier classification (see
    `PostgresDataSource.channel_chatter_breakdown`): each chatter's messages
    split into exactly one of moderator / vip / subscriber / plain-viewer,
    matching Twitch's own badge display precedence, so the four counts
    always sum to `message_count`.

    Args:
        channel: The channel/login to look up — seeds the RNG so the same
            channel always returns the same shape.

    Returns:
        DataFrame with columns `chatter_id`, `chatter`, `message_count`,
        `first_message_at`, `last_message_at`, `moderator_message_count`,
        `vip_message_count`, `subscriber_message_count`,
        `plain_viewer_message_count`, `emote_usage_count`.
    """
    seed = _SEED + 80 + sum(map(ord, channel))
    rng = np.random.default_rng(seed)
    n = int(rng.integers(40, 160))

    message_count = rng.lognormal(mean=2.5, sigma=1.2, size=n).astype(int) + 1
    offsets = np.sort(rng.uniform(0, _EVENT_DURATION_HOURS * 0.9, size=n))
    active_hours = rng.uniform(0.1, 6.0, size=n)
    first_message_at = [_EVENT_START + timedelta(hours=float(h)) for h in offsets]
    last_message_at = [
        start + timedelta(hours=float(span))
        for start, span in zip(first_message_at, active_hours, strict=True)
    ]

    # Most chatters are plain viewers; a handful are subscribers, fewer still
    # VIP or moderator — same skew as the real per-channel badge mix.
    tier = rng.choice(
        ["moderator", "vip", "subscriber", "plain_viewer"], size=n, p=[0.03, 0.04, 0.23, 0.70]
    )
    moderator = np.where(tier == "moderator", message_count, 0)
    vip = np.where(tier == "vip", message_count, 0)
    subscriber = np.where(tier == "subscriber", message_count, 0)
    plain_viewer = np.where(tier == "plain_viewer", message_count, 0)

    return pl.DataFrame(
        {
            "chatter_id": [str(rng.integers(10_000_000, 999_999_999)) for _ in range(n)],
            "chatter": [f"Chatter{i}" for i in range(1, n + 1)],
            "message_count": message_count,
            "first_message_at": first_message_at,
            "last_message_at": last_message_at,
            "moderator_message_count": moderator,
            "vip_message_count": vip,
            "subscriber_message_count": subscriber,
            "plain_viewer_message_count": plain_viewer,
            "emote_usage_count": (message_count * rng.uniform(0, 1.5, size=n)).astype(int),
        }
    ).sort("message_count", descending=True)


def stream_activity_log(channel: str) -> pl.DataFrame:
    """Generate one streamer's title/category timeline, segmented by change.

    Args:
        channel: The streamer's channel/login (used only to seed variation).

    Returns:
        DataFrame with columns `title`, `category`, `started_at`, `ended_at`, `snapshot_count`.
    """
    seed = _SEED + sum(map(ord, channel)) + 50
    rng = np.random.default_rng(seed)
    n_segments = int(rng.integers(3, 7))
    categories = rng.choice(_CATEGORIES, size=n_segments, replace=False)
    titles = [f"{channel} plays {cat}" for cat in categories]
    boundaries = sorted(rng.uniform(1, _EVENT_DURATION_HOURS - 1, size=n_segments - 1))
    starts_h = [0.0, *boundaries]
    ends_h = [*boundaries, float(_EVENT_DURATION_HOURS)]
    return pl.DataFrame(
        {
            "title": titles,
            "category": categories,
            "started_at": [_EVENT_START + timedelta(hours=h) for h in starts_h],
            "ended_at": [_EVENT_START + timedelta(hours=h) for h in ends_h],
            "snapshot_count": rng.integers(20, 400, size=n_segments),
        }
    )


def donations_by_category() -> pl.DataFrame:
    """Generate donations attributed to the Twitch category being played at the time.

    Returns:
        DataFrame with columns `category`, `donations_eur`, `channels`.
    """
    rng = np.random.default_rng(_SEED + 51)
    n = len(_CATEGORIES)
    return pl.DataFrame(
        {
            "category": _CATEGORIES,
            "donations_eur": (rng.pareto(a=2.0, size=n) * 5_000 + 500).round(2),
            "channels": rng.integers(1, 5, size=n),
        }
    ).sort("donations_eur", descending=True)


def category_change_impact() -> pl.DataFrame:
    """Generate category switches ranked by viewer-count impact.

    Mirrors `marts.mart_streams__category_timeline`.

    Returns:
        DataFrame with columns `channel`, `changed_at`, `prev_category`,
        `new_category`, `viewer_count_at_change`, `avg_viewer_count_hour_after`.
    """
    rng = np.random.default_rng(_SEED + 60)
    n = 15
    offsets = rng.uniform(1, _EVENT_DURATION_HOURS - 1, size=n)
    viewer_before = rng.integers(1_000, 30_000, size=n)
    viewer_after = viewer_before * rng.uniform(0.5, 2.0, size=n)
    return pl.DataFrame(
        {
            "channel": rng.choice([s.lower() for s in _STREAMERS], size=n),
            "changed_at": [_EVENT_START + timedelta(hours=float(h)) for h in offsets],
            "prev_category": rng.choice(_CATEGORIES, size=n),
            "new_category": rng.choice(_CATEGORIES, size=n),
            "viewer_count_at_change": viewer_before,
            "avg_viewer_count_hour_after": viewer_after.round(0),
        }
    )


def chatter_migrations() -> pl.DataFrame:
    """Generate channel-to-channel chatter hop counts, event-wide.

    Mirrors `marts.mart_community__chatter_migrations`.

    Returns:
        DataFrame with columns `from_channel`, `to_channel`, `hop_count`,
        `distinct_chatters_hopping`, `avg_gap_seconds`.
    """
    rng = np.random.default_rng(_SEED + 61)
    channels = [s.lower() for s in _STREAMERS]
    all_pairs = [(a, b) for a in channels for b in channels if a != b]
    chosen = [all_pairs[i] for i in rng.permutation(len(all_pairs))[:20]]
    hop_count = rng.integers(3, 80, size=len(chosen))
    return pl.DataFrame(
        {
            "from_channel": [p[0] for p in chosen],
            "to_channel": [p[1] for p in chosen],
            "hop_count": hop_count,
            "distinct_chatters_hopping": (
                hop_count * rng.uniform(0.6, 0.9, size=len(chosen))
            ).astype(int),
            "avg_gap_seconds": rng.uniform(60, 3_600, size=len(chosen)).round(1),
        }
    ).sort("hop_count", descending=True)


def donation_spike_moments() -> pl.DataFrame:
    """Generate standout single-donation moments, event-wide.

    Mirrors `marts.mart_donations__spike_moments`.

    Returns:
        DataFrame with columns `twitch_login`, `display_name`, `ingested_at`,
        `donation_delta_eur`, `title`, `category`, `chat_messages_that_hour`.
    """
    rng = np.random.default_rng(_SEED + 62)
    n = 10
    idx = rng.integers(0, len(_STREAMERS), size=n)
    offsets = rng.uniform(0, _EVENT_DURATION_HOURS, size=n)
    titles = [
        "ZEvent J-1 : on prépare le setup !",
        "Objectif final atteint ?! Sprint de fin",
        "On tente le record de dons !",
    ]
    return pl.DataFrame(
        {
            "twitch_login": [_STREAMERS[i].lower() for i in idx],
            "display_name": [_STREAMERS[i] for i in idx],
            "ingested_at": [_EVENT_START + timedelta(hours=float(h)) for h in offsets],
            "donation_delta_eur": (rng.pareto(a=1.5, size=n) * 500 + 200).round(2),
            "title": rng.choice(titles, size=n),
            "category": rng.choice(_CATEGORIES, size=n),
            "chat_messages_that_hour": rng.integers(100, 3_000, size=n),
        }
    ).sort("donation_delta_eur", descending=True)


def goal_ambition_vs_reality() -> pl.DataFrame:
    """Generate per-streamer donation-goal coverage (set vs. actually raised).

    Mirrors `marts.mart_donations__goal_ambition_vs_reality`.

    Returns:
        DataFrame with columns `twitch_login`, `total_goal_amount_eur_for_streamer`,
        `latest_donation_amount_eur`, `surplus_eur`, `pct_of_goals_covered`.
    """
    rng = np.random.default_rng(_SEED + 63)
    sb = streamer_breakdown()
    n = len(sb)
    donations = sb["amount_eur"].to_numpy()
    # Some streamers set jokingly-huge goals (under-covered), some set modest
    # ones already blown past — same "goals are often exaggerated" theme the
    # rest of the Donation Goals page already leans on.
    goal_totals = donations * rng.uniform(0.3, 3.0, size=n)
    return pl.DataFrame(
        {
            "twitch_login": sb["channel"].to_list(),
            "total_goal_amount_eur_for_streamer": goal_totals.round(2),
            "latest_donation_amount_eur": donations.round(2),
            "surplus_eur": (donations - goal_totals).round(2),
            "pct_of_goals_covered": np.clip(donations / goal_totals * 100, 0, 999).round(1),
        }
    ).sort("pct_of_goals_covered", descending=False)


def event_daily_rollup() -> pl.DataFrame:
    """Generate day-bucketed event-wide totals.

    Mirrors `marts.mart_event__daily_rollup`.

    Returns:
        DataFrame with columns `day_bucket`, `message_count`, `active_channels`,
        `donation_delta_eur`, `total_donation_amount_eur_end_of_day`,
        `avg_total_viewer_count`.
    """
    rng = np.random.default_rng(_SEED + 64)
    n_days = int(_EVENT_DURATION_HOURS // 24) + 2
    day_start = _EVENT_START.replace(hour=0, minute=0, second=0, microsecond=0)
    donation_deltas = rng.uniform(5_000, 40_000, size=n_days)
    return pl.DataFrame(
        {
            "day_bucket": [day_start + timedelta(days=i) for i in range(n_days)],
            "message_count": rng.integers(50_000, 300_000, size=n_days),
            "active_channels": rng.integers(20, len(_STREAMERS) * 8, size=n_days),
            "donation_delta_eur": donation_deltas.round(2),
            "total_donation_amount_eur_end_of_day": np.cumsum(donation_deltas).round(2),
            "avg_total_viewer_count": rng.uniform(15_000, 60_000, size=n_days).round(0),
        }
    )


def streamer_night_shift(channel: str) -> pl.DataFrame:
    """Generate one streamer's donation efficiency by hour of day.

    Mirrors `marts.mart_streamers__night_shift`.

    Args:
        channel: The streamer's channel/login (used only to seed variation).

    Returns:
        DataFrame with columns `hour_of_day`, `donation_delta_eur`,
        `avg_viewer_count`, `donation_eur_per_viewer`, `is_overnight`.
    """
    seed = _SEED + 65 + sum(map(ord, channel))
    rng = np.random.default_rng(seed)
    hour_of_day = np.arange(24)
    is_overnight = (hour_of_day >= 1) & (hour_of_day <= 7)
    avg_viewers = np.clip(3_000 + 2_000 * np.sin((hour_of_day - 14) / 24 * 2 * np.pi), 200, None)
    donation_delta = avg_viewers * rng.uniform(0.05, 0.3, size=24)
    return pl.DataFrame(
        {
            "hour_of_day": hour_of_day,
            "donation_delta_eur": donation_delta.round(2),
            "avg_viewer_count": avg_viewers.round(0),
            "donation_eur_per_viewer": (donation_delta / avg_viewers).round(4),
            "is_overnight": is_overnight,
        }
    )


def chat_spikes() -> pl.DataFrame:
    """Generate the biggest per-channel message-volume anomalies, event-wide.

    Mirrors `marts.mart_chat__spikes`.

    Returns:
        DataFrame with columns `channel`, `hour_bucket`, `message_count`,
        `unique_chatter_count`, `channel_avg_message_count`,
        `channel_stddev_message_count`, `message_count_zscore`.
    """
    rng = np.random.default_rng(_SEED + 66)
    n = 12
    idx = rng.integers(0, len(_STREAMERS), size=n)
    offsets = rng.integers(0, _EVENT_DURATION_HOURS, size=n)
    channel_avg = rng.uniform(80, 300, size=n)
    channel_std = channel_avg * rng.uniform(0.15, 0.35, size=n)
    zscore = rng.uniform(2.0, 5.0, size=n)
    message_count = channel_avg + zscore * channel_std
    return pl.DataFrame(
        {
            "channel": [_STREAMERS[i].lower() for i in idx],
            "hour_bucket": [_EVENT_START + timedelta(hours=int(h)) for h in offsets],
            "message_count": message_count.round(0).astype(int),
            "unique_chatter_count": (message_count * rng.uniform(0.2, 0.5, size=n)).astype(int),
            "channel_avg_message_count": channel_avg.round(1),
            "channel_stddev_message_count": channel_std.round(1),
            "message_count_zscore": zscore.round(2),
        }
    ).sort("message_count_zscore", descending=True)


def new_chatters_per_channel() -> pl.DataFrame:
    """Generate new-chatter counts per channel, per day.

    Mirrors `marts.mart_chat__new_chatters_per_channel`.

    Returns:
        DataFrame with columns `channel`, `day_bucket`, `new_chatters_to_channel`.
    """
    rng = np.random.default_rng(_SEED + 67)
    n_days = int(_EVENT_DURATION_HOURS // 24) + 2
    day_start = _EVENT_START.replace(hour=0, minute=0, second=0, microsecond=0)
    day_starts = [day_start + timedelta(days=i) for i in range(n_days)]
    rows = [
        {
            "channel": channel,
            "day_bucket": day,
            "new_chatters_to_channel": int(rng.integers(10, 400)),
        }
        for channel in (s.lower() for s in _STREAMERS)
        for day in day_starts
    ]
    return pl.DataFrame(rows)


_EMOTE_CATALOG = [
    ("Kappa", "25"),
    ("4Head", "354"),
    ("DansGame", "33"),
    ("SwiftRage", "34"),
    ("ResidentSleeper", "245"),
    ("NotLikeThis", "58765"),
    ("ANELE", "43"),
    ("BloodTrail", "76"),
    ("PJSalt", "36"),
    ("Kreygasm", "41"),
]


def search_emote_catalog(query: str) -> pl.DataFrame:
    """Search the (small, mock) emote catalog by code substring.

    Mirrors `stg.stg_bronze__emote_catalog`.

    Args:
        query: Substring to match against emote codes (case-insensitive).

    Returns:
        DataFrame with columns `service`, `emote_id`, `emote_code`.
    """
    query_lower = query.lower()
    matches = [(code, emote_id) for code, emote_id in _EMOTE_CATALOG if query_lower in code.lower()]
    return pl.DataFrame(
        {
            "service": ["twitch"] * len(matches),
            "emote_id": [emote_id for _, emote_id in matches],
            "emote_code": [code for code, _ in matches],
        }
    )


def emote_usage_search(emote_id: str, start: datetime, end: datetime) -> pl.DataFrame:
    """Generate synthetic chat messages using a given emote within `[start, end]`.

    Mirrors `stg.stg_bronze__live_chat` filtered by `jsonb_exists(emotes, emote_id)`.

    Args:
        emote_id: The emote's catalog id to search for.
        start: Start of the window to narrow to.
        end: End of the window to narrow to.

    Returns:
        DataFrame with columns `chatter`, `channel`, `message_text`, `message_sent_at`.
    """
    schema = {
        "chatter": pl.Utf8,
        "channel": pl.Utf8,
        "message_text": pl.Utf8,
        "message_sent_at": pl.Datetime("us"),
    }
    span_hours = (end - start).total_seconds() / 3600
    if span_hours <= 0:
        return pl.DataFrame(schema=schema)

    seed = _SEED + 70 + sum(map(ord, emote_id))
    rng = np.random.default_rng(seed)
    code = next((c for c, i in _EMOTE_CATALOG if i == emote_id), emote_id)
    n = int(rng.integers(5, 40))
    offsets = rng.uniform(0, span_hours, size=n)
    templates = ["{code}", "lol {code} {code}", "{code} incroyable", "on est pas bien la {code}"]
    return pl.DataFrame(
        {
            "chatter": [f"Chatter{i}" for i in rng.integers(1, 400, size=n)],
            "channel": rng.choice([s.lower() for s in _STREAMERS], size=n),
            "message_text": [str(rng.choice(templates)).format(code=code) for _ in range(n)],
            "message_sent_at": [start + timedelta(hours=float(h)) for h in offsets],
        },
        schema=schema,
    ).sort("message_sent_at", descending=True)


_MESSAGE_TEMPLATES = [
    "hype hype hype",
    "on est trop bien la",
    "gg les gars",
    "quelqu'un a le lien du don ?",
    "LUL incroyable ce moment",
    "on va y arriver, courage !",
    "PogChamp",
    "merci pour le stream <3",
    "c'est reparti pour un tour",
    "MODCHECK",
    "nice run",
    ":)",
    # A couple of hostile-flavored templates so `chat_toxicity_examples`
    # (which filters this same pool for `HOSTILE_WORDS`) has something to
    # show in mock mode too, not just against real data.
    "ta gueule mdr",
    "quel idiot celui-la",
]


def chat_message_search(
    start: datetime,
    end: datetime,
    *,
    channel: str | None = None,
    chatter_query: str | None = None,
    text_query: str | None = None,
    limit: int = 500,
) -> pl.DataFrame:
    """Generate synthetic individual chat messages within `[start, end]`.

    Mirrors `stg.stg_bronze__live_chat`, filtered the same way
    `PostgresDataSource.chat_message_search` filters it in SQL.

    Args:
        start: Start of the window to narrow to.
        end: End of the window to narrow to.
        channel: If given, only messages sent in this channel.
        chatter_query: If given, only messages from a chatter whose name
            contains this (case-insensitive substring).
        text_query: If given, only messages whose text contains this
            (case-insensitive substring).
        limit: Maximum number of messages to return.

    Returns:
        DataFrame with columns `message_sent_at`, `channel`, `chatter_id`,
        `chatter`, `message_text`, `badge`, `has_long_digit_suffix` (mirrors
        `PostgresDataSource.chat_message_search`'s bot-signal join, so
        `bot_filter_expr` works identically here).
    """
    schema = {
        "message_sent_at": pl.Datetime("us"),
        "channel": pl.Utf8,
        "chatter_id": pl.Utf8,
        "chatter": pl.Utf8,
        "message_text": pl.Utf8,
        "badge": pl.Utf8,
        "has_long_digit_suffix": pl.Boolean,
    }
    span_hours = (end - start).total_seconds() / 3600
    if span_hours <= 0:
        return pl.DataFrame(schema=schema)

    # Seeded on the window and every filter, not just `channel` — otherwise
    # two different searches over the same window (e.g. two chatter queries)
    # would draw the exact same underlying pool and just differ in which
    # rows survive the filter, rather than each feeling like its own search.
    seed_text = (
        f"{start.isoformat()}{end.isoformat()}{channel or ''}{chatter_query or ''}"
        f"{text_query or ''}"
    )
    rng = np.random.default_rng(_SEED + 90 + sum(map(ord, seed_text)))
    channels = [channel] if channel else [s.lower() for s in _STREAMERS]
    n = max(int(span_hours * 40), 20)
    offsets = rng.uniform(0, span_hours, size=n)
    # Same index feeds both id and display name so a given synthetic chatter
    # keeps one consistent (chatter_id, chatter) pair, same as the real
    # warehouse — needed for `anonymize_chatters` to pseudonymize by id.
    chatter_indices = rng.integers(1, 2000, size=n)
    df = pl.DataFrame(
        {
            "message_sent_at": [start + timedelta(hours=float(h)) for h in offsets],
            "channel": rng.choice(channels, size=n),
            "chatter_id": [f"cid{i}" for i in chatter_indices],
            "chatter": [f"Chatter{i}" for i in chatter_indices],
            "message_text": rng.choice(_MESSAGE_TEMPLATES, size=n),
            "badge": rng.choice(
                ["moderator", "vip", "subscriber", "plain_viewer"],
                size=n,
                p=[0.03, 0.02, 0.15, 0.80],
            ),
            # Same 5% rate as `top_chatters`/`chatter_breakdown`'s mock bot signal.
            "has_long_digit_suffix": rng.uniform(size=n) < 0.05,
        },
        schema=schema,
    )
    if chatter_query:
        df = df.filter(
            pl.col("chatter").str.to_lowercase().str.contains(chatter_query.lower(), literal=True)
        )
    if text_query:
        df = df.filter(
            pl.col("message_text").str.to_lowercase().str.contains(text_query.lower(), literal=True)
        )
    return df.sort("message_sent_at", descending=True).head(limit)


def category_popularity_timeseries() -> pl.DataFrame:
    """Generate hourly channel-count-playing per Twitch category.

    Mirrors `marts.mart_streams__category_cooccurrence`, which
    `category_breakdown()` also reads but collapses down to an event-wide
    total — this keeps the hour-by-hour dimension, for a "what was trending
    when" view rather than just "what was trending overall."

    Returns:
        DataFrame with columns `timestamp`, `category`, `channel_count_playing`.
    """
    rng = np.random.default_rng(_SEED + 70)
    hours = _hours()
    timestamps = _timestamps(hours)
    frames = []
    for category in _CATEGORIES:
        base = rng.uniform(0.5, 4.0)
        counts = np.maximum((base * rng.uniform(0.2, 1.8, size=hours.size)).round().astype(int), 0)
        frames.append(
            pl.DataFrame(
                {
                    "timestamp": timestamps,
                    "category": [category] * hours.size,
                    "channel_count_playing": counts,
                }
            )
        )
    return pl.concat(frames).filter(pl.col("channel_count_playing") > 0)


def channel_viewership_leaderboard_timeseries(top_n: int) -> pl.DataFrame:
    """Generate the top-N-by-viewers channel leaderboard, hour by hour.

    Mirrors `marts.mart_streams__viewership_timeseries`'s precomputed
    `viewer_rank_at_hour` — computed against every channel, then narrowed to
    the `top_n` channels by *overall average* viewers across the whole
    window, with every hour of their own history kept (not just the hours
    they happened to be near the very top), so a channel's line stays
    continuous instead of collapsing to isolated points.

    Returns:
        DataFrame with columns `timestamp`, `channel`, `avg_viewer_count`,
        `viewer_rank_at_hour`.
    """
    rng = np.random.default_rng(_SEED + 71)
    hours = _hours()
    timestamps = _timestamps(hours)
    channels = [s.lower() for s in _STREAMERS]
    base_popularity = dict(zip(channels, rng.uniform(500, 20_000, size=len(channels)), strict=True))
    rows = []
    for ts in timestamps:
        counts = {c: max(0.0, base_popularity[c] * rng.uniform(0.5, 1.5)) for c in channels}
        ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
        rows.extend(
            {
                "timestamp": ts,
                "channel": channel,
                "avg_viewer_count": round(count, 1),
                "viewer_rank_at_hour": rank,
            }
            for rank, (channel, count) in enumerate(ranked, start=1)
        )
    df = pl.DataFrame(rows)
    top_channels = (
        df.group_by("channel")
        .agg(pl.col("avg_viewer_count").mean().alias("overall_avg_viewers"))
        .sort("overall_avg_viewers", descending=True)
        .head(top_n)["channel"]
        .to_list()
    )
    return df.filter(pl.col("channel").is_in(top_channels))


def channel_messages_leaderboard_timeseries(top_n: int) -> pl.DataFrame:
    """Generate the top-N-by-messages channel leaderboard, hour by hour.

    Same "rank against everyone, keep the overall top N's full history"
    shape as `channel_viewership_leaderboard_timeseries` (see its
    docstring), ranking by chat message volume instead of average viewers —
    channels here are picked by *summed* message count across the window.

    Returns:
        DataFrame with columns `timestamp`, `channel`, `message_count`,
        `message_rank_at_hour`.
    """
    rng = np.random.default_rng(_SEED + 72)
    hours = _hours()
    timestamps = _timestamps(hours)
    channels = [s.lower() for s in _STREAMERS]
    base_activity = dict(zip(channels, rng.uniform(50, 400, size=len(channels)), strict=True))
    night_dip = np.where((hours % 24 >= 2) & (hours % 24 <= 8), 0.3, 1.0)
    rows = []
    for i, ts in enumerate(timestamps):
        counts = {
            c: max(0.0, base_activity[c] * night_dip[i] * rng.uniform(0.6, 1.4)) for c in channels
        }
        ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
        rows.extend(
            {
                "timestamp": ts,
                "channel": channel,
                "message_count": round(count),
                "message_rank_at_hour": rank,
            }
            for rank, (channel, count) in enumerate(ranked, start=1)
        )
    df = pl.DataFrame(rows)
    top_channels = (
        df.group_by("channel")
        .agg(pl.col("message_count").sum().alias("total_messages"))
        .sort("total_messages", descending=True)
        .head(top_n)["channel"]
        .to_list()
    )
    return df.filter(pl.col("channel").is_in(top_channels))


def channel_donations_leaderboard_timeseries(top_n: int) -> pl.DataFrame:
    """Generate the top-N-by-cumulative-donations channel leaderboard, hour by hour.

    Same "rank against everyone, keep the overall top N's full history"
    shape as `channel_viewership_leaderboard_timeseries` (see its
    docstring), ranking by each streamer's own running donation total
    instead of viewers — channels here are picked by their own highest
    cumulative total reached anywhere in the window, which (since a running
    total only ever grows) is just each streamer's final value.

    Returns:
        DataFrame with columns `timestamp`, `channel`, `amount_eur`,
        `donation_rank_at_hour`.
    """
    rng = np.random.default_rng(_SEED + 73)
    hours = _hours()
    timestamps = _timestamps(hours)
    channels = [s.lower() for s in _STREAMERS]
    night_dip = np.where((hours % 24 >= 2) & (hours % 24 <= 8), 0.4, 1.0)
    final_surge = np.where(hours >= _EVENT_DURATION_HOURS - 4, 2.5, 1.0)
    # Each streamer's own hourly pace, Pareto-weighted like `streamer_breakdown`'s
    # final totals — a handful of streamers dominate the top of the leaderboard
    # rather than every channel raising a similar amount.
    weights = dict(zip(channels, rng.pareto(a=2.0, size=len(channels)) * 300 + 50, strict=True))
    cumulative = dict.fromkeys(channels, 0.0)
    rows = []
    for i, ts in enumerate(timestamps):
        for c in channels:
            hourly = weights[c] * night_dip[i] * final_surge[i] * rng.uniform(0.5, 1.5)
            cumulative[c] += hourly
        ranked = sorted(cumulative.items(), key=lambda kv: kv[1], reverse=True)
        rows.extend(
            {
                "timestamp": ts,
                "channel": channel,
                "amount_eur": round(amount, 2),
                "donation_rank_at_hour": rank,
            }
            for rank, (channel, amount) in enumerate(ranked, start=1)
        )
    df = pl.DataFrame(rows)
    top_channels = (
        df.group_by("channel")
        .agg(pl.col("amount_eur").max().alias("overall_amount_eur"))
        .sort("overall_amount_eur", descending=True)
        .head(top_n)["channel"]
        .to_list()
    )
    return df.filter(pl.col("channel").is_in(top_channels))


def chat_hype_components_timeseries() -> pl.DataFrame:
    """Generate every channel-hour's raw, unweighted hype components.

    See `PostgresDataSource.chat_hype_components_timeseries` — for the Chat
    Intelligence page's weight-tuning sliders, so mock mode needs the three
    raw rates (not a pre-weighted score) for every channel, not just a
    top-N leaderboard slice.

    Returns:
        DataFrame with columns `channel`, `timestamp`, `message_count`,
        `punct_rate`, `caps_rate`, `emote_rate`.
    """
    rng = np.random.default_rng(_SEED + 78)
    hours = _hours()
    timestamps = _timestamps(hours)
    channels = [s.lower() for s in _STREAMERS]
    rows = [
        {
            "channel": channel,
            "timestamp": ts,
            "message_count": int(rng.integers(20, 500)),
            "punct_rate": round(float(rng.uniform(0.0, 0.15)), 4),
            "caps_rate": round(float(rng.uniform(0.0, 0.35)), 4),
            "emote_rate": round(float(rng.uniform(0.0, 0.2)), 4),
        }
        for ts in timestamps
        for channel in channels
    ]
    return pl.DataFrame(rows)


def channel_sentiment_leaderboard_timeseries(top_n: int) -> pl.DataFrame:
    """Generate the top-N-most-positive channel leaderboard, hour by hour.

    Same "rank against everyone, keep the overall top N's full history"
    shape as `channel_viewership_leaderboard_timeseries` (see its
    docstring) — channels here are picked by their average sentiment score
    (mostly positive, matching a charity-stream chat's real overall mood,
    with per-channel variance and rare negative dips), not raw activity.

    Returns:
        DataFrame with columns `timestamp`, `channel`, `sentiment_score`,
        `sentiment_rank_at_hour`.
    """
    rng = np.random.default_rng(_SEED + 75)
    hours = _hours()
    timestamps = _timestamps(hours)
    channels = [s.lower() for s in _STREAMERS]
    baseline = dict(zip(channels, rng.uniform(-5, 15, size=len(channels)), strict=True))
    rows = []
    for ts in timestamps:
        scores = {c: baseline[c] + rng.normal(0, 8) for c in channels}
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        rows.extend(
            {
                "timestamp": ts,
                "channel": channel,
                "sentiment_score": round(score, 2),
                "sentiment_rank_at_hour": rank,
            }
            for rank, (channel, score) in enumerate(ranked, start=1)
        )
    df = pl.DataFrame(rows)
    top_channels = (
        df.group_by("channel")
        .agg(pl.col("sentiment_score").mean().alias("overall_sentiment"))
        .sort("overall_sentiment", descending=True)
        .head(top_n)["channel"]
        .to_list()
    )
    return df.filter(pl.col("channel").is_in(top_channels))


def channel_toxicity_leaderboard_timeseries(top_n: int) -> pl.DataFrame:
    """Generate the top-N-most-hostile channel leaderboard, hour by hour.

    Same "rank against everyone, keep the overall top N's full history"
    shape as `channel_viewership_leaderboard_timeseries` (see its
    docstring). Deliberately channel-level, not per-chatter — same
    reasoning as `PostgresDataSource.channel_toxicity_leaderboard_timeseries`.

    Returns:
        DataFrame with columns `timestamp`, `channel`, `toxicity_score`,
        `toxicity_rank_at_hour`.
    """
    rng = np.random.default_rng(_SEED + 76)
    hours = _hours()
    timestamps = _timestamps(hours)
    channels = [s.lower() for s in _STREAMERS]
    baseline = dict(zip(channels, rng.uniform(0.2, 3.0, size=len(channels)), strict=True))
    rows = []
    for ts in timestamps:
        scores = {
            c: max(0.0, baseline[c] * rng.uniform(0.3, 2.0))
            # Rare flare-ups (a heated moment in chat) rather than every
            # channel drifting as a flat random walk around its baseline.
            + (rng.uniform(3, 8) if rng.uniform() < 0.03 else 0.0)
            for c in channels
        }
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        rows.extend(
            {
                "timestamp": ts,
                "channel": channel,
                "toxicity_score": round(score, 2),
                "toxicity_rank_at_hour": rank,
            }
            for rank, (channel, score) in enumerate(ranked, start=1)
        )
    df = pl.DataFrame(rows)
    top_channels = (
        df.group_by("channel")
        .agg(pl.col("toxicity_score").mean().alias("overall_toxicity"))
        .sort("overall_toxicity", descending=True)
        .head(top_n)["channel"]
        .to_list()
    )
    return df.filter(pl.col("channel").is_in(top_channels))


def chat_toxicity_examples(start: datetime, end: datetime, limit: int) -> pl.DataFrame:
    """Generate a sample of messages the toxicity heuristic flagged as hostile.

    Filters `chat_message_search`'s messages with the same `HOSTILE_WORDS`
    check the real query uses (`contains_any`), so mock mode demonstrates
    the same "check the heuristic's work" feature — see
    `PostgresDataSource.chat_toxicity_examples`.

    Returns:
        DataFrame with columns `channel`, `chatter`, `message_sent_at`,
        `message_text`.
    """
    messages = chat_message_search(start, end, limit=50_000)
    return (
        messages.filter(
            pl.col("message_text").map_elements(
                lambda text: contains_any(text, HOSTILE_WORDS), return_dtype=pl.Boolean
            )
        )
        .select("channel", "chatter", "message_sent_at", "message_text")
        .head(limit)
    )


def chat_message_sample(start: datetime, end: datetime, limit: int) -> pl.DataFrame:
    """Generate a random sample of raw messages, event-wide, for the Chat ML Lab page.

    Reuses `chat_message_search` across every channel — see
    `PostgresDataSource.chat_message_sample`.

    Returns:
        DataFrame with columns `channel`, `chatter`, `message_sent_at`,
        `message_text`.
    """
    return chat_message_search(start, end, limit=limit).select(
        "channel", "chatter", "message_sent_at", "message_text"
    )


def chat_mood_timeseries() -> pl.DataFrame:
    """Generate event-wide chat hype/sentiment, hour by hour, across every channel.

    Same shape as `PostgresDataSource.chat_mood_timeseries` — one hype and
    one sentiment figure per hour, no per-channel dimension. Scaled to match
    the real event's observed range (a handful of points, not the 0-100
    theoretical max), since it averages in every quiet channel too, unlike
    the leaderboard charts' top-N lines.

    Returns:
        DataFrame with columns `timestamp`, `avg_hype_score`,
        `avg_sentiment_score`.
    """
    rng = np.random.default_rng(_SEED + 77)
    hours = _hours()
    timestamps = _timestamps(hours)
    return pl.DataFrame(
        {
            "timestamp": timestamps,
            "avg_hype_score": (3.0 + rng.normal(0, 1.0, size=hours.size)).clip(min=0).round(2),
            "avg_sentiment_score": (2.5 + rng.normal(0, 1.5, size=hours.size)).round(2),
        }
    )


def chat_trending_phrases(top_n: int) -> pl.DataFrame:
    """Generate the top-N most-repeated normalized messages, event-wide.

    Reuses `chat_message_search`'s small, fixed `_MESSAGE_TEMPLATES` pool —
    drawing many synthetic messages from a small template set naturally
    produces exact repeats, the same "copypasta" shape
    `PostgresDataSource.chat_trending_phrases` looks for in real text.

    Returns:
        DataFrame with columns `channel`, `hour_bucket`, `phrase`,
        `repeat_count`.
    """
    start = _EVENT_START
    end = start + timedelta(hours=float(_EVENT_DURATION_HOURS))
    messages = chat_message_search(start, end, limit=50_000)
    return (
        messages.with_columns(
            pl.col("message_sent_at").dt.truncate("1h").alias("hour_bucket"),
            pl.col("message_text").alias("phrase"),
        )
        .group_by("channel", "hour_bucket", "phrase")
        .len("repeat_count")
        .filter(pl.col("repeat_count") >= 3)
        .sort("repeat_count", descending=True)
        .head(top_n)
    )


def chat_trending_keywords(channel: str, start: datetime, end: datetime) -> pl.DataFrame:
    """Generate one channel's most distinctive chat words, hour by hour.

    Reuses `chat_message_search` for the raw per-message text and the same
    `top_keywords_per_hour` TF-IDF helper the real implementation uses (see
    `app.data.chat_nlp`) — the extraction method itself doesn't depend on
    where the messages came from.

    Returns:
        See `app.data.chat_nlp.top_keywords_per_hour`.
    """
    messages = chat_message_search(start, end, channel=channel, limit=100_000)
    return top_keywords_per_hour(messages)
