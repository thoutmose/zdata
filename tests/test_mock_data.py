from typing import cast

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
    ]
    assert set(df["status"]).issubset({"done", "in_progress", "not_started"})
