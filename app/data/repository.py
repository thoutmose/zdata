"""Typed data-access API used by every page.

Pages never talk to `mock.py` or the database directly — they call the
functions at the bottom of this module. That indirection is intentionally
thin: it exists so that swapping mock data for the real database touches
only `PostgresDataSource`, not a single page.

`PostgresDataSource` queries the real dbt-modeled warehouse (`raw` -> `stg`
-> `int` -> `marts` schemas, read-only role). Notes from exploring it:

- There is no "team" dimension anywhere in the schema — streamers stand alone.
- Two independent pipelines feed this warehouse: a donations pipeline (ZEvent's
  own site, `marts.mart_donations__*`/`mart_event__*`) and a Twitch metadata/chat
  pipeline (`marts.mart_streams__*`/`mart_chat__*`/`mart_chatters__*`/
  `mart_community__*`). The donation pipeline's `game` field is not populated
  pre-event ("Offline" only) — category/game breakdowns instead use the Twitch
  metadata pipeline, which already has real categories.
- Chat usernames are NOT in `raw.chat_messages_raw`/`_staging` (empty/seed-only)
  but ARE available via `int.int_chat__chatter_activity.chatter`, joined here
  onto `marts.mart_chatters__leaderboard.chatter_id`.
- Donation-goal amounts are streamer-chosen and often intentionally
  exaggerated for humor (goals in the billions of euros exist as jokes), so
  goal-related methods avoid summing raw goal amounts as a headline figure.
  The donation-goal *tracker* (start/complete/duration per goal) only applies
  to `goal_category = 'donation'` — the classic cumulative-total milestone —
  since the other goal types (recurring, per-single-donation threshold, ...)
  don't fit a "cumulative total crosses a threshold" model.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Protocol

import polars as pl
import sqlalchemy as sa
import streamlit as st

from app.core.config import Settings, get_settings
from app.core.db import get_connection
from app.core.tz import PARIS_TZ_NAME
from app.data import mock
from app.data.emote_cdn import emote_image_url
from app.data.goal_progress import compute_goal_progress

logger = logging.getLogger(__name__)


class DataSource(Protocol):
    """Interface every backend (mock or real database) must implement."""

    def donation_timeseries(self) -> pl.DataFrame:
        """Return the cumulative-donations curve for the event."""
        ...

    def event_phase_breakdown(self) -> pl.DataFrame:
        """Return donations and streamer counts by event phase."""
        ...

    def leaderboard_movers(self) -> pl.DataFrame:
        """Return the streamers with the biggest recent donation-rank swings."""
        ...

    def data_quality_check(self) -> pl.DataFrame:
        """Return the latest donation-total reconciliation check."""
        ...

    def streamer_breakdown(self) -> pl.DataFrame:
        """Return per-streamer donation, audience and engagement figures."""
        ...

    def streamer_diurnal_profile(self, channel: str) -> pl.DataFrame:
        """Return one streamer's hourly viewer pattern vs. the event average."""
        ...

    def category_breakdown(self) -> pl.DataFrame:
        """Return channel-hours played per Twitch category."""
        ...

    def viewership_timeseries(self) -> pl.DataFrame:
        """Return event-wide concurrent viewership over time."""
        ...

    def stream_sessions(self) -> pl.DataFrame:
        """Return the most recent individual stream sessions."""
        ...

    def goals_by_category(self) -> pl.DataFrame:
        """Return per-category donation-goal figures."""
        ...

    def top_goal_setters(self) -> pl.DataFrame:
        """Return the streamers with the most donation goals set."""
        ...

    def chat_activity_timeseries(self) -> pl.DataFrame:
        """Return event-wide chat message volume over time."""
        ...

    def top_chat_channels(self) -> pl.DataFrame:
        """Return the busiest channels by chat message composition."""
        ...

    def top_emotes(self) -> pl.DataFrame:
        """Return the most-used emotes across the event."""
        ...

    def chatter_profile_mix(self) -> pl.DataFrame:
        """Return the breakdown of chatters by loyalty profile."""
        ...

    def chatter_account_age_mix(self) -> pl.DataFrame:
        """Return the breakdown of chatters by Twitch account age."""
        ...

    def top_chatters(self) -> pl.DataFrame:
        """Return the most active chatters by message count."""
        ...

    def channel_network(self) -> pl.DataFrame:
        """Return channel pairs ranked by shared chat audience."""
        ...

    def chatter_growth_timeseries(self) -> pl.DataFrame:
        """Return new-chatter counts per hour, event-wide."""
        ...

    def channel_hour_heatmap(self) -> pl.DataFrame:
        """Return per-channel, per-hour message counts for a heatmap."""
        ...

    def goal_amount_distribution(self) -> pl.DataFrame:
        """Return every 'donation'-type goal's raw amount, for a distribution view."""
        ...

    def donation_goal_tracker(self, twitch_login: str) -> pl.DataFrame:
        """Return one streamer's 'donation'-type goals with start/complete/duration."""
        ...

    def donation_goal_tracker_global(self) -> pl.DataFrame:
        """Return 'donation'-type goal progress for every streamer that has one."""
        ...

    def chat_engagement_rate(self) -> pl.DataFrame:
        """Return the event-wide average chat-messages-per-100-viewers rate over time."""
        ...

    def hourly_network_hours(self) -> list[datetime]:
        """Return the hours for which an hourly chatter-community network exists."""
        ...

    def hourly_network(self, hour: datetime) -> pl.DataFrame:
        """Return the chatter-community network (channel pairs) for one hour."""
        ...

    def title_leaderboard(self) -> pl.DataFrame:
        """Return stream titles ranked by chat messages and donations."""
        ...

    def chatter_breakdown(self) -> pl.DataFrame:
        """Return per-chatter loyalty, activity and bot-signal figures."""
        ...

    def chatter_channel_breakdown(self, chatter_id: str) -> pl.DataFrame:
        """Return one chatter's per-channel message activity."""
        ...

    def stream_activity_log(self, channel: str) -> pl.DataFrame:
        """Return one streamer's title/category timeline, segmented by change."""
        ...

    def donations_by_category(self) -> pl.DataFrame:
        """Return donations attributed to the Twitch category being played at the time."""
        ...


