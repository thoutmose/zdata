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
  The donation-goal *tracker* (start/complete/duration per goal) includes
  every `goal_category`, not just `'donation'` (the classic cumulative-total
  milestone) — but its "start = previous goal's completion" chain only
  makes sense within one category, so each category is tracked as its own
  independent chain against the same timeseries rather than mixed into one
  sequence — see `app.data.goal_progress.goal_progress_by_category`.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Protocol, cast

import polars as pl
import sqlalchemy as sa
import streamlit as st

from app.core.config import Settings, get_settings
from app.core.db import get_connection
from app.core.tz import PARIS, PARIS_TZ_NAME
from app.data import mock
from app.data.chat_lexicons import (
    HOSTILE_WORDS,
    HYPE_EMOTE_WORDS,
    POSITIVE_WORDS,
    leading_boundary_sql,
)
from app.data.chat_nlp import top_keywords_per_hour
from app.data.emote_cdn import emote_image_url
from app.data.goal_progress import goal_progress_by_category

logger = logging.getLogger(__name__)


class DataSource(Protocol):
    """Interface every backend (mock or real database) must implement."""

    def donation_timeseries(self) -> pl.DataFrame:
        """Return the cumulative-donations curve for the event."""
        ...

    def event_phase_breakdown(self) -> pl.DataFrame:
        """Return donations and streamer counts by event phase."""
        ...

    def leaderboard_movers(self, end: datetime) -> pl.DataFrame:
        """Return the streamers with the biggest donation-rank swings as of `end`."""
        ...

    def data_quality_check(self) -> pl.DataFrame:
        """Return the latest donation-total reconciliation check."""
        ...

    def schema_table_stats(self) -> pl.DataFrame:
        """Return every stg/int/marts table's row count and on-disk size."""
        ...

    def streamer_breakdown(self) -> pl.DataFrame:
        """Return per-streamer donation, audience and engagement figures."""
        ...

    def streamer_diurnal_profile(self, channel: str) -> pl.DataFrame:
        """Return one streamer's hourly viewer pattern vs. the event average."""
        ...

    def donation_forecast_features(
        self, start: datetime, end: datetime, cutoff: datetime
    ) -> pl.DataFrame:
        """Return each streamer's mid-event snapshot plus their eventual final total.

        For the Chat ML Lab page's donation-forecasting regression: unlike
        predicting a streamer's final total from their *own final* stats
        (which `streamer_breakdown` alone would make circular — using a
        number to predict itself), this snapshots each streamer's
        cumulative donations, average/peak viewers, and total chat messages
        as of `cutoff` — a real point in time strictly before the event's
        end — so a model trained on this genuinely forecasts an unknown
        future from a known past, the same distinction any real forecasting
        problem needs.
        """
        ...

    def category_breakdown(self, start: datetime, end: datetime) -> pl.DataFrame:
        """Return channel-hours played per Twitch category within `[start, end]`."""
        ...

    def category_popularity_timeseries(self, start: datetime, end: datetime) -> pl.DataFrame:
        """Return how many channels were playing each Twitch category, hour by hour."""
        ...

    def viewership_timeseries(self) -> pl.DataFrame:
        """Return event-wide concurrent viewership over time."""
        ...

    def channel_viewership_leaderboard_timeseries(
        self, start: datetime, end: datetime, top_n: int
    ) -> pl.DataFrame:
        """Return the hour-by-hour average-viewer trend for the `top_n` channels overall.

        `top_n` selects channels by their average viewers across the whole
        `[start, end]` window, not by who happened to be leading in any
        single hour — each selected channel gets a row for every hour it has
        data for, not just the hours it was near the very top, so its line
        stays continuous instead of collapsing to isolated points. Each row
        still carries that hour's true rank among *every* channel (not just
        the selected ones), for the hover tooltip.
        """
        ...

    def channel_messages_leaderboard_timeseries(
        self, start: datetime, end: datetime, top_n: int
    ) -> pl.DataFrame:
        """Return the hour-by-hour chat message trend for the `top_n` channels overall.

        Same "overall top N, full per-channel history" shape as
        `channel_viewership_leaderboard_timeseries` — see its docstring.
        """
        ...

    def channel_donations_leaderboard_timeseries(
        self, start: datetime, end: datetime, top_n: int
    ) -> pl.DataFrame:
        """Return the hour-by-hour cumulative-donations trend for the `top_n` channels overall.

        Same "overall top N, full per-channel history" shape as
        `channel_viewership_leaderboard_timeseries` — see its docstring.
        """
        ...

    def chat_hype_components_timeseries(self, start: datetime, end: datetime) -> pl.DataFrame:
        """Return each channel-hour's raw hype *components*, unweighted and unranked.

        Hype score is a lexicon/heuristic composite (message punctuation,
        all-caps shouting, and known hype-emote mentions — no ML model) of
        three per-message signals, not raw message volume — a smaller, more
        excitable community can out-hype a much bigger, calmer one. This
        returns the three raw rates rather than a single pre-weighted score:
        the Chat Intelligence page lets a viewer tune the weights via
        sliders, and baking in a fixed weighting server-side would mean a
        new query per slider drag. The page recombines the rates with any
        weights client-side instead — instant on every slider move, no
        round trip — and does the "top N by overall weighted score, full
        per-channel history, global rank" selection itself, in Polars, the
        same way `channel_viewership_leaderboard_timeseries` does it in SQL
        — see that method's docstring. Every channel-hour with enough
        sampled messages is included (no `top_n` here — the client picks
        the top N *after* weighting).
        """
        ...

    def channel_sentiment_leaderboard_timeseries(
        self, start: datetime, end: datetime, top_n: int
    ) -> pl.DataFrame:
        """Return the hour-by-hour chat sentiment trend for the `top_n` most positive channels.

        Same "overall top N, full per-channel history" shape as
        `channel_viewership_leaderboard_timeseries` — see its docstring.
        Sentiment score (-100 to +100) is positive-word rate minus
        hostile-word rate per message, averaged per hour, from a curated,
        real-data-verified French/English lexicon (see
        `PostgresDataSource`'s implementation) — not a trained sentiment
        model. The hostile side is the same lexicon
        `channel_toxicity_leaderboard_timeseries` uses.
        """
        ...

    def channel_toxicity_leaderboard_timeseries(
        self, start: datetime, end: datetime, top_n: int
    ) -> pl.DataFrame:
        """Return the hour-by-hour "toxicity score" trend for the `top_n` most hostile channels.

        Same "overall top N, full per-channel history" shape as
        `channel_viewership_leaderboard_timeseries` — see its docstring.
        Deliberately a *channel-level* trend, not a per-chatter "who is
        toxic" tracker: real, on-screen chatter names attached to a
        heuristic toxicity label would risk enabling harassment of
        misclassified individuals, so this answers "where/when is chat most
        hostile" without naming anyone — a channel's line rising then
        falling as another's rises already shows hostility shifting between
        communities over the event. See `PostgresDataSource`'s
        implementation for the exact (curated, real-data-verified) word
        list and its limitations.
        """
        ...

    def chat_toxicity_examples(self, start: datetime, end: datetime, limit: int) -> pl.DataFrame:
        """Return a random sample of messages the toxicity heuristic flagged as hostile.

        Lets a viewer check the heuristic's work rather than trust the
        toxicity score as a black box — see `channel_toxicity_leaderboard_timeseries`'s
        docstring for why it's worth checking. Carries `channel` and
        `chatter` (real, on-screen username, same as every other
        chatter-listing page in this app — Chatters/Streamers/Community) so
        a viewer can see exactly who sent a flagged message, not just that
        one exists.
        """
        ...

    def chat_message_sample(self, start: datetime, end: datetime, limit: int) -> pl.DataFrame:
        """Return a random sample of raw messages, event-wide, for the Chat ML Lab page.

        No lexicon/word filter, unlike `chat_toxicity_examples` — a general-
        purpose feed for the real ML models (topic clustering, sentiment/
        toxicity classifiers) that page uses. Same `channel`/`chatter`
        columns as `chat_toxicity_examples`.
        """
        ...

    def chat_mood_timeseries(self, start: datetime, end: datetime) -> pl.DataFrame:
        """Return event-wide chat hype/sentiment, hour by hour, across every channel.

        Unlike the leaderboard methods above, this has no `top_n` and no
        per-channel dimension at all — one hype and one sentiment figure per
        hour, averaged over every sampled message regardless of channel
        (see `_chat_sample_rate`). Meant to be joined against
        `donation_timeseries` (same hourly grain) to see whether chat mood
        and donation pace move together — see the Chat Intelligence page.
        Values run much lower than the leaderboard charts' top-N lines,
        since those deliberately pick the most extreme channels each hour
        while this averages in every quiet one too.
        """
        ...

    def chat_trending_phrases(self, start: datetime, end: datetime, top_n: int) -> pl.DataFrame:
        """Return the `top_n` most-repeated normalized messages, event-wide.

        Surfaces copypasta/spam moments: the same message (case/whitespace
        normalized) sent many times within one channel's one hour — real
        Twitch chat's dominant "conversational" pattern (see the Chat
        Intelligence page's docstring), not something a generic sentiment or
        topic model would even look for.
        """
        ...

    def chat_trending_keywords(self, channel: str, start: datetime, end: datetime) -> pl.DataFrame:
        """Return one channel's most distinctive chat words, hour by hour.

        See `app.data.chat_nlp.top_keywords_per_hour` for the TF-IDF-over-
        pooled-hourly-text method both implementations share.
        """
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

    def chat_channel_list(self) -> list[str]:
        """Return every channel that has any chat message, event-wide.

        Deliberately not `top_chat_channels()` (capped to the top 12, for
        that leaderboard's own display purposes) — a page letting someone
        pick *any* channel to filter to needs the full list, not just the
        busiest handful.
        """
        ...

    def chatter_directory(self) -> pl.DataFrame:
        """Return the chatter population for the global chatter-filter picker.

        Capped to the most active chatters (not the full, potentially
        multi-thousand-row chatter universe) — see `PostgresDataSource`'s
        docstring for why.
        """
        ...

    def top_emotes(self, start: datetime, end: datetime) -> pl.DataFrame:
        """Return the most-used emotes within `[start, end]` (day-grain)."""
        ...

    def chatter_profile_mix(self) -> pl.DataFrame:
        """Return the breakdown of chatters by loyalty profile."""
        ...

    def chatter_account_age_mix(self) -> pl.DataFrame:
        """Return the breakdown of chatters by Twitch account age."""
        ...

    def top_chatters(self, start: datetime, end: datetime) -> pl.DataFrame:
        """Return the most active chatters active at any point within `[start, end]`."""
        ...

    def top_chatters_for_channels(
        self, channels: list[str], start: datetime, end: datetime
    ) -> pl.DataFrame:
        """Return the most active chatters across a given set of channels."""
        ...

    def top_chatter_per_channel(self, start: datetime, end: datetime) -> pl.DataFrame:
        """Return each channel's single most active chatter ("#1 fan") within `[start, end]`."""
        ...

    def channel_network(self) -> pl.DataFrame:
        """Return channel pairs ranked by shared chat audience."""
        ...

    def chatter_growth_timeseries(self) -> pl.DataFrame:
        """Return new-chatter counts per hour, event-wide."""
        ...

    def chatter_day1_retention(self) -> pl.DataFrame:
        """Return day-N retention of the event's first-day chatters."""
        ...

    def channel_hour_heatmap(self) -> pl.DataFrame:
        """Return per-channel, per-hour message counts for a heatmap."""
        ...

    def goal_amount_distribution(self) -> pl.DataFrame:
        """Return every goal's raw amount and category, for a distribution view."""
        ...

    def donation_goal_tracker(self, twitch_login: str) -> pl.DataFrame:
        """Return one streamer's goals (every category) with start/complete/duration."""
        ...

    def donation_goal_tracker_global(self) -> pl.DataFrame:
        """Return goal progress (every category) for every streamer that has one."""
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

    def title_leaderboard(self, start: datetime, end: datetime) -> pl.DataFrame:
        """Return stream titles ranked by chat messages and donations within `[start, end]`."""
        ...

    def chatter_breakdown(self, start: datetime, end: datetime) -> pl.DataFrame:
        """Return per-chatter figures for chatters active within `[start, end]`."""
        ...

    def chatter_channel_breakdown(self, chatter_id: str) -> pl.DataFrame:
        """Return one chatter's per-channel message activity."""
        ...

    def channel_chatter_breakdown(
        self, channel: str, start: datetime, end: datetime
    ) -> pl.DataFrame:
        """Return every chatter active in one channel within `[start, end]`.

        Includes each chatter's badge composition and emote usage there.
        """
        ...

    def stream_activity_log(self, channel: str) -> pl.DataFrame:
        """Return one streamer's title/category timeline, segmented by change."""
        ...

    def donations_by_category(self, start: datetime, end: datetime) -> pl.DataFrame:
        """Return donations within `[start, end]` attributed to the category playing at the time."""
        ...

    def category_change_impact(self, start: datetime, end: datetime) -> pl.DataFrame:
        """Return category switches within `[start, end]` ranked by viewer-count impact."""
        ...

    def chatter_migrations(self) -> pl.DataFrame:
        """Return channel-to-channel chatter hop counts, event-wide."""
        ...

    def donation_spike_moments(self, start: datetime, end: datetime) -> pl.DataFrame:
        """Return standout single-donation moments within `[start, end]`."""
        ...

    def goal_ambition_vs_reality(self) -> pl.DataFrame:
        """Return per-streamer donation-goal coverage (set vs. actually raised)."""
        ...

    def event_daily_rollup(self, start: datetime, end: datetime) -> pl.DataFrame:
        """Return day-bucketed event-wide totals within `[start, end]`."""
        ...

    def streamer_night_shift(self, channel: str) -> pl.DataFrame:
        """Return one streamer's donation efficiency by hour of day, overnight flagged."""
        ...

    def chat_spikes(self, start: datetime, end: datetime) -> pl.DataFrame:
        """Return the biggest per-channel message-volume anomalies within `[start, end]`."""
        ...

    def new_chatters_per_channel(self, start: datetime, end: datetime) -> pl.DataFrame:
        """Return new-chatter counts per channel, per day, within `[start, end]`."""
        ...

    def search_emote_catalog(self, query: str) -> pl.DataFrame:
        """Return emotes whose code matches `query` (case-insensitive substring)."""
        ...

    def emote_usage_search(self, emote_id: str, start: datetime, end: datetime) -> pl.DataFrame:
        """Return individual chat messages using `emote_id` within `[start, end]`."""
        ...

    def chat_message_search(
        self,
        start: datetime,
        end: datetime,
        *,
        channel: str | None = None,
        chatter_query: str | None = None,
        text_query: str | None = None,
        limit: int = 500,
    ) -> pl.DataFrame:
        """Return individual chat messages within `[start, end]`, most recent first.

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
            DataFrame with `message_sent_at`, `channel`, `chatter_id`,
            `chatter`, `message_text`, `badge`, and `has_long_digit_suffix`
            (for `app.data.bot_heuristic.bot_filter_expr`, same as every
            other chatter-listing page).
        """
        ...


