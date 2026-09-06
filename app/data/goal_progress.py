"""Pure computation: turn a streamer's goals + donation timeseries into a progress table.

Shared by `repository.py::PostgresDataSource` (real data) and `mock.py`
(sample data) so both backends compute "when did each goal start/complete"
identically — this has no database dependency, so it lives in its own module
rather than in either.
"""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import polars as pl

_SCHEMA = {
    "goal_name": pl.Utf8,
    "goal_amount_eur": pl.Float64,
    # Naive — Europe/Paris wall-clock time with the tzinfo already stripped
    # by the time it reaches here (see `repository.py::_run`'s docstring).
    "started_at": pl.Datetime("us"),
    "completed_at": pl.Datetime("us"),
    "status": pl.Utf8,
    "duration": pl.Duration("us"),
    "elapsed_so_far": pl.Duration("us"),
}


def compute_goal_progress(goals: pl.DataFrame, timeseries: pl.DataFrame) -> pl.DataFrame:
    """Compute start/completion/duration for each of a streamer's donation goals.

    A goal "starts" when the previous goal (ordered by amount, ascending)
    completed — i.e. when the streamer's cumulative donation total first
    reached the previous goal's amount. It "completes" when the total first
    reaches its own amount. A goal whose amount was never reached is
    `"in_progress"` if the previous goal completed, or `"not_started"` if
    even the previous goal hasn't completed yet.

    An `"in_progress"` goal also gets `elapsed_so_far` — time from its start
    to the *latest known snapshot* (not wall-clock time, so this is identical
    for real and mock data, and correct regardless of when the page happens
    to be viewed relative to the event).

    The result always uses an explicit schema (see `_SCHEMA`) rather than
    letting polars infer one from the row data — a streamer whose goals are
    *all* `"not_started"` would otherwise produce all-null `duration`/
    `elapsed_so_far` columns with no way to infer they're time deltas, which
    breaks any later `.dt`-style access.

    Args:
        goals: DataFrame with `goal_name`, `goal_amount_eur` (any order).
        timeseries: DataFrame with `ingested_at`, `total_donation_amount_eur`,
            for the same streamer.

    Returns:
        DataFrame matching `_SCHEMA`: `goal_name`, `goal_amount_eur`,
        `started_at`, `completed_at`, `status` (`"done"` / `"in_progress"` /
        `"not_started"`), `duration` (null if not completed), `elapsed_so_far`
        (only set when `status == "in_progress"`).
    """
    ts = timeseries.sort("ingested_at")
    # `total_donation_amount_eur` is meant to be a monotonically non-decreasing
    # cumulative total, but the warehouse occasionally has a transient dip (a
    # reconciliation correction to an earlier snapshot) — `np.searchsorted`
    # below assumes a sorted, non-decreasing array, and a real dip makes its
    # result depend on exactly which rows are present. Forcing a running
    # maximum removes that dependency: the crossing point becomes "the
    # highest confirmed total reached so far," and is now identical whether
    # this receives every raw snapshot or a de-duplicated subset (verified
    # against a live streamer whose data had exactly this kind of dip).
    amounts = np.maximum.accumulate(ts["total_donation_amount_eur"].to_numpy())
    times = ts["ingested_at"].to_list()
    as_of = times[-1] if times else None

    rows = []
    # Seeded with the first snapshot so the very first (smallest) goal is
    # "in_progress" from the start, not "not_started". Reset to None the
    # moment a goal fails to complete — that breaks the chain, so every
    # later goal correctly becomes "not_started" rather than inheriting a
    # stale start time from before the chain broke.
    prev_completed_at = times[0] if times else None
    for goal in goals.sort("goal_amount_eur").iter_rows(named=True):
        threshold = float(goal["goal_amount_eur"])
        idx = int(np.searchsorted(amounts, threshold, side="left"))
        started_at = prev_completed_at
        if idx < len(amounts):
            completed_at = times[idx]
            status = "done"
            prev_completed_at = completed_at
        else:
            completed_at = None
            status = "in_progress" if started_at is not None else "not_started"
            prev_completed_at = None

        duration: timedelta | None = (
            completed_at - started_at
            if completed_at is not None and started_at is not None
            else None
        )
        elapsed_so_far: timedelta | None = (
            as_of - started_at
            if status == "in_progress" and started_at is not None and as_of is not None
            else None
        )
        rows.append(
            {
                "goal_name": goal["goal_name"],
                "goal_amount_eur": threshold,
                "started_at": started_at,
                "completed_at": completed_at,
                "status": status,
                "duration": duration,
                "elapsed_so_far": elapsed_so_far,
            }
        )

    return pl.DataFrame(rows, schema=_SCHEMA)


def goal_progress_by_category(goals: pl.DataFrame, timeseries: pl.DataFrame) -> pl.DataFrame:
    """Run `compute_goal_progress` once per `goal_category`, then recombine.

    `compute_goal_progress`'s whole model is a *chain*: goal N starts when
    goal N-1 (the next amount down) completed. That's only meaningful within
    one category — a `"donation"` cumulative-total milestone and an
    unrelated `"incentive"` goal aren't checkpoints in the same sequence
    just because the same streamer set both. Every category still gets
    included (nothing is dropped the way filtering to a single category
    would), just tracked independently against the same timeseries.

    Args:
        goals: DataFrame with `goal_category`, `goal_name`, `goal_amount_eur`
            (any order, any number of categories).
        timeseries: DataFrame with `ingested_at`, `total_donation_amount_eur`,
            shared across every category (goal progress depends only on the
            streamer's cumulative total, not on the category).

    Returns:
        The concatenation of `compute_goal_progress` per category, each
        row tagged with its `goal_category`. Empty (matching
        `compute_goal_progress`'s empty shape, plus `goal_category`) if
        `goals` is empty.
    """
    if goals.is_empty():
        return compute_goal_progress(goals, timeseries).with_columns(
            goal_category=pl.lit(None, dtype=pl.Utf8)
        )
    results = [
        compute_goal_progress(category_goals, timeseries).with_columns(
            goal_category=pl.lit(category)
        )
        for (category,), category_goals in goals.group_by("goal_category")
    ]
    return pl.concat(results, how="vertical")
