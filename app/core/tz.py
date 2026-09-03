"""The single display timezone for the whole app.

ZEvent happens in France, so every timestamp shown to a user — chart axes,
tables, KPI captions — is converted to Europe/Paris, regardless of what
timezone the warehouse stores it in (Postgres returns UTC-labeled
`timestamptz` values). The conversion happens centrally, in
`PostgresDataSource._run()` and in `mock.py`'s timestamp generator, so no
page has to remember to do it.
"""

from __future__ import annotations

from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")
PARIS_TZ_NAME = "Europe/Paris"
