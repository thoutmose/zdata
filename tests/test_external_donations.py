import polars as pl
from app.data.external_donations import day_boundary_breakdown


def _curve(points: list[tuple[float, float]]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "hours_since_start": [h for h, _ in points],
            "cumulative_amount_eur": [v for _, v in points],
        }
    )


def test_day_boundary_breakdown_empty_curve_returns_empty() -> None:
    empty_schema = {"hours_since_start": pl.Float64, "cumulative_amount_eur": pl.Float64}
    result = day_boundary_breakdown(pl.DataFrame(schema=empty_schema))
    assert result.is_empty()
    assert list(result.columns) == [
        "day",
        "cumulative_amount_eur",
        "delta_eur",
        "avg_per_hour_eur",
        "complete",
    ]


def test_day_boundary_breakdown_two_complete_days_and_one_partial() -> None:
    # Day 1 (0-24h): reaches 1000€. Day 2 (24-48h): reaches 3000€ (delta 2000€).
    # Day 3 (48-72h): curve stops at hour 60, reaches 3600€ (delta 600€ over 12h).
    curve = _curve([(0, 0), (24, 1000), (48, 3000), (60, 3600)])
    result = day_boundary_breakdown(curve)
    assert result["day"].to_list() == [1, 2, 3]
    assert result["cumulative_amount_eur"].to_list() == [1000, 3000, 3600]
    assert result["delta_eur"].to_list() == [1000, 2000, 600]
    assert result["complete"].to_list() == [True, True, False]
    # Day 3 only covers 12 real hours (48->60), not the full 24h window.
    assert result["avg_per_hour_eur"][2] == 50.0


def test_day_boundary_breakdown_stops_after_first_incomplete_day() -> None:
    # Curve doesn't even reach day 1's boundary (24h) yet.
    curve = _curve([(0, 0), (10, 500)])
    result = day_boundary_breakdown(curve)
    assert len(result) == 1
    assert result["complete"].to_list() == [False]
    assert result["day"].to_list() == [1]


def test_day_boundary_breakdown_respects_max_days() -> None:
    curve = _curve([(0, 0), (24, 1000), (48, 2000), (72, 3000), (96, 4000)])
    result = day_boundary_breakdown(curve, max_days=2)
    assert result["day"].to_list() == [1, 2]


def test_day_boundary_breakdown_custom_day_length() -> None:
    curve = _curve([(0, 0), (12, 500), (24, 1000)])
    result = day_boundary_breakdown(curve, day_hours=12.0, max_days=2)
    assert result["day"].to_list() == [1, 2]
    assert result["delta_eur"].to_list() == [500, 500]
