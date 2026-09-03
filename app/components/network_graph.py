"""Force-directed network-graph rendering, built on `networkx` + Plotly.

Used for the hour-by-hour chatter-community graph on the Community page —
nodes are channels, edges are "these two channels share chatters," edge
width/opacity scales with how many.
"""

from __future__ import annotations

import networkx as nx
import plotly.graph_objects as go
import polars as pl

from app.components.theme import CHROME, apply_base_layout, node_palette


def build_network_figure(
    edges: pl.DataFrame,
    *,
    a_col: str,
    b_col: str,
    weight_col: str,
    title: str,
    height: int = 480,
    color_universe: list[str] | None = None,
) -> go.Figure:
    """Build a force-directed network graph figure from an edge list.

    Args:
        edges: DataFrame with at least `a_col`, `b_col`, `weight_col`.
        a_col: Column holding one endpoint of each edge.
        b_col: Column holding the other endpoint of each edge.
        weight_col: Column holding the edge weight (used for layout and line width).
        title: Chart title.
        height: Chart height in pixels.
        color_universe: The full set of possible node names this chart type
            can ever show (e.g. every channel, across every hour), so a given
            node keeps the same color even when a different subset is drawn.
            Defaults to just the nodes in `edges`.

    Returns:
        A styled Plotly figure with edges as lines and each node in its own
        stable color (see `app.components.theme.node_palette`).
    """
    graph = nx.Graph()
    for row in edges.iter_rows(named=True):
        graph.add_edge(row[a_col], row[b_col], weight=float(row[weight_col]))
    positions = nx.spring_layout(graph, seed=42, weight="weight", k=1.2)
    # Always include this render's own nodes, even if `color_universe` (built
    # from a different, wider query) happens to miss one — a node must never
    # be left out of the palette it's about to be looked up in.
    palette = node_palette([*(color_universe or []), *graph.nodes])

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
                hoverinfo="skip",
                showlegend=False,
            )
        )

    node_names = list(graph.nodes)
    degree = dict(graph.degree(weight="weight"))
    node_trace = go.Scatter(
        x=[positions[n][0] for n in node_names],
        y=[positions[n][1] for n in node_names],
        mode="markers+text",
        text=node_names,
        textposition="top center",
        textfont={"color": CHROME["text_secondary"], "size": 11},
        marker={
            "size": [12 + 6 * degree[n] for n in node_names],
            "color": [palette[n] for n in node_names],
            "line": {"width": 1, "color": "white"},
        },
        hovertemplate="%{text}<extra></extra>",
        showlegend=False,
    )

    fig = go.Figure(data=[*edge_traces, node_trace])
    apply_base_layout(fig, title=title, height=height)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(hovermode="closest")
    return fig
