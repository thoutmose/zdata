"""Shared chart theme and color palette.

Any new chart in this project must be built against the constants and helpers
here rather than picking colors ad hoc. The palette is validated for
colorblind-safety in fixed order (see the project's `dataviz` skill
guidance) — categorical hues must never be reassigned, cycled, or picked by a
filtered dataframe's row order, or the color-blind-safety guarantee breaks.
"""

from __future__ import annotations

import colorsys

import plotly.graph_objects as go
import streamlit as st

# Categorical palette, light-surface variant, in validated fixed order.
# Never reorder; a color is assigned by position in this list, not by the
# order categories happen to appear in a (possibly filtered) dataframe.
CATEGORICAL = [
    "#2a78d6",  # 1 blue
    "#eb6834",  # 2 orange
    "#1baf7a",  # 3 aqua
    "#eda100",  # 4 yellow
    "#e87ba4",  # 5 magenta
    "#008300",  # 6 green
    "#4a3aa7",  # 7 violet
    "#e34948",  # 8 red
]

# Single-hue sequential ramp (magnitude), light -> dark.
SEQUENTIAL_BLUE = ["#cde2fb", "#9ec5f4", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"]

# Plotly colorscale built from the same ramp, for heatmaps.
SEQUENTIAL_BLUE_COLORSCALE = [
    [i / (len(SEQUENTIAL_BLUE) - 1), color] for i, color in enumerate(SEQUENTIAL_BLUE)
]

# Fixed, never themed — a status color is never reused for "series N".
STATUS = {
    "good": "#0ca30c",
    "warning": "#fab219",
    "critical": "#d03b3b",
    "muted": "#898781",
}

CHROME = {
    "surface": "#fcfcfb",
    "page": "#f9f9f7",
    "text_primary": "#0b0b0b",
    "text_secondary": "#52514e",
    "text_muted": "#898781",
    "gridline": "#e1e0d9",
    "baseline": "#c3c2b7",
}


_GLOBAL_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {{
    font-family: 'Inter', system-ui, -apple-system, "Segoe UI", sans-serif;
}}

[data-testid="stHeading"] h1 {{
    font-weight: 800;
    letter-spacing: -0.02em;
}}
[data-testid="stHeading"] h2, [data-testid="stHeading"] h3 {{
    font-weight: 700;
    letter-spacing: -0.01em;
}}

/* Metric "cards": the plain st.metric block gets a surface, border and a
   thin brand-colored top accent so KPI rows read as distinct cards rather
   than bare numbers floating in the page. */
[data-testid="stMetric"] {{
    background: {CHROME["surface"]};
    border: 1px solid {CHROME["gridline"]};
    border-top: 3px solid {CATEGORICAL[0]};
    border-radius: 10px;
    padding: 0.9rem 1rem 0.7rem;
    box-shadow: 0 1px 2px rgba(11, 11, 11, 0.04);
}}
[data-testid="stMetricLabel"] {{
    color: {CHROME["text_muted"]};
    font-weight: 600;
}}

[data-testid="stSidebar"] {{
    border-right: 1px solid {CHROME["gridline"]};
}}

div[data-testid="stExpander"] {{
    border-radius: 10px;
    border: 1px solid {CHROME["gridline"]};
}}

.stButton > button, .stDownloadButton > button {{
    border-radius: 8px;
    font-weight: 600;
}}

hr {{
    margin: 1.75rem 0;
    border-color: {CHROME["gridline"]};
}}
</style>
"""


def inject_global_css() -> None:
    """Inject the app's global CSS (font, KPI cards, spacing) once per page render.

    Streamlit re-executes every page's module top-to-bottom on each render
    (there's no persistent "layout" file), so this is called from
    `page_header()` and the home page — cheap and idempotent, since it's just
    a `<style>` block the browser applies identically each time.
    """
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


def node_palette(entities: list[str]) -> dict[str, str]:
    """Assign one stable color per entity, for identity-encoded node/network charts.

    Only used where every individual entity must stay visually distinguishable
    (e.g. one node per channel in the chatter-community network graph) —
    ordinary ranked bar/line charts should keep using a single hue from
    `CATEGORICAL`, per the project's dataviz guidance. The first 8 entities
    (sorted, so assignment doesn't depend on render order) get the validated
    `CATEGORICAL` hues; beyond that, extra hues are generated with golden-angle
    spacing at the same saturation/lightness so they stay visually consistent
    with the base palette without ever reusing a hue.

    Args:
        entities: The full set of entity names that may need a color across
            every render this chart type can show (e.g. every channel name,
            not just the ones in the currently selected hour) — this keeps a
            given entity's color stable even as a filter changes which subset
            is drawn.

    Returns:
        Mapping from entity name to hex color, stable for a given `entities` set.
    """
    ordered = sorted(set(entities))
    colors = list(CATEGORICAL)
    golden_angle = 137.508
    hue = 0.0
    while len(colors) < len(ordered):
        hue = (hue + golden_angle) % 360
        r, g, b = colorsys.hls_to_rgb(hue / 360, 0.52, 0.55)
        colors.append(f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}")
    return dict(zip(ordered, colors, strict=False))


def apply_base_layout(fig: go.Figure, *, title: str, height: int = 420) -> go.Figure:
    """Apply the shared chart chrome (fonts, gridlines, background) to a figure.

    Args:
        fig: The Plotly figure to style in place.
        title: Chart title, rendered in the shared type scale.
        height: Chart height in pixels.

    Returns:
        The same figure, styled and returned for chaining.
    """
    fig.update_layout(
        title={"text": title, "font": {"size": 16, "color": CHROME["text_primary"]}},
        height=height,
        margin={"l": 10, "r": 10, "t": 48, "b": 10},
        paper_bgcolor=CHROME["surface"],
        plot_bgcolor=CHROME["surface"],
        font={
            "family": "system-ui, -apple-system, Segoe UI, sans-serif",
            "color": CHROME["text_secondary"],
        },
        hovermode="x unified",
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.0,
            "xanchor": "left",
            "x": 0,
            "font": {"color": CHROME["text_secondary"]},
        },
    )
    fig.update_xaxes(showgrid=False, linecolor=CHROME["baseline"], color=CHROME["text_muted"])
    fig.update_yaxes(
        showgrid=True,
        gridcolor=CHROME["gridline"],
        zeroline=False,
        color=CHROME["text_muted"],
    )
    return fig
