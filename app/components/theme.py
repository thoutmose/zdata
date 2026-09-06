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
import polars as pl
import streamlit as st

# Categorical palette, dark-surface variant, in validated fixed order. Never
# reorder; a color is assigned by position in this list, not by the order
# categories happen to appear in a (possibly filtered) dataframe.
#
# Positions 1 and 4 are ZEvent's own brand colors, scraped straight from
# zevent.fr's <meta name="theme-color"> tag (#00bd00) and its bundled CSS
# (#e7b22b gold). Two entries that worked on the app's old light background
# don't here: the CSS bundle's #007100 dark green sits at the exact same hue
# as the brand green (position 1) and is unreadably low-contrast against a
# near-black page (WCAG contrast ~3:1, vs. ~7-10:1 for the rest of this
# list) — duplicating a hue AND failing contrast at once — so position 6 is
# a sky blue instead (this palette had no blue left after green took
# position 1's old slot, and it fills the gap in the hue wheel cleanly).
# Position 7's violet is lightened for the same contrast reason. Verified
# with the WCAG relative-luminance formula against both CHROME["page"] and
# CHROME["surface"] — every entry clears 4.5:1.
CATEGORICAL = [
    "#00bd00",  # 1 ZEvent green (brand primary)
    "#eb6834",  # 2 orange
    "#1baf7a",  # 3 aqua
    "#e7b22b",  # 4 ZEvent gold
    "#e87ba4",  # 5 magenta
    "#4ea8ff",  # 6 sky blue
    "#a78bfa",  # 7 light violet
    "#e34948",  # 8 red
]

# Single-hue sequential ramp (magnitude), dark -> bright. On a near-black
# page a low-magnitude cell should recede toward the background (not "pop"
# the way a pale tint would on a white page) and a high-magnitude cell
# should glow — so this ramp runs the opposite direction from a light-theme
# ramp. Anchored on the brand green's own hue/saturation (from #00bd00),
# lightness stepped from near-background to a vivid highlight. For a bar
# chart (see `node_palette`'s callers) that's fine — a bar still has shape
# and position even at its dimmest step.
SEQUENTIAL_GREEN = ["#002e00", "#006200", "#009600", "#00ca00", "#00fe00", "#33ff33"]

# Same idea, but for heatmaps specifically: a heatmap cell has *no* shape or
# position cue of its own, only its fill color — so its dimmest step still
# needs to read as "a cell with some data" rather than being indistinguishable
# from the chart's own background (SEQUENTIAL_GREEN's floor, #002e00, sits at
# ~1.2:1 contrast against the app's dark surface; this ramp's floor clears
# ~2.2:1, still visibly the dim end of the ramp but not background-colored).
SEQUENTIAL_GREEN_HEATMAP = ["#006600", "#008f00", "#00b800", "#00e000", "#0aff0a", "#33ff33"]
SEQUENTIAL_GREEN_HEATMAP_COLORSCALE = [
    [i / (len(SEQUENTIAL_GREEN_HEATMAP) - 1), color]
    for i, color in enumerate(SEQUENTIAL_GREEN_HEATMAP)
]

# A second sequential ramp, anchored on ZEvent's gold (#e7b22b) rather than
# the brand green, for a continuous *third variable* encoded as marker color
# on top of a scatter's x/y (e.g. donation efficiency on the streamers
# audience-vs-engagement chart). Deliberately not green: every other hue in
# this app already reads as "the brand," so a chart that's ALSO all green
# for its color channel loses the one visual cue that's supposed to vary —
# everything blends into an undifferentiated green field. Gold is the
# app's only other real brand color, so this stays on-brand while still
# being immediately distinguishable from the rest of the page.
SEQUENTIAL_GOLD = ["#896710", "#b38614", "#dca519", "#e9b73a", "#edc663", "#f2d58c"]
SEQUENTIAL_GOLD_COLORSCALE = [
    [i / (len(SEQUENTIAL_GOLD) - 1), color] for i, color in enumerate(SEQUENTIAL_GOLD)
]

# Fixed, never themed — a status color is never reused for "series N".
STATUS = {
    "good": "#0ca30c",
    "warning": "#fab219",
    "critical": "#d03b3b",
    "muted": "#9c9c9c",
}

# Medal colors for a podium chart — deliberately not brand colors. A
# podium's whole visual language depends on gold/silver/bronze being
# instantly recognizable as 1st/2nd/3rd; substituting an on-brand hue for
# "silver" would just read as a bug.
PODIUM = {
    "gold": "#e7b22b",
    "silver": "#c7cbd1",
    "bronze": "#cd7f32",
}

