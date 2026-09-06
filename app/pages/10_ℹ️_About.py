"""About page: what ZEvent is, what this dashboard does, and how its data pipeline works."""

from __future__ import annotations

import logging

import polars as pl
import streamlit as st
from app.components.chrome import page_footer, page_header
from app.core.i18n import t
from app.core.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

page_header(t("about.title"), "ℹ️", t("about.description"))  # noqa: RUF001

st.subheader(t("about.what_heading"))
st.markdown(t("about.what_body"))

st.subheader(t("about.dashboard_heading"))
st.markdown(t("about.dashboard_body"))

st.subheader(t("about.pipeline_heading"))
st.markdown(t("about.pipeline_body"))
st.dataframe(
    pl.DataFrame(
        {
            t("about.pipeline.column_schema"): ["raw", "stg", "int", "marts"],
            t("about.pipeline.column_purpose"): [
                t("about.pipeline.raw"),
                t("about.pipeline.stg"),
                t("about.pipeline.int"),
                t("about.pipeline.marts"),
            ],
        }
    ),
    width="stretch",
    hide_index=True,
)

st.subheader(t("about.infra_heading"))
st.markdown(t("about.infra_body"))

st.subheader(t("about.freshness_heading"))
st.markdown(t("about.freshness_body"))

st.subheader(t("about.privacy_heading"))
st.markdown(t("about.privacy_body"))

st.subheader(t("about.stack_heading"))
st.markdown(t("about.stack_body"))

st.divider()
st.markdown(t("about.related_heading"))
st.markdown(t("about.related_body"))

page_footer()

logger.info("About page rendered")