class MockDataSource:
    """Deterministic sample data, used until the real database is wired up."""

    def donation_timeseries(self) -> pl.DataFrame:
        """See `DataSource.donation_timeseries`."""
        return mock.donation_timeseries()

    def event_phase_breakdown(self) -> pl.DataFrame:
        """See `DataSource.event_phase_breakdown`."""
        return mock.event_phase_breakdown()

    def leaderboard_movers(self) -> pl.DataFrame:
        """See `DataSource.leaderboard_movers`."""
        return mock.leaderboard_movers()

    def data_quality_check(self) -> pl.DataFrame:
        """See `DataSource.data_quality_check`."""
        return mock.data_quality_check()

    def streamer_breakdown(self) -> pl.DataFrame:
        """See `DataSource.streamer_breakdown`."""
        return mock.streamer_breakdown()

    def streamer_diurnal_profile(self, channel: str) -> pl.DataFrame:
        """See `DataSource.streamer_diurnal_profile`."""
        return mock.streamer_diurnal_profile(channel)

    def category_breakdown(self) -> pl.DataFrame:
        """See `DataSource.category_breakdown`."""
        return mock.category_breakdown()

    def viewership_timeseries(self) -> pl.DataFrame:
        """See `DataSource.viewership_timeseries`."""
        return mock.viewership_timeseries()

    def stream_sessions(self) -> pl.DataFrame:
        """See `DataSource.stream_sessions`."""
        return mock.stream_sessions()

    def goals_by_category(self) -> pl.DataFrame:
        """See `DataSource.goals_by_category`."""
        return mock.goals_by_category()

    def top_goal_setters(self) -> pl.DataFrame:
        """See `DataSource.top_goal_setters`."""
        return mock.top_goal_setters()

    def chat_activity_timeseries(self) -> pl.DataFrame:
        """See `DataSource.chat_activity_timeseries`."""
        return mock.chat_activity_timeseries()

    def top_chat_channels(self) -> pl.DataFrame:
        """See `DataSource.top_chat_channels`."""
        return mock.top_chat_channels()

    def top_emotes(self) -> pl.DataFrame:
        """See `DataSource.top_emotes`."""
        return mock.top_emotes()

    def chatter_profile_mix(self) -> pl.DataFrame:
        """See `DataSource.chatter_profile_mix`."""
        return mock.chatter_profile_mix()

    def chatter_account_age_mix(self) -> pl.DataFrame:
        """See `DataSource.chatter_account_age_mix`."""
        return mock.chatter_account_age_mix()

    def top_chatters(self) -> pl.DataFrame:
        """See `DataSource.top_chatters`."""
        return mock.top_chatters()

    def channel_network(self) -> pl.DataFrame:
        """See `DataSource.channel_network`."""
        return mock.channel_network()

    def chatter_growth_timeseries(self) -> pl.DataFrame:
        """See `DataSource.chatter_growth_timeseries`."""
        return mock.chatter_growth_timeseries()

    def channel_hour_heatmap(self) -> pl.DataFrame:
        """See `DataSource.channel_hour_heatmap`."""
        return mock.channel_hour_heatmap()

    def goal_amount_distribution(self) -> pl.DataFrame:
        """See `DataSource.goal_amount_distribution`."""
        return mock.goal_amount_distribution()

    def donation_goal_tracker(self, twitch_login: str) -> pl.DataFrame:
        """See `DataSource.donation_goal_tracker`."""
        return mock.donation_goal_tracker(twitch_login)

    def donation_goal_tracker_global(self) -> pl.DataFrame:
        """See `DataSource.donation_goal_tracker_global`."""
        return mock.donation_goal_tracker_global()

    def chat_engagement_rate(self) -> pl.DataFrame:
        """See `DataSource.chat_engagement_rate`."""
        return mock.chat_engagement_rate()

    def hourly_network_hours(self) -> list[datetime]:
        """See `DataSource.hourly_network_hours`."""
        return mock.hourly_network_hours()

    def hourly_network(self, hour: datetime) -> pl.DataFrame:
        """See `DataSource.hourly_network`."""
        return mock.hourly_network(hour)

    def title_leaderboard(self) -> pl.DataFrame:
        """See `DataSource.title_leaderboard`."""
        return mock.title_leaderboard()

    def chatter_breakdown(self) -> pl.DataFrame:
        """See `DataSource.chatter_breakdown`."""
        return mock.chatter_breakdown()

    def chatter_channel_breakdown(self, chatter_id: str) -> pl.DataFrame:
        """See `DataSource.chatter_channel_breakdown`."""
        return mock.chatter_channel_breakdown(chatter_id)

    def stream_activity_log(self, channel: str) -> pl.DataFrame:
        """See `DataSource.stream_activity_log`."""
        return mock.stream_activity_log(channel)

    def donations_by_category(self) -> pl.DataFrame:
        """See `DataSource.donations_by_category`."""
        return mock.donations_by_category()


