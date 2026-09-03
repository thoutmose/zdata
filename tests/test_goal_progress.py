from datetime import UTC, timedelta

import polars as pl
from app.data.goal_progress import compute_goal_progress


def _timeseries(*, ingested_at: list[str], totals: list[float]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "ingested_at": pl.Series(ingested_at, dtype=pl.Utf8).str.to_datetime(time_zone="UTC"),
            "total_donation_amount_eur": totals,
        }
    )


def test_goal_marked_done_when_threshold_crossed() -> None:
    goals = pl.DataFrame({"goal_name": ["A"], "goal_amount_eur": [100.0]})
    ts = _timeseries(ingested_at=["2026-01-01T00:00Z", "2026-01-01T01:00Z"], totals=[50.0, 150.0])

    result = compute_goal_progress(goals, ts)

    row = result.row(0, named=True)
    assert row["status"] == "done"
    # `completed_at` is displayed in Europe/Paris (see `goal_progress._SCHEMA`);
    # compare the underlying instant so this doesn't depend on that offset.
    assert row["completed_at"].astimezone(UTC).isoformat().startswith("2026-01-01T01:00:00")


def test_first_goal_is_in_progress_not_not_started() -> None:
    """The very first (smallest) goal always "started" at the first snapshot."""
    goals = pl.DataFrame({"goal_name": ["A"], "goal_amount_eur": [1_000.0]})
    ts = _timeseries(ingested_at=["2026-01-01T00:00Z", "2026-01-01T01:00Z"], totals=[10.0, 20.0])

    result = compute_goal_progress(goals, ts)

    row = result.row(0, named=True)
    assert row["status"] == "in_progress"
    assert row["completed_at"] is None


def test_second_goal_not_started_while_first_unfinished() -> None:
    goals = pl.DataFrame({"goal_name": ["A", "B"], "goal_amount_eur": [1_000.0, 2_000.0]})
    ts = _timeseries(ingested_at=["2026-01-01T00:00Z", "2026-01-01T01:00Z"], totals=[10.0, 20.0])

    result = compute_goal_progress(goals, ts).sort("goal_amount_eur")

    assert result.row(0, named=True)["status"] == "in_progress"
    row1 = result.row(1, named=True)
    assert row1["status"] == "not_started"
    assert row1["started_at"] is None


def test_second_goal_starts_when_first_completes() -> None:
    goals = pl.DataFrame({"goal_name": ["A", "B"], "goal_amount_eur": [100.0, 200.0]})
    ts = _timeseries(
        ingested_at=["2026-01-01T00:00Z", "2026-01-01T01:00Z", "2026-01-01T02:00Z"],
        totals=[50.0, 150.0, 250.0],
    )

    result = compute_goal_progress(goals, ts).sort("goal_amount_eur")

    row0 = result.row(0, named=True)
    row1 = result.row(1, named=True)
    assert row0["status"] == "done"
    assert row1["status"] == "done"
    assert row1["started_at"] == row0["completed_at"]
    assert row1["duration"] == timedelta(hours=1)


def test_goal_in_progress_gets_elapsed_so_far_not_duration() -> None:
    goals = pl.DataFrame({"goal_name": ["A", "B"], "goal_amount_eur": [100.0, 1_000_000.0]})
    ts = _timeseries(
        ingested_at=["2026-01-01T00:00Z", "2026-01-01T01:00Z", "2026-01-01T03:00Z"],
        totals=[50.0, 150.0, 200.0],
    )

    result = compute_goal_progress(goals, ts).sort("goal_amount_eur")

    second = result.row(1, named=True)
    assert second["status"] == "in_progress"
    assert second["duration"] is None
    assert second["elapsed_so_far"] == timedelta(hours=2)
