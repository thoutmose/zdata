"""Curated, real-data-verified word lists behind Chat Intelligence's lexicon/heuristic scores.

Every word here was tested individually against real ZEvent chat before being
kept, not assumed from a generic list — see `HOSTILE_WORDS` below for what was
tried and rejected, and why. Single source of truth, shared by
`app/data/repository.py` (to build each SQL `CASE` fragment once instead of
duplicating the list per query) and `app/data/mock.py` (so mock toxicity
examples use the exact same words the real query does).
"""

from __future__ import annotations

import re
from collections.abc import Sequence

POSITIVE_WORDS: tuple[str, ...] = (
    "merci",
    "super",
    "genial",
    "bravo",
    "parfait",
    "excellent",
    "adorable",
    "magnifique",
    "incroyable",
    "love",
)

HYPE_EMOTE_WORDS: tuple[str, ...] = ("lul", "kekw", "pog", "hype")

# Candidates tried and dropped, by testing each one against real event chat:
# bare "con" (~99% false positives — "configurer", "continue", "contacter"),
# "cretin" (mostly "Lapin Crétin", a game title, not an insult), "stupide"
# (mostly Twitch emote codes like "just1chatStupide"), "minable" (mostly the
# unrelated word "interminable"), "pourri"/"batard" (usually describe an
# object's quality or are positive slang — "un flow de batard" is a
# compliment — not aimed at a person), and "putain"/"merde" (a casual
# exclamation, like "damn", not typically directed at anyone). What's left
# was confirmed to mostly hit genuine hostile language in a real sample. It
# will still miss slurs, hate speech, and harassment that avoids these exact
# words, and can't tell a targeted insult from friendly banter.
#
# Matched with a *leading*-only word boundary (see `leading_boundary_sql`),
# not a plain substring: bare substring matching on "idiot" also matched
# Twitch emote codes ("melokaIdiot", "nyamas1Idiote") and even someone's
# actual username being mentioned ("@je_un_idiot") — both confirmed on real
# data, both false positives a leading boundary rules out (neither has a
# real word boundary right before "idiot"). A *trailing* boundary was tried
# and rejected too: it would have silently dropped genuine plurals
# ("connards") and emphasis-lengthened forms ("CONNASSEEEE"), which are
# still the same insult — the raw substring drop from anchoring both ends
# turned out to be false negatives, not further precision.
HOSTILE_WORDS: tuple[str, ...] = (
    "connard",
    "connasse",
    "idiot",
    "debile",
    "degage",
    "ta gueule",
)


def leading_boundary_sql(column: str, words: Sequence[str]) -> str:
    r"""Build a `CASE WHEN <column> ~* '\y(w1|w2|...)' THEN 1.0 ELSE 0.0 END` SQL fragment.

    A word boundary (`\y`, Postgres' POSIX word-boundary escape) only
    before each word, not after — see `HOSTILE_WORDS` for why the trailing
    boundary was tried and rejected. `words` must be plain
    letters/spaces (true of every list in this module) — this doesn't
    escape regex metacharacters, so don't add a word containing one without
    updating this function.

    Args:
        column: The SQL column to match against.
        words: Words to match, each requiring a word boundary right before it.

    Returns:
        A `CASE` expression evaluating to `1.0` if `column` contains any of
        `words` at a word boundary (case-insensitively), else `0.0` — ready
        to `AVG()`.
    """
    alternatives = "|".join(words)
    return f"CASE WHEN {column} ~* '\\y({alternatives})' THEN 1.0 ELSE 0.0 END"


def contains_any(text: str, words: Sequence[str]) -> bool:
    """Return whether `text` contains any of `words` at a word boundary, case-insensitively.

    The Python-side equivalent of `leading_boundary_sql`'s condition — used
    by mock data generation and the toxicity-examples viewer, so both stay
    in sync with the real SQL query's definition of a match. `re.search`
    caches compiled patterns internally, so calling this repeatedly with the
    same `words` (as every caller does) doesn't recompile per call.
    """
    return re.search(r"\b(?:" + "|".join(words) + ")", text, re.IGNORECASE) is not None