class PostgresDataSource:
    """Real backend, querying the production PostgreSQL warehouse (via PgBouncer)."""

    def donation_timeseries(self) -> pl.DataFrame:
        """See `DataSource.donation_timeseries`.

        Sums each snapshot's donation delta into an hourly total across all
        streamers, then takes a running sum over hours to get the event-wide
        cumulative curve.
        """
        query = sa.text("""
            WITH hourly AS (
                SELECT
                    date_trunc('hour', ingested_at) AS ts,
                    SUM(donation_delta_eur) AS hourly_amount_eur,
                    COUNT(DISTINCT twitch_login) AS active_streamers
                FROM marts.mart_donations__timeseries
                GROUP BY 1
            )
            SELECT
                ts AS timestamp,
                SUM(hourly_amount_eur) OVER (ORDER BY ts) AS cumulative_amount_eur,
                active_streamers
            FROM hourly
            ORDER BY ts
        """)
        return self._run(query)

    def event_phase_breakdown(self) -> pl.DataFrame:
        """See `DataSource.event_phase_breakdown`."""
        query = sa.text("""
            SELECT
                event_phase AS phase,
                SUM(donation_delta_eur) AS donations_eur,
                COUNT(DISTINCT twitch_login) AS streamers
            FROM marts.mart_event__phase_segmentation
            GROUP BY event_phase
            ORDER BY CASE event_phase
                WHEN 'opening' THEN 1 WHEN 'middle' THEN 2 WHEN 'final_push' THEN 3 ELSE 4
            END
        """)
        return self._run(query)

    def leaderboard_movers(self) -> pl.DataFrame:
        """See `DataSource.leaderboard_movers`.

        Compares each streamer's most recent donation rank to their previous
        one, so this fills in with real movement once donations start flowing.
        """
        query = sa.text("""
            WITH latest AS (
                SELECT DISTINCT ON (twitch_login)
                    twitch_login, display_name, donation_rank, rank_change
                FROM marts.mart_donations__rank_churn
                ORDER BY twitch_login, ingested_at DESC
            )
            SELECT display_name AS streamer, donation_rank, rank_change
            FROM latest
            ORDER BY ABS(rank_change) DESC, donation_rank ASC
            LIMIT 10
        """)
        return self._run(query)

    def data_quality_check(self) -> pl.DataFrame:
        """See `DataSource.data_quality_check`.

        Compares the event-wide donation total against the sum of individual
        streamer totals at the latest snapshot — a basic reconciliation check
        the underlying dbt model already computes.
        """
        query = sa.text("""
            SELECT ingested_at AS checked_at, divergence_eur
            FROM marts.mart_donations__reconciliation
            ORDER BY ingested_at DESC
            LIMIT 1
        """)
        return self._run(query)

    def streamer_breakdown(self) -> pl.DataFrame:
        """See `DataSource.streamer_breakdown`."""
        query = sa.text("""
            SELECT
                channel,
                display_name AS streamer,
                COALESCE(latest_donation_amount_eur, 0) AS amount_eur,
                COALESCE(total_stream_duration_seconds, 0) / 3600.0 AS hours_live,
                COALESCE(avg_viewer_count, 0) AS avg_viewers,
                COALESCE(peak_viewer_count, 0) AS peak_viewers,
                COALESCE(unique_chatter_count, 0) AS unique_chatters,
                COALESCE(total_message_count, 0) AS total_messages,
                COALESCE(sedentaire_chatter_count, 0) AS sedentaire_chatters,
                COALESCE(multi_streamer_chatter_count, 0) AS multi_streamer_chatters,
                COALESCE(semi_nomade_chatter_count, 0) AS semi_nomade_chatters,
                COALESCE(nomade_chatter_count, 0) AS nomade_chatters,
                top_category,
                COALESCE(uptime_pct, 0) * 100 AS uptime_pct
            FROM marts.mart_streamers__profile
            ORDER BY amount_eur DESC
        """)
        return self._run(query)

    def streamer_diurnal_profile(self, channel: str) -> pl.DataFrame:
        """See `DataSource.streamer_diurnal_profile`.

        `hour_of_day` is bucketed in UTC by the dbt model; shifted by +2 here
        to Europe/Paris (CEST, UTC+2) since the event runs entirely within
        French summer time — no DST transition falls inside the event dates.
        """
        query = sa.text("""
            SELECT
                (hour_of_day + 2) % 24 AS hour_of_day,
                streamer_avg_viewer_count,
                event_avg_viewer_count
            FROM marts.mart_streamers__diurnal_profile
            WHERE channel = :channel
            ORDER BY (hour_of_day + 2) % 24
        """)
        return self._run(query, {"channel": channel})

    def category_breakdown(self) -> pl.DataFrame:
        """See `DataSource.category_breakdown`.

        Uses the Twitch-metadata pipeline (`mart_streams__category_cooccurrence`),
        not the donations pipeline's `game` field, which isn't populated pre-event.
        """
        query = sa.text("""
            SELECT category, SUM(channel_count_playing) AS channel_hours
            FROM marts.mart_streams__category_cooccurrence
            GROUP BY category
            ORDER BY channel_hours DESC
        """)
        return self._run(query)

    def viewership_timeseries(self) -> pl.DataFrame:
        """See `DataSource.viewership_timeseries`."""
        query = sa.text("""
            SELECT DISTINCT hour_bucket AS timestamp, total_avg_viewer_count, live_channel_count
            FROM marts.mart_streams__concurrency_vs_performance
            ORDER BY hour_bucket
        """)
        return self._run(query)

    def stream_sessions(self) -> pl.DataFrame:
        """See `DataSource.stream_sessions`."""
        query = sa.text("""
            SELECT
                channel,
                stream_started_at,
                duration_seconds / 3600.0 AS duration_hours,
                avg_viewer_count,
                peak_viewer_count,
                viewer_change
            FROM marts.mart_streams__session_analysis
            ORDER BY stream_started_at DESC
            LIMIT 15
        """)
        return self._run(query)

    def goals_by_category(self) -> pl.DataFrame:
        """See `DataSource.goals_by_category`.

        Deliberately does not select `total_goal_amount_eur`: a handful of
        joke goals (in the hundreds of millions of euros) would dwarf every
        real figure in a sum. `avg_goal_amount_eur` is kept only as a rough
        signal, not a headline number. Excludes the `test` category, which is
        leftover QA data rather than a real goal type.
        """
        query = sa.text("""
            SELECT
                goal_category AS category,
                goal_count,
                streamer_count,
                avg_goal_amount_eur
            FROM marts.mart_donation_goals__by_category
            WHERE goal_category <> 'test'
            ORDER BY goal_count DESC
        """)
        return self._run(query)

    def top_goal_setters(self) -> pl.DataFrame:
        """See `DataSource.top_goal_setters`.

        `realistic_goal_amount_eur` excludes goals >= €100,000 — a threshold
        chosen to filter out obvious joke/troll goals while still allowing
        genuinely ambitious real ones. Excludes the `test` category (see
        `goals_by_category`).
        """
        query = sa.text("""
            SELECT
                streamer_name,
                COUNT(*) AS goal_count,
                COALESCE(SUM(goal_amount_eur) FILTER (WHERE goal_amount_eur < 100000), 0)
                    AS realistic_goal_amount_eur
            FROM marts.mart_donation_goals__current
            WHERE goal_category <> 'test'
            GROUP BY streamer_name
            ORDER BY goal_count DESC
            LIMIT 15
        """)
        return self._run(query)

    def chat_activity_timeseries(self) -> pl.DataFrame:
        """See `DataSource.chat_activity_timeseries`."""
        query = sa.text("""
            SELECT
                hour_bucket AS timestamp,
                SUM(message_count) AS message_count,
                SUM(unique_chatter_count) AS unique_chatters
            FROM marts.mart_chat__engagement_vs_donations
            GROUP BY hour_bucket
            ORDER BY hour_bucket
        """)
        return self._run(query)

    def top_chat_channels(self) -> pl.DataFrame:
        """See `DataSource.top_chat_channels`."""
        query = sa.text("""
            SELECT
                channel,
                message_count,
                subscriber_message_count,
                vip_message_count,
                moderator_message_count,
                plain_viewer_message_count,
                avg_message_length
            FROM marts.mart_chat__badge_and_verbosity
            ORDER BY message_count DESC
            LIMIT 12
        """)
        return self._run(query)

    def top_emotes(self) -> pl.DataFrame:
        """See `DataSource.top_emotes`.

        Joins emote IDs to their human-readable code via the emote catalog
        (deduplicated to one code per emote, since the catalog has one row
        per channel scope it was seen in) and to an actual image, built from
        `(service, emote_id)` via `emote_image_url` — the catalog itself
        carries no image URL. A handful of emotes may predate the catalog
        being populated and so fall back to a shortened raw ID; `is_named`
        flags which is which, so the page can caveat accordingly rather than
        silently presenting a raw ID as if it were a real code.
        """
        query = sa.text("""
            WITH catalog AS (
                SELECT DISTINCT ON (service, emote_id) service, emote_id, emote_code
                FROM stg.stg_bronze__emote_catalog
                ORDER BY service, emote_id, fetched_at DESC
            )
            SELECT
                e.service,
                e.emote_id,
                COALESCE(
                    c.emote_code,
                    '#' || LEFT(e.emote_id, 10)
                        || CASE WHEN LENGTH(e.emote_id) > 10 THEN '…' ELSE '' END
                ) AS emote,
                c.emote_code IS NOT NULL AS is_named,
                SUM(e.usage_count) AS usage_count
            FROM marts.mart_chat__emote_trends e
            LEFT JOIN catalog c ON c.service = e.service AND c.emote_id = e.emote_id
            GROUP BY 1, 2, 3, 4
            ORDER BY usage_count DESC
            LIMIT 12
        """)
        df = self._run(query)
        if df.is_empty():
            return df
        image_urls = [
            emote_image_url(row["service"], row["emote_id"]) for row in df.iter_rows(named=True)
        ]
        return df.with_columns(pl.Series("image_url", image_urls, dtype=pl.Utf8))

    def chatter_profile_mix(self) -> pl.DataFrame:
        """See `DataSource.chatter_profile_mix`."""
        query = sa.text("""
            SELECT chatter_profile AS profile, COUNT(*) AS chatter_count
            FROM marts.mart_chatters__profile
            GROUP BY chatter_profile
            ORDER BY chatter_count DESC
        """)
        return self._run(query)

    def chatter_account_age_mix(self) -> pl.DataFrame:
        """See `DataSource.chatter_account_age_mix`."""
        query = sa.text("""
            SELECT COALESCE(account_age_bucket, 'unknown') AS age_bucket, COUNT(*) AS chatter_count
            FROM marts.mart_chatters__account_age_profile
            GROUP BY 1
            ORDER BY CASE COALESCE(account_age_bucket, 'unknown')
                WHEN 'new (<30d)' THEN 1 WHEN '1mo-1yr' THEN 2 WHEN '1-3yr' THEN 3
                WHEN '3yr+' THEN 4 ELSE 5
            END
        """)
        return self._run(query)

    def top_chatters(self) -> pl.DataFrame:
        """See `DataSource.top_chatters`.

        Usernames come from `int.int_chat__chatter_activity.chatter`, joined
        by `chatter_id` — that table isn't in `mart_chatters__leaderboard`
        itself. Some "top chatters" are bots (e.g. moderation bots like
        Fossabot) rather than people; `channel` is shown alongside, and
        `has_long_digit_suffix` (from the bot-signal mart) is included so the
        page can offer a "hide likely bots" filter. Limit raised from 15 to
        60 so filtering bots out still leaves a meaningful list to rank.
        """
        query = sa.text("""
            SELECT
                l.chatter_id,
                COALESCE(a.chatter, l.chatter_id) AS chatter,
                l.channel,
                l.message_count,
                l.distinct_channel_count,
                COALESCE(b.has_long_digit_suffix, false) AS has_long_digit_suffix
            FROM marts.mart_chatters__leaderboard l
            LEFT JOIN int.int_chat__chatter_activity a ON a.chatter_id = l.chatter_id
            LEFT JOIN marts.mart_chatters__bot_signal b ON b.chatter_id = l.chatter_id
            ORDER BY l.rank_global
            LIMIT 60
        """)
        return self._run(query)

    def channel_network(self) -> pl.DataFrame:
        """See `DataSource.channel_network`."""
        query = sa.text("""
            SELECT channel_a, channel_b, shared_chatter_count, jaccard_index
            FROM marts.mart_community__channel_network
            ORDER BY shared_chatter_count DESC
        """)
        return self._run(query)

    def chatter_growth_timeseries(self) -> pl.DataFrame:
        """See `DataSource.chatter_growth_timeseries`."""
        query = sa.text("""
            SELECT date_trunc('hour', first_message_at) AS timestamp, COUNT(*) AS new_chatters
            FROM int.int_chat__chatter_activity
            GROUP BY 1
            ORDER BY 1
        """)
        return self._run(query)

    def channel_hour_heatmap(self) -> pl.DataFrame:
        """See `DataSource.channel_hour_heatmap`."""
        query = sa.text("""
            SELECT channel, hour_bucket AS timestamp, message_count
            FROM int.int_chat__hourly_channel_activity
            ORDER BY channel, hour_bucket
        """)
        return self._run(query)

    def goal_amount_distribution(self) -> pl.DataFrame:
        """See `DataSource.goal_amount_distribution`.

        Raw, unfiltered amounts for `goal_category = 'donation'` — the
        skew from joke goals is the point here: this is the distribution
        view an analyst uses to pick their own sane cutoff, rather than
        trusting a single hardcoded threshold.
        """
        query = sa.text("""
            SELECT goal_amount_eur
            FROM marts.mart_donation_goals__current
            WHERE goal_category = 'donation'
        """)
        return self._run(query)

    def donation_goal_tracker(self, twitch_login: str) -> pl.DataFrame:
        """See `DataSource.donation_goal_tracker`.

        Computed in Python rather than SQL: for each goal (ascending by
        amount), find the first snapshot where the streamer's cumulative
        total crossed that goal's threshold. A goal "starts" when the
        previous goal (by amount) was completed; "completes" when its own
        threshold is crossed; not yet crossed = still in progress (or not
        started, if the previous goal in the sequence hasn't completed
        either).
        """
        goals = self._run(
            sa.text("""
                SELECT goal_name, goal_amount_eur
                FROM marts.mart_donation_goals__current
                WHERE twitch_login = :login AND goal_category = 'donation'
                ORDER BY goal_amount_eur
            """),
            {"login": twitch_login},
        )
        timeseries = self._run(
            sa.text("""
                SELECT ingested_at, total_donation_amount_eur
                FROM marts.mart_donations__timeseries
                WHERE twitch_login = :login
                ORDER BY ingested_at
            """),
            {"login": twitch_login},
        )
        return compute_goal_progress(goals, timeseries)

    def donation_goal_tracker_global(self) -> pl.DataFrame:
        """See `DataSource.donation_goal_tracker_global`.

        Fetches every 'donation'-type goal and the timeseries for every
        streamer that has one, in two queries, then applies
        `compute_goal_progress` per streamer in Python — far cheaper than one
        query pair per streamer.
        """
        goals = self._run(
            sa.text("""
                SELECT twitch_login, goal_name, goal_amount_eur
                FROM marts.mart_donation_goals__current
                WHERE goal_category = 'donation'
            """)
        )
        if goals.is_empty():
            return pl.DataFrame(schema={"twitch_login": pl.Utf8, "status": pl.Utf8})
        timeseries = self._run(
            sa.text("""
                SELECT twitch_login, ingested_at, total_donation_amount_eur
                FROM marts.mart_donations__timeseries
                WHERE twitch_login IN (
                    SELECT DISTINCT twitch_login FROM marts.mart_donation_goals__current
                    WHERE goal_category = 'donation'
                )
            """)
        )
        results = []
        for (login,), streamer_goals in goals.group_by("twitch_login"):
            streamer_ts = timeseries.filter(pl.col("twitch_login") == login)
            if streamer_ts.is_empty():
                continue
            progress = compute_goal_progress(streamer_goals, streamer_ts).with_columns(
                twitch_login=pl.lit(login)
            )
            results.append(progress)
        return (
            pl.concat(results, how="vertical")
            if results
            else pl.DataFrame(schema={"twitch_login": pl.Utf8, "status": pl.Utf8})
        )

    def chat_engagement_rate(self) -> pl.DataFrame:
        """See `DataSource.chat_engagement_rate`.

        `msgs_per_min_per_100_viewers` is `NULL` when a channel has zero
        viewers (division guard in the dbt model) — expect this to be empty
        pre-event and fill in once streams actually go live.
        """
        query = sa.text("""
            SELECT
                hour_bucket AS timestamp,
                AVG(msgs_per_min_per_100_viewers) AS avg_engagement_rate
            FROM marts.mart_chat__engagement_vs_donations
            WHERE msgs_per_min_per_100_viewers IS NOT NULL
            GROUP BY 1
            ORDER BY 1
        """)
        return self._run(query)

    def hourly_network_hours(self) -> list[datetime]:
        """See `DataSource.hourly_network_hours`."""
        df = self._run(
            sa.text(
                "SELECT DISTINCT hour_bucket FROM marts.mart_community__hourly_network ORDER BY 1"
            )
        )
        return list(df["hour_bucket"])

    def hourly_network(self, hour: datetime) -> pl.DataFrame:
        """See `DataSource.hourly_network`."""
        query = sa.text("""
            SELECT channel_a, channel_b, shared_chatter_count
            FROM marts.mart_community__hourly_network
            WHERE hour_bucket = :hour
            ORDER BY shared_chatter_count DESC
        """)
        return self._run(query, {"hour": hour})

    def title_leaderboard(self) -> pl.DataFrame:
        """See `DataSource.title_leaderboard`.

        Attributes chat messages and donations to a stream title by matching
        on (channel, hour) — an hour-grain approximation, since a title
        change mid-hour would split that hour's activity across titles. Uses
        `stg.stg_bronze__metadata_snapshots` (Twitch pipeline) for titles,
        since the donations pipeline doesn't carry titles pre-event.
        """
        query = sa.text("""
            WITH title_hours AS (
                SELECT DISTINCT
                    channel, title, category, date_trunc('hour', snapshot_at) AS hour_bucket
                FROM stg.stg_bronze__metadata_snapshots
                WHERE title IS NOT NULL
            ),
            donations AS (
                SELECT
                    twitch_login AS channel,
                    date_trunc('hour', ingested_at) AS hour_bucket,
                    SUM(donation_delta_eur) AS donation_delta_eur
                FROM marts.mart_donations__timeseries
                GROUP BY 1, 2
            )
            SELECT
                th.title,
                th.category,
                COUNT(DISTINCT th.channel) AS channels,
                COALESCE(SUM(m.message_count), 0) AS message_count,
                COALESCE(SUM(d.donation_delta_eur), 0) AS donations_eur
            FROM title_hours th
            LEFT JOIN int.int_chat__hourly_channel_activity m
                ON m.channel = th.channel AND m.hour_bucket = th.hour_bucket
            LEFT JOIN donations d
                ON d.channel = th.channel AND d.hour_bucket = th.hour_bucket
            GROUP BY th.title, th.category
            ORDER BY message_count DESC, donations_eur DESC
            LIMIT 20
        """)
        return self._run(query)

    def chatter_breakdown(self) -> pl.DataFrame:
        """See `DataSource.chatter_breakdown`.

        Combines the loyalty-profile mart with the bot-signal mart (real
        username, account age, message-timing regularity) and the
        account-age mart. Usernames fall back to the raw `chatter_id` when a
        chatter has no `bot_signal` row (mirrors `top_chatters`).
        """
        query = sa.text("""
            SELECT
                p.chatter_id,
                COALESCE(b.chatter, p.chatter_id) AS chatter,
                p.distinct_channel_count,
                p.total_message_count,
                p.top_channel_share,
                p.chatter_profile,
                b.account_created_at,
                COALESCE(b.has_long_digit_suffix, false) AS has_long_digit_suffix,
                b.gap_coefficient_of_variation,
                COALESCE(a.account_age_bucket, 'unknown') AS account_age_bucket
            FROM marts.mart_chatters__profile p
            LEFT JOIN marts.mart_chatters__bot_signal b ON b.chatter_id = p.chatter_id
            LEFT JOIN marts.mart_chatters__account_age_profile a ON a.chatter_id = p.chatter_id
            ORDER BY p.total_message_count DESC
        """)
        return self._run(query)

    def chatter_channel_breakdown(self, chatter_id: str) -> pl.DataFrame:
        """See `DataSource.chatter_channel_breakdown`."""
        query = sa.text("""
            SELECT channel, message_count, first_message_at, last_message_at, active_hours
            FROM int.int_chat__chatter_channel_activity
            WHERE chatter_id = :chatter_id
            ORDER BY message_count DESC
        """)
        return self._run(query, {"chatter_id": chatter_id})

    def stream_activity_log(self, channel: str) -> pl.DataFrame:
        """See `DataSource.stream_activity_log`.

        A streamer's title (and sometimes category) changes as they move
        between activities — this turns the raw metadata-snapshot stream into
        one row per contiguous (title, category) run: a `LAG` window flags
        every snapshot where either value changed since the previous
        snapshot, a running sum of those flags groups consecutive unchanged
        snapshots into a segment id, and the segment's span is that group's
        min/max `snapshot_at`.
        """
        query = sa.text("""
            WITH snaps AS (
                SELECT title, category, snapshot_at,
                       LAG(title) OVER (ORDER BY snapshot_at) AS prev_title,
                       LAG(category) OVER (ORDER BY snapshot_at) AS prev_category
                FROM stg.stg_bronze__metadata_snapshots
                WHERE channel = :channel AND title IS NOT NULL AND category IS NOT NULL
            ),
            flagged AS (
                SELECT *,
                    CASE
                        WHEN prev_title IS DISTINCT FROM title
                            OR prev_category IS DISTINCT FROM category
                        THEN 1 ELSE 0
                    END AS is_new_segment
                FROM snaps
            ),
            grouped AS (
                SELECT *, SUM(is_new_segment) OVER (ORDER BY snapshot_at) AS segment_id
                FROM flagged
            )
            SELECT title, category, MIN(snapshot_at) AS started_at, MAX(snapshot_at) AS ended_at,
                   COUNT(*) AS snapshot_count
            FROM grouped
            GROUP BY segment_id, title, category
            ORDER BY started_at
        """)
        return self._run(query, {"channel": channel})

    def donations_by_category(self) -> pl.DataFrame:
        """See `DataSource.donations_by_category`.

        Attributes each hour's donation delta to whichever category a channel
        was streaming that hour (matching on channel + hour, the same
        hour-grain approximation `title_leaderboard` uses) — pre-event this
        is expected to be all zero, and fills in as donations start flowing.
        """
        query = sa.text("""
            WITH cat_hours AS (
                SELECT DISTINCT channel, category, date_trunc('hour', snapshot_at) AS hour_bucket
                FROM stg.stg_bronze__metadata_snapshots
                WHERE category IS NOT NULL
            ),
            donations AS (
                SELECT
                    twitch_login AS channel,
                    date_trunc('hour', ingested_at) AS hour_bucket,
                    SUM(donation_delta_eur) AS donation_delta_eur
                FROM marts.mart_donations__timeseries
                GROUP BY 1, 2
            )
            SELECT
                ch.category,
                COALESCE(SUM(d.donation_delta_eur), 0) AS donations_eur,
                COUNT(DISTINCT ch.channel) AS channels
            FROM cat_hours ch
            JOIN donations d ON d.channel = ch.channel AND d.hour_bucket = ch.hour_bucket
            GROUP BY ch.category
            ORDER BY donations_eur DESC
        """)
        return self._run(query)

    @staticmethod
    def _run(query: sa.TextClause, params: dict[str, object] | None = None) -> pl.DataFrame:
        """Execute a parameterized, read-only query and return it as a DataFrame.

        Postgres `NUMERIC`/`DECIMAL` columns come back from `pl.read_database`
        as polars `Decimal`, which doesn't support common arithmetic (e.g.
        `.pow()`) that plain `float` columns do. Every such column is cast to
        `Float64` here, once, rather than leaving every caller to remember to
        do it — `NUMERIC` columns are common in this schema (most `_eur`
        amounts) and it's an easy thing to trip over otherwise.

        Every `Datetime` column is also converted to Europe/Paris here — the
        event happens in France, and the warehouse stores `timestamptz`
        values labeled UTC, so every chart axis/table/caption should show
        French local time without every page having to remember to convert.

        Args:
            query: A `sqlalchemy.text()` statement with named bind parameters.
            params: Bound parameter values for the statement.

        Returns:
            The query result as a polars DataFrame, with no `Decimal`
            columns and every timestamp in Europe/Paris.
        """
        with get_connection() as conn:
            execute_options = {"parameters": params} if params else None
            df = pl.read_database(query, connection=conn, execute_options=execute_options)
        decimal_columns = [
            name for name, dtype in df.schema.items() if dtype.base_type() == pl.Decimal
        ]
        if decimal_columns:
            df = df.with_columns(pl.col(c).cast(pl.Float64) for c in decimal_columns)
        datetime_columns = [
            (name, dtype) for name, dtype in df.schema.items() if isinstance(dtype, pl.Datetime)
        ]
        for name, dtype in datetime_columns:
            col = pl.col(name)
            if dtype.time_zone is None:
                col = col.dt.replace_time_zone("UTC")
            df = df.with_columns(col.dt.convert_time_zone(PARIS_TZ_NAME).alias(name))
        return df


