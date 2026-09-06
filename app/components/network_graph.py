"""Network and flow rendering for the Community page, built on `networkx` + Plotly.

Two genuinely different graph shapes live here, and they're kept as two
different chart types rather than forced through one function:

- `build_network_figure` — an undirected weighted graph (nodes are channels,
  edges are "these two channels share chatters"). Used for the hour-by-hour
  and event-wide shared-audience graphs.
- `build_migration_sankey` — a directed flow diagram (from-channel to
  to-channel chatter hops). Migrations are directed and a channel pair
  routinely has hops in both directions; rendering that as an undirected
  `networkx.Graph` (as this module used to) is silently lossy —
  `Graph.add_edge(a, b, weight=w)` called twice for the same unordered pair
  (once for each direction) overwrites rather than keeping both, so one
  direction's hop count just vanishes. A Sankey keeps every directed flow as
  its own band, which is also the standard chart for "flow between
  categories" data in the first place.
"""

from __future__ import annotations

import math

import networkx as nx
import numpy as np
import plotly.graph_objects as go
import polars as pl
from networkx.algorithms.community import greedy_modularity_communities

from app.components.theme import CHROME, apply_base_layout, hex_to_rgba, node_palette

# How many node labels stay permanently on-canvas, at most — every node is
# still hoverable for its name regardless. A force-directed layout with a
# label glued to every node is unreadable well before it has 20 nodes; only
# the biggest hubs earn a persistent label, everyone else is a click away.
_MAX_STATIC_LABELS = 15


