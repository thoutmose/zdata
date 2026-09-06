"""The single display timezone for the whole app.

ZEvent happens in France, so every timestamp shown to a user — chart axes,
tables, KPI captions — is converted to Europe/Paris, regardless of what
timezone the warehouse stores it in (Postgres returns UTC-labeled
`timestamptz` values). The conversion happens centrally, in
`PostgresDataSource._run()` and in `mock.py`'s timestamp generator, so no
page has to remember to do it.

Every timestamp is left tz-naive after that conversion — Streamlit's widgets
and Plotly's charts render a tz-aware datetime in the *viewer's browser*
timezone rather than the one attached in Python, so a tz-aware value doesn't
reliably display as the Europe/Paris time it actually holds. `PARIS` is still
needed to *compute* that wall-clock time in the first place (converting from
the warehouse's UTC-labeled instants) — just not to hold onto afterwards.
"""

from __future__ import annotations

from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")
PARIS_TZ_NAME = "Europe/Paris"
