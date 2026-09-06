"""Historical ZEvent donation totals sourced from EvenMoreStats' public metrics cache.

EvenMoreStats (the project behind `zevent.gdoc.fr`) publishes each
edition's cumulative donation curve as a static JSON file on a public,
unauthenticated object-storage bucket with `Access-Control-Allow-Origin: *`
— it's meant to be fetched directly by a browser, so reading it here is no
different from what their own site's client-side code does. There's no
documented index of past editions' event IDs, though, so the ones below
were found by inspecting that site's own bundled JS for each year's
archived subdomain; add a year here once its ID has been found the same
way.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from datetime import datetime
from urllib.error import URLError

import polars as pl
import streamlit as st

from app.core.tz import PARIS

logger = logging.getLogger(__name__)

_CACHE_BASE = "https://evenmorestats-cache.s3.gra.io.cloud.ovh.net"
_REQUEST_TIMEOUT_S = 5

_EVENT_IDS = {
    2021: "019ebc50-efd9-7070-9663-404f8d79a410",
    2022: "019ebc61-62e7-7fdc-aa5c-a0047c921878",
    2024: "019ebc62-7050-751b-aee8-eb7dc7ab6ceb",
    2025: "019d3f95-bd24-7e5d-861b-1de6243e3169",
    2026: "019f5bd1-fe07-7d78-a326-a02198a9d50f",
}
KNOWN_EDITION_YEARS = sorted(_EVENT_IDS)

_EMPTY_CURVE_SCHEMA = {"hours_since_start": pl.Float64, "cumulative_amount_eur": pl.Float64}


def _fetch_donation_series(year: int) -> tuple[list[int], list[float]] | None:
    """Fetch and time-sort one edition's raw `(labels_ms, values)` samples.

    Returns:
        `None` on any failure or if the edition has no data yet — this is
        optional enrichment from an unofficial third party, not something
        worth crashing the page over if their bucket is unreachable or its
        shape changes.
    """
    event_id = _EVENT_IDS.get(year)
    if event_id is None:
        return None
    url = f"{_CACHE_BASE}/metrics/{event_id}/global.json"
    try:
        with urllib.request.urlopen(url, timeout=_REQUEST_TIMEOUT_S) as response:
            payload = json.load(response)
        series = payload["graph"]["donations"]["all"]
        labels_ms: list[int] = series["labels"]
        values: list[float] = series["values"]
    except (URLError, TimeoutError, ValueError, KeyError) as exc:
        logger.warning("Failed to fetch %s donation curve from EvenMoreStats: %s", year, exc)
        return None
    if not labels_ms:
        return None
    # Most editions' samples arrive already sorted ascending by time, but
    # 2021's payload is in reverse-chronological order (values still pair
    # correctly with their label, just descending) — sort defensively so
    # `labels_ms[0]` is reliably the earliest sample.
    labels_ms, values = (
        list(seq)
        for seq in zip(*sorted(zip(labels_ms, values, strict=True)), strict=True)
    )
    return labels_ms, values


@st.cache_data(show_spinner=False)
def get_historical_donation_curve(year: int) -> pl.DataFrame:
    """Fetch one past edition's cumulative donation curve from EvenMoreStats.

    Cached indefinitely (no `ttl`) rather than per-session, unlike this
    app's own live-event queries: a past edition's totals are frozen and
    will never change, so there's nothing to invalidate.

    Args:
        year: Edition year. Silently returns empty if not in `_EVENT_IDS`.

    Returns:
        Columns `hours_since_start` (float, 0 at the event's first sample)
        and `cumulative_amount_eur` (float), one row per ~10-minute
        sample. Empty on any failure.
    """
    series = _fetch_donation_series(year)
    if series is None:
        return pl.DataFrame(schema=_EMPTY_CURVE_SCHEMA)
    labels_ms, values = series
    start_ms = labels_ms[0]
    return pl.DataFrame(
        {
            "hours_since_start": [(ms - start_ms) / 3_600_000 for ms in labels_ms],
            # EvenMoreStats emits whole-euro samples as bare JSON integers
            # (e.g. `2808`) and later ones with cents as floats — Polars
            # infers the column's type from the first value, so without
            # this cast an early integer sample makes a later float one
            # fail to build the Series at all.
            "cumulative_amount_eur": [float(v) for v in values],
        }
    )


# EvenMoreStats' own first sample is a reliable kickoff anchor for every
# *past* edition here (2021: Friday 17:00 Paris; 2022/2024/2025: Friday
# 18:00 Paris — all already climbing fast within minutes of that first
# sample, confirmed by inspecting each edition's own early data points).
# 2026 breaks that pattern: EvenMoreStats started recording it ~22 hours
# early, during a Thursday-evening pre-show/tech-check period where the
# total barely moves (this app's own warehouse shows the same thing —
# donations flat under €600K from 2026-09-03 19:00 Paris through
# 2026-09-04 17:00, then nearly doubling within the hour at 18:00, which
# lines up with every other edition's Friday ~18:00 Paris kickoff). Add an
# override here, the same way `_EVENT_IDS` gets a new entry each year, if
# a future edition's data turns out to need one too.
_KICKOFF_OVERRIDES: dict[int, datetime] = {
    2026: datetime(2026, 9, 4, 18, 0),
}


@st.cache_data(show_spinner=False)
def get_edition_kickoff_time(year: int) -> datetime | None:
    """Return the moment edition `year`'s donation drive actually starts.

    This app's own warehouse starts ingesting well before the event's real
    kickoff for every edition — its earliest snapshots cover a pre-show/
    tech-check period (donations near-zero, barely moving) rather than the
    marathon itself. Using our own first snapshot as "hour 0" for the
    current edition's curve on the Donations page would count that quiet
    lead-in as part of the event, making the current year look far behind
    every past edition at the same "hours since start" — even though it's
    genuinely on pace once both curves start at the same real moment. This
    anchor (EvenMoreStats' own first sample, or `_KICKOFF_OVERRIDES` for
    the editions where even that carries a pre-show lead-in) fixes that.

    Returns:
        A tz-naive Europe/Paris wall-clock `datetime` (matching every
        timestamp this app's own warehouse queries return), or `None` if
        the edition isn't registered or its data is unreachable.
    """
    if year in _KICKOFF_OVERRIDES:
        return _KICKOFF_OVERRIDES[year]
    series = _fetch_donation_series(year)
    if series is None:
        return None
    labels_ms, _values = series
    return datetime.fromtimestamp(labels_ms[0] / 1000, tz=PARIS).replace(tzinfo=None)