def get_data_source(settings: Settings | None = None) -> DataSource:
    """Select the backend to use, based on whether DB credentials are configured.

    Args:
        settings: Settings to use; defaults to the process-wide singleton.

    Returns:
        A `MockDataSource` or `PostgresDataSource`.
    """
    settings = settings or get_settings()
    if settings.use_mock_data:
        return MockDataSource()
    return PostgresDataSource()


@st.cache_data(ttl=60, show_spinner="Loading donations...")
def get_donation_timeseries() -> pl.DataFrame:
    """Cached, page-facing accessor for the donation timeseries.

    Cached server-side for 60 seconds so many concurrent visitors share one
    query result instead of each triggering their own database round trip.

    Returns:
        See `DataSource.donation_timeseries`.
    """
    return get_data_source().donation_timeseries()


@st.cache_data(ttl=60, show_spinner=False)
def get_event_phase_breakdown() -> pl.DataFrame:
    """Cached, page-facing accessor for the event-phase donation breakdown.

    Returns:
        See `DataSource.event_phase_breakdown`.
    """
    return get_data_source().event_phase_breakdown()


@st.cache_data(ttl=60, show_spinner=False)
def get_leaderboard_movers() -> pl.DataFrame:
    """Cached, page-facing accessor for the biggest donation-rank movers.

    Returns:
        See `DataSource.leaderboard_movers`.
    """
    return get_data_source().leaderboard_movers()


