"""Application settings, loaded from environment variables / `.env`.

No secret ever lives in source control. Every value that differs between a
developer's laptop and production (database credentials, log level, pool
sizing) is read here and nowhere else.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    """Runtime configuration for the ZEvent Dataviz application.

    All fields are overridable via environment variables (or a `.env` file in
    the project root) using their upper-cased field name, e.g. `DB_HOST`.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Also selects the logging profile in logging.yml (see app/core/logging_config.py).
    app_env: Literal["development", "production"] = "development"

    db_host: str | None = None
    db_port: int = 5432
    db_name: str | None = None
    db_user: str | None = None
    db_password: SecretStr | None = None

    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_recycle_s: int = 1800
    db_statement_timeout_ms: int = 15_000

    # Set once a `dbt docs generate` build is hosted somewhere reachable
    # (this app has no access to the dbt project's own manifest.json/
    # target/ output by itself — it lives in a separate repo, `zevent-db`)
    # — the Home page's data-engineering section links to it when set.
    dbt_docs_url: str | None = None

    @computed_field
    @property
    def has_db_credentials(self) -> bool:
        """Whether enough information was supplied to connect to a real database.

        Returns:
            True if host, database name, user, and password are all set.
        """
        return all([self.db_host, self.db_name, self.db_user, self.db_password])

    @computed_field
    @property
    def use_mock_data(self) -> bool:
        """Whether the app should serve deterministic sample data instead of the DB.

        Returns:
            True until real database credentials are configured.
        """
        return not self.has_db_credentials

    @property
    def database_url(self) -> URL:
        """Build a SQLAlchemy URL for the configured PostgreSQL database.

        Uses `sqlalchemy.URL.create` rather than an f-string so that special
        characters in the password (`@`, `/`, `:`, ...) are escaped correctly
        instead of silently breaking the connection string.

        Returns:
            A SQLAlchemy `URL` for the `postgresql+psycopg` driver.
        """
        if not self.has_db_credentials:
            msg = "Database credentials are not configured; cannot build a database URL."
            raise RuntimeError(msg)
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.db_user,
            password=self.db_password.get_secret_value() if self.db_password else None,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide `Settings` singleton.

    Cached so environment variables are parsed once per process; Streamlit
    reruns the script on every interaction, so re-parsing `.env` every time
    would be wasted work.

    Returns:
        The cached `Settings` instance.
    """
    return Settings()
