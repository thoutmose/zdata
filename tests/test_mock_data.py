from datetime import timedelta
from typing import cast

import polars as pl
from app.data import mock


def test_donation_timeseries_is_monotonically_increasing() -> None:
    df = mock.donation_timeseries()
    assert (df["cumulative_amount_eur"].diff().drop_nulls() >= 0).all()


def test_donation_timeseries_is_deterministic() -> None:
    assert mock.donation_timeseries().equals(mock.donation_timeseries())


def test_event_phase_breakdown_covers_all_phases() -> None:
    df = mock.event_phase_breakdown()
    assert set(df["phase"]) == {"opening", "middle", "final_push"}


def test_leaderboard_movers_sorted_by_absolute_change() -> None:
    df = mock.leaderboard_movers()
    assert (df["rank_change"].abs().diff().drop_nulls() <= 0).all()


def test_data_quality_check_has_one_row() -> None:
    df = mock.data_quality_check()
    assert len(df) == 1
    assert list(df.columns) == ["checked_at", "divergence_eur"]


def test_streamer_breakdown_has_expected_columns() -> None:
    df = mock.streamer_breakdown()
    assert "channel" in df.columns
    assert "streamer" in df.columns
    assert "team" not in df.columns
    assert len(df) > 0
    assert (df["amount_eur"] > 0).all()


def test_streamer_diurnal_profile_has_24_hours() -> None:
    df = mock.streamer_diurnal_profile("zevrix")
    assert len(df) == 24
    assert list(df["hour_of_day"]) == list(range(24))


def test_donation_forecast_features_mid_snapshot_never_exceeds_final() -> None:
    df = mock.donation_forecast_features(mock._EVENT_START + timedelta(hours=20))
    assert len(df) == len(mock.streamer_breakdown())
    assert (df["amount_eur_mid"] <= df["amount_eur"] + 1e-6).all()
    assert (df["peak_viewers_mid"] >= 0).all()


def test_donation_forecast_features_at_event_start_is_near_zero() -> None:
    df = mock.donation_forecast_features(mock._EVENT_START)
    # A `cutoff` at the very start of the event should clamp to the minimum
    # progress floor (5%), not literal zero — see the `np.clip(..., 0.05, 1.0)`
    # in `donation_forecast_features`.
    assert (df["amount_eur_mid"] < df["amount_eur"]).all()


def test_category_breakdown_is_sorted_descending() -> None:
    df = mock.category_breakdown()
    assert (df["channel_hours"].diff().drop_nulls() <= 0).all()


def test_viewership_timeseries_has_expected_columns() -> None:
    df = mock.viewership_timeseries()
    assert list(df.columns) == ["timestamp", "total_avg_viewer_count", "live_channel_count"]
    assert (df["live_channel_count"] > 0).all()


def test_stream_sessions_has_expected_columns() -> None:
    df = mock.stream_sessions()
    assert "channel" in df.columns
    assert "duration_hours" in df.columns


def test_goals_by_category_has_expected_columns() -> None:
    df = mock.goals_by_category()
    assert list(df.columns) == ["category", "goal_count", "streamer_count", "avg_goal_amount_eur"]
    assert len(df) > 0


def test_top_goal_setters_is_sorted_by_goal_count_descending() -> None:
    df = mock.top_goal_setters()
    assert (df["goal_count"].diff().drop_nulls() <= 0).all()


def test_chat_activity_timeseries_has_expected_columns() -> None:
    df = mock.chat_activity_timeseries()
    assert list(df.columns) == ["timestamp", "message_count", "unique_chatters"]


def test_top_chat_channels_message_composition_sums_correctly() -> None:
    df = mock.top_chat_channels()
    components = (
        df["subscriber_message_count"]
        + df["vip_message_count"]
        + df["moderator_message_count"]
        + df["plain_viewer_message_count"]
    )
    assert (components <= df["message_count"]).all()


def test_top_emotes_is_sorted_descending() -> None:
    df = mock.top_emotes()
    assert (df["usage_count"].diff().drop_nulls() <= 0).all()


def test_chatter_profile_mix_covers_all_profiles() -> None:
    df = mock.chatter_profile_mix()
    assert set(df["profile"]) == {"sedentaire", "multi_streamer", "semi_nomade", "nomade"}