# Every value below is ZEvent's own, scraped from zevent.fr's bundled CSS —
# this is their actual dark UI (near-black page/surface, off-white text,
# neutral grays for gridlines), not an invented dark mode.
CHROME = {
    "surface": "#171717",
    "page": "#0e0e0e",
    "text_primary": "#fafafa",
    "text_secondary": "#cfcfcf",
    "text_muted": "#9c9c9c",
    "gridline": "#313131",
    "baseline": "#515151",
}


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Convert a `#rrggbb` color to a Plotly-ready `rgba(...)` string.

    Lets fill/shading colors (e.g. the tint under a line chart) stay derived
    from `CATEGORICAL`/`CHROME` instead of being hardcoded separately — a
    palette change (e.g. swapping in a new brand color) then never leaves a
    stray hardcoded rgba() mismatched against the line it's shading. Defined
    before `_GLOBAL_CSS` (not with the rest of this module's functions,
    further down) because that CSS block is an f-string built at import
    time and calls this directly for the page-link hover tint.

    Args:
        hex_color: A `#rrggbb` hex color.
        alpha: Opacity from 0 to 1.

    Returns:
        `"rgba(r, g, b, alpha)"`.
    """
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"


_FONT_STACK = "'JetBrains Mono', ui-monospace, 'SF Mono', Consolas, monospace"

_GLOBAL_CSS = f"""
<style>
/* No @import for the font here: `.streamlit/config.toml`'s `theme.font`
   already loads JetBrains Mono from Google Fonts natively, once, before
   this stylesheet even runs. A second `@import` used to duplicate that
   fetch on every single page navigation — `@import` is also render-blocking
   (the browser must fetch and parse it before the rest of this stylesheet
   applies), so it was adding avoidable latency to every page, not just the
   first one. This block only needs to reference the family name.

   JetBrains Mono ships contextual ligatures (->, =>, !=, >=, ...) via the
   OpenType `calt` feature — on by default in code editors, but browsers
   need it asked for explicitly outside a `<code>` context. */
html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {{
    font-family: {_FONT_STACK};
    font-feature-settings: "calt" 1, "liga" 1;
    font-variant-ligatures: contextual;
}}

/* Headers in brand green, not just bold — every st.title/subheader in the
   app is a section header, and green is the one color that's unmistakably
   "this app," so it does double duty as free, consistent visual hierarchy. */
[data-testid="stHeading"] h1 {{
    font-weight: 800;
    letter-spacing: -0.02em;
    color: {CATEGORICAL[0]};
}}
[data-testid="stHeading"] h2, [data-testid="stHeading"] h3 {{
    font-weight: 700;
    letter-spacing: -0.01em;
    color: {CATEGORICAL[0]};
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
}}
[data-testid="stMetricLabel"] {{
    color: {CHROME["text_muted"]};
    font-weight: 600;
}}
/* A wide formatted number (e.g. "1,032,223 €") in a narrow KPI column would
   otherwise be cut short with "..." — wrap instead of truncating, since a
   silently-truncated KPI value is worse than one that wraps to two lines. */
