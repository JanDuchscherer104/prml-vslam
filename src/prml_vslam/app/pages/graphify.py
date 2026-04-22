"""Streamlit wrapper around generated Graphify inspection artifacts."""

from __future__ import annotations

import json
import re
import tempfile
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import networkx as nx
import streamlit as st
import streamlit.components.v1 as components
from graphify.export import to_html
from networkx.readwrite import json_graph

from ..ui import render_page_intro

if TYPE_CHECKING:
    from ..bootstrap import AppContext


@dataclass(frozen=True, slots=True)
class GraphifyArtifacts:
    """Resolved Graphify artifact paths for the repository root."""

    root: Path
    """Graphify output directory."""
    report: Path
    """Generated markdown report."""
    graph_json: Path
    """Generated graph data."""
    graph_html: Path
    """Generated self-contained HTML viewer."""

    @property
    def all_present(self) -> bool:
        """Return whether the standard Graphify viewer artifact set exists."""
        return self.report.exists() and self.graph_json.exists() and self.graph_html.exists()


@dataclass(frozen=True, slots=True)
class GraphifySummary:
    """Small display summary derived from generated Graphify artifacts."""

    report_title: str
    """Report title line."""
    graph_date: str
    """Graph generation date from the report, when available."""
    nodes: int
    """Number of graph nodes."""
    links: int
    """Number of graph links."""
    communities: int
    """Number of communities in the report summary."""


class GraphifySourceScope(StrEnum):
    """Source-file scopes exposed by the Graphify app page."""

    ALL = "all"
    PRML_VSLAM = "prml_vslam"
    EXCLUDE_TESTS = "exclude_tests"
    TESTS_ONLY = "tests_only"

    @property
    def label(self) -> str:
        """Return the UI label for this source scope."""
        return {
            GraphifySourceScope.ALL: "All sources",
            GraphifySourceScope.PRML_VSLAM: "Only src/prml_vslam",
            GraphifySourceScope.EXCLUDE_TESTS: "Exclude tests",
            GraphifySourceScope.TESTS_ONLY: "Only tests",
        }[self]


class GraphifyViewerFilter(StrEnum):
    """Chip-style filter options for the Graphify viewer."""

    ONLY_PRML_VSLAM = "only_prml_vslam"
    EXCLUDE_TESTS = "exclude_tests"
    ONLY_TESTS = "only_tests"
    CODE_ONLY = "code_only"

    @property
    def label(self) -> str:
        """Return the UI label for this viewer filter."""
        return {
            GraphifyViewerFilter.ONLY_PRML_VSLAM: "Only src/prml_vslam",
            GraphifyViewerFilter.EXCLUDE_TESTS: "Exclude tests",
            GraphifyViewerFilter.ONLY_TESTS: "Only tests",
            GraphifyViewerFilter.CODE_ONLY: "Code nodes only",
        }[self]


@dataclass(frozen=True, slots=True)
class GraphifyFilterOptions:
    """Filtering controls for the embedded Graphify viewer."""

    source_scope: GraphifySourceScope = GraphifySourceScope.ALL
    """Which source-file subset should be kept."""
    include_rationale_nodes: bool = True
    """Whether rationale/docstring-derived nodes should remain visible."""
    minimum_degree: int = 0
    """Minimum graph degree required for each retained node."""

    @classmethod
    def from_selected_filters(
        cls,
        selected_filters: list[GraphifyViewerFilter],
        *,
        minimum_degree: int = 0,
    ) -> GraphifyFilterOptions:
        """Build viewer options from chip-style multiselect filters."""
        selected = set(selected_filters)
        if GraphifyViewerFilter.ONLY_TESTS in selected:
            source_scope = GraphifySourceScope.TESTS_ONLY
        elif GraphifyViewerFilter.ONLY_PRML_VSLAM in selected:
            source_scope = GraphifySourceScope.PRML_VSLAM
        elif GraphifyViewerFilter.EXCLUDE_TESTS in selected:
            source_scope = GraphifySourceScope.EXCLUDE_TESTS
        else:
            source_scope = GraphifySourceScope.ALL
        return cls(
            source_scope=source_scope,
            include_rationale_nodes=GraphifyViewerFilter.CODE_ONLY not in selected,
            minimum_degree=minimum_degree,
        )