class MockDataSource:
    """Deterministic sample data, used until the real database is wired up."""

    def donation_timeseries(self) -> pl.DataFrame:
        """See `DataSource.donation_timeseries`."""
        return mock.donation_timeseries()

    def event_phase_breakdown(self) -> pl.DataFrame:
        """See `DataSource.event_phase_breakdown`."""
        return mock.event_phase_breakdown()

    def leaderboard_movers(self, end: datetime) -> pl.DataFrame:
        """See `DataSource.leaderboard_movers`.

        `end` is unused — mock data has no per-row `ingested_at` to filter by.
        """
        return mock.leaderboard_movers()

    def data_quality_check(self) -> pl.DataFrame:
        """See `DataSource.data_quality_check`."""
        return mock.data_quality_check()

    def schema_table_stats(self) -> pl.DataFrame:
        """See `DataSource.schema_table_stats`.

        Empty — this section is specifically about the real warehouse's
        catalog metadata, which doesn't exist for mock data; the page shows
        an explanatory message instead of a fabricated row/size count.
        """
        return pl.DataFrame(
            schema={
                "schema": pl.Utf8,
                "table": pl.Utf8,
                "kind": pl.Utf8,
                "row_estimate": pl.Int64,
                "size_bytes": pl.Int64,
            }
        )

    def streamer_breakdown(self) -> pl.DataFrame:
        """See `DataSource.streamer_breakdown`."""
        return mock.streamer_breakdown()

    def streamer_diurnal_profile(self, channel: str) -> pl.DataFrame:
        """See `DataSource.streamer_diurnal_profile`."""
        return mock.streamer_diurnal_profile(channel)

    def donation_forecast_features(
        self, start: datetime, end: datetime, cutoff: datetime
    ) -> pl.DataFrame:
        """See `DataSource.donation_forecast_features`.

        `start`/`end` are unused — mock data has no per-row `hour_bucket` to
        filter by.
        """
        return mock.donation_forecast_features(cutoff)

    def category_breakdown(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.category_breakdown`.

        `start`/`end` are unused — mock data has no per-row `hour_bucket` to
        filter by.
        """
        return mock.category_breakdown()

    def category_popularity_timeseries(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.category_popularity_timeseries`.

        `start`/`end` are unused — mock data has no per-row `hour_bucket` to
        filter by.
        """
        return mock.category_popularity_timeseries()

    def viewership_timeseries(self) -> pl.DataFrame:
        """See `DataSource.viewership_timeseries`."""
        return mock.viewership_timeseries()

    def channel_viewership_leaderboard_timeseries(
        self, start: datetime, end: datetime, top_n: int
    ) -> pl.DataFrame:
        """See `DataSource.channel_viewership_leaderboard_timeseries`.

        `start`/`end` are unused — mock data has no per-row `hour_bucket` to
        filter by.
        """
        return mock.channel_viewership_leaderboard_timeseries(top_n)

    def channel_messages_leaderboard_timeseries(
        self, start: datetime, end: datetime, top_n: int
    ) -> pl.DataFrame:
        """See `DataSource.channel_messages_leaderboard_timeseries`.

        `start`/`end` are unused — mock data has no per-row `hour_bucket` to
        filter by.
        """
        return mock.channel_messages_leaderboard_timeseries(top_n)

    def channel_donations_leaderboard_timeseries(
        self, start: datetime, end: datetime, top_n: int
    ) -> pl.DataFrame:
        """See `DataSource.channel_donations_leaderboard_timeseries`.

        `start`/`end` are unused — mock data has no per-row `hour_bucket` to
        filter by.
        """
        return mock.channel_donations_leaderboard_timeseries(top_n)

    def chat_hype_components_timeseries(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.chat_hype_components_timeseries`.

        `start`/`end` are unused — mock data has no per-row `hour_bucket` to
        filter by.
        """
        return mock.chat_hype_components_timeseries()

    def channel_sentiment_leaderboard_timeseries(
        self, start: datetime, end: datetime, top_n: int
    ) -> pl.DataFrame:
        """See `DataSource.channel_sentiment_leaderboard_timeseries`.

        `start`/`end` are unused — mock data has no per-row `hour_bucket` to
        filter by.
        """
        return mock.channel_sentiment_leaderboard_timeseries(top_n)

    def channel_toxicity_leaderboard_timeseries(
        self, start: datetime, end: datetime, top_n: int
    ) -> pl.DataFrame:
        """See `DataSource.channel_toxicity_leaderboard_timeseries`.

        `start`/`end` are unused — mock data has no per-row `hour_bucket` to
        filter by.
        """
        return mock.channel_toxicity_leaderboard_timeseries(top_n)

    def chat_toxicity_examples(self, start: datetime, end: datetime, limit: int) -> pl.DataFrame:
        """See `DataSource.chat_toxicity_examples`."""
        return mock.chat_toxicity_examples(start, end, limit)

    def chat_message_sample(self, start: datetime, end: datetime, limit: int) -> pl.DataFrame:
        """See `DataSource.chat_message_sample`."""
        return mock.chat_message_sample(start, end, limit)

    def chat_mood_timeseries(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.chat_mood_timeseries`.

        `start`/`end` are unused — mock data has no per-row `hour_bucket` to
        filter by.
        """
        return mock.chat_mood_timeseries()

    def chat_trending_phrases(self, start: datetime, end: datetime, top_n: int) -> pl.DataFrame:
        """See `DataSource.chat_trending_phrases`.

        `start`/`end` are unused — mock data has no per-row `hour_bucket` to
        filter by.
        """
        return mock.chat_trending_phrases(top_n)

    def chat_trending_keywords(self, channel: str, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.chat_trending_keywords`."""
        return mock.chat_trending_keywords(channel, start, end)

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

    def chat_channel_list(self) -> list[str]:
        """See `DataSource.chat_channel_list`.

        Mock data has no artificial "top 12" cap in the first place — every
        mock streamer's channel has chat activity — so this is just the
        full channel universe, sorted.
        """
        return mock.chat_channel_list()

    def chatter_directory(self) -> pl.DataFrame:
        """See `DataSource.chatter_directory`."""
        return mock.chatter_directory()

    def top_emotes(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.top_emotes`.

        `start`/`end` are unused — mock data has no per-row `day_bucket` to
        filter by.
        """
        return mock.top_emotes()

    def chatter_profile_mix(self) -> pl.DataFrame:
        """See `DataSource.chatter_profile_mix`."""
        return mock.chatter_profile_mix()

    def chatter_account_age_mix(self) -> pl.DataFrame:
        """See `DataSource.chatter_account_age_mix`."""
        return mock.chatter_account_age_mix()

    def top_chatters(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.top_chatters`.

        `start`/`end` are unused — mock data has no per-row activity window to
        filter by.
        """
        return mock.top_chatters()

    def top_chatters_for_channels(
        self, channels: list[str], start: datetime, end: datetime
    ) -> pl.DataFrame:
        """See `DataSource.top_chatters_for_channels`.

        `start`/`end` are unused — mock data has no per-row activity window to
        filter by.
        """
        return mock.top_chatters_for_channels(channels)

    def top_chatter_per_channel(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.top_chatter_per_channel`.

        `start`/`end` are unused — mock data has no per-row activity window to
        filter by.
        """
        return mock.top_chatter_per_channel()

    def channel_network(self) -> pl.DataFrame:
        """See `DataSource.channel_network`."""
        return mock.channel_network()

    def chatter_growth_timeseries(self) -> pl.DataFrame:
        """See `DataSource.chatter_growth_timeseries`."""
        return mock.chatter_growth_timeseries()

    def chatter_day1_retention(self) -> pl.DataFrame:
        """See `DataSource.chatter_day1_retention`."""
        return mock.chatter_day1_retention()

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

    def title_leaderboard(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.title_leaderboard`.

        `start`/`end` are unused — mock data has no per-row `hour_bucket` to
        filter by.
        """
        return mock.title_leaderboard()

    def chatter_breakdown(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.chatter_breakdown`.

        Filtered by first/last-message overlap with `[start, end]`, same as
        `top_chatters`.
        """
        df = mock.chatter_breakdown()
        return df.filter((pl.col("first_message_at") <= end) & (pl.col("last_message_at") >= start))

    def chatter_channel_breakdown(self, chatter_id: str) -> pl.DataFrame:
        """See `DataSource.chatter_channel_breakdown`."""
        return mock.chatter_channel_breakdown(chatter_id)

    def channel_chatter_breakdown(
        self, channel: str, start: datetime, end: datetime
    ) -> pl.DataFrame:
        """See `DataSource.channel_chatter_breakdown`."""
        df = mock.channel_chatter_breakdown(channel)
        return df.filter((pl.col("first_message_at") <= end) & (pl.col("last_message_at") >= start))

    def stream_activity_log(self, channel: str) -> pl.DataFrame:
        """See `DataSource.stream_activity_log`."""
        return mock.stream_activity_log(channel)

    def donations_by_category(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.donations_by_category`.

        `start`/`end` are unused — mock data has no per-row `hour_bucket` to
        filter by.
        """
        return mock.donations_by_category()

    def category_change_impact(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.category_change_impact`."""
        df = mock.category_change_impact()
        return df.filter(pl.col("changed_at").is_between(start, end))

    def chatter_migrations(self) -> pl.DataFrame:
        """See `DataSource.chatter_migrations`."""
        return mock.chatter_migrations()

    def donation_spike_moments(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.donation_spike_moments`."""
        df = mock.donation_spike_moments()
        return df.filter(pl.col("ingested_at").is_between(start, end))

    def goal_ambition_vs_reality(self) -> pl.DataFrame:
        """See `DataSource.goal_ambition_vs_reality`."""
        return mock.goal_ambition_vs_reality()

    def event_daily_rollup(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.event_daily_rollup`."""
        df = mock.event_daily_rollup()
        return df.filter(pl.col("day_bucket").dt.date().is_between(start.date(), end.date()))

    def streamer_night_shift(self, channel: str) -> pl.DataFrame:
        """See `DataSource.streamer_night_shift`."""
        return mock.streamer_night_shift(channel)

    def chat_spikes(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.chat_spikes`."""
        df = mock.chat_spikes()
        return df.filter(pl.col("hour_bucket").is_between(start, end))

    def new_chatters_per_channel(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.new_chatters_per_channel`."""
        df = mock.new_chatters_per_channel()
        return df.filter(pl.col("day_bucket").dt.date().is_between(start.date(), end.date()))

    def search_emote_catalog(self, query: str) -> pl.DataFrame:
        """See `DataSource.search_emote_catalog`."""
        return mock.search_emote_catalog(query)

    def emote_usage_search(self, emote_id: str, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.emote_usage_search`."""
        return mock.emote_usage_search(emote_id, start, end)

    def chat_message_search(
        self,
        start: datetime,
        end: datetime,
        *,
        channel: str | None = None,
        chatter_query: str | None = None,
        text_query: str | None = None,
        limit: int = 500,
    ) -> pl.DataFrame:
        """See `DataSource.chat_message_search`."""
        return mock.chat_message_search(
            start,
            end,
            channel=channel,
            chatter_query=chatter_query,
            text_query=text_query,
            limit=limit,
        )


@st.cache_data(ttl=300, show_spinner=False)
def _cached_chat_row_count(start: datetime, end: datetime) -> int:
    """Cached count of raw chat rows in `[start, end]`, shared across every accessor.

    Module-level, not a method on `PostgresDataSource` — `get_data_source()`
    returns a *fresh* instance on every call, so instance-level memoization
    would never hit. This matters because several Chat Intelligence
    sections (hype/sentiment/toxicity/mood/trending) call
    `PostgresDataSource._chat_sample_rate` with the *same* `(start, end)`
    window on one page load; without this, each one repeated the same
    `COUNT(*)` query — cheap alone (well under a second) but adding up
    across 5-6 calls every time.
    """
    result = PostgresDataSource._run(
        sa.text("""
            SELECT COUNT(*) AS total FROM stg.stg_bronze__live_chat
            WHERE message_sent_at BETWEEN :start AND :end
        """),
        {"start": start.replace(tzinfo=PARIS), "end": end.replace(tzinfo=PARIS)},
    )
    return int(result["total"][0])


class PostgresDataSource:
    """Real backend, querying the production PostgreSQL warehouse (via PgBouncer)."""

    def donation_timeseries(self) -> pl.DataFrame:
        """See `DataSource.donation_timeseries`.

        `mart_donations__timeseries` carries `total_donation_amount_eur` —
        the event-wide cumulative total, already computed and broadcast
        identically onto every streamer's row at each snapshot (verified:
        all 337 streamer rows share the same value at a given `ingested_at`).
        Read that directly (`MAX` per hour, since it's monotonic and constant
        across streamers within an hour) rather than reconstructing a total
        by summing `donation_delta_eur` — that used to be this query's
        approach, and undercounted by hundreds of thousands of euros against
        the real total, apparently from gaps in per-streamer delta capture.
        """
        query = sa.text("""
            SELECT
                date_trunc('hour', ingested_at) AS timestamp,
                MAX(total_donation_amount_eur) AS cumulative_amount_eur,
                COUNT(DISTINCT twitch_login) AS active_streamers
            FROM marts.mart_donations__timeseries
            GROUP BY 1
            ORDER BY 1
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

    def leaderboard_movers(self, end: datetime) -> pl.DataFrame:
        """See `DataSource.leaderboard_movers`.

        Compares each streamer's most recent donation rank (as of `end`) to
        their previous one, so this fills in with real movement once
        donations start flowing.
        """
        query = sa.text("""
            WITH latest AS (
                SELECT DISTINCT ON (twitch_login)
                    twitch_login, display_name, donation_rank, rank_change
                FROM marts.mart_donations__rank_churn
                WHERE ingested_at <= :end
                ORDER BY twitch_login, ingested_at DESC
            )
            SELECT display_name AS streamer, donation_rank, rank_change
            FROM latest
            ORDER BY ABS(rank_change) DESC, donation_rank ASC
            LIMIT 10
        """)
        return self._run(query, {"end": end.replace(tzinfo=PARIS)})

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

    def schema_table_stats(self) -> pl.DataFrame:
        """See `DataSource.schema_table_stats`.

        Reads Postgres' own catalog (`pg_class`/`pg_namespace`), not
        `SELECT COUNT(*)` per table — a real `COUNT(*)` over
        `stg.stg_bronze__live_chat` (millions of rows, no index) would
        itself risk the 15s statement timeout this app already works around
        elsewhere (see `chat_message_sample`'s sampling). `reltuples` is the
        same planner-maintained estimate `EXPLAIN` uses, refreshed by
        autovacuum/analyze — accurate to within a few percent in practice,
        which is all a "how big is this table" overview needs. Views
        (`relkind = 'v'`) have no `reltuples`/storage of their own (Postgres
        reports `-1`/`0`) — surfaced as `null`, not a fabricated zero.
        """
        query = sa.text("""
            SELECT
                n.nspname AS schema,
                c.relname AS table,
                CASE c.relkind WHEN 'v' THEN 'view' ELSE 'table' END AS kind,
                NULLIF(c.reltuples::bigint, -1) AS row_estimate,
                NULLIF(pg_total_relation_size(c.oid), 0) AS size_bytes
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname IN ('raw', 'stg', 'int', 'marts')
              AND c.relkind IN ('r', 'v', 'm')
            ORDER BY n.nspname, c.relname
        """)
        return self._run(query)

    def streamer_breakdown(self) -> pl.DataFrame:
        """See `DataSource.streamer_breakdown`.

        `donation_eur_per_avg_viewer`/`donation_eur_per_unique_chatter` come
        from `mart_donations__normalized`, joined on `twitch_login = channel`.
        """
        query = sa.text("""
            SELECT
                p.channel,
                p.display_name AS streamer,
                COALESCE(p.latest_donation_amount_eur, 0) AS amount_eur,
                COALESCE(p.total_stream_duration_seconds, 0) / 3600.0 AS hours_live,
                COALESCE(p.avg_viewer_count, 0) AS avg_viewers,
                COALESCE(p.peak_viewer_count, 0) AS peak_viewers,
                COALESCE(p.unique_chatter_count, 0) AS unique_chatters,
                COALESCE(p.total_message_count, 0) AS total_messages,
                COALESCE(p.sedentaire_chatter_count, 0) AS sedentaire_chatters,
                COALESCE(p.multi_streamer_chatter_count, 0) AS multi_streamer_chatters,
                COALESCE(p.semi_nomade_chatter_count, 0) AS semi_nomade_chatters,
                COALESCE(p.nomade_chatter_count, 0) AS nomade_chatters,
                p.top_category,
                COALESCE(p.uptime_pct, 0) * 100 AS uptime_pct,
                n.donation_eur_per_avg_viewer,
                n.donation_eur_per_unique_chatter
            FROM marts.mart_streamers__profile p
            LEFT JOIN marts.mart_donations__normalized n ON n.twitch_login = p.channel
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

    def donation_forecast_features(
        self, start: datetime, end: datetime, cutoff: datetime
    ) -> pl.DataFrame:
        """See `DataSource.donation_forecast_features`.

        `start`/`end` bound which streamers even get a final total via
        `streamer_breakdown` (event-wide, so unused here directly beyond
        that join) — `cutoff` is what actually defines the snapshot. Three
        marts, one per feature group, each already using the
        latest-snapshot-before-cutoff / sum-before-cutoff pattern the rest
        of this class uses for point-in-time reads against these same
        tables (see `channel_donations_leaderboard_timeseries`).
        """
        cutoff_naive = cutoff.replace(tzinfo=PARIS) if cutoff.tzinfo is None else cutoff
        donations_mid = sa.text("""
            WITH bucketed AS (
                SELECT
                    twitch_login,
                    donation_amount_eur,
                    ROW_NUMBER() OVER (
                        PARTITION BY twitch_login ORDER BY ingested_at DESC
                    ) AS rn
                FROM marts.mart_donations__timeseries
                WHERE ingested_at <= :cutoff
            )
            SELECT twitch_login AS channel, donation_amount_eur AS amount_eur_mid
            FROM bucketed
            WHERE rn = 1
        """)
        viewers_mid = sa.text("""
            SELECT
                channel,
                AVG(avg_viewer_count) AS avg_viewers_mid,
                MAX(peak_viewer_count) AS peak_viewers_mid
            FROM marts.mart_streams__viewership_timeseries
            WHERE hour_bucket <= :cutoff
            GROUP BY channel
        """)
        messages_mid = sa.text("""
            SELECT channel, SUM(message_count) AS total_messages_mid
            FROM int.int_chat__hourly_channel_activity
            WHERE hour_bucket <= :cutoff
            GROUP BY channel
        """)
        params = {"cutoff": cutoff_naive}
        donations_df = self._run(donations_mid, params)
        viewers_df = self._run(viewers_mid, params)
        messages_df = self._run(messages_mid, params)
        final = self.streamer_breakdown().select("channel", "streamer", "amount_eur")
        return (
            donations_df.join(viewers_df, on="channel", how="inner")
            .join(messages_df, on="channel", how="inner")
            .join(final, on="channel", how="inner")
        )

    def category_breakdown(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.category_breakdown`.

        Uses the Twitch-metadata pipeline (`mart_streams__category_cooccurrence`),
        not the donations pipeline's `game` field, which isn't populated pre-event.
        """
        query = sa.text("""
            SELECT category, SUM(channel_count_playing) AS channel_hours
            FROM marts.mart_streams__category_cooccurrence
            WHERE hour_bucket BETWEEN :start AND :end
            GROUP BY category
            ORDER BY channel_hours DESC
        """)
        return self._run(
            query, {"start": start.replace(tzinfo=PARIS), "end": end.replace(tzinfo=PARIS)}
        )

    def category_popularity_timeseries(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.category_popularity_timeseries`.

        Same source table as `category_breakdown`, but keeping the
        `hour_bucket` dimension instead of summing it away — "what was
        trending when," not just "what was trending overall."
        """
        query = sa.text("""
            SELECT hour_bucket AS timestamp, category, channel_count_playing
            FROM marts.mart_streams__category_cooccurrence
            WHERE hour_bucket BETWEEN :start AND :end
            ORDER BY hour_bucket
        """)
        return self._run(
            query, {"start": start.replace(tzinfo=PARIS), "end": end.replace(tzinfo=PARIS)}
        )

    def viewership_timeseries(self) -> pl.DataFrame:
        """See `DataSource.viewership_timeseries`."""
        query = sa.text("""
            SELECT DISTINCT hour_bucket AS timestamp, total_avg_viewer_count, live_channel_count
            FROM marts.mart_streams__concurrency_vs_performance
            ORDER BY hour_bucket
        """)
        return self._run(query)

    def channel_viewership_leaderboard_timeseries(
        self, start: datetime, end: datetime, top_n: int
    ) -> pl.DataFrame:
        """See `DataSource.channel_viewership_leaderboard_timeseries`.

        `top_n` channels are picked by their *average* viewers across the
        whole window (`totals`, below) — not by who was in any single hour's
        top spots — then every hour of *their own* history is returned, so a
        channel that only briefly cracked the hourly lead doesn't get
        reduced to an isolated point while a consistently mid-pack channel
        goes missing entirely. `viewer_rank_at_hour` is
        `mart_streams__viewership_timeseries`'s precomputed rank against
        *every* channel that hour, computed before the `totals` filter, so
        the hover tooltip still reports a true rank rather than one relative
        to just the selected channels.
        """
        query = sa.text("""
            WITH totals AS (
                SELECT channel, AVG(avg_viewer_count) AS overall_avg_viewers
                FROM marts.mart_streams__viewership_timeseries
                WHERE hour_bucket BETWEEN :start AND :end
                GROUP BY channel
                ORDER BY overall_avg_viewers DESC
                LIMIT :top_n
            )
            SELECT v.hour_bucket AS timestamp, v.channel, v.avg_viewer_count, v.viewer_rank_at_hour
            FROM marts.mart_streams__viewership_timeseries v
            JOIN totals t ON t.channel = v.channel
            WHERE v.hour_bucket BETWEEN :start AND :end
            ORDER BY v.hour_bucket, v.viewer_rank_at_hour
        """)
        return self._run(
            query,
            {
                "start": start.replace(tzinfo=PARIS),
                "end": end.replace(tzinfo=PARIS),
                "top_n": top_n,
            },
        )

    def channel_messages_leaderboard_timeseries(
        self, start: datetime, end: datetime, top_n: int
    ) -> pl.DataFrame:
        """See `DataSource.channel_messages_leaderboard_timeseries`.

        Same "overall top N, full per-channel history" shape as
        `channel_viewership_leaderboard_timeseries` (see its docstring) —
        `top_n` channels are picked by their *summed* message count across
        the whole window (`totals`), and `int.int_chat__hourly_channel_activity`
        (also used by `channel_hour_heatmap`) has no precomputed rank column
        unlike the viewer mart, so `message_rank_at_hour` is computed here
        with a window function over *every* channel before the `totals`
        filter narrows the result set.
        """
        query = sa.text("""
            WITH totals AS (
                SELECT channel, SUM(message_count) AS total_messages
                FROM int.int_chat__hourly_channel_activity
                WHERE hour_bucket BETWEEN :start AND :end
                GROUP BY channel
                ORDER BY total_messages DESC
                LIMIT :top_n
            ),
            ranked AS (
                SELECT
                    hour_bucket AS timestamp,
                    channel,
                    message_count,
                    RANK() OVER (
                        PARTITION BY hour_bucket ORDER BY message_count DESC
                    ) AS message_rank_at_hour
                FROM int.int_chat__hourly_channel_activity
                WHERE hour_bucket BETWEEN :start AND :end
            )
            SELECT r.timestamp, r.channel, r.message_count, r.message_rank_at_hour
            FROM ranked r
            JOIN totals t ON t.channel = r.channel
            ORDER BY r.timestamp, r.message_rank_at_hour
        """)
        return self._run(
            query,
            {
                "start": start.replace(tzinfo=PARIS),
                "end": end.replace(tzinfo=PARIS),
                "top_n": top_n,
            },
        )

    def channel_donations_leaderboard_timeseries(
        self, start: datetime, end: datetime, top_n: int
    ) -> pl.DataFrame:
        """See `DataSource.channel_donations_leaderboard_timeseries`.

        Ranks by `donation_amount_eur` — each streamer's own cumulative
        total, not `total_donation_amount_eur` (event-wide, broadcast onto
        every row) — same distinction as `donation_goal_tracker`'s docstring.
        `mart_donations__timeseries` snapshots arrive at irregular,
        sub-hourly intervals with no per-hour grain of its own, so this
        first takes each streamer's latest snapshot within each hour
        (`ROW_NUMBER` per `twitch_login, hour_bucket`, filtered to the
        `[start, end]` window *before* windowing — the same
        filter-before-window ordering `donation_goal_tracker_global` uses
        against this same large, unindexed table), then ranks those
        per-hour totals.

        Same "overall top N, full per-channel history" shape as
        `channel_viewership_leaderboard_timeseries` (see its docstring) —
        `top_n` channels are picked by their own highest cumulative total
        reached anywhere in the window (`totals`; since `amount_eur` only
        ever grows, that's just each streamer's latest snapshot in range),
        with `donation_rank_at_hour` still computed over every streamer
        before that filter narrows the result set.
        """
        query = sa.text("""
            WITH bucketed AS (
                SELECT
                    twitch_login,
                    date_trunc('hour', ingested_at) AS hour_bucket,
                    donation_amount_eur,
                    ROW_NUMBER() OVER (
                        PARTITION BY twitch_login, date_trunc('hour', ingested_at)
                        ORDER BY ingested_at DESC
                    ) AS rn
                FROM marts.mart_donations__timeseries
                WHERE ingested_at BETWEEN :start AND :end
            ),
            latest_per_hour AS (
                SELECT twitch_login AS channel, hour_bucket, donation_amount_eur AS amount_eur
                FROM bucketed
                WHERE rn = 1
            ),
            totals AS (
                SELECT channel, MAX(amount_eur) AS overall_amount_eur
                FROM latest_per_hour
                GROUP BY channel
                ORDER BY overall_amount_eur DESC
                LIMIT :top_n
            ),
            ranked AS (
                SELECT
                    hour_bucket AS timestamp,
                    channel,
                    amount_eur,
                    RANK() OVER (
                        PARTITION BY hour_bucket ORDER BY amount_eur DESC
                    ) AS donation_rank_at_hour
                FROM latest_per_hour
            )
            SELECT r.timestamp, r.channel, r.amount_eur, r.donation_rank_at_hour
            FROM ranked r
            JOIN totals t ON t.channel = r.channel
            ORDER BY r.timestamp, r.donation_rank_at_hour
        """)
        return self._run(
            query,
            {
                "start": start.replace(tzinfo=PARIS),
                "end": end.replace(tzinfo=PARIS),
                "top_n": top_n,
            },
        )

    def _chat_sample_rate(self, start: datetime, end: datetime, *, target_rows: int) -> float:
        """Return a `random() <` fraction sampling the raw chat table down to `target_rows`.

        That table has no index at all (see `channel_messages_leaderboard_timeseries`'s
        docstring) and any per-row text function — even a single simple regex,
        confirmed against the real ~7.7M-row event window — pushes a
        full-window aggregate past `Settings.db_statement_timeout_ms` (15s).
        A plain `COUNT(*)` over the same window is cheap (no per-row text
        work), so this spends one fast query finding out how much data there
        is before the expensive one, rather than guessing a fixed fraction
        that would be wasteful on a narrow window and still too slow on the
        full event. 1.0 (no sampling) when the window already has fewer rows
        than `target_rows` — small windows get exact figures, not noisier
        sampled ones. The count itself is cached at module level (see
        `_cached_chat_row_count`) since several callers share the same
        window in one page load.
        """
        total = _cached_chat_row_count(start, end)
        return min(1.0, target_rows / max(total, 1))

    # Built once from `app.data.chat_lexicons`'s curated, real-data-verified
    # word lists (see that module for what was tried and rejected, and why),
    # so every query below shares one definition instead of duplicating the
    # word lists per query.
    _HOSTILE_WORD_CASE = leading_boundary_sql("message_text", HOSTILE_WORDS)
    _POSITIVE_WORD_CASE = leading_boundary_sql("message_text", POSITIVE_WORDS)
    _HYPE_EMOTE_CASE = leading_boundary_sql("message_text", HYPE_EMOTE_WORDS)
    _PUNCT_CASE = "CASE WHEN message_text LIKE '%!!%' THEN 1.0 ELSE 0.0 END"
    _CAPS_CASE = """
        CASE
            WHEN message_text = upper(message_text)
                AND message_text != lower(message_text)
                AND LENGTH(message_text) >= 4
            THEN 1.0 ELSE 0.0 END
    """
    # The fixed 0.4/0.3/0.3 weighting `chat_mood_timeseries` uses for its
    # single event-wide hype figure — `chat_hype_components_timeseries`
    # returns these same three rates unweighted for the Chat Intelligence
    # page's per-channel leaderboard, which recombines them with
    # user-chosen weights client-side instead of a fixed weighting here.
    _HYPE_SCORE_EXPR = f"""
        100.0 * (
            0.4 * AVG({_PUNCT_CASE})
            + 0.3 * AVG({_CAPS_CASE})
            + 0.3 * AVG({_HYPE_EMOTE_CASE})
        )
    """

    def chat_hype_components_timeseries(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.chat_hype_components_timeseries`."""
        sample_rate = self._chat_sample_rate(start, end, target_rows=250_000)
        query = sa.text(f"""
            SELECT
                channel,
                date_trunc('hour', message_sent_at) AS timestamp,
                COUNT(*) AS message_count,
                AVG({self._PUNCT_CASE}) AS punct_rate,
                AVG({self._CAPS_CASE}) AS caps_rate,
                AVG({self._HYPE_EMOTE_CASE}) AS emote_rate
            FROM stg.stg_bronze__live_chat
            WHERE message_sent_at BETWEEN :start AND :end AND random() < :sample_rate
            GROUP BY channel, date_trunc('hour', message_sent_at)
            HAVING COUNT(*) >= 20
        """)
        return self._run(
            query,
            {
                "start": start.replace(tzinfo=PARIS),
                "end": end.replace(tzinfo=PARIS),
                "sample_rate": sample_rate,
            },
        )

    def channel_sentiment_leaderboard_timeseries(
        self, start: datetime, end: datetime, top_n: int
    ) -> pl.DataFrame:
        """See `DataSource.channel_sentiment_leaderboard_timeseries`.

        Positive-word rate (a curated, real-data-verified French/English
        lexicon — "merci", "super", "bravo", "excellent", ... — chosen the
        same way as `_HOSTILE_WORD_CASE`, favoring words confirmed not to
        collide with emote codes or unrelated words) minus
        `_HOSTILE_WORD_CASE`'s hostile-word rate, times 100, averaged per
        hour over a random sample (see `_chat_sample_rate`). Same sampling,
        `HAVING COUNT(*) >= 20` noise floor, and "overall top N, full
        history, global rank" shape as `channel_viewership_leaderboard_timeseries`
        — see its docstring — ranked by *most positive* rather than most
        viewers.
        """
        sample_rate = self._chat_sample_rate(start, end, target_rows=250_000)
        query = sa.text(f"""
            WITH scored AS (
                SELECT
                    channel,
                    date_trunc('hour', message_sent_at) AS hour_bucket,
                    100.0 * (AVG({self._POSITIVE_WORD_CASE}) - AVG({self._HOSTILE_WORD_CASE}))
                        AS sentiment_score
                FROM stg.stg_bronze__live_chat
                WHERE message_sent_at BETWEEN :start AND :end AND random() < :sample_rate
                GROUP BY channel, date_trunc('hour', message_sent_at)
                HAVING COUNT(*) >= 20
            ),
            ranked AS (
                SELECT
                    hour_bucket AS timestamp,
                    channel,
                    sentiment_score,
                    RANK() OVER (
                        PARTITION BY hour_bucket ORDER BY sentiment_score DESC
                    ) AS sentiment_rank_at_hour
                FROM scored
            ),
            totals AS (
                SELECT channel, AVG(sentiment_score) AS overall_sentiment
                FROM scored
                GROUP BY channel
                ORDER BY overall_sentiment DESC
                LIMIT :top_n
            )
            SELECT r.timestamp, r.channel, r.sentiment_score, r.sentiment_rank_at_hour
            FROM ranked r
            JOIN totals t ON t.channel = r.channel
            ORDER BY r.timestamp, r.sentiment_rank_at_hour
        """)
        return self._run(
            query,
            {
                "start": start.replace(tzinfo=PARIS),
                "end": end.replace(tzinfo=PARIS),
                "sample_rate": sample_rate,
                "top_n": top_n,
            },
        )

    def channel_toxicity_leaderboard_timeseries(
        self, start: datetime, end: datetime, top_n: int
    ) -> pl.DataFrame:
        """See `DataSource.channel_toxicity_leaderboard_timeseries`.

        `_HOSTILE_WORD_CASE`'s rate, times 100, averaged per hour over a
        random sample (see `_chat_sample_rate`) — same sampling,
        `HAVING COUNT(*) >= 20` noise floor, and "overall top N, full
        history, global rank" shape as
        `channel_viewership_leaderboard_timeseries` — see its docstring —
        ranked by *highest* hostility rather than most viewers.

        The word list was arrived at by testing candidates individually
        against real event chat, not assumed from a generic profanity list:
        dropped were bare "con" (99% false positives — "configurer",
        "continue", "contacter"), "cretin" (mostly "Lapin Crétin", a game
        title), "stupide" (mostly Twitch emote codes like
        "just1chatStupide"), "minable" (mostly "interminable", an unrelated
        word), "pourri"/"batard" (usually describe an object's quality or
        are positive slang — "un flow de batard" is a compliment — not
        aimed at a person), and "putain"/"merde" (used as a casual
        exclamation, like "damn", not typically directed at anyone). What's
        left — "connard", "connasse", "idiot", "debile", "degage", "ta
        gueule" — was confirmed to mostly hit genuine hostile language in a
        real sample. It will still miss slurs, hate speech, and harassment
        that avoids these exact words, and can't tell a targeted insult from
        friendly banter.
        """
        sample_rate = self._chat_sample_rate(start, end, target_rows=250_000)
        query = sa.text(f"""
            WITH scored AS (
                SELECT
                    channel,
                    date_trunc('hour', message_sent_at) AS hour_bucket,
                    100.0 * AVG({self._HOSTILE_WORD_CASE}) AS toxicity_score
                FROM stg.stg_bronze__live_chat
                WHERE message_sent_at BETWEEN :start AND :end AND random() < :sample_rate
                GROUP BY channel, date_trunc('hour', message_sent_at)
                HAVING COUNT(*) >= 20
            ),
            ranked AS (
                SELECT
                    hour_bucket AS timestamp,
                    channel,
                    toxicity_score,
                    RANK() OVER (
                        PARTITION BY hour_bucket ORDER BY toxicity_score DESC
                    ) AS toxicity_rank_at_hour
                FROM scored
            ),
            totals AS (
                SELECT channel, AVG(toxicity_score) AS overall_toxicity
                FROM scored
                GROUP BY channel
                ORDER BY overall_toxicity DESC
                LIMIT :top_n
            )
            SELECT r.timestamp, r.channel, r.toxicity_score, r.toxicity_rank_at_hour
            FROM ranked r
            JOIN totals t ON t.channel = r.channel
            ORDER BY r.timestamp, r.toxicity_rank_at_hour
        """)
        return self._run(
            query,
            {
                "start": start.replace(tzinfo=PARIS),
                "end": end.replace(tzinfo=PARIS),
                "sample_rate": sample_rate,
                "top_n": top_n,
            },
        )

    def chat_toxicity_examples(self, start: datetime, end: datetime, limit: int) -> pl.DataFrame:
        """See `DataSource.chat_toxicity_examples`.

        Filters on the same word-boundary condition `_HOSTILE_WORD_CASE`
        evaluates as an aggregate, applied directly as a `WHERE` clause here
        instead — still sampled first (see `_chat_sample_rate`), since
        evaluating the same regex against every row of an unindexed
        ~7.7M-row table before filtering is the same per-row cost either
        way; sampling first cut this from ~7s to ~2s in testing.
        """
        sample_rate = self._chat_sample_rate(start, end, target_rows=250_000)
        hostile_alternatives = "|".join(HOSTILE_WORDS)
        query = sa.text(f"""
            SELECT channel, chatter, message_sent_at, message_text
            FROM stg.stg_bronze__live_chat
            WHERE message_sent_at BETWEEN :start AND :end AND random() < :sample_rate
                AND message_text ~* '\\y({hostile_alternatives})'
            ORDER BY random()
            LIMIT :limit
        """)
        return self._run(
            query,
            {
                "start": start.replace(tzinfo=PARIS),
                "end": end.replace(tzinfo=PARIS),
                "sample_rate": sample_rate,
                "limit": limit,
            },
        )

    def chat_message_sample(self, start: datetime, end: datetime, limit: int) -> pl.DataFrame:
        """See `DataSource.chat_message_sample`."""
        sample_rate = self._chat_sample_rate(start, end, target_rows=250_000)
        query = sa.text("""
            SELECT channel, chatter, message_sent_at, message_text
            FROM stg.stg_bronze__live_chat
            WHERE message_sent_at BETWEEN :start AND :end AND random() < :sample_rate
            ORDER BY random()
            LIMIT :limit
        """)
        return self._run(
            query,
            {
                "start": start.replace(tzinfo=PARIS),
                "end": end.replace(tzinfo=PARIS),
                "sample_rate": sample_rate,
                "limit": limit,
            },
        )

    def chat_mood_timeseries(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.chat_mood_timeseries`.

        Same hype/sentiment formulas and sampling as
        `chat_hype_components_timeseries`/`channel_sentiment_leaderboard_timeseries`,
        just grouped by hour alone (no `channel` in the `GROUP BY`, no top-N
        filter) — every sampled message across every channel that hour
        contributes to one event-wide figure.
        """
        sample_rate = self._chat_sample_rate(start, end, target_rows=250_000)
        query = sa.text(f"""
            SELECT
                date_trunc('hour', message_sent_at) AS timestamp,
                {self._HYPE_SCORE_EXPR} AS avg_hype_score,
                100.0 * (AVG({self._POSITIVE_WORD_CASE}) - AVG({self._HOSTILE_WORD_CASE}))
                    AS avg_sentiment_score
            FROM stg.stg_bronze__live_chat
            WHERE message_sent_at BETWEEN :start AND :end AND random() < :sample_rate
            GROUP BY date_trunc('hour', message_sent_at)
            HAVING COUNT(*) >= 20
            ORDER BY timestamp
        """)
        return self._run(
            query,
            {
                "start": start.replace(tzinfo=PARIS),
                "end": end.replace(tzinfo=PARIS),
                "sample_rate": sample_rate,
            },
        )

    def chat_trending_phrases(self, start: datetime, end: datetime, top_n: int) -> pl.DataFrame:
        """See `DataSource.chat_trending_phrases`.

        Normalizes only by case/whitespace (`lower(trim(...))`) — cheap
        string functions, unlike the regex normalization a stricter
        near-duplicate detector would need (see `_chat_sample_rate`) — over
        the same kind of random sample as `chat_hype_components_timeseries`.
        `HAVING COUNT(*) >= 5` keeps this to genuine repeats rather than
        coincidental short messages ("ok", "gg") a couple of unrelated
        chatters happened to both send once.
        """
        sample_rate = self._chat_sample_rate(start, end, target_rows=300_000)
        query = sa.text("""
            SELECT
                channel,
                date_trunc('hour', message_sent_at) AS hour_bucket,
                lower(trim(message_text)) AS phrase,
                COUNT(*) AS repeat_count
            FROM stg.stg_bronze__live_chat
            WHERE message_sent_at BETWEEN :start AND :end
                AND random() < :sample_rate
                AND LENGTH(trim(message_text)) >= 2
            GROUP BY channel, date_trunc('hour', message_sent_at), lower(trim(message_text))
            HAVING COUNT(*) >= 5
            ORDER BY repeat_count DESC
            LIMIT :top_n
        """)
        return self._run(
            query,
            {
                "start": start.replace(tzinfo=PARIS),
                "end": end.replace(tzinfo=PARIS),
                "sample_rate": sample_rate,
                "top_n": top_n,
            },
        )

    def chat_trending_keywords(self, channel: str, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.chat_trending_keywords`.

        Already scoped to one channel, so — unlike the two leaderboard
        methods above — this fetches its raw text directly with no sampling
        needed: confirmed against the real event's single busiest channel
        (538k messages) at under 2 seconds, comfortably inside the
        statement timeout.
        """
        query = sa.text("""
            SELECT message_sent_at, message_text
            FROM stg.stg_bronze__live_chat
            WHERE message_sent_at BETWEEN :start AND :end AND channel = :channel
        """)
        messages = self._run(
            query,
            {
                "start": start.replace(tzinfo=PARIS),
                "end": end.replace(tzinfo=PARIS),
                "channel": channel,
            },
        )
        return top_keywords_per_hour(messages)

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

    def chat_channel_list(self) -> list[str]:
        """See `DataSource.chat_channel_list`.

        Reads `stg.stg_bronze__live_chat` directly rather than
        `mart_chat__badge_and_verbosity` — that mart is (currently) missing
        a handful of the raw table's channels, and the whole point here is
        completeness, not aggregated figures.
        """
        query = sa.text("SELECT DISTINCT channel FROM stg.stg_bronze__live_chat ORDER BY channel")
        return self._run(query)["channel"].to_list()

    def chatter_directory(self) -> pl.DataFrame:
        """See `DataSource.chatter_directory`.

        Capped to the top 500 by `total_message_count` — the real chatter
        universe can run into the thousands, which would make the global
        chatter-filter multiselect slow to render and useless to scroll
        through. Same `DISTINCT ON (chatter_id)` + username join as
        `top_chatters`.
        """
        query = sa.text("""
            SELECT chatter_id, chatter, total_message_count
            FROM (
                SELECT DISTINCT ON (l.chatter_id)
                    l.chatter_id,
                    COALESCE(a.chatter, l.chatter_id) AS chatter,
                    l.total_message_count
                FROM marts.mart_chatters__leaderboard l
                LEFT JOIN int.int_chat__chatter_activity a ON a.chatter_id = l.chatter_id
                ORDER BY l.chatter_id, l.message_count DESC
            ) deduped
            ORDER BY total_message_count DESC
            LIMIT 500
        """)
        return self._run(query)

    def top_emotes(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.top_emotes`.

        Joins emote IDs to their human-readable code via the emote catalog
        (deduplicated to one code per emote, since the catalog has one row
        per channel scope it was seen in) and to an actual image, built from
        `(service, emote_id)` via `emote_image_url` — the catalog itself
        carries no image URL. A handful of emotes may predate the catalog
        being populated and so fall back to a shortened raw ID; `is_named`
        flags which is which, so the page can caveat accordingly rather than
        silently presenting a raw ID as if it were a real code.

        `mart_chat__emote_trends` is bucketed by day, not hour — coarser than
        the sidebar filter's own granularity, but still a real narrowing.
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
            WHERE e.day_bucket BETWEEN date_trunc('day', :start) AND date_trunc('day', :end)
            GROUP BY 1, 2, 3, 4
            ORDER BY usage_count DESC
            LIMIT 12
        """)
        df = self._run(
            query, {"start": start.replace(tzinfo=PARIS), "end": end.replace(tzinfo=PARIS)}
        )
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

    def top_chatters(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.top_chatters`.

        Usernames come from `int.int_chat__chatter_activity.chatter`, joined
        by `chatter_id` — that table isn't in `mart_chatters__leaderboard`
        itself. Some "top chatters" are bots (e.g. moderation bots like
        Fossabot) rather than people; `channel` is shown alongside, and
        `has_long_digit_suffix` (from the bot-signal mart) is included so the
        page can offer a "hide likely bots" filter. Limit raised from 15 to
        60 so filtering bots out still leaves a meaningful list to rank.

        `mart_chatters__leaderboard` is grained one row per (chatter,
        channel) — `rank_global`/`total_message_count` are the chatter's
        overall figures, broadcast onto every one of their channel rows
        (same pattern as `mart_donations__timeseries`'s cumulative total),
        while `message_count` is that one channel's own count. A plain
        `ORDER BY rank_global LIMIT 60` (this query's previous form) doesn't
        dedupe by chatter, so a handful of chatters active in dozens of
        channels each could occupy most of the 60 slots with repeat rows
        for themselves — crowding out everyone else, up to and including
        every chatter whose *only* channel is a busy one like the event's
        own official channel. `DISTINCT ON (chatter_id)` (picking each
        chatter's single highest-message channel as the one shown) plus
        `total_message_count` as the ranked/displayed count fixes both: one
        row per chatter, and the true event-wide count rather than a single
        channel's slice of it.

        Filtered by whether a chatter was active *at all* within
        `[start, end]` (`first_message_at`/`last_message_at` overlap the
        range) — `total_message_count`/`rank_global` themselves stay the
        chatter's event-wide totals, since the mart doesn't carry a windowed
        count.
        """
        query = sa.text("""
            SELECT chatter_id, chatter, channel, message_count, distinct_channel_count,
                   has_long_digit_suffix
            FROM (
                SELECT DISTINCT ON (l.chatter_id)
                    l.chatter_id,
                    COALESCE(a.chatter, l.chatter_id) AS chatter,
                    l.channel,
                    l.total_message_count AS message_count,
                    l.distinct_channel_count,
                    l.rank_global,
                    COALESCE(b.has_long_digit_suffix, false) AS has_long_digit_suffix
                FROM marts.mart_chatters__leaderboard l
                LEFT JOIN int.int_chat__chatter_activity a ON a.chatter_id = l.chatter_id
                LEFT JOIN marts.mart_chatters__bot_signal b ON b.chatter_id = l.chatter_id
                WHERE l.first_message_at <= :end AND l.last_message_at >= :start
                ORDER BY l.chatter_id, l.message_count DESC
            ) deduped
            ORDER BY rank_global
            LIMIT 60
        """)
        return self._run(
            query, {"start": start.replace(tzinfo=PARIS), "end": end.replace(tzinfo=PARIS)}
        )

    def top_chatters_for_channels(
        self, channels: list[str], start: datetime, end: datetime
    ) -> pl.DataFrame:
        """See `DataSource.top_chatters_for_channels`.

        Unlike `top_chatters` (deduped to each chatter's single best channel,
        since it ranks across the *whole* event), this sums `message_count`
        across every one of the given channels a chatter appears in — the
        page-facing "N streamers filtered above" scope this exists for wants
        a chatter's activity *within that filtered set*, not their one best
        channel in it. `channels_in_filter` says how many of the given
        channels they were actually active in, in case a chatter's total
        looks high only because they're spread across many of them.
        """
        if not channels:
            return pl.DataFrame(
                schema={
                    "chatter_id": pl.Utf8,
                    "chatter": pl.Utf8,
                    "message_count": pl.Float64,
                    "channels_in_filter": pl.Int64,
                    "has_long_digit_suffix": pl.Boolean,
                }
            )
        query = sa.text("""
            SELECT chatter_id, chatter, message_count, channels_in_filter, has_long_digit_suffix
            FROM (
                SELECT
                    l.chatter_id,
                    COALESCE(a.chatter, l.chatter_id) AS chatter,
                    SUM(l.message_count) AS message_count,
                    COUNT(DISTINCT l.channel) AS channels_in_filter,
                    COALESCE(b.has_long_digit_suffix, false) AS has_long_digit_suffix
                FROM marts.mart_chatters__leaderboard l
                LEFT JOIN int.int_chat__chatter_activity a ON a.chatter_id = l.chatter_id
                LEFT JOIN marts.mart_chatters__bot_signal b ON b.chatter_id = l.chatter_id
                WHERE l.channel = ANY(:channels)
                  AND l.first_message_at <= :end AND l.last_message_at >= :start
                GROUP BY l.chatter_id, a.chatter, b.has_long_digit_suffix
            ) grouped
            ORDER BY message_count DESC
            LIMIT 200
        """)
        return self._run(
            query,
            {
                "channels": channels,
                "start": start.replace(tzinfo=PARIS),
                "end": end.replace(tzinfo=PARIS),
            },
        )

    def top_chatter_per_channel(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.top_chatter_per_channel`.

        `DISTINCT ON (l.channel) ... ORDER BY l.channel, l.message_count DESC`
        is the standard Postgres "top 1 row per group" idiom — same trick
        `top_chatters` uses the other way around (`DISTINCT ON (chatter_id)`,
        picking each chatter's own busiest channel). Here the grouping is
        flipped: for every channel, the one chatter with the most messages
        *in that channel* specifically (not their event-wide total, which
        `top_chatters` already covers) — a channel's "#1 fan" can easily not
        be a globally top-60 chatter at all if the streamer themself is niche.
        """
        query = sa.text("""
            SELECT DISTINCT ON (l.channel)
                l.channel,
                l.chatter_id,
                COALESCE(a.chatter, l.chatter_id) AS chatter,
                l.message_count,
                COALESCE(b.has_long_digit_suffix, false) AS has_long_digit_suffix
            FROM marts.mart_chatters__leaderboard l
            LEFT JOIN int.int_chat__chatter_activity a ON a.chatter_id = l.chatter_id
            LEFT JOIN marts.mart_chatters__bot_signal b ON b.chatter_id = l.chatter_id
            WHERE l.first_message_at <= :end AND l.last_message_at >= :start
            ORDER BY l.channel, l.message_count DESC
        """)
        return self._run(
            query, {"start": start.replace(tzinfo=PARIS), "end": end.replace(tzinfo=PARIS)}
        )

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

    def chatter_day1_retention(self) -> pl.DataFrame:
        """See `DataSource.chatter_day1_retention`.

        Reads `marts.mart_chatters__retention` (grained one row per
        (chatter, quarter-hour), already deduplicated by the dbt model)
        rather than scanning raw `stg.stg_bronze__live_chat` — much
        cheaper, and this mart exists for exactly this purpose.

        "Day" is bucketed relative to the event's own first active
        quarter-hour, not calendar-date `date_trunc('day', ...)` — the
        event doesn't start at midnight, so a calendar-day bucket would
        make "day 0" a few unrepresentative overnight hours instead of a
        full day, and every later boundary would inherit that same offset.
        `day_index` 0 is that first 24h window; the cohort is whoever
        chatted at all during it, and each later `day_index`'s
        `retained_chatters` is how many of that same cohort chatted again
        during that later window — a standard day-N retention curve,
        anchored to the event's own start rather than the wall clock.
        """
        query = sa.text("""
            WITH bounds AS (
                SELECT MIN(quarter_hour_bucket) AS event_start
                FROM marts.mart_chatters__retention
            ),
            daily AS (
                SELECT DISTINCT
                    chatter_id,
                    FLOOR(
                        EXTRACT(EPOCH FROM (quarter_hour_bucket - bounds.event_start)) / 86400
                    )::int AS day_index
                FROM marts.mart_chatters__retention, bounds
            ),
            day0_cohort AS (
                SELECT chatter_id FROM daily WHERE day_index = 0
            )
            SELECT d.day_index, COUNT(DISTINCT d.chatter_id) AS retained_chatters
            FROM daily d
            JOIN day0_cohort c ON c.chatter_id = d.chatter_id
            GROUP BY d.day_index
            ORDER BY d.day_index
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

        Raw, unfiltered amounts across every goal category (excluding only
        `'test'`) — the skew from joke goals is the point here: this is the
        distribution view an analyst uses to pick their own sane cutoff,
        rather than trusting a single hardcoded threshold. `goal_category`
        is included so a caller can break the distribution down by type
        instead of only seeing it as one undifferentiated pool.
        """
        query = sa.text("""
            SELECT goal_category, goal_amount_eur
            FROM marts.mart_donation_goals__current
            WHERE goal_category <> 'test'
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

        Every goal category is included (not just `'donation'`) — but
        `compute_goal_progress`'s "start = previous goal's completion"
        chain only makes sense *within* one category (a `'donation'`
        milestone and an unrelated `'incentive'` goal aren't checkpoints in
        the same sequence just because they're both this streamer's goals),
        so each category gets its own independent chain against the same
        timeseries, tagged with `goal_category` in the output.

        Uses `donation_amount_eur` — that streamer's own cumulative total.
        `total_donation_amount_eur` (despite the name) is the event-wide
        total broadcast onto every streamer's row, not a per-streamer figure
        — using it here compared each streamer's goals against everyone's
        combined donations, which crosses thresholds far too early and with
        the wrong timestamps entirely (same bug as `donation_timeseries`,
        different query).
        """
        goals = self._run(
            sa.text("""
                SELECT goal_category, goal_name, goal_amount_eur
                FROM marts.mart_donation_goals__current
                WHERE twitch_login = :login AND goal_category <> 'test'
                ORDER BY goal_amount_eur
            """),
            {"login": twitch_login},
        )
        timeseries = self._run(
            sa.text("""
                SELECT ingested_at, donation_amount_eur AS total_donation_amount_eur
                FROM marts.mart_donations__timeseries
                WHERE twitch_login = :login
                ORDER BY ingested_at
            """),
            {"login": twitch_login},
        )
        return goal_progress_by_category(goals, timeseries)

    def donation_goal_tracker_global(self) -> pl.DataFrame:
        """See `DataSource.donation_goal_tracker_global`.

        Fetches every goal (every category, not just `'donation'`) and the
        timeseries for every streamer that has one, in two queries, then
        applies `compute_goal_progress` per (streamer, category) in Python —
        far cheaper than one query pair per streamer. See
        `donation_goal_tracker`'s docstring for why category stays a
        grouping key even though every type is now included. Uses
        `donation_amount_eur` (per-streamer), not `total_donation_amount_eur`
        (event-wide) — see `donation_goal_tracker`'s docstring.

        `mart_donations__timeseries` has no index and ~2.7M rows total, most
        of them consecutive snapshots where a streamer's cumulative total
        didn't change since the row before — `compute_goal_progress` only
        needs the timestamp of the first snapshot at each new amount
        (`np.searchsorted` against ascending amounts), so a `LAG` window
        function drops same-amount repeats before the data ever leaves
        Postgres. Measured: 2.55M rows / ~7.6s over the wire down to ~48k
        rows / ~1.6s, with identical crossing timestamps since the dropped
        rows carry no new information — except the very last row per
        streamer, which is kept unconditionally even when it duplicates the
        amount before it: `compute_goal_progress` also reads the *last*
        timestamp as "the latest known snapshot" (for `elapsed_so_far` on
        an in-progress goal), and dropping a same-amount final row would
        make that look stale by however long the total had been flat.
        Verified identical output (`.equals()`) against the undeduped query
        for a real streamer, including `elapsed_so_far`.
        """
        goals = self._run(
            sa.text("""
                SELECT twitch_login, goal_category, goal_name, goal_amount_eur
                FROM marts.mart_donation_goals__current
                WHERE goal_category <> 'test'
            """)
        )
        if goals.is_empty():
            return pl.DataFrame(schema={"twitch_login": pl.Utf8, "status": pl.Utf8})
        timeseries = self._run(
            sa.text("""
                SELECT twitch_login, ingested_at, donation_amount_eur AS total_donation_amount_eur
                FROM (
                    SELECT
                        twitch_login, ingested_at, donation_amount_eur,
                        LAG(donation_amount_eur) OVER (
                            PARTITION BY twitch_login ORDER BY ingested_at
                        ) AS prev_amount,
                        MAX(ingested_at) OVER (PARTITION BY twitch_login) AS max_ingested_at
                    FROM marts.mart_donations__timeseries
                    WHERE twitch_login IN (
                        SELECT DISTINCT twitch_login FROM marts.mart_donation_goals__current
                        WHERE goal_category <> 'test'
                    )
                ) t
                WHERE prev_amount IS NULL
                   OR prev_amount IS DISTINCT FROM donation_amount_eur
                   OR ingested_at = max_ingested_at
            """)
        )
        # Partitioned once up front rather than `timeseries.filter(twitch_login
        # == login)` inside the loop below: that re-scanned the full (multi-
        # million-row) timeseries per streamer (~300+ streamers here), which
        # measured at ~10s end-to-end. A single partition pass is ~0.1s.
        timeseries_by_login = timeseries.partition_by("twitch_login", as_dict=True)
        results = []
        for (login,), streamer_goals in goals.group_by("twitch_login"):
            streamer_ts = timeseries_by_login.get((login,))
            if streamer_ts is None or streamer_ts.is_empty():
                continue
            progress = goal_progress_by_category(streamer_goals, streamer_ts).with_columns(
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

    def title_leaderboard(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.title_leaderboard`.

        Chat messages are still attributed to a title by matching on
        (channel, hour) — an hour-grain approximation, since a title change
        mid-hour would split that hour's activity across titles, using
        `stg.stg_bronze__metadata_snapshots` (Twitch pipeline) for titles
        (the donations pipeline doesn't carry titles pre-event). Donations,
        though, come straight from `mart_donations__by_title`, which already
        attributes each donation to its title at the dbt layer — more
        accurate than the hour-bucket approximation this used to also apply
        to donations. A `FULL OUTER JOIN` combines the two since a title can
        have messages with no donations that hour, or vice versa.
        """
        query = sa.text("""
            WITH title_hours AS (
                SELECT DISTINCT
                    channel, title, category, date_trunc('hour', snapshot_at) AS hour_bucket
                FROM stg.stg_bronze__metadata_snapshots
                WHERE title IS NOT NULL AND snapshot_at BETWEEN :start AND :end
            ),
            title_messages AS (
                SELECT
                    th.title,
                    th.category,
                    COUNT(DISTINCT th.channel) AS channels,
                    COALESCE(SUM(m.message_count), 0) AS message_count
                FROM title_hours th
                LEFT JOIN int.int_chat__hourly_channel_activity m
                    ON m.channel = th.channel AND m.hour_bucket = th.hour_bucket
                GROUP BY th.title, th.category
            ),
            title_donations AS (
                SELECT title, category, SUM(donation_delta_eur) AS donations_eur
                FROM marts.mart_donations__by_title
                WHERE ingested_at BETWEEN :start AND :end
                GROUP BY title, category
            )
            SELECT
                COALESCE(tm.title, td.title) AS title,
                COALESCE(tm.category, td.category) AS category,
                COALESCE(tm.channels, 0) AS channels,
                COALESCE(tm.message_count, 0) AS message_count,
                COALESCE(td.donations_eur, 0) AS donations_eur
            FROM title_messages tm
            FULL OUTER JOIN title_donations td ON td.title = tm.title AND td.category = tm.category
            ORDER BY message_count DESC, donations_eur DESC
            LIMIT 20
        """)
        return self._run(
            query, {"start": start.replace(tzinfo=PARIS), "end": end.replace(tzinfo=PARIS)}
        )

    def chatter_breakdown(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.chatter_breakdown`.

        Combines the loyalty-profile mart with the bot-signal mart (real
        username, account age, message-timing regularity), the account-age
        mart, and `mart_chatters__breadth_depth_lifespan` (first/last message,
        lifespan). Usernames fall back to the raw `chatter_id` when a chatter
        has no `bot_signal` row (mirrors `top_chatters`). Filtered by
        first/last-message overlap with `[start, end]`, same as
        `top_chatters` — this is what makes the whole Chatters page
        filterable, unlike most other per-chatter marts.
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
                COALESCE(a.account_age_bucket, 'unknown') AS account_age_bucket,
                l.first_message_at,
                l.last_message_at,
                l.lifespan_hours,
                l.avg_messages_per_channel
            FROM marts.mart_chatters__profile p
            LEFT JOIN marts.mart_chatters__bot_signal b ON b.chatter_id = p.chatter_id
            LEFT JOIN marts.mart_chatters__account_age_profile a ON a.chatter_id = p.chatter_id
            JOIN marts.mart_chatters__breadth_depth_lifespan l ON l.chatter_id = p.chatter_id
            WHERE l.first_message_at <= :end AND l.last_message_at >= :start
            ORDER BY p.total_message_count DESC
        """)
        return self._run(
            query, {"start": start.replace(tzinfo=PARIS), "end": end.replace(tzinfo=PARIS)}
        )

    def chatter_channel_breakdown(self, chatter_id: str) -> pl.DataFrame:
        """See `DataSource.chatter_channel_breakdown`."""
        query = sa.text("""
            SELECT channel, message_count, first_message_at, last_message_at, active_hours
            FROM int.int_chat__chatter_channel_activity
            WHERE chatter_id = :chatter_id
            ORDER BY message_count DESC
        """)
        return self._run(query, {"chatter_id": chatter_id})

    def channel_chatter_breakdown(
        self, channel: str, start: datetime, end: datetime
    ) -> pl.DataFrame:
        """See `DataSource.channel_chatter_breakdown`.

        No mart is grained (channel, chatter) *with* badge/emote detail —
        `mart_chat__badge_and_verbosity` has badges but only rolled up to
        one row per channel, and `int_chat__chatter_channel_activity` has
        the chatter grain but not badges — so this reads straight from
        `stg.stg_bronze__live_chat`, filtered to one channel (indexed;
        fast even though the unfiltered table is ~370k rows), and classifies
        each message into exactly one badge tier by the same precedence
        Twitch itself displays badges in (broadcaster/moderator > vip >
        subscriber > plain viewer) so a message with multiple badges isn't
        double-counted across tiers. `lead_moderator` counts as moderator.
        Emote usage sums every emote's per-message count from the `emotes`
        JSONB column (`{emote_id: count_in_that_message}`).
        """
        query = sa.text("""
            SELECT
                chatter_id,
                MAX(chatter) AS chatter,
                COUNT(*) AS message_count,
                MIN(message_sent_at) AS first_message_at,
                MAX(message_sent_at) AS last_message_at,
                COUNT(*) FILTER (
                    WHERE badges ? 'moderator'
                       OR badges ? 'lead_moderator'
                       OR badges ? 'broadcaster'
                ) AS moderator_message_count,
                COUNT(*) FILTER (
                    WHERE NOT (
                        badges ? 'moderator' OR badges ? 'lead_moderator' OR badges ? 'broadcaster'
                    )
                    AND badges ? 'vip'
                ) AS vip_message_count,
                COUNT(*) FILTER (
                    WHERE NOT (
                        badges ? 'moderator' OR badges ? 'lead_moderator' OR badges ? 'broadcaster'
                        OR badges ? 'vip'
                    )
                    AND badges ? 'subscriber'
                ) AS subscriber_message_count,
                COUNT(*) FILTER (
                    WHERE NOT (
                        badges ? 'moderator' OR badges ? 'lead_moderator' OR badges ? 'broadcaster'
                        OR badges ? 'vip' OR badges ? 'subscriber'
                    )
                ) AS plain_viewer_message_count,
                COALESCE(
                    SUM(COALESCE((SELECT SUM(value::int) FROM jsonb_each_text(emotes)), 0)), 0
                ) AS emote_usage_count
            FROM stg.stg_bronze__live_chat
            WHERE channel = :channel AND message_sent_at BETWEEN :start AND :end
            GROUP BY chatter_id
            ORDER BY message_count DESC
        """)
        return self._run(
            query,
            {
                "channel": channel,
                "start": start.replace(tzinfo=PARIS),
                "end": end.replace(tzinfo=PARIS),
            },
        )

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

    def donations_by_category(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.donations_by_category`.

        `mart_donations__by_title` already attributes each donation to the
        category being played at the time (at the dbt layer) — pre-event
        this is expected to be all zero, and fills in as donations start
        flowing. This used to hand-roll the same attribution via an
        hour-bucket join against `stg_bronze__metadata_snapshots`; the mart
        now does that more accurately, so this just filters and sums it.
        """
        query = sa.text("""
            SELECT
                category,
                COALESCE(SUM(donation_delta_eur), 0) AS donations_eur,
                COUNT(DISTINCT twitch_login) AS channels
            FROM marts.mart_donations__by_title
            WHERE ingested_at BETWEEN :start AND :end
            GROUP BY category
            ORDER BY donations_eur DESC
        """)
        return self._run(
            query, {"start": start.replace(tzinfo=PARIS), "end": end.replace(tzinfo=PARIS)}
        )

    def category_change_impact(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.category_change_impact`."""
        query = sa.text("""
            SELECT
                channel, changed_at, prev_category, new_category,
                viewer_count_at_change, avg_viewer_count_hour_after
            FROM marts.mart_streams__category_timeline
            WHERE changed_at BETWEEN :start AND :end
                AND viewer_count_at_change IS NOT NULL
                AND avg_viewer_count_hour_after IS NOT NULL
            ORDER BY ABS(avg_viewer_count_hour_after - viewer_count_at_change) DESC
            LIMIT 15
        """)
        return self._run(
            query, {"start": start.replace(tzinfo=PARIS), "end": end.replace(tzinfo=PARIS)}
        )

    def chatter_migrations(self) -> pl.DataFrame:
        """See `DataSource.chatter_migrations`."""
        query = sa.text("""
            SELECT from_channel, to_channel, hop_count, distinct_chatters_hopping, avg_gap_seconds
            FROM marts.mart_community__chatter_migrations
            ORDER BY hop_count DESC
            LIMIT 20
        """)
        return self._run(query)

    def donation_spike_moments(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.donation_spike_moments`."""
        query = sa.text("""
            SELECT
                twitch_login, display_name, ingested_at, donation_delta_eur,
                title, category, chat_messages_that_hour
            FROM marts.mart_donations__spike_moments
            WHERE ingested_at BETWEEN :start AND :end
            ORDER BY donation_delta_eur DESC
            LIMIT 15
        """)
        return self._run(
            query, {"start": start.replace(tzinfo=PARIS), "end": end.replace(tzinfo=PARIS)}
        )

    def goal_ambition_vs_reality(self) -> pl.DataFrame:
        """See `DataSource.goal_ambition_vs_reality`."""
        query = sa.text("""
            SELECT
                twitch_login, total_goal_amount_eur_for_streamer,
                latest_donation_amount_eur, surplus_eur, pct_of_goals_covered
            FROM marts.mart_donations__goal_ambition_vs_reality
            ORDER BY pct_of_goals_covered ASC
        """)
        return self._run(query)

    def event_daily_rollup(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.event_daily_rollup`."""
        query = sa.text("""
            SELECT
                day_bucket, message_count, active_channels, donation_delta_eur,
                total_donation_amount_eur_end_of_day, avg_total_viewer_count
            FROM marts.mart_event__daily_rollup
            WHERE day_bucket BETWEEN date_trunc('day', :start) AND date_trunc('day', :end)
            ORDER BY day_bucket
        """)
        return self._run(
            query, {"start": start.replace(tzinfo=PARIS), "end": end.replace(tzinfo=PARIS)}
        )

    def streamer_night_shift(self, channel: str) -> pl.DataFrame:
        """See `DataSource.streamer_night_shift`.

        `hour_of_day` is bucketed in UTC by the dbt model, same as
        `mart_streamers__diurnal_profile` — shifted by +2 here to Europe/Paris
        for display, same reasoning as `streamer_diurnal_profile`. `is_overnight`
        is left as the mart computed it (against the original UTC hour), not
        recomputed against the shifted hour — it's a business flag from the
        model, not something to guess a new definition for here.
        """
        query = sa.text("""
            SELECT
                (hour_of_day + 2) % 24 AS hour_of_day,
                donation_delta_eur, avg_viewer_count, donation_eur_per_viewer, is_overnight
            FROM marts.mart_streamers__night_shift
            WHERE channel = :channel
            ORDER BY (hour_of_day + 2) % 24
        """)
        return self._run(query, {"channel": channel})

    def chat_spikes(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.chat_spikes`."""
        query = sa.text("""
            SELECT
                channel, hour_bucket, message_count, unique_chatter_count,
                channel_avg_message_count, channel_stddev_message_count, message_count_zscore
            FROM marts.mart_chat__spikes
            WHERE hour_bucket BETWEEN :start AND :end
            ORDER BY message_count_zscore DESC
            LIMIT 15
        """)
        return self._run(
            query, {"start": start.replace(tzinfo=PARIS), "end": end.replace(tzinfo=PARIS)}
        )

    def new_chatters_per_channel(self, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.new_chatters_per_channel`."""
        query = sa.text("""
            SELECT channel, day_bucket, new_chatters_to_channel
            FROM marts.mart_chat__new_chatters_per_channel
            WHERE day_bucket BETWEEN date_trunc('day', :start) AND date_trunc('day', :end)
            ORDER BY day_bucket, new_chatters_to_channel DESC
        """)
        return self._run(
            query, {"start": start.replace(tzinfo=PARIS), "end": end.replace(tzinfo=PARIS)}
        )

    def search_emote_catalog(self, query: str) -> pl.DataFrame:
        """See `DataSource.search_emote_catalog`."""
        sql = sa.text("""
            SELECT DISTINCT service, emote_id, emote_code
            FROM stg.stg_bronze__emote_catalog
            WHERE emote_code ILIKE :pattern
            ORDER BY emote_code
            LIMIT 20
        """)
        return self._run(sql, {"pattern": f"%{query}%"})

    def emote_usage_search(self, emote_id: str, start: datetime, end: datetime) -> pl.DataFrame:
        """See `DataSource.emote_usage_search`.

        Queries `stg.stg_bronze__live_chat` directly rather than a `marts`
        model — per-chatter emote usage isn't modeled anywhere above raw/
        staging (the `marts`/`int` emote marts only go down to channel+hour).
        `emotes` is a JSONB object keyed by emote id (e.g. `{"425618": 1}`);
        `jsonb_exists` checks for that key, same as the `?` operator but
        without any ambiguity against SQLAlchemy's `:name` bind-param syntax.
        """
        query = sa.text("""
            SELECT chatter, channel, message_text, message_sent_at
            FROM stg.stg_bronze__live_chat
            WHERE jsonb_exists(emotes, :emote_id)
                AND message_sent_at BETWEEN :start AND :end
            ORDER BY message_sent_at DESC
            LIMIT 200
        """)
        return self._run(
            query,
            {
                "emote_id": emote_id,
                "start": start.replace(tzinfo=PARIS),
                "end": end.replace(tzinfo=PARIS),
            },
        )

    def chat_message_search(
        self,
        start: datetime,
        end: datetime,
        *,
        channel: str | None = None,
        chatter_query: str | None = None,
        text_query: str | None = None,
        limit: int = 500,
    ) -> pl.DataFrame:
        """See `DataSource.chat_message_search`.

        Queries `stg.stg_bronze__live_chat` directly, same as
        `emote_usage_search` above — no mart carries individual messages.
        Optional filters are `(:param IS NULL OR ...)` clauses rather than
        conditionally building the SQL string, so every call goes through
        one static, fully parameterized query (no per-call SQL assembly, and
        no risk of interpolating user-typed search text into the query
        itself); an explicit `CAST(:param AS text)` on each is required
        since `psycopg` can't otherwise infer a bind parameter's type from a
        bare `NULL` (and SQLAlchemy's `:name` parser doesn't accept a `::`
        cast directly against the bind param token itself). `badge` is
        classified with the same broadcaster/moderator > vip > subscriber >
        plain-viewer precedence as
        `channel_chatter_breakdown`, so a message with multiple badges isn't
        ambiguous here either. `has_long_digit_suffix` is joined in from the
        bot-signal mart (same `LEFT JOIN ... COALESCE(..., false)` as
        `chatter_breakdown`/`top_chatters`) so the page can offer the same
        `bot_filter_expr` "hide likely bots" control every other
        chatter-listing page has, instead of a one-off, weaker heuristic
        just for this page.
        """
        query = sa.text("""
            SELECT
                lc.message_sent_at,
                lc.channel,
                lc.chatter_id,
                lc.chatter,
                lc.message_text,
                CASE
                    WHEN lc.badges ? 'moderator' OR lc.badges ? 'lead_moderator'
                        OR lc.badges ? 'broadcaster' THEN 'moderator'
                    WHEN lc.badges ? 'vip' THEN 'vip'
                    WHEN lc.badges ? 'subscriber' THEN 'subscriber'
                    ELSE 'plain_viewer'
                END AS badge,
                COALESCE(b.has_long_digit_suffix, false) AS has_long_digit_suffix
            FROM stg.stg_bronze__live_chat lc
            LEFT JOIN marts.mart_chatters__bot_signal b ON b.chatter_id = lc.chatter_id
            WHERE lc.message_sent_at BETWEEN :start AND :end
                AND (CAST(:channel AS text) IS NULL OR lc.channel = :channel)
                AND (
                    CAST(:chatter_query AS text) IS NULL
                    OR lc.chatter ILIKE '%' || :chatter_query || '%'
                )
                AND (
                    CAST(:text_query AS text) IS NULL
                    OR lc.message_text ILIKE '%' || :text_query || '%'
                )
            ORDER BY lc.message_sent_at DESC
            LIMIT :limit
        """)
        return self._run(
            query,
            {
                "start": start.replace(tzinfo=PARIS),
                "end": end.replace(tzinfo=PARIS),
                "channel": channel,
                "chatter_query": chatter_query,
                "text_query": text_query,
                "limit": limit,
            },
        )

    @staticmethod
    def _run(query: sa.TextClause, params: dict[str, object] | None = None) -> pl.DataFrame:
        """Execute a parameterized, read-only query and return it as a DataFrame.

        Postgres `NUMERIC`/`DECIMAL` columns come back from `pl.read_database`
        as polars `Decimal`, which doesn't support common arithmetic (e.g.
        `.pow()`) that plain `float` columns do. Every such column is cast to
        `Float64` here, once, rather than leaving every caller to remember to
        do it — `NUMERIC` columns are common in this schema (most `_eur`
        amounts) and it's an easy thing to trip over otherwise.

        Every `Datetime` column is also converted to Europe/Paris wall-clock
        time here, then made tz-naive — the event happens in France, and the
        warehouse stores `timestamptz` values labeled UTC, so every chart
        axis/table/caption should show French local time without every page
        having to remember to convert. Naive rather than tz-aware because
        Streamlit's widgets and Plotly's charts render a tz-aware datetime in
        the *viewer's* browser timezone, not the one attached in Python —
        naive values have nothing for the frontend to reinterpret.

        Args:
            query: A `sqlalchemy.text()` statement with named bind parameters.
            params: Bound parameter values for the statement.

        Returns:
            The query result as a polars DataFrame, with no `Decimal`
            columns and every timestamp as Europe/Paris wall-clock time
            (tz-naive).
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
            # Shift to Europe/Paris wall-clock time, then drop the tzinfo.
            # Streamlit's widgets (the date-range slider) and dataframe grid,
            # and Plotly's charts, all format tz-aware datetimes using the
            # *viewer's browser* timezone rather than the one attached in
            # Python — so a tz-aware value renders as whatever offset the
            # browser happens to be in, not necessarily Paris. A naive
            # datetime has nothing for any of those to reinterpret: every
            # frontend just displays the wall-clock numbers as given, which
            # are already correct Paris local time at this point.
            df = df.with_columns(
                col.dt.convert_time_zone(PARIS_TZ_NAME).dt.replace_time_zone(None).alias(name)
            )
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
def get_event_bounds() -> tuple[datetime, datetime] | None:
    """Cached accessor for the event's own timestamp span.

    Reuses `get_donation_timeseries()` (already cached) rather than issuing a
    new query — the same source `app/🏠_Home.py`'s duration KPI already reads.

    Returns:
        `(earliest, latest)` timestamp in the donation timeseries, or `None`
        if there's no data yet.
    """
    df = get_donation_timeseries()
    if df.is_empty():
        return None
    return cast(datetime, df["timestamp"].min()), cast(datetime, df["timestamp"].max())


@st.cache_data(ttl=60, show_spinner=False)
def get_event_phase_breakdown() -> pl.DataFrame:
    """Cached, page-facing accessor for the event-phase donation breakdown.

    Returns:
        See `DataSource.event_phase_breakdown`.
    """
    return get_data_source().event_phase_breakdown()


@st.cache_data(ttl=60, show_spinner=False)
def get_leaderboard_movers(end: datetime) -> pl.DataFrame:
    """Cached, page-facing accessor for the biggest donation-rank movers.

    Args:
        end: Show ranks as of this timestamp.

    Returns:
        See `DataSource.leaderboard_movers`.
    """
    return get_data_source().leaderboard_movers(end)


@st.cache_data(ttl=60, show_spinner=False)
def get_data_quality_check() -> pl.DataFrame:
    """Cached, page-facing accessor for the donation-total reconciliation check.

    Returns:
        See `DataSource.data_quality_check`.
    """
    return get_data_source().data_quality_check()


@st.cache_data(ttl=300, show_spinner=False)
def get_schema_table_stats() -> pl.DataFrame:
    """Cached, page-facing accessor for stg/int/marts row counts and sizes.

    A 5-minute TTL, longer than the app's usual 60s — table row counts and
    on-disk sizes change slowly enough (unlike live event figures) that a
    short TTL would just re-run the catalog scan for the same answer.

    Returns:
        See `DataSource.schema_table_stats`.
    """
    return get_data_source().schema_table_stats()


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


@st.cache_data(ttl=60, show_spinner=False)
def get_donation_forecast_features(
    start: datetime, end: datetime, cutoff: datetime
) -> pl.DataFrame:
    """Cached, page-facing accessor for donation-forecasting training features.

    Args:
        start: Start of the event window streamers are drawn from.
        end: End of the event window streamers are drawn from.
        cutoff: The mid-event point in time to snapshot features at.

    Returns:
        See `DataSource.donation_forecast_features`.
    """
    return get_data_source().donation_forecast_features(start, end, cutoff)


@st.cache_data(ttl=60, show_spinner="Loading category data...")
def get_category_breakdown(start: datetime, end: datetime) -> pl.DataFrame:
    """Cached, page-facing accessor for the per-category channel-hours breakdown.

    Args:
        start: Start of the window to narrow to.
        end: End of the window to narrow to.

    Returns:
        See `DataSource.category_breakdown`.
    """
    return get_data_source().category_breakdown(start, end)


@st.cache_data(ttl=60, show_spinner=False)
def get_category_popularity_timeseries(start: datetime, end: datetime) -> pl.DataFrame:
    """Cached, page-facing accessor for hour-by-hour category popularity.

    Args:
        start: Start of the window to narrow to.
        end: End of the window to narrow to.

    Returns:
        See `DataSource.category_popularity_timeseries`.
    """
    return get_data_source().category_popularity_timeseries(start, end)


@st.cache_data(ttl=60, show_spinner=False)
def get_viewership_timeseries() -> pl.DataFrame:
    """Cached, page-facing accessor for event-wide concurrent viewership.

    Returns:
        See `DataSource.viewership_timeseries`.
    """
    return get_data_source().viewership_timeseries()


@st.cache_data(ttl=60, show_spinner=False)
def get_channel_viewership_leaderboard_timeseries(
    start: datetime, end: datetime, top_n: int
) -> pl.DataFrame:
    """Cached, page-facing accessor for the hour-by-hour top-N viewer leaderboard.

    Args:
        start: Start of the window to narrow to.
        end: End of the window to narrow to.
        top_n: How many channels to include, ranked by overall average
            viewers across the window.

    Returns:
        See `DataSource.channel_viewership_leaderboard_timeseries`.
    """
    return get_data_source().channel_viewership_leaderboard_timeseries(start, end, top_n)


@st.cache_data(ttl=60, show_spinner=False)
def get_channel_messages_leaderboard_timeseries(
    start: datetime, end: datetime, top_n: int
) -> pl.DataFrame:
    """Cached, page-facing accessor for the hour-by-hour top-N message leaderboard.

    Args:
        start: Start of the window to narrow to.
        end: End of the window to narrow to.
        top_n: How many channels to include, ranked by overall message count
            across the window.

    Returns:
        See `DataSource.channel_messages_leaderboard_timeseries`.
    """
    return get_data_source().channel_messages_leaderboard_timeseries(start, end, top_n)


@st.cache_data(ttl=60, show_spinner=False)
def get_channel_donations_leaderboard_timeseries(
    start: datetime, end: datetime, top_n: int
) -> pl.DataFrame:
    """Cached, page-facing accessor for the hour-by-hour top-N donation leaderboard.

    Args:
        start: Start of the window to narrow to.
        end: End of the window to narrow to.
        top_n: How many channels to include, ranked by each streamer's own
            highest cumulative total reached in the window.

    Returns:
        See `DataSource.channel_donations_leaderboard_timeseries`.
    """
    return get_data_source().channel_donations_leaderboard_timeseries(start, end, top_n)


# The 7 accessors below all read `stg.stg_bronze__live_chat` — 8.3M rows,
# 1.8GB, and (confirmed via `EXPLAIN (ANALYZE, BUFFERS)` against the real
# warehouse) genuinely no index at all, not even a primary key. Every one
# of them costs 1.5-8s even sampled, because Postgres has no way to seek
# to a date range or skip rows without an index — it must sequentially
# scan and evaluate the full filter (including any regex) against all
# 8.3M rows regardless of how selective `random() < rate` or `LIMIT` are;
# confirmed directly: cutting the target sample size 50x changed nothing,
# because the scan cost is the *table's*, not the *sample's*. That's a
# warehouse-side gap this app's read-only connection can't fix (adding an
# index is a `zevent-db` change, a separate project — see the About page's
# "related projects"). The only lever available here is caching more
# aggressively than the app's usual 60s: these figures don't need
# sub-minute freshness (hostility/sentiment/trending phrases are already
# hour-bucketed aggregates), so a 5-minute TTL cuts how often *anyone*
# pays this cost by 5x, without the data going meaningfully stale.
@st.cache_data(ttl=300, show_spinner=False)
def get_chat_hype_components_timeseries(start: datetime, end: datetime) -> pl.DataFrame:
    """Cached, page-facing accessor for every channel-hour's raw, unweighted hype components.

    Args:
        start: Start of the window to narrow to.
        end: End of the window to narrow to.

    Returns:
        See `DataSource.chat_hype_components_timeseries`.
    """
    return get_data_source().chat_hype_components_timeseries(start, end)


@st.cache_data(ttl=300, show_spinner=False)
def get_channel_sentiment_leaderboard_timeseries(
    start: datetime, end: datetime, top_n: int
) -> pl.DataFrame:
    """Cached, page-facing accessor for the hour-by-hour top-N chat sentiment leaderboard.

    Args:
        start: Start of the window to narrow to.
        end: End of the window to narrow to.
        top_n: How many channels to include, ranked by overall sentiment
            (most positive first) across the window.

    Returns:
        See `DataSource.channel_sentiment_leaderboard_timeseries`.
    """
    return get_data_source().channel_sentiment_leaderboard_timeseries(start, end, top_n)


@st.cache_data(ttl=300, show_spinner=False)
def get_channel_toxicity_leaderboard_timeseries(
    start: datetime, end: datetime, top_n: int
) -> pl.DataFrame:
    """Cached, page-facing accessor for the hour-by-hour top-N chat toxicity leaderboard.

    Args:
        start: Start of the window to narrow to.
        end: End of the window to narrow to.
        top_n: How many channels to include, ranked by overall toxicity
            (most hostile first) across the window.

    Returns:
        See `DataSource.channel_toxicity_leaderboard_timeseries`.
    """
    return get_data_source().channel_toxicity_leaderboard_timeseries(start, end, top_n)


@st.cache_data(ttl=300, show_spinner=False)
def get_chat_toxicity_examples(start: datetime, end: datetime, limit: int) -> pl.DataFrame:
    """Cached, page-facing accessor for a sample of messages flagged as hostile.

    Args:
        start: Start of the window to narrow to.
        end: End of the window to narrow to.
        limit: How many example messages to return.

    Returns:
        See `DataSource.chat_toxicity_examples`.
    """
    return get_data_source().chat_toxicity_examples(start, end, limit)


@st.cache_data(ttl=300, show_spinner=False)
def get_chat_message_sample(start: datetime, end: datetime, limit: int) -> pl.DataFrame:
    """Cached, page-facing accessor for a general-purpose random message sample.

    Args:
        start: Start of the window to narrow to.
        end: End of the window to narrow to.
        limit: How many messages to return.

    Returns:
        See `DataSource.chat_message_sample`.
    """
    return get_data_source().chat_message_sample(start, end, limit)


@st.cache_data(ttl=300, show_spinner=False)
def get_chat_mood_timeseries(start: datetime, end: datetime) -> pl.DataFrame:
    """Cached, page-facing accessor for event-wide chat hype/sentiment, hour by hour.

    Args:
        start: Start of the window to narrow to.
        end: End of the window to narrow to.

    Returns:
        See `DataSource.chat_mood_timeseries`.
    """
    return get_data_source().chat_mood_timeseries(start, end)


@st.cache_data(ttl=300, show_spinner=False)
def get_chat_trending_phrases(start: datetime, end: datetime, top_n: int) -> pl.DataFrame:
    """Cached, page-facing accessor for the event-wide trending/copypasta phrase leaderboard.

    Args:
        start: Start of the window to narrow to.
        end: End of the window to narrow to.
        top_n: How many repeated phrases to include, ranked by repeat count.

    Returns:
        See `DataSource.chat_trending_phrases`.
    """
    return get_data_source().chat_trending_phrases(start, end, top_n)


@st.cache_data(ttl=60, show_spinner=False)
def get_chat_trending_keywords(channel: str, start: datetime, end: datetime) -> pl.DataFrame:
    """Cached, page-facing accessor for one channel's hour-by-hour trending keywords.

    Args:
        channel: The channel/login to analyze.
        start: Start of the window to narrow to.
        end: End of the window to narrow to.

    Returns:
        See `DataSource.chat_trending_keywords`.
    """
    return get_data_source().chat_trending_keywords(channel, start, end)


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
def get_chat_channel_list() -> list[str]:
    """Cached, page-facing accessor for every channel with chat activity.

    Returns:
        See `DataSource.chat_channel_list`.
    """
    return get_data_source().chat_channel_list()


@st.cache_data(ttl=60, show_spinner=False)
def get_chatter_directory() -> pl.DataFrame:
    """Cached, page-facing accessor for the global chatter-filter picker population.

    Returns:
        See `DataSource.chatter_directory`.
    """
    return get_data_source().chatter_directory()


@st.cache_data(ttl=60, show_spinner=False)
def get_top_emotes(start: datetime, end: datetime) -> pl.DataFrame:
    """Cached, page-facing accessor for the most-used emotes.

    Args:
        start: Start of the window to narrow to.
        end: End of the window to narrow to.

    Returns:
        See `DataSource.top_emotes`.
    """
    return get_data_source().top_emotes(start, end)


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
def get_top_chatters(start: datetime, end: datetime) -> pl.DataFrame:
    """Cached, page-facing accessor for the most active chatters.

    Args:
        start: Start of the window to narrow to.
        end: End of the window to narrow to.

    Returns:
        See `DataSource.top_chatters`.
    """
    return get_data_source().top_chatters(start, end)


@st.cache_data(ttl=60, show_spinner="Loading chatter leaderboard...")
def get_top_chatters_for_channels(
    channels: list[str], start: datetime, end: datetime
) -> pl.DataFrame:
    """Cached, page-facing accessor for the most active chatters across a channel set.

    Args:
        channels: The channels to include — a chatter's `message_count` is
            summed across only these, not the whole event.
        start: Start of the window to narrow to.
        end: End of the window to narrow to.

    Returns:
        See `DataSource.top_chatters_for_channels`.
    """
    return get_data_source().top_chatters_for_channels(channels, start, end)


@st.cache_data(ttl=60, show_spinner=False)
def get_top_chatter_per_channel(start: datetime, end: datetime) -> pl.DataFrame:
    """Cached, page-facing accessor for each channel's single most active chatter.

    Args:
        start: Start of the window to narrow to.
        end: End of the window to narrow to.

    Returns:
        See `DataSource.top_chatter_per_channel`.
    """
    return get_data_source().top_chatter_per_channel(start, end)


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
def get_chatter_day1_retention() -> pl.DataFrame:
    """Cached, page-facing accessor for day-N retention of the event's first-day chatters.

    Returns:
        See `DataSource.chatter_day1_retention`.
    """
    return get_data_source().chatter_day1_retention()


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
def get_title_leaderboard(start: datetime, end: datetime) -> pl.DataFrame:
    """Cached, page-facing accessor for the stream-title leaderboard.

    Args:
        start: Start of the window to narrow to.
        end: End of the window to narrow to.

    Returns:
        See `DataSource.title_leaderboard`.
    """
    return get_data_source().title_leaderboard(start, end)


@st.cache_data(ttl=60, show_spinner="Loading chatter data...")
def get_chatter_breakdown(start: datetime, end: datetime) -> pl.DataFrame:
    """Cached, page-facing accessor for the per-chatter breakdown.

    Args:
        start: Start of the window to narrow to.
        end: End of the window to narrow to.

    Returns:
        See `DataSource.chatter_breakdown`.
    """
    return get_data_source().chatter_breakdown(start, end)


@st.cache_data(ttl=60, show_spinner=False)
def get_chatter_channel_breakdown(chatter_id: str) -> pl.DataFrame:
    """Cached, page-facing accessor for one chatter's per-channel activity.

    Args:
        chatter_id: The chatter's id to look up.

    Returns:
        See `DataSource.chatter_channel_breakdown`.
    """
    return get_data_source().chatter_channel_breakdown(chatter_id)


@st.cache_data(ttl=60, show_spinner="Loading chatters for this channel...")
def get_channel_chatter_breakdown(channel: str, start: datetime, end: datetime) -> pl.DataFrame:
    """Cached, page-facing accessor for every chatter active in one channel.

    Args:
        channel: The channel/login to look up.
        start: Start of the window to narrow to.
        end: End of the window to narrow to.

    Returns:
        See `DataSource.channel_chatter_breakdown`.
    """
    return get_data_source().channel_chatter_breakdown(channel, start, end)


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
def get_donations_by_category(start: datetime, end: datetime) -> pl.DataFrame:
    """Cached, page-facing accessor for donations attributed to Twitch category.

    Args:
        start: Start of the window to narrow to.
        end: End of the window to narrow to.

    Returns:
        See `DataSource.donations_by_category`.
    """
    return get_data_source().donations_by_category(start, end)


@st.cache_data(ttl=60, show_spinner=False)
def get_category_change_impact(start: datetime, end: datetime) -> pl.DataFrame:
    """Cached, page-facing accessor for category switches ranked by viewer impact.

    Args:
        start: Start of the window to narrow to.
        end: End of the window to narrow to.

    Returns:
        See `DataSource.category_change_impact`.
    """
    return get_data_source().category_change_impact(start, end)


@st.cache_data(ttl=60, show_spinner=False)
def get_chatter_migrations() -> pl.DataFrame:
    """Cached, page-facing accessor for channel-to-channel chatter hop counts.

    Returns:
        See `DataSource.chatter_migrations`.
    """
    return get_data_source().chatter_migrations()


@st.cache_data(ttl=60, show_spinner=False)
def get_donation_spike_moments(start: datetime, end: datetime) -> pl.DataFrame:
    """Cached, page-facing accessor for standout single-donation moments.

    Args:
        start: Start of the window to narrow to.
        end: End of the window to narrow to.

    Returns:
        See `DataSource.donation_spike_moments`.
    """
    return get_data_source().donation_spike_moments(start, end)


@st.cache_data(ttl=60, show_spinner=False)
def get_goal_ambition_vs_reality() -> pl.DataFrame:
    """Cached, page-facing accessor for per-streamer donation-goal coverage.

    Returns:
        See `DataSource.goal_ambition_vs_reality`.
    """
    return get_data_source().goal_ambition_vs_reality()


@st.cache_data(ttl=60, show_spinner=False)
def get_event_daily_rollup(start: datetime, end: datetime) -> pl.DataFrame:
    """Cached, page-facing accessor for day-bucketed event-wide totals.

    Args:
        start: Start of the window to narrow to.
        end: End of the window to narrow to.

    Returns:
        See `DataSource.event_daily_rollup`.
    """
    return get_data_source().event_daily_rollup(start, end)


@st.cache_data(ttl=60, show_spinner=False)
def get_streamer_night_shift(channel: str) -> pl.DataFrame:
    """Cached, page-facing accessor for one streamer's donation efficiency by hour of day.

    Args:
        channel: The streamer's channel/login to look up.

    Returns:
        See `DataSource.streamer_night_shift`.
    """
    return get_data_source().streamer_night_shift(channel)


@st.cache_data(ttl=60, show_spinner=False)
def get_chat_spikes(start: datetime, end: datetime) -> pl.DataFrame:
    """Cached, page-facing accessor for the biggest per-channel message-volume anomalies.

    Args:
        start: Start of the window to narrow to.
        end: End of the window to narrow to.

    Returns:
        See `DataSource.chat_spikes`.
    """
    return get_data_source().chat_spikes(start, end)


@st.cache_data(ttl=60, show_spinner=False)
def get_new_chatters_per_channel(start: datetime, end: datetime) -> pl.DataFrame:
    """Cached, page-facing accessor for new-chatter counts per channel, per day.

    Args:
        start: Start of the window to narrow to.
        end: End of the window to narrow to.

    Returns:
        See `DataSource.new_chatters_per_channel`.
    """
    return get_data_source().new_chatters_per_channel(start, end)


@st.cache_data(ttl=60, show_spinner=False)
def get_emote_catalog_search(query: str) -> pl.DataFrame:
    """Cached, page-facing accessor for emote-catalog search by code.

    Args:
        query: Substring to match against emote codes (case-insensitive).

    Returns:
        See `DataSource.search_emote_catalog`.
    """
    return get_data_source().search_emote_catalog(query)


@st.cache_data(ttl=60, show_spinner="Searching chat...")
def get_emote_usage_search(emote_id: str, start: datetime, end: datetime) -> pl.DataFrame:
    """Cached, page-facing accessor for individual chat messages using one emote.

    Args:
        emote_id: The emote's catalog id to search for.
        start: Start of the window to narrow to.
        end: End of the window to narrow to.

    Returns:
        See `DataSource.emote_usage_search`.
    """
    return get_data_source().emote_usage_search(emote_id, start, end)


@st.cache_data(ttl=60, show_spinner="Searching chat...")
def get_chat_message_search(
    start: datetime,
    end: datetime,
    *,
    channel: str | None = None,
    chatter_query: str | None = None,
    text_query: str | None = None,
    limit: int = 500,
) -> pl.DataFrame:
    """Cached, page-facing accessor for browsing individual chat messages.

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
        See `DataSource.chat_message_search`.
    """
    return get_data_source().chat_message_search(
        start,
        end,
        channel=channel,
        chatter_query=chatter_query,
        text_query=text_query,
        limit=limit,
    )