@st.cache_data(ttl=60, show_spinner=False)
def get_data_quality_check() -> pl.DataFrame:
    """Cached, page-facing accessor for the donation-total reconciliation check.

    Returns:
        See `DataSource.data_quality_check`.
    """
    return get_data_source().data_quality_check()


@st.cache_data(ttl=60, show_spinner="Loading streamer data...")
def get_streamer_breakdown() -> pl.DataFrame:
    """Cached, page-facing accessor for the per-streamer breakdown.

    Returns:
        See `DataSource.streamer_breakdown`.
    """
    return get_data_source().streamer_breakdown()


@st.cache_data(ttl=60, show_spinner=False)
def get_streamer_diurnal_profile(channel: str) -> pl.DataFrame:
    """Cached, page-facing accessor for one streamer's hourly viewer pattern.

    Args:
        channel: The streamer's channel/login to look up.

    Returns:
        See `DataSource.streamer_diurnal_profile`.
    """
    return get_data_source().streamer_diurnal_profile(channel)


@st.cache_data(ttl=60, show_spinner="Loading category data...")
def get_category_breakdown() -> pl.DataFrame:
    """Cached, page-facing accessor for the per-category channel-hours breakdown.

    Returns:
        See `DataSource.category_breakdown`.
    """
    return get_data_source().category_breakdown()


