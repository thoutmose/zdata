"""Pooled database access.

A Streamlit server runs one Python process shared by every visitor; each
browser session gets its own script-run thread. If every page rerun opened a
fresh `psycopg` connection, a modest number of concurrent public users would
exhaust the database's connection limit in minutes. Instead, a single
`Engine` with a bounded connection pool is created once per process (cached
with `st.cache_resource`) and shared by all sessions.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import sqlalchemy as sa
import streamlit as st
from sqlalchemy import event

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@st.cache_resource(show_spinner=False)
def get_engine() -> sa.Engine:
    """Build and cache the process-wide pooled SQLAlchemy engine.

    `pool_pre_ping` avoids handing out dead connections after a database
    restart or idle timeout. `statement_timeout` is applied with a `SET` on
    every pool checkout (see `_set_statement_timeout` below) rather than as a
    startup parameter: this database sits behind PgBouncer, which only
    forwards a fixed allowlist of startup parameters and rejects unknown ones
    outright — and re-applying it per checkout is also the correct behavior
    under PgBouncer's transaction-pooling mode, where a "session" can be
    handed a different backend connection between transactions.

    Returns:
        A SQLAlchemy engine backed by a bounded `QueuePool`.
    """
    settings = get_settings()
    engine = sa.create_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
        pool_recycle=settings.db_pool_recycle_s,
        connect_args={"connect_timeout": 5},
    )

    @event.listens_for(engine, "checkout")
    def _set_statement_timeout(
        dbapi_connection: Any, connection_record: Any, connection_proxy: Any
    ) -> None:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute(f"SET statement_timeout = {settings.db_statement_timeout_ms}")
        finally:
            cursor.close()

    logger.info(
        "Database engine created (pool_size=%s, max_overflow=%s, statement_timeout_ms=%s)",
        settings.db_pool_size,
        settings.db_max_overflow,
        settings.db_statement_timeout_ms,
    )
    return engine


@contextmanager
def get_connection() -> Iterator[sa.Connection]:
    """Check out a pooled, read-only-intent connection for the duration of a query.

    Yields:
        An active SQLAlchemy connection, returned to the pool on exit.
    """
    engine = get_engine()
    with engine.connect() as connection:
        yield connection


def check_connection() -> bool:
    """Verify the database is reachable, without raising.

    Used by the landing page to show a clear status banner instead of a raw
    stack trace when the database is unreachable or misconfigured.

    Returns:
        True if a trivial query succeeds, False otherwise.
    """
    try:
        with get_connection() as conn:
            conn.execute(sa.text("SELECT 1"))
        return True
    except Exception:
        logger.exception("Database health check failed")
        return False