def resolve_graphify_artifacts(repo_root: Path) -> GraphifyArtifacts:
    """Resolve standard Graphify artifact paths under a repository root."""
    graphify_root = repo_root / "graphify-out"
    return GraphifyArtifacts(
        root=graphify_root,
        report=graphify_root / "GRAPH_REPORT.md",
        graph_json=graphify_root / "graph.json",
        graph_html=graphify_root / "graph.html",
    )


def load_graphify_graph(artifacts: GraphifyArtifacts) -> nx.Graph:
    """Load the generated Graphify JSON as a NetworkX graph."""
    payload = json.loads(artifacts.graph_json.read_text(encoding="utf-8"))
    try:
        graph = json_graph.node_link_graph(payload, edges="links")
    except TypeError:
        graph = json_graph.node_link_graph(payload)
    return graph


def filter_graphify_graph(graph: nx.Graph, options: GraphifyFilterOptions) -> nx.Graph:
    """Return a Graphify subgraph matching viewer filter options."""
    degrees = dict(graph.degree())
    kept_nodes = [
        node_id
        for node_id, data in graph.nodes(data=True)
        if _source_scope_matches(str(data.get("source_file") or ""), options.source_scope)
        and (options.include_rationale_nodes or data.get("file_type") != "rationale")
        and degrees.get(node_id, 0) >= options.minimum_degree
    ]
    return graph.subgraph(kept_nodes).copy()


def render_filtered_graph_html(graph: nx.Graph) -> str:
    """Render a filtered Graphify graph through Graphify's own HTML exporter."""
    communities = _communities_from_graph(graph)
    with tempfile.TemporaryDirectory(prefix="prml-graphify-viewer-") as tmp_dir:
        output_path = Path(tmp_dir) / "graph.html"
        to_html(graph, communities, output_path.as_posix())
        return output_path.read_text(encoding="utf-8")


def load_graphify_summary(artifacts: GraphifyArtifacts) -> GraphifySummary:
    """Load the compact Graphify status summary used by the app page."""
    report_text = artifacts.report.read_text(encoding="utf-8")
    graph_payload: dict[str, Any] = json.loads(artifacts.graph_json.read_text(encoding="utf-8"))
    nodes = graph_payload.get("nodes", [])
    links = graph_payload.get("links", graph_payload.get("edges", []))
    title = report_text.splitlines()[0] if report_text else "# Graph Report"
    date_match = re.search(r"^# Graph Report - .*\(([^)]*)\)", report_text, re.M)
    summary_match = re.search(r"^- (\d+) nodes .+? (\d+) edges .+? (\d+) communities detected", report_text, re.M)
    return GraphifySummary(
        report_title=title,
        graph_date=date_match.group(1) if date_match else "unknown",
        nodes=int(summary_match.group(1)) if summary_match else len(nodes),
        links=int(summary_match.group(2)) if summary_match else len(links),
        communities=int(summary_match.group(3)) if summary_match else 0,
    )


def render(context: AppContext) -> None:
    """Render the generated Graphify graph viewer and report."""
    render_page_intro(
        eyebrow="Code Knowledge Graph",
        title="Graphify",
        body=(
            "Inspect the repository knowledge graph generated by Graphify. This page embeds the official "
            "`graphify-out/graph.html` viewer and surfaces the generated report without introducing a custom renderer."
        ),
    )
    artifacts = resolve_graphify_artifacts(context.path_config.root)
    _render_artifact_status(artifacts)
    if not artifacts.all_present:
        st.warning("Graphify artifacts are incomplete. Rebuild them from the repository root.")
        st.code("make graphify-rebuild", language="bash")
        return

    summary = load_graphify_summary(artifacts)
    _render_summary(summary)
    viewer_tab, report_tab, files_tab = st.tabs(["Viewer", "Report", "Files"])
    with viewer_tab:
        _render_viewer(artifacts)
    with report_tab:
        st.markdown(artifacts.report.read_text(encoding="utf-8"))
    with files_tab:
        _render_files(artifacts)