def test_chatter_account_age_mix_covers_all_buckets() -> None:
    df = mock.chatter_account_age_mix()
    assert set(df["age_bucket"]) == {"new (<30d)", "1mo-1yr", "1-3yr", "3yr+", "unknown"}


def test_top_chatters_has_expected_columns() -> None:
    df = mock.top_chatters()
    assert list(df.columns) == [
        "chatter_id",
        "chatter",
        "channel",
        "message_count",
        "distinct_channel_count",
        "has_long_digit_suffix",
    ]


def test_channel_network_is_sorted_descending() -> None:
    df = mock.channel_network()
    assert (df["shared_chatter_count"].diff().drop_nulls() <= 0).all()


def test_chatter_growth_timeseries_has_expected_columns() -> None:
    df = mock.chatter_growth_timeseries()
    assert list(df.columns) == ["timestamp", "new_chatters"]
    assert (df["new_chatters"] >= 0).all()


def test_channel_hour_heatmap_covers_every_streamer() -> None:
    df = mock.channel_hour_heatmap()
    assert set(df["channel"]) == {s.lower() for s in mock._STREAMERS}


def test_goal_amount_distribution_is_right_skewed() -> None:
    df = mock.goal_amount_distribution()
    median = cast(float, df["goal_amount_eur"].median())
    mean = cast(float, df["goal_amount_eur"].mean())
    assert median < mean


def test_donation_goal_tracker_has_expected_columns() -> None:
    df = mock.donation_goal_tracker("zevrix")
    assert list(df.columns) == [
        "goal_name",
        "goal_amount_eur",
        "started_at",
        "completed_at",
        "status",
        "duration",
        "elapsed_so_far",
        "goal_category",
    ]
    assert set(df["status"]).issubset({"done", "in_progress", "not_started"})
    assert set(df["goal_category"]).issubset(
        {
            "donation",
            "recurent",
            "donation_equal",
            "donation_more_than",
            "incentive",
            "donation_largest",
            "global",
        }
    )


def test_chatter_directory_has_expected_columns_and_is_sorted_by_activity() -> None:
    df = mock.chatter_directory()
    assert list(df.columns) == ["chatter_id", "chatter", "total_message_count"]
    assert (df["total_message_count"].diff().drop_nulls() <= 0).all()


def test_channel_messages_leaderboard_timeseries_keeps_top_n_channels_full_history() -> None:
    total_hours = mock._hours().size
    df = mock.channel_messages_leaderboard_timeseries(top_n=3)
    assert list(df.columns) == ["timestamp", "channel", "message_count", "message_rank_at_hour"]
    assert df["channel"].n_unique() == 3
    # Every selected channel keeps a row for every hour it has data for, not just the
    # hours it happened to be near the very top — a real per-hour top-8 cutoff used to
    # fragment a channel's line down to a handful of isolated points.
    assert (df.group_by("channel").len()["len"] == total_hours).all()
    assert df["message_rank_at_hour"].min() == 1
    # Rank is computed against every channel, not just the selected top_n, so it isn't
    # capped at top_n.
    assert df["message_rank_at_hour"].max() > 3


def test_channel_donations_leaderboard_timeseries_keeps_top_n_channels_full_history() -> None:
    total_hours = mock._hours().size
    df = mock.channel_donations_leaderboard_timeseries(top_n=3)
    assert list(df.columns) == ["timestamp", "channel", "amount_eur", "donation_rank_at_hour"]
    assert df["channel"].n_unique() == 3
    assert (df.group_by("channel").len()["len"] == total_hours).all()
    assert df["donation_rank_at_hour"].min() == 1
    assert df["donation_rank_at_hour"].max() > 3
    # Each streamer's own cumulative total must never decrease hour to hour.
    for channel in df["channel"].unique().to_list():
        amounts = df.filter(pl.col("channel") == channel).sort("timestamp")["amount_eur"]
        assert (amounts.diff().drop_nulls() >= 0).all()


def test_channel_viewership_leaderboard_timeseries_keeps_top_n_channels_full_history() -> None:
    total_hours = mock._hours().size
    df = mock.channel_viewership_leaderboard_timeseries(top_n=3)
    assert list(df.columns) == ["timestamp", "channel", "avg_viewer_count", "viewer_rank_at_hour"]
    assert df["channel"].n_unique() == 3
    assert (df.group_by("channel").len()["len"] == total_hours).all()
    assert df["viewer_rank_at_hour"].min() == 1
    assert df["viewer_rank_at_hour"].max() > 3