@st.cache_data(ttl=60, show_spinner=False)
def get_viewership_timeseries() -> pl.DataFrame:
    """Cached, page-facing accessor for event-wide concurrent viewership.

    Returns:
        See `DataSource.viewership_timeseries`.
    """
    return get_data_source().viewership_timeseries()


@st.cache_data(ttl=60, show_spinner=False)
def get_stream_sessions() -> pl.DataFrame:
    """Cached, page-facing accessor for recent individual stream sessions.

    Returns:
        See `DataSource.stream_sessions`.
    """
    return get_data_source().stream_sessions()


@st.cache_data(ttl=60, show_spinner="Loading donation goals...")
def get_goals_by_category() -> pl.DataFrame:
    """Cached, page-facing accessor for the per-category donation-goal breakdown.

    Returns:
        See `DataSource.goals_by_category`.
    """
    return get_data_source().goals_by_category()


@st.cache_data(ttl=60, show_spinner="Loading top goal setters...")
def get_top_goal_setters() -> pl.DataFrame:
    """Cached, page-facing accessor for the streamers with the most donation goals.

    Returns:
        See `DataSource.top_goal_setters`.
    """
    return get_data_source().top_goal_setters()


@st.cache_data(ttl=60, show_spinner="Loading chat activity...")
def get_chat_activity_timeseries() -> pl.DataFrame:
    """Cached, page-facing accessor for event-wide chat message volume.

    Returns:
        See `DataSource.chat_activity_timeseries`.
    """
    return get_data_source().chat_activity_timeseries()


