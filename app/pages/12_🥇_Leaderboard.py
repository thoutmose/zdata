"""Leaderboard page: consolidated top-3 podiums and full rankings.

Every ranking here already exists in more depth elsewhere (Donations,
Streamers, Chatters) — this page is deliberately a consolidated "who's
winning" hub, not a replacement for those pages' own filters and drill-downs.
Every ranking stays event-wide by *time* (not affected by the sidebar date
filter), same as the Donations page's own "Top fundraisers" podium, since a
leaderboard is meant to be the definitive standing, not a moving window —
but the sidebar's streamer/chatter filters still narrow *who's eligible* to
rank, same as everywhere else in the app.

Chat usernames are real and shown on-screen, exactly as on the Chatters,
Streamers, and Community pages (see `app/pages/8_🗣️_Chatters.py`'s module
docstring) — the CSV export is the one place a real identifier must never
leave the app, so it goes through `anonymize_chatters` first, same as there.
"""

from __future__ import annotations

import logging

import polars as pl
import streamlit as st
from app.components.chrome import (
    bounded_top_n_slider,
    chart_explainer,
    date_filter_caveat,
    page_footer,
    page_header,
)
from app.components.filters import apply_global_chatter_filter, apply_global_streamer_filter
from app.components.theme import build_podium_figure
from app.core.i18n import t
from app.core.logging_config import setup_logging
from app.data.anonymize import anonymize_chatters
from app.data.bot_heuristic import bot_filter_expr
from app.data.repository import (
    get_chatter_breakdown,
    get_event_bounds,
    get_streamer_breakdown,
    get_top_chatter_per_channel,
)

setup_logging()
logger = logging.getLogger(__name__)