def build_network_figure(
    edges: pl.DataFrame,
    *,
    a_col: str,
    b_col: str,
    weight_col: str,
    title: str,
    height: int = 480,
    min_weight: float = 0,
    weight_label: str = "shared chatters",
    weight_format: str = ",.0f",
) -> go.Figure:
    """Build a force-directed network graph figure from an undirected edge list.

    Three changes from a "plain" force-directed graph, all aimed at the same
    problem — a dense weighted graph rendered with a cold-start layout and
    one arbitrary color per node reads as a hairball, not an analysis:

    - Weak edges are dropped before layout (`min_weight`). A shared-audience
      graph is close to a *complete* graph — almost every pair of channels
      shares at least a few chatters — so rendering every edge regardless of
      strength draws hundreds of near-invisible, mutually crossing lines that
      still add up to visual noise and drag `spring_layout` toward a
      cold-start-like blob. Dropping edges below the threshold (and any node
      that has none left) leaves the graph showing what it's actually meant
      to: which channels' audiences overlap *substantially*.
    - Node color encodes a *detected community* (modularity clustering via
      `networkx`), not an arbitrary per-node hue. This is also the actual
      analytical point of a "community" page's network graph: which
      channels' audiences cluster together.
    - The layout is community-aware: nodes start near an anchor point for
      their own community (arranged around a circle) instead of a random
      cold start, so `spring_layout`'s force simulation refines an
      already-sensible starting arrangement instead of relaxing from noise.
      Same-community nodes reliably end up spatially close, not just
      same-colored.

    Args:
        edges: DataFrame with at least `a_col`, `b_col`, `weight_col`.
        a_col: Column holding one endpoint of each edge.
        b_col: Column holding the other endpoint of each edge.
        weight_col: Column holding the edge weight (used for layout and line width).
        title: Chart title.
        height: Chart height in pixels.
        min_weight: Drop edges below this weight before laying out or
            drawing anything. Defaults to 0 (keep everything), since not
            every caller's weights are on the same scale — callers showing a
            near-complete graph should pass a threshold (e.g. a percentile of
            their own `weight_col`) rather than relying on a fixed default
            here that would be meaningless across different weight scales.
        weight_label: Unit shown after the weight in each edge's hover text
            (e.g. "shared chatters" for a raw count, "Jaccard overlap" for a
            0-1 ratio) — `weight_col` isn't always the same metric.
        weight_format: A `format()` spec for the weight's hover value.
            Defaults to a thousands-grouped integer; override for a ratio
            (e.g. `".3f"`), which the default would otherwise floor to 0.

    Returns:
        A styled Plotly figure with edges as lines (hoverable for their exact
        weight) and nodes colored by detected community, sized by
        area-proportional weighted degree, and labeled if they're among the
        `_MAX_STATIC_LABELS` biggest hubs (every node is hoverable regardless).
    """
    if min_weight > 0:
        edges = edges.filter(pl.col(weight_col) >= min_weight)

    graph = nx.Graph()
    for row in edges.iter_rows(named=True):
        graph.add_edge(row[a_col], row[b_col], weight=float(row[weight_col]))

    communities = list(greedy_modularity_communities(graph, weight="weight"))
    community_of = {node: i for i, community in enumerate(communities) for node in community}
    n_communities = max(len(communities), 1)
    # Reuse node_palette's own dark-surface-safe hue generation (validated
    # CATEGORICAL first, golden-angle extension beyond that) rather than
    # duplicating that logic here — the "entities" are community indices,
    # not node names, but the function doesn't care.
    community_colors = node_palette([str(i) for i in range(n_communities)])

    # Community-aware warm start: each node begins near its community's own
    # anchor point on a circle (radius grows with community count so they
    # don't overlap), with a little jitter so nodes in the same community
    # aren't stacked exactly on top of each other before the force
    # simulation spreads them out.
    anchor_radius = 1.0 + 0.15 * n_communities
    anchors = {
        i: (
            anchor_radius * math.cos(2 * math.pi * i / n_communities),
            anchor_radius * math.sin(2 * math.pi * i / n_communities),
        )
        for i in range(n_communities)
    }
    rng = np.random.default_rng(42)
    initial_pos = {
        node: (
            anchors[community_of[node]][0] + rng.uniform(-0.3, 0.3),
            anchors[community_of[node]][1] + rng.uniform(-0.3, 0.3),
        )
        for node in graph.nodes
    }
    # k (ideal spring length) scales with node count so the layout stays
    # legible whether an hour has 4 active channels or all of them — a fixed
    # k either crowds a big graph or leaves a small one adrift. iterations is
    # raised well past nx's default (50) so the simulation has room to
    # refine the community-aware warm start rather than barely move from it.
    node_count = max(graph.number_of_nodes(), 1)
    positions = nx.spring_layout(
        graph, pos=initial_pos, seed=42, weight="weight", k=2.2 / node_count**0.5, iterations=200
    )

    max_weight = float(edges.select(pl.col(weight_col).cast(pl.Float64).max()).item() or 1)
    edge_traces = []
    for row in edges.iter_rows(named=True):
        x0, y0 = positions[row[a_col]]
        x1, y1 = positions[row[b_col]]
        weight_ratio = float(row[weight_col]) / max_weight
        edge_traces.append(
            go.Scatter(
                x=[x0, x1],
                y=[y0, y1],
                mode="lines",
                line={"color": CHROME["baseline"], "width": 1 + 4 * weight_ratio},
                opacity=0.3 + 0.5 * weight_ratio,
                # Midpoint-labeled hover rather than "skip": a network graph
                # whose edges can't tell you their own weight on hover isn't
                # really explorable, just decorative.
                hoverinfo="text",
                hovertext=(
                    f"{row[a_col]} ↔ {row[b_col]}<br>"
                    f"{format(row[weight_col], weight_format)} {weight_label}"
                ),
                showlegend=False,
            )
        )

    node_names = list(graph.nodes)
    degree = dict(graph.degree(weight="weight"))
    max_degree = max(degree.values(), default=1) or 1
    labeled = set(sorted(degree, key=degree.get, reverse=True)[:_MAX_STATIC_LABELS])
    node_trace = go.Scatter(
        x=[positions[n][0] for n in node_names],
        y=[positions[n][1] for n in node_names],
        mode="markers+text",
        text=[n if n in labeled else "" for n in node_names],
        textposition="top center",
        textfont={"color": CHROME["text_secondary"], "size": 11},
        marker={
            # Size by sqrt of weighted degree, not degree itself: humans read
            # a marker's *area*, not its diameter, as its magnitude, and area
            # already grows with the square of radius — sizing linearly in
            # degree overstates the gap between a hub and a leaf node.
            "size": [10 + 22 * (degree[n] / max_degree) ** 0.5 for n in node_names],
            "color": [community_colors[str(community_of[n])] for n in node_names],
            # Page-colored ring, not white: on the app's dark surface a white
            # halo around every node would fight the background rather than
            # simply separating overlapping markers.
            "line": {"width": 1, "color": CHROME["page"]},
        },
        customdata=[[n, degree[n]] for n in node_names],
        hovertemplate="%{customdata[0]}<br>%{customdata[1]:,.0f} weighted degree<extra></extra>",
        showlegend=False,
    )

    fig = go.Figure(data=[*edge_traces, node_trace])
    apply_base_layout(fig, title=title, height=height)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(hovermode="closest")
    return fig