@st.cache_data(ttl=60, show_spinner=False)
def get_top_chat_channels() -> pl.DataFrame:
    """Cached, page-facing accessor for the busiest chat channels.

    Returns:
        See `DataSource.top_chat_channels`.
    """
    return get_data_source().top_chat_channels()


@st.cache_data(ttl=60, show_spinner=False)
def get_top_emotes() -> pl.DataFrame:
    """Cached, page-facing accessor for the most-used emotes.

    Returns:
        See `DataSource.top_emotes`.
    """
    return get_data_source().top_emotes()


@st.cache_data(ttl=60, show_spinner=False)
def get_chatter_profile_mix() -> pl.DataFrame:
    """Cached, page-facing accessor for the chatter loyalty-profile mix.

    Returns:
        See `DataSource.chatter_profile_mix`.
    """
    return get_data_source().chatter_profile_mix()


@st.cache_data(ttl=60, show_spinner=False)
def get_chatter_account_age_mix() -> pl.DataFrame:
    """Cached, page-facing accessor for the chatter account-age mix.

    Returns:
        See `DataSource.chatter_account_age_mix`.
    """
    return get_data_source().chatter_account_age_mix()


@st.cache_data(ttl=60, show_spinner="Loading chatter leaderboard...")
def get_top_chatters() -> pl.DataFrame:
    """Cached, page-facing accessor for the most active chatters.

    Returns:
        See `DataSource.top_chatters`.
    """
    return get_data_source().top_chatters()