def test_chat_hype_components_timeseries_covers_every_channel_and_hour() -> None:
    total_hours = mock._hours().size
    df = mock.chat_hype_components_timeseries()
    assert list(df.columns) == [
        "channel",
        "timestamp",
        "message_count",
        "punct_rate",
        "caps_rate",
        "emote_rate",
    ]
    assert df["channel"].n_unique() == len(mock._STREAMERS)
    assert (df.group_by("channel").len()["len"] == total_hours).all()
    for col in ("punct_rate", "caps_rate", "emote_rate"):
        assert df[col].min() >= 0
        assert df[col].max() <= 1


def test_channel_sentiment_leaderboard_timeseries_keeps_top_n_channels_full_history() -> None:
    total_hours = mock._hours().size
    df = mock.channel_sentiment_leaderboard_timeseries(top_n=3)
    assert list(df.columns) == ["timestamp", "channel", "sentiment_score", "sentiment_rank_at_hour"]
    assert df["channel"].n_unique() == 3
    assert (df.group_by("channel").len()["len"] == total_hours).all()
    assert df["sentiment_rank_at_hour"].min() == 1
    assert df["sentiment_rank_at_hour"].max() > 3


def test_channel_toxicity_leaderboard_timeseries_keeps_top_n_channels_full_history() -> None:
    total_hours = mock._hours().size
    df = mock.channel_toxicity_leaderboard_timeseries(top_n=3)
    assert list(df.columns) == ["timestamp", "channel", "toxicity_score", "toxicity_rank_at_hour"]
    assert df["channel"].n_unique() == 3
    assert (df.group_by("channel").len()["len"] == total_hours).all()
    assert df["toxicity_rank_at_hour"].min() == 1
    assert df["toxicity_rank_at_hour"].max() > 3
    assert (df["toxicity_score"] >= 0).all()


def test_chat_toxicity_examples_only_returns_flagged_messages_with_chatter_identity() -> None:
    from datetime import timedelta

    from app.data.chat_lexicons import HOSTILE_WORDS, contains_any

    start = mock._EVENT_START
    end = start + timedelta(hours=float(mock._EVENT_DURATION_HOURS))
    df = mock.chat_toxicity_examples(start, end, limit=10)
    assert list(df.columns) == ["channel", "chatter", "message_sent_at", "message_text"]
    assert not df.is_empty()
    assert all(contains_any(text, HOSTILE_WORDS) for text in df["message_text"].to_list())


def test_chat_message_sample_has_chatter_identity() -> None:
    from datetime import timedelta

    start = mock._EVENT_START
    end = start + timedelta(hours=float(mock._EVENT_DURATION_HOURS))
    df = mock.chat_message_sample(start, end, limit=50)
    assert list(df.columns) == ["channel", "chatter", "message_sent_at", "message_text"]
    assert not df.is_empty()


def test_chat_mood_timeseries_has_one_row_per_hour_with_no_channel_dimension() -> None:
    total_hours = mock._hours().size
    df = mock.chat_mood_timeseries()
    assert list(df.columns) == ["timestamp", "avg_hype_score", "avg_sentiment_score"]
    assert len(df) == total_hours
    assert (df["avg_hype_score"] >= 0).all()


def test_chat_trending_phrases_only_keeps_genuine_repeats() -> None:
    df = mock.chat_trending_phrases(top_n=10)
    assert list(df.columns) == ["channel", "hour_bucket", "phrase", "repeat_count"]
    assert len(df) <= 10
    assert (df["repeat_count"] >= 3).all()
    assert (df["repeat_count"].diff().drop_nulls() <= 0).all()


def test_chat_trending_keywords_covers_every_hour_with_messages() -> None:
    from datetime import timedelta

    start = mock._EVENT_START
    end = start + timedelta(hours=float(mock._EVENT_DURATION_HOURS))
    channel = mock._STREAMERS[0].lower()
    df = mock.chat_trending_keywords(channel, start, end)
    assert list(df.columns) == ["hour_bucket", "keywords"]
    assert not df.is_empty()
    assert (df["keywords"].str.len_chars() > 0).all()