def build_migration_sankey(
    edges: pl.DataFrame,
    *,
    source_col: str,
    target_col: str,
    value_col: str,
    title: str,
    height: int = 480,
    color_universe: list[str] | None = None,
) -> go.Figure:
    """Build a directed flow diagram for channel-to-channel chatter migrations.

    Every channel gets two node instances — a left "from" copy and a right
    "to" copy — rather than one shared node per channel. A Sankey lays nodes
    out in strict left-to-right columns and can't draw a cycle (e.g. both
    `a -> b` and `b -> a`, which real migration data has); splitting each
    channel into a from-copy and a to-copy turns that cycle into two
    perfectly normal cross-diagram bands instead.

    Args:
        edges: DataFrame with at least `source_col`, `target_col`, `value_col`.
        source_col: Column holding the origin channel of each hop.
        target_col: Column holding the destination channel of each hop.
        value_col: Column holding the flow magnitude (band width).
        title: Chart title.
        height: Chart height in pixels.
        color_universe: The full set of channels this chart can ever show, so
            a channel keeps the same color as it has in the network graphs
            above it. Defaults to just the channels in `edges`.

    Returns:
        A styled Plotly Sankey figure, one band per directed (from, to) pair.
    """
    channels = sorted(
        {*(color_universe or []), *edges[source_col].to_list(), *edges[target_col].to_list()}
    )
    palette = node_palette(channels)
    from_index = {name: i for i, name in enumerate(channels)}
    to_index = {name: i + len(channels) for i, name in enumerate(channels)}

    node_labels = [f"{c} →" for c in channels] + [f"→ {c}" for c in channels]
    node_colors = [palette[c] for c in channels] * 2

    rows = edges.iter_rows(named=True)
    links_source, links_target, links_value, links_label, links_color = [], [], [], [], []
    for row in rows:
        links_source.append(from_index[row[source_col]])
        links_target.append(to_index[row[target_col]])
        links_value.append(float(row[value_col]))
        links_label.append(f"{row[source_col]} → {row[target_col]}: {row[value_col]:,.0f}")
        links_color.append(hex_to_rgba(palette[row[source_col]], 0.45))

    fig = go.Figure(
        go.Sankey(
            arrangement="snap",
            node={
                "label": node_labels,
                "color": node_colors,
                "pad": 14,
                "thickness": 16,
                "line": {"color": CHROME["page"], "width": 1},
                "hovertemplate": "%{label}<extra></extra>",
            },
            link={
                "source": links_source,
                "target": links_target,
                "value": links_value,
                "color": links_color,
                "customdata": links_label,
                "hovertemplate": "%{customdata}<extra></extra>",
            },
        )
    )
    apply_base_layout(fig, title=title, height=height)
    fig.update_layout(font={"color": CHROME["text_secondary"]}, hovermode="closest")
    return fig
