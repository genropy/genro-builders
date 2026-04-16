# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Dependency graph for reactive dispatch.

Tracks how data paths in the global store relate to each other
(formula chains) and to builder output (render / build dependencies).

Built incrementally during the build phase. The manager queries it
when data changes to determine which builders need updating and how.

Edge types:
    formula — data path depends on another data path via FormulaResolver.
              Used for transitive closure (propagation of staleness).
    render  — a built node has a ^pointer to a data path.
              The builder needs re-rendering (output is stale).
    build   — a built node's structure depends on a data path (e.g. iterate).
              The builder needs rebuilding (built tree is stale).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class DepEdge:
    """A single dependency edge in the graph.

    Attributes:
        source_path: Data path that, when changed, triggers this edge.
        target: Target path (formula output path, or built node path).
        dep_type: One of 'formula', 'render', 'build'.
        builder_name: Name of the builder affected (None for formula edges
            that are pure data-to-data propagation).
    """

    source_path: str
    target: str
    dep_type: str
    builder_name: str | None


class DependencyGraph:
    """Cross-builder dependency graph for reactive dispatch.

    Inverse index: given a changed data path, find all targets
    that depend on it (directly or transitively via formula chains).
    """

    def __init__(self) -> None:
        self._edges: dict[str, list[DepEdge]] = defaultdict(list)

    @property
    def edges(self) -> dict[str, list[DepEdge]]:
        """Read-only access to the edge index."""
        return dict(self._edges)

    def add(self, edge: DepEdge) -> None:
        """Register a dependency edge."""
        self._edges[edge.source_path].append(edge)

    def clear(self) -> None:
        """Remove all edges (called before rebuild)."""
        self._edges.clear()

    def clear_builder(self, builder_name: str) -> None:
        """Remove all edges for a specific builder."""
        for path in list(self._edges):
            self._edges[path] = [
                e for e in self._edges[path]
                if e.builder_name != builder_name
            ]
            if not self._edges[path]:
                del self._edges[path]

    def impacted_builders(self, changed_paths: list[str]) -> dict[str, str]:
        """Given changed data paths, return {builder_name: max_dep_type}.

        Walks the graph following formula edges transitively.
        Collects terminal edges (render/build) and groups by builder.
        The max dep_type per builder is returned (build > render).

        Args:
            changed_paths: List of absolute data paths that changed.

        Returns:
            Dict mapping builder name to the highest dependency type
            ('build' beats 'render').
        """
        visited: set[str] = set()
        result: dict[str, str] = {}
        queue = list(changed_paths)

        while queue:
            path = queue.pop(0)
            if path in visited:
                continue
            visited.add(path)

            for edge in self._edges.get(path, []):
                if edge.dep_type == "formula":
                    queue.append(edge.target)
                elif edge.builder_name is not None:
                    current = result.get(edge.builder_name)
                    if current != "build":
                        result[edge.builder_name] = edge.dep_type

        return result
