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
from app.data.emote_cdn import emote_image_url
from app.data.goal_progress import compute_goal_progress

_SEED = 42
_EVENT_START = datetime(2026, 9, 4, 20, 0, 0, tzinfo=PARIS)
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
]
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
    return pl.DataFrame({"checked_at": [datetime.now(PARIS)], "divergence_eur": [0.0]})


def streamer_breakdown() -> pl.DataFrame:
    """Generate per-streamer donation, audience and engagement figures.

    Returns:
        DataFrame with columns `channel`, `streamer`, `amount_eur`,
        `hours_live`, `avg_viewers`, `peak_viewers`, `unique_chatters`,
        `total_messages`, `sedentaire_chatters`, `multi_streamer_chatters`,
        `semi_nomade_chatters`, `nomade_chatters`, `top_category`, `uptime_pct`.
    """
    rng = np.random.default_rng(_SEED + 1)
    n = len(_STREAMERS)
    amounts = rng.pareto(a=2.0, size=n) * 15_000 + 5_000
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
            "avg_viewers": rng.integers(1_500, 45_000, size=n),
            "peak_viewers": rng.integers(2_000, 60_000, size=n),
            "unique_chatters": unique_chatters,
            "total_messages": unique_chatters * rng.integers(3, 15, size=n),
            "sedentaire_chatters": sedentaire,
            "multi_streamer_chatters": multi_streamer,
            "semi_nomade_chatters": semi_nomade,
            "nomade_chatters": nomade,
            "top_category": rng.choice(_CATEGORIES, size=n),
            "uptime_pct": rng.uniform(40, 99, size=n).round(1),
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
    """Generate new-chatter counts per hour, event-wide.

    Returns:
        DataFrame with columns `timestamp`, `new_chatters`.
    """
    rng = np.random.default_rng(_SEED + 27)
    hours = _hours()
    base = 150 * np.exp(-hours / 30) + 20  # most new chatters arrive early
    return pl.DataFrame(
        {
            "timestamp": _timestamps(hours),
            "new_chatters": (base * rng.uniform(0.8, 1.2, size=hours.size)).astype(int),
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
    """Generate a right-skewed distribution of donation-goal amounts.

    A few large (joke) amounts alongside many small, realistic ones — matches
    the shape of the real data, which is why callers can't just sum this.

    Returns:
        DataFrame with one column, `goal_amount_eur`.
    """
    rng = np.random.default_rng(_SEED + 29)
    n = 400
    realistic = rng.pareto(a=1.5, size=int(n * 0.97)) * 300 + 10
    jokes = rng.uniform(1_000_000, 1_000_000_000, size=n - int(n * 0.97))
    return pl.DataFrame({"goal_amount_eur": np.concatenate([realistic, jokes])})


def donation_goal_tracker(twitch_login: str) -> pl.DataFrame:
    """Generate one streamer's donation-goal progress (start/complete/duration).

    Args:
        twitch_login: The streamer's channel/login (used only to seed variation).

    Returns:
        See `app.data.goal_progress.compute_goal_progress`.
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
    goals = pl.DataFrame(
        {
            "goal_name": [f"Goal #{i + 1}" for i in range(n_goals)],
            "goal_amount_eur": amounts.round(0),
        }
    )
    return compute_goal_progress(goals, timeseries)


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

    Returns:
        DataFrame with columns `chatter_id`, `chatter`, `distinct_channel_count`,
        `total_message_count`, `top_channel_share`, `chatter_profile`,
        `account_created_at`, `has_long_digit_suffix`,
        `gap_coefficient_of_variation`, `account_age_bucket`.
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
        }
    ).sort("total_message_count", descending=True)


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
