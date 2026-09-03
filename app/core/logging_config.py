"""Application-wide logging setup, driven by `logging.yml`.

`logging.yml` declares formatters, handlers, and two profiles
(`development` / `production`); `setup_logging()` picks the profile matching
`Settings.app_env`, wires it onto the root logger, and hands the whole thing
to `logging.config.dictConfig`. Every logger in this project propagates to
root by default, so the chosen profile is what actually decides where
output goes.

Every handler is additionally tagged (via the `session_id` filter) with the
active Streamlit session id, so log lines from concurrent users on a public
deployment can be told apart.
"""

from __future__ import annotations

import gzip
import logging
import logging.config
import logging.handlers
import os
import shutil
from pathlib import Path

import yaml

from app.core.config import get_settings

_LOGGING_YML = Path(__file__).resolve().parents[2] / "logging.yml"
_CONFIGURED = False


class SessionIdFilter(logging.Filter):
    """Attach the current Streamlit session id to every log record.

    Falls back to `"system"` for log lines emitted outside of an active
    Streamlit script run (e.g. at process startup).
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Add a `session_id` attribute to the record before it is formatted.

        Args:
            record: The log record being emitted.

        Returns:
            Always True; this filter only enriches records, never drops them.
        """
        record.session_id = _current_session_id()
        return True


def _current_session_id() -> str:
    """Best-effort lookup of the active Streamlit session id.

    Returns:
        A short session identifier, or `"system"` if none is active (for
        example during module import or in a background thread).
    """
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        ctx = get_script_run_ctx()
    except Exception:
        return "system"
    if ctx is None:
        return "system"
    return ctx.session_id[:8]


def _gzip_rotator(source: str, dest: str) -> None:
    """Compress a just-rotated log file and remove the plain-text original.

    Args:
        source: Path of the rotated (plain-text) log file.
        dest: Path the compressed file should be written to.
    """
    with open(source, "rb") as f_in, gzip.open(dest, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    os.remove(source)


class CompressedRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """A `RotatingFileHandler` whose rotated backups are gzip-compressed.

    Uses the `namer`/`rotator` extension points the stdlib provides for this
    exact purpose, so the built-in rotation chain (shifting `.1` -> `.2`, and
    deleting anything past `backupCount`) keeps working correctly with `.gz`
    names — a hand-rolled override of `doRollover` would desync from that
    chain after the first rotation.
    """

    def __init__(
        self,
        filename: str,
        mode: str = "a",
        maxBytes: int = 0,  # matches stdlib RotatingFileHandler's argument names
        backupCount: int = 0,
        encoding: str | None = None,
        delay: bool = False,
    ) -> None:
        """Initialize the handler and install the gzip namer/rotator.

        Args:
            filename: Path of the active (uncompressed) log file.
            mode: File open mode.
            maxBytes: Size in bytes that triggers a rotation.
            backupCount: Number of rotated (compressed) files to keep.
            encoding: Text encoding for the log file.
            delay: If True, defer file opening until the first emit.
        """
        super().__init__(
            filename,
            mode=mode,
            maxBytes=maxBytes,
            backupCount=backupCount,
            encoding=encoding,
            delay=delay,
        )
        self.namer = lambda name: f"{name}.gz"
        self.rotator = _gzip_rotator


def setup_logging() -> None:
    """Configure the root logger for the whole application from `logging.yml`.

    Idempotent: safe to call from every page module on every Streamlit rerun
    without reconfiguring or installing duplicate handlers.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    settings = get_settings()
    with _LOGGING_YML.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    profile = config["loggers"].get(settings.app_env, config["loggers"]["production"])
    config["root"]["level"] = profile["level"]
    config["root"]["handlers"] = profile["handlers"]
    config["loggers"] = {}

    for handler in config["handlers"].values():
        if "filename" in handler:
            Path(handler["filename"]).parent.mkdir(parents=True, exist_ok=True)

    logging.config.dictConfig(config)
    _CONFIGURED = True
    logging.getLogger(__name__).info(
        "Logging configured from logging.yml (profile=%s)", settings.app_env
    )