[data-testid="stMetricValue"] {{
    white-space: normal;
    overflow-wrap: break-word;
    line-height: 1.15;
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

/* Page-nav links (the Home page's "Pages" grid, and any other st.page_link)
   as bordered, hoverable button cards instead of bare text — a link you
   have to notice is a link is worse than one that visibly invites a click. */
[data-testid="stPageLink"] {{
    border: 1px solid {CHROME["gridline"]};
    border-radius: 8px;
    padding: 0.5rem 0.9rem;
    background: {CHROME["surface"]};
    transition: border-color 0.15s ease, background 0.15s ease;
}}
[data-testid="stPageLink"]:hover {{
    border-color: {CATEGORICAL[0]};
    background: {hex_to_rgba(CATEGORICAL[0], 0.08)};
}}
[data-testid="stPageLink"] p {{
    font-weight: 600;
    color: {CHROME["text_primary"]};
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
    # Lightness 0.65, not the ~0.5 that would suit a light background — every
    # generated hue still needs to clear ~4.5:1 contrast against the app's
    # near-black surface (verified: worst-case hue at 0.65 lands ~4.8:1;
    # 0.5-0.55 drops as low as ~2.6:1 on blue/violet hues).
    while len(colors) < len(ordered):
        hue = (hue + golden_angle) % 360
        r, g, b = colorsys.hls_to_rgb(hue / 360, 0.65, 0.55)
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
            "family": _FONT_STACK,
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


def build_pie_figure(
    labels: list[str],
    values: list[float],
    *,
    title: str,
    height: int = 420,
    colors: list[str] | None = None,
    unit: str = "",
) -> go.Figure:
    """Build a donut chart in the app's shared style.

    A donut (not a full pie) leaves a hole to put the total in, if a caller
    wants one, and reads slightly easier for angle comparison. Colors come
    from `CATEGORICAL` by position unless overridden — callers collapsing a
    long tail into a trailing "Other" slice should pass `colors` explicitly
    so that slice gets `CHROME["baseline"]` instead of a false 9th hue.

    Args:
        labels: Slice labels, already in the order they should be drawn/colored.
        values: Slice magnitudes, same order as `labels`.
        title: Chart title.
        height: Chart height in pixels.
        colors: One color per slice. Defaults to `CATEGORICAL`, cycled.
        unit: Optional unit suffix shown in the hover tooltip (e.g. "messages").

    Returns:
        A styled Plotly donut chart.
    """
    slice_colors = colors or [CATEGORICAL[i % len(CATEGORICAL)] for i in range(len(labels))]
    unit_suffix = f" {unit}" if unit else ""
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.5,
            sort=False,
            marker={"colors": slice_colors, "line": {"color": CHROME["surface"], "width": 2}},
            textinfo="percent",
            textfont={"color": "white", "size": 12, "family": _FONT_STACK},
            hovertemplate=(
                f"%{{label}}<br>%{{value:,.0f}}{unit_suffix} (%{{percent}})<extra></extra>"
            ),
        )
    )
    apply_base_layout(fig, title=title, height=height)
    fig.update_layout(
        hovermode="closest",
        legend={
            "orientation": "v",
            "yanchor": "middle",
            "y": 0.5,
            "xanchor": "left",
            "x": 1.02,
            "font": {"color": CHROME["text_secondary"]},
        },
    )
    return fig


def build_podium_figure(
    labels: list[str],
    values: list[float],
    *,
    title: str,
    unit: str = "",
    height: int = 380,
) -> go.Figure:
    """Build a 3-bar "podium" chart for a top-3 leaderboard.

    Args:
        labels: Exactly 3 names, ranked 1st, 2nd, 3rd in that order.
        values: Exactly 3 values, same order as `labels`.
        title: Chart title.
        unit: Optional unit suffix for the value label/tooltip (e.g. "€").
        height: Chart height in pixels.

    Returns:
        A styled Plotly bar chart arranged 2nd/1st/3rd (the classic podium
        layout, tallest in the middle) — bar height is the real value, not
        a fake fixed-height block, colored gold/silver/bronze with a medal
        + value label above each bar.
    """
    if len(labels) != 3 or len(values) != 3:
        msg = "build_podium_figure needs exactly 3 labels and 3 values."
        raise ValueError(msg)
    podium_order = [1, 0, 2]  # 2nd, 1st, 3rd
    medals = ["🥇", "🥈", "🥉"]
    colors = [PODIUM["gold"], PODIUM["silver"], PODIUM["bronze"]]
    podium_labels = [labels[i] for i in podium_order]
    podium_values = [values[i] for i in podium_order]
    podium_colors = [colors[i] for i in podium_order]
    podium_text = [
        f"{medals[i]} {labels[i]}<br>{values[i]:,.0f}{f' {unit}' if unit else ''}"
        for i in podium_order
    ]

    fig = go.Figure(
        go.Bar(
            x=podium_labels,
            y=podium_values,
            marker={"color": podium_colors},
            text=podium_text,
            textposition="outside",
            textfont={"size": 13, "color": CHROME["text_primary"]},
            hovertemplate=f"%{{x}}<br>%{{y:,.0f}}{f' {unit}' if unit else ''}<extra></extra>",
        )
    )
    apply_base_layout(fig, title=title, height=height)
    fig.update_yaxes(title_text=unit, range=[0, max(podium_values) * 1.35])
    fig.update_xaxes(title_text="", showticklabels=False)
    fig.update_layout(showlegend=False)
    return fig


def build_radar_figure(
    categories: list[str],
    series: list[tuple[str, list[float]]],
    *,
    title: str,
    height: int = 420,
    reference_value: float | None = None,
    reference_name: str = "",
) -> go.Figure:
    """Build a radar ("star") chart comparing one or more entities across several metrics at once.

    Each series' values must already be on one common, comparable scale
    (this app uses percentile rank, 0-100) before they reach here — a radar
    chart plotting raw units (€, viewers, messages) on the same axes would
    visually imply they're the same kind of magnitude when they're not,
    which is far more misleading on a radar than on a bar chart, where each
    axis at least keeps its own label. Percentile rank against the same
    population is the standard normalization for exactly this.

    `apply_base_layout` isn't used here — it configures cartesian x/y axes
    and an "x unified" hover mode that don't apply to a polar chart, so this
    styles the polar-specific layout directly instead, matching the same
    palette and fonts.

    Args:
        categories: Axis labels, in the order they should appear around the
            circle.
        series: One `(name, values)` pair per entity to plot, each `values`
            list in the same order as `categories` and already normalized
            (e.g. 0-100 percentile rank). A single-entity radar is just a
            `series` of length 1 — there's no separate single/multi API.
        title: Chart title.
        height: Chart height in pixels.
        reference_value: If given, draws an extra, dashed reference trace
            at this same value on every axis (e.g. 50 for "the median of
            the field") — comparing a shape against a flat, undecorated
            baseline is far easier to read than remembering an axis's own
            unlabeled scale.
        reference_name: Legend label for the reference trace. Required if
            `reference_value` is given.

    Returns:
        A styled Plotly `Scatterpolar` figure.
    """
    theta = [*categories, categories[0]]
    fig = go.Figure()
    for i, (name, values) in enumerate(series):
        color = CATEGORICAL[i % len(CATEGORICAL)]
        r = [*values, values[0]]
        fig.add_trace(
            go.Scatterpolar(
                r=r,
                theta=theta,
                fill="toself",
                name=name,
                line={"color": color, "width": 2},
                fillcolor=hex_to_rgba(color, 0.25),
                hovertemplate="%{theta}<br>%{r:.0f}<extra></extra>",
            )
        )
    if reference_value is not None:
        ref_r = [reference_value] * len(theta)
        fig.add_trace(
            go.Scatterpolar(
                r=ref_r,
                theta=theta,
                name=reference_name,
                line={"color": CHROME["baseline"], "width": 1, "dash": "dot"},
                hoverinfo="skip",
            )
        )
    fig.update_layout(
        title={"text": title, "font": {"size": 16, "color": CHROME["text_primary"]}},
        height=height,
        paper_bgcolor=CHROME["surface"],
        font={"family": _FONT_STACK, "color": CHROME["text_secondary"]},
        polar={
            "bgcolor": CHROME["surface"],
            "radialaxis": {
                "visible": True,
                "range": [0, 100],
                "gridcolor": CHROME["gridline"],
                "color": CHROME["text_muted"],
            },
            "angularaxis": {"gridcolor": CHROME["gridline"], "color": CHROME["text_secondary"]},
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": -0.2,
            "xanchor": "center",
            "x": 0.5,
            "font": {"color": CHROME["text_secondary"]},
        },
    )
    return fig


def build_race_figure(
    df: pl.DataFrame,
    *,
    value_col: str,
    rank_col: str,
    title: str,
    unit: str,
    height: int = 560,
) -> go.Figure:
    """Build a "leaderboard race" chart: one line per channel, hour by hour.

    Shared by every "each hour's top-8 by X, over time" chart in the app
    (viewer/message/donation leaderboards) — same shape each time: one
    trace per channel that was ever in an hour's top 8, with that hour's
    exact rank surfaced on hover.

    A channel not in a given hour's top 8 simply has no row for that hour
    (`df` is expected pre-filtered to top-8-per-hour, e.g. by
    `channel_viewership_leaderboard_timeseries`) — its line has a gap there
    rather than a fabricated zero.

    The legend sits below the plot, not `apply_base_layout`'s default above
    it — this chart can have dozens of channels (every one that ever
    cracked the top 8 across the whole window), and that many horizontal
    legend entries wrap onto the title at the default position.

    Args:
        df: Columns `timestamp`, `channel`, `value_col`, `rank_col` — one
            row per (channel, hour) it appeared in the top 8.
        value_col: Column to plot on the y-axis (e.g. `avg_viewer_count`).
        rank_col: Column with that hour's 1-based rank, shown on hover.
        title: Chart title.
        unit: Unit label for the y-axis and hover tooltip (e.g. "viewers").
        height: Chart height in pixels.

    Returns:
        A styled Plotly figure with one trace per channel.
    """
    channels = sorted(df["channel"].unique().to_list())
    palette = node_palette(channels)
    fig = go.Figure()
    for channel in channels:
        subset = df.filter(pl.col("channel") == channel).sort("timestamp")
        fig.add_trace(
            go.Scatter(
                x=subset["timestamp"],
                y=subset[value_col],
                mode="lines+markers",
                name=channel,
                line={"color": palette[channel], "width": 2},
                marker={"size": 5},
                customdata=subset[rank_col],
                hovertemplate=(
                    f"{channel}<br>%{{x|%a %H:%M}}<br>%{{y:,.0f}} {unit} "
                    "(rank #%{customdata})<extra></extra>"
                ),
            )
        )
    apply_base_layout(fig, title=title, height=height)
    fig.update_yaxes(title_text=unit)
    fig.update_layout(
        legend={"orientation": "h", "yanchor": "top", "y": -0.18, "xanchor": "left", "x": 0},
        margin={"l": 10, "r": 10, "t": 48, "b": 120},
    )
    return fig
