"""Heuristic for flagging likely-bot chatters, shared by every chatter-level page.

No single warehouse field says "this is a bot" — this combines the bot-signal
mart's `has_long_digit_suffix` flag (an account-name pattern) with a plain
substring check on the username, which catches well-known moderation bots
(Fossabot, Nightbot, StreamElements, ...) that don't have a digit-suffixed
name at all.
"""

from __future__ import annotations

import polars as pl


def bot_filter_expr() -> pl.Expr:
    """Return a polars expression that is true for a likely-bot chatter row.

    Requires the DataFrame to have `chatter` and `has_long_digit_suffix` columns.

    Returns:
        A boolean `pl.Expr`, usable in `.filter()`.
    """
    return pl.col("has_long_digit_suffix") | pl.col("chatter").str.to_lowercase().str.contains(
        "bot"
    )