def _page_offset(*, total_rows: int, page_size: int, key: str) -> int:
    """Render Previous/Next controls for paging through a ranking and return the row offset.

    The "top N" slider already picked a page size; this lets you page past
    it to see ranks beyond it (e.g. #16-30) instead of only ever seeing the
    field from rank 1. Rendered whenever the slider itself would be (i.e.
    whenever there's more than one row to rank at all) — Prev/Next are
    only *disabled*, never hidden, when the current top-N already covers
    every row. An earlier version hid the whole control in that case, which
    made it disappear any time the sidebar's streamer/chatter filter (or
    the top-N slider's own default snapping to a small filtered count)
    left everything fitting on one page — a very common state, not a rare
    edge case, so the control kept vanishing on ordinary use rather than
    only when genuinely irrelevant.

    Same session-state guard as `bounded_top_n_slider`: `page_size` or
    `total_rows` can shrink across reruns (a smaller top-N choice, "hide
    likely bots" toggled on) and strand a stored page past the new last
    page, so it's reset only when it no longer fits — a still-valid page
    survives an unrelated rerun instead of jumping back to page 1.

    Args:
        total_rows: Rows available to page through.
        page_size: Rows per page (the current top-N choice).
        key: Unique Streamlit widget key for the stored page number.

    Returns:
        0-based row offset of the current page's first row.
    """
    if total_rows <= 1:
        return 0
    last_page = max(0, (total_rows - 1) // page_size)
    if key not in st.session_state or not (0 <= st.session_state[key] <= last_page):
        st.session_state[key] = 0

    def _step(delta: int) -> None:
        # An `on_click` callback runs *before* the rerun that redraws these
        # buttons, so `disabled=` below reflects the post-click page on the
        # very next render — updating `session_state` from inside `if
        # st.button(...):` instead would only take effect one rerun late,
        # leaving Prev/Next visibly stale (e.g. Prev still greyed out right
        # after a Next click actually moved off page 1).
        st.session_state[key] = max(0, min(last_page, st.session_state[key] + delta))

    prev_col, label_col, next_col = st.columns([1, 2, 1])
    with prev_col:
        st.button(
            t("common.prev_page"),
            key=f"{key}_prev",
            disabled=st.session_state[key] == 0,
            on_click=_step,
            args=(-1,),
        )
    with next_col:
        st.button(
            t("common.next_page"),
            key=f"{key}_next",
            disabled=st.session_state[key] == last_page,
            on_click=_step,
            args=(1,),
        )
    with label_col:
        st.caption(t("common.page_of", page=st.session_state[key] + 1, pages=last_page + 1))
    return st.session_state[key] * page_size


def _ranked_table(
    df: pl.DataFrame, *, sort_col: str, columns: dict[str, str], top_n: int, offset: int = 0
) -> pl.DataFrame:
    """Sort `df` descending by `sort_col`, number rows `offset+1..offset+top_n`, and rename columns.

    Args:
        df: Source DataFrame.
        sort_col: Column to rank by, descending.
        columns: Mapping from source column (must include `sort_col`) to its
            display name, in display order. A leading "Rank" column
            (1-based, starting at `offset + 1`) is added automatically.
        top_n: How many rows to keep (the page size).
        offset: How many higher-ranked rows to skip before this page starts.

    Returns:
        `df` sorted, ranked, sliced to this page, and renamed for display.
    """
    return (
        df.sort(sort_col, descending=True)
        .slice(offset, top_n)
        .select(list(columns.keys()))
        .rename(columns)
        .with_row_index(t("leaderboard.column.rank"), offset=offset + 1)
    )


page_header(t("leaderboard.title"), "🥇", t("leaderboard.description"))
date_filter_caveat()

streamers = apply_global_streamer_filter(get_streamer_breakdown())
if streamers.is_empty():
    st.warning(t("leaderboard.no_data"))
    st.stop()
# Donations per hour actually streamed — a time-efficiency read distinct
# from `donation_eur_per_avg_viewer` (audience-efficiency): a streamer can
# convert their own audience well yet still raise less per hour on air than
# someone with a smaller but more generous one. Null (not 0 or inf) for the
# ~30% of streamers with `hours_live == 0` in the real data (goal set before
# ever going live, or the streaming-metadata pipeline hasn't caught up yet)
# — dividing by zero would otherwise fabricate an infinite rate.
streamers = streamers.with_columns(
    pl.when(pl.col("hours_live") > 0)
    .then(pl.col("amount_eur") / pl.col("hours_live"))
    .otherwise(None)
    .alias("amount_eur_per_hour")
)

event_bounds = get_event_bounds()
chatters = get_chatter_breakdown(*event_bounds) if event_bounds else pl.DataFrame()
chatters = apply_global_chatter_filter(chatters)
fan_per_channel = get_top_chatter_per_channel(*event_bounds) if event_bounds else pl.DataFrame()
fan_per_channel = apply_global_streamer_filter(fan_per_channel)

# --- Section 1: top streamers by donations ---
st.subheader(t("leaderboard.donations_heading"))
st.caption(t("leaderboard.donations_caption"))
top3_donations = streamers.sort("amount_eur", descending=True).head(3)
if len(top3_donations) == 3:
    st.plotly_chart(
        build_podium_figure(
            top3_donations["streamer"].to_list(),
            top3_donations["amount_eur"].to_list(),
            title=t("leaderboard.chart.donations_podium"),
            unit="€",
        ),
        width="stretch",
    )
donations_top_n = bounded_top_n_slider(
    label=t("leaderboard.top_n"), max_value=len(streamers), key="leaderboard_donations_top_n"
)
donations_offset = _page_offset(
    total_rows=len(streamers), page_size=donations_top_n, key="leaderboard_donations_page"
)
amount_col = t("leaderboard.column.amount")
donations_table = _ranked_table(
    streamers,
    sort_col="amount_eur",
    columns={"streamer": t("leaderboard.column.streamer"), "amount_eur": amount_col},
    top_n=donations_top_n,
    offset=donations_offset,
).with_columns(
    pl.col(amount_col).map_elements(lambda v: f"{v:,.0f} €", return_dtype=pl.Utf8)
)
st.dataframe(donations_table, width="stretch", hide_index=True)
chart_explainer(t("leaderboard.explain.donations"))

# --- Section 2: top chatters, event-wide ---
st.subheader(t("leaderboard.chatters_heading"))
st.caption(t("leaderboard.chatters_caption"))
if chatters.is_empty():
    st.info(t("common.no_data_in_range"))
else:
    hide_bots_chatters = st.checkbox(
        t("chatters.hide_bots"), value=True, key="leaderboard_chatters_hide_bots"
    )
    shown_chatters = chatters.filter(~bot_filter_expr()) if hide_bots_chatters else chatters
    if shown_chatters.is_empty():
        st.info(t("common.no_data_in_range"))
    else:
        top3_chatters = shown_chatters.sort("total_message_count", descending=True).head(3)
        if len(top3_chatters) == 3:
            st.plotly_chart(
                build_podium_figure(
                    top3_chatters["chatter"].to_list(),
                    top3_chatters["total_message_count"].to_list(),
                    title=t("leaderboard.chart.chatters_podium"),
                    unit=t("common.unit.messages"),
                ),
                width="stretch",
            )
        chatters_top_n = bounded_top_n_slider(
            label=t("leaderboard.top_n"),
            max_value=len(shown_chatters),
            key="leaderboard_chatters_top_n",
        )
        chatters_offset = _page_offset(
            total_rows=len(shown_chatters),
            page_size=chatters_top_n,
            key="leaderboard_chatters_page",
        )
        chatters_table = _ranked_table(
            shown_chatters,
            sort_col="total_message_count",
            columns={
                "chatter": t("leaderboard.column.chatter"),
                "total_message_count": t("leaderboard.column.messages"),
            },
            top_n=chatters_top_n,
            offset=chatters_offset,
        )
        st.dataframe(chatters_table, width="stretch", hide_index=True)
        chart_explainer(t("leaderboard.explain.chatters"))

# --- Section 3: top chatter per streamer ("#1 fan") ---
st.subheader(t("leaderboard.fans_heading"))
st.caption(t("leaderboard.fans_caption"))
if fan_per_channel.is_empty():
    st.info(t("common.no_data_in_range"))
else:
    hide_bots_fans = st.checkbox(
        t("chatters.hide_bots"), value=True, key="leaderboard_fans_hide_bots"
    )
    shown_fans = fan_per_channel.filter(~bot_filter_expr()) if hide_bots_fans else fan_per_channel
    if shown_fans.is_empty():
        st.info(t("common.no_data_in_range"))
    else:
        # Fans are joined to the human streamer display name, not just the
        # raw channel login — everywhere else in the app that shows a
        # streamer by name goes through this same `get_streamer_breakdown`
        # mapping, so a channel with no streamer-breakdown row (shouldn't
        # normally happen, but a real warehouse can have gaps) falls back to
        # its raw login rather than disappearing from the table.
        fans_with_names = shown_fans.join(
            streamers.select("channel", "streamer"), on="channel", how="left"
        ).with_columns(pl.col("streamer").fill_null(pl.col("channel")))
        fan_search = st.text_input(t("leaderboard.fans_search"), key="leaderboard_fans_search")
        if fan_search:
            fans_with_names = fans_with_names.filter(
                pl.col("streamer").str.to_lowercase().str.contains(fan_search.lower(), literal=True)
            )
        if fans_with_names.is_empty():
            st.info(t("common.no_data_in_range"))
        else:
            fans_display = (
                fans_with_names.sort("message_count", descending=True)
                .select("streamer", "chatter", "message_count")
                .rename(
                    {
                        "streamer": t("leaderboard.column.streamer"),
                        "chatter": t("leaderboard.column.top_fan"),
                        "message_count": t("leaderboard.column.messages"),
                    }
                )
            )
            st.dataframe(fans_display, width="stretch", hide_index=True)
            chart_explainer(t("leaderboard.explain.fans"))

# --- Section 4: top streamers by audience / engagement / efficiency ---
st.subheader(t("leaderboard.audience_heading"))
st.caption(t("leaderboard.audience_caption"))
AUDIENCE_METRICS = {
    t("leaderboard.metric.viewers"): ("avg_viewers", t("common.unit.viewers")),
    t("leaderboard.metric.engagement"): ("total_messages", t("common.unit.messages")),
    t("leaderboard.metric.efficiency"): ("donation_eur_per_avg_viewer", "€"),
    t("leaderboard.metric.efficiency_chatters"): ("donation_eur_per_unique_chatter", "€"),
    t("leaderboard.metric.rate"): ("amount_eur_per_hour", "€/h"),
}
audience_metric_choice = st.radio(
    t("leaderboard.metric_picker"), list(AUDIENCE_METRICS.keys()), horizontal=True
)
audience_col, audience_unit = AUDIENCE_METRICS[audience_metric_choice]
if audience_col == "amount_eur_per_hour":
    # A streamer live only a handful of hours can post an extreme rate off
    # a single big donation — not wrong, but worth flagging rather than
    # letting a tiny denominator masquerade as sustained fundraising pace.
    st.caption(t("leaderboard.rate_caveat"))
audience_ranked = streamers.filter(pl.col(audience_col).is_not_null())
top3_audience = audience_ranked.sort(audience_col, descending=True).head(3)
if len(top3_audience) == 3:
    st.plotly_chart(
        build_podium_figure(
            top3_audience["streamer"].to_list(),
            top3_audience[audience_col].to_list(),
            title=t("leaderboard.chart.audience_podium", metric=audience_metric_choice),
            unit=audience_unit,
        ),
        width="stretch",
    )
audience_top_n = bounded_top_n_slider(
    label=t("leaderboard.top_n"), max_value=len(audience_ranked), key="leaderboard_audience_top_n"
)
audience_offset = _page_offset(
    total_rows=len(audience_ranked), page_size=audience_top_n, key="leaderboard_audience_page"
)
audience_table = _ranked_table(
    audience_ranked,
    sort_col=audience_col,
    columns={"streamer": t("leaderboard.column.streamer"), audience_col: audience_metric_choice},
    top_n=audience_top_n,
    offset=audience_offset,
)
st.dataframe(audience_table, width="stretch", hide_index=True)
chart_explainer(t("leaderboard.explain.audience"))

with st.expander(t("common.view_data")):
    st.caption(t("chatters.anonymize_caption"))
    if not chatters.is_empty():
        st.download_button(
            t("common.download_csv"),
            anonymize_chatters(chatters).write_csv(),
            file_name="leaderboard_chatters_anonymized.csv",
            mime="text/csv",
            key="leaderboard_download_chatters",
        )
    if not fan_per_channel.is_empty():
        st.download_button(
            t("common.download_csv"),
            anonymize_chatters(fan_per_channel).write_csv(),
            file_name="leaderboard_top_fans_anonymized.csv",
            mime="text/csv",
            key="leaderboard_download_fans",
        )

page_footer()

logger.info(
    "Leaderboard page rendered (streamers=%s, chatters=%s, fans=%s)",
    len(streamers),
    len(chatters),
    len(fan_per_channel),
)