def _render_artifact_status(artifacts: GraphifyArtifacts) -> None:
    with st.container(border=True):
        st.subheader("Artifact Set")
        st.caption(f"Directory: `{artifacts.root}`")
        rows = [
            {"Artifact": "Report", "Path": artifacts.report.as_posix(), "Available": artifacts.report.exists()},
            {
                "Artifact": "Graph JSON",
                "Path": artifacts.graph_json.as_posix(),
                "Available": artifacts.graph_json.exists(),
            },
            {
                "Artifact": "HTML Viewer",
                "Path": artifacts.graph_html.as_posix(),
                "Available": artifacts.graph_html.exists(),
            },
        ]
        st.dataframe(rows, hide_index=True, width="stretch")


def _render_summary(summary: GraphifySummary) -> None:
    columns = st.columns(4, gap="small")
    columns[0].metric("Nodes", f"{summary.nodes:,}")
    columns[1].metric("Links", f"{summary.links:,}")
    columns[2].metric("Communities", f"{summary.communities:,}")
    columns[3].metric("Graph Date", summary.graph_date)
    st.caption(summary.report_title)


def _render_viewer(artifacts: GraphifyArtifacts) -> None:
    height = st.slider("Viewer height", min_value=500, max_value=1200, value=800, step=100)
    options = _render_filter_controls()
    graph = filter_graphify_graph(load_graphify_graph(artifacts), options)
    node_count = graph.number_of_nodes()
    edge_count = graph.number_of_edges()
    st.caption(f"Showing `{node_count:,}` nodes and `{edge_count:,}` edges after filters.")
    if node_count == 0:
        st.warning("No graph nodes match the selected filters.")
        return
    components.html(render_filtered_graph_html(graph), height=height, scrolling=True)


def _render_filter_controls() -> GraphifyFilterOptions:
    with st.container(border=True):
        st.subheader("Viewer Filters")
        selected_filters = st.multiselect(
            "Filter Override",
            options=list(GraphifyViewerFilter),
            default=[],
            format_func=lambda item: item.label,
            placeholder="Leave empty to show the full generated graph",
        )
        minimum_degree = st.slider("Minimum graph degree", min_value=0, max_value=12, value=0, step=1)
        active_labels = [item.label for item in selected_filters] or ["Full generated graph"]
        if minimum_degree:
            active_labels.append(f"Degree >= {minimum_degree}")
        st.caption("Active view: " + ", ".join(active_labels))
    return GraphifyFilterOptions.from_selected_filters(
        selected_filters,
        minimum_degree=minimum_degree,
    )


def _source_scope_matches(source_file: str, scope: GraphifySourceScope) -> bool:
    match scope:
        case GraphifySourceScope.ALL:
            return True
        case GraphifySourceScope.PRML_VSLAM:
            return source_file.startswith("src/prml_vslam/")
        case GraphifySourceScope.EXCLUDE_TESTS:
            return not source_file.startswith("tests/")
        case GraphifySourceScope.TESTS_ONLY:
            return source_file.startswith("tests/")


def _communities_from_graph(graph: nx.Graph) -> dict[int, list[str]]:
    communities: dict[int, list[str]] = {}
    for node_id, data in graph.nodes(data=True):
        community_id = data.get("community")
        if community_id is None:
            continue
        communities.setdefault(int(community_id), []).append(str(node_id))
    return communities


def _render_files(artifacts: GraphifyArtifacts) -> None:
    st.markdown("**Open from shell**")
    st.code(f"xdg-open {artifacts.graph_html.as_posix()}", language="bash")
    st.download_button(
        "Download graph.json",
        data=artifacts.graph_json.read_bytes(),
        file_name="graph.json",
        mime="application/json",
    )
    st.download_button(
        "Download GRAPH_REPORT.md",
        data=artifacts.report.read_bytes(),
        file_name="GRAPH_REPORT.md",
        mime="text/markdown",
    )


__all__ = [
    "GraphifyArtifacts",
    "GraphifyFilterOptions",
    "GraphifySourceScope",
    "GraphifyViewerFilter",
    "GraphifySummary",
    "filter_graphify_graph",
    "load_graphify_graph",
    "load_graphify_summary",
    "render",
    "render_filtered_graph_html",
    "resolve_graphify_artifacts",
]