@st.cache_data(ttl=60, show_spinner=False)
def get_channel_network() -> pl.DataFrame:
    """Cached, page-facing accessor for the channel shared-audience network.

    Returns:
        See `DataSource.channel_network`.
    """
    return get_data_source().channel_network()


@st.cache_data(ttl=60, show_spinner=False)
def get_chatter_growth_timeseries() -> pl.DataFrame:
    """Cached, page-facing accessor for hourly new-chatter counts.

    Returns:
        See `DataSource.chatter_growth_timeseries`.
    """
    return get_data_source().chatter_growth_timeseries()


@st.cache_data(ttl=60, show_spinner=False)
def get_channel_hour_heatmap() -> pl.DataFrame:
    """Cached, page-facing accessor for the channel x hour message-count heatmap.

    Returns:
        See `DataSource.channel_hour_heatmap`.
    """
    return get_data_source().channel_hour_heatmap()


@st.cache_data(ttl=60, show_spinner=False)
def get_goal_amount_distribution() -> pl.DataFrame:
    """Cached, page-facing accessor for the raw distribution of donation-goal amounts.

    Returns:
        See `DataSource.goal_amount_distribution`.
    """
    return get_data_source().goal_amount_distribution()


@st.cache_data(ttl=60, show_spinner="Loading goal progress...")
def get_donation_goal_tracker(twitch_login: str) -> pl.DataFrame:
    """Cached, page-facing accessor for one streamer's donation-goal progress.

    Args:
        twitch_login: The streamer's channel/login to look up.

    Returns:
        See `DataSource.donation_goal_tracker`.
    """
    return get_data_source().donation_goal_tracker(twitch_login)


@st.cache_data(ttl=60, show_spinner="Loading goal progress for every streamer...")
def get_donation_goal_tracker_global() -> pl.DataFrame:
    """Cached, page-facing accessor for donation-goal progress across every streamer.

    Returns:
        See `DataSource.donation_goal_tracker_global`.
    """
    return get_data_source().donation_goal_tracker_global()


@st.cache_data(ttl=60, show_spinner=False)
def get_chat_engagement_rate() -> pl.DataFrame:
    """Cached, page-facing accessor for the event-wide chat engagement rate.

    Returns:
        See `DataSource.chat_engagement_rate`.
    """
    return get_data_source().chat_engagement_rate()


@st.cache_data(ttl=60, show_spinner=False)
def get_hourly_network_hours() -> list[datetime]:
    """Cached, page-facing accessor for the hours with an hourly network available.

    Returns:
        See `DataSource.hourly_network_hours`.
    """
    return get_data_source().hourly_network_hours()


@st.cache_data(ttl=60, show_spinner=False)
def get_hourly_network(hour: datetime) -> pl.DataFrame:
    """Cached, page-facing accessor for one hour's chatter-community network.

    Args:
        hour: The hour bucket to look up.

    Returns:
        See `DataSource.hourly_network`.
    """
    return get_data_source().hourly_network(hour)


@st.cache_data(ttl=60, show_spinner="Loading title leaderboard...")
def get_title_leaderboard() -> pl.DataFrame:
    """Cached, page-facing accessor for the stream-title leaderboard.

    Returns:
        See `DataSource.title_leaderboard`.
    """
    return get_data_source().title_leaderboard()


@st.cache_data(ttl=60, show_spinner="Loading chatter data...")
def get_chatter_breakdown() -> pl.DataFrame:
    """Cached, page-facing accessor for the per-chatter breakdown.

    Returns:
        See `DataSource.chatter_breakdown`.
    """
    return get_data_source().chatter_breakdown()


@st.cache_data(ttl=60, show_spinner=False)
def get_chatter_channel_breakdown(chatter_id: str) -> pl.DataFrame:
    """Cached, page-facing accessor for one chatter's per-channel activity.

    Args:
        chatter_id: The chatter's id to look up.

    Returns:
        See `DataSource.chatter_channel_breakdown`.
    """
    return get_data_source().chatter_channel_breakdown(chatter_id)


@st.cache_data(ttl=60, show_spinner="Loading activity timeline...")
def get_stream_activity_log(channel: str) -> pl.DataFrame:
    """Cached, page-facing accessor for one streamer's title/category timeline.

    Args:
        channel: The streamer's channel/login to look up.

    Returns:
        See `DataSource.stream_activity_log`.
    """
    return get_data_source().stream_activity_log(channel)


@st.cache_data(ttl=60, show_spinner=False)
def get_donations_by_category() -> pl.DataFrame:
    """Cached, page-facing accessor for donations attributed to Twitch category.

    Returns:
        See `DataSource.donations_by_category`.
    """
    return get_data_source().donations_by_category()
