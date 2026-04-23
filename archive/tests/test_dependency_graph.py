# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for the dependency graph — edge registration, transitive closure, query."""
from __future__ import annotations

from genro_builders.dependency_graph import DepEdge, DependencyGraph
from genro_builders.manager import ReactiveManager

from .helpers import TestBuilder


# =============================================================================
# Unit tests: DependencyGraph in isolation
# =============================================================================


class TestDepEdge:
    """DepEdge is a frozen dataclass."""

    def test_create(self):
        edge = DepEdge("a.x", "a.y", "formula", "page")
        assert edge.source_path == "a.x"
        assert edge.target == "a.y"
        assert edge.dep_type == "formula"
        assert edge.builder_name == "page"

    def test_frozen(self):
        edge = DepEdge("a", "b", "render", "p")
        try:
            edge.source_path = "c"
            assert False, "should be frozen"
        except AttributeError:
            pass


class TestGraphBasics:
    """Add edges, clear, clear_builder."""

    def test_add_and_query(self):
        g = DependencyGraph()
        g.add(DepEdge("price", "total", "formula", None))
        g.add(DepEdge("total", "div_total", "render", "page"))
        result = g.impacted_builders(["price"])
        assert result == {"page": "render"}

    def test_clear(self):
        g = DependencyGraph()
        g.add(DepEdge("x", "y", "render", "p"))
        g.clear()
        assert g.impacted_builders(["x"]) == {}

    def test_clear_builder(self):
        g = DependencyGraph()
        g.add(DepEdge("x", "y", "render", "page"))
        g.add(DepEdge("x", "z", "render", "sidebar"))
        g.clear_builder("page")
        result = g.impacted_builders(["x"])
        assert result == {"sidebar": "render"}

    def test_no_edges(self):
        g = DependencyGraph()
        assert g.impacted_builders(["anything"]) == {}


class TestTransitiveClosure:
    """Formula chains are followed transitively."""

    def test_simple_chain(self):
        """clock → elapsed → div: change clock impacts page."""
        g = DependencyGraph()
        g.add(DepEdge("page.clock", "page.elapsed", "formula", None))
        g.add(DepEdge("page.elapsed", "div_el", "render", "page"))
        result = g.impacted_builders(["page.clock"])
        assert result == {"page": "render"}

    def test_deep_chain(self):
        """clock → elapsed → product → div: 3-level chain."""
        g = DependencyGraph()
        g.add(DepEdge("page.clock", "page.elapsed", "formula", None))
        g.add(DepEdge("page.elapsed", "page.product", "formula", None))
        g.add(DepEdge("page.tick_count", "page.product", "formula", None))
        g.add(DepEdge("page.product", "div_prod", "render", "page"))
        result = g.impacted_builders(["page.clock"])
        assert result == {"page": "render"}

    def test_multiple_sources(self):
        """Two paths change, both lead to same builder."""
        g = DependencyGraph()
        g.add(DepEdge("page.clock", "page.elapsed", "formula", None))
        g.add(DepEdge("page.elapsed", "div_el", "render", "page"))
        g.add(DepEdge("page.tick_count", "page.product", "formula", None))
        g.add(DepEdge("page.product", "div_prod", "render", "page"))
        result = g.impacted_builders(["page.clock", "page.tick_count"])
        assert result == {"page": "render"}

    def test_cycle_safe(self):
        """Cycles in formulas don't cause infinite loop."""
        g = DependencyGraph()
        g.add(DepEdge("a", "b", "formula", None))
        g.add(DepEdge("b", "a", "formula", None))
        g.add(DepEdge("b", "node_x", "render", "page"))
        result = g.impacted_builders(["a"])
        assert result == {"page": "render"}


class TestBuildVsRender:
    """Build dep_type beats render."""

    def test_build_wins(self):
        """If both render and build edges exist, build wins."""
        g = DependencyGraph()
        g.add(DepEdge("products", "card_list", "build", "page"))
        g.add(DepEdge("products", "counter", "render", "page"))
        result = g.impacted_builders(["products"])
        assert result == {"page": "build"}

    def test_render_only(self):
        g = DependencyGraph()
        g.add(DepEdge("title", "h1_node", "render", "page"))
        result = g.impacted_builders(["title"])
        assert result == {"page": "render"}

    def test_build_via_chain(self):
        """Build reached transitively through formula chain."""
        g = DependencyGraph()
        g.add(DepEdge("raw", "computed", "formula", None))
        g.add(DepEdge("computed", "iterate_node", "build", "page"))
        result = g.impacted_builders(["raw"])
        assert result == {"page": "build"}


class TestCrossBuilder:
    """Dependencies across builders."""

    def test_cross_builder_formula(self):
        """Formula in builder B depends on data in builder A."""
        g = DependencyGraph()
        g.add(DepEdge("a.clock", "b.elapsed", "formula", None))
        g.add(DepEdge("b.elapsed", "div_el", "render", "b"))
        result = g.impacted_builders(["a.clock"])
        assert result == {"b": "render"}

    def test_multiple_builders_impacted(self):
        """One data change impacts two builders."""
        g = DependencyGraph()
        g.add(DepEdge("shared.price", "div_price_a", "render", "page"))
        g.add(DepEdge("shared.price", "div_price_b", "render", "sidebar"))
        result = g.impacted_builders(["shared.price"])
        assert "page" in result
        assert "sidebar" in result


# =============================================================================
# Integration tests: graph populated by build()
# =============================================================================


class TestGraphIntegrationFormula:
    """Build populates formula edges in the graph."""

    def test_formula_deps_registered(self):
        """data_formula with ^pointer deps registers formula edges."""

        class App(ReactiveManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)
                self.run()

            def main(self, source):
                source.data_formula(
                    "total",
                    func=lambda price, tax: price * (1 + tax),
                    price="^price",
                    tax="^tax_rate",
                )
                self.local_store()["price"] = 100
                self.local_store()["tax_rate"] = 0.2
                source.heading(value="^total")

        app = App()
        edges = app.dep_graph.edges

        # Formula edges: price → total, tax_rate → total
        formula_sources = set()
        for path, edge_list in edges.items():
            for e in edge_list:
                if e.dep_type == "formula":
                    formula_sources.add(e.source_path)
        assert "page.price" in formula_sources
        assert "page.tax_rate" in formula_sources

    def test_render_deps_registered(self):
        """Built nodes with ^pointer value register render edges."""

        class App(ReactiveManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)
                self.run()

            def main(self, source):
                self.local_store()["title"] = "Hello"
                source.heading(value="^title")

        app = App()
        edges = app.dep_graph.edges

        # Render edge: title → heading node
        render_edges = []
        for path, edge_list in edges.items():
            for e in edge_list:
                if e.dep_type == "render":
                    render_edges.append(e)
        assert len(render_edges) >= 1
        assert any(e.source_path == "page.title" for e in render_edges)
        assert any(e.builder_name == "page" for e in render_edges)

    def test_impacted_builders_formula_chain(self):
        """Formula chain: price → total → heading. Changing price impacts page."""

        class App(ReactiveManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)
                self.run()

            def main(self, source):
                self.local_store()["price"] = 100
                self.local_store()["tax_rate"] = 0.2
                source.data_formula(
                    "total",
                    func=lambda price, tax: price * (1 + tax),
                    price="^price",
                    tax="^tax_rate",
                )
                source.heading(value="^total")

        app = App()
        result = app.dep_graph.impacted_builders(["page.price"])
        assert result == {"page": "render"}

    def test_graph_cleared_on_rebuild(self):
        """build() clears the graph before repopulating."""

        class App(ReactiveManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)
                self.run()

            def main(self, source):
                self.local_store()["x"] = 1
                source.heading(value="^x")

        app = App()
        assert app.dep_graph.impacted_builders(["page.x"]) == {"page": "render"}

        # Rebuild should clear and repopulate
        app.build()
        assert app.dep_graph.impacted_builders(["page.x"]) == {"page": "render"}


class TestGraphIntegrationCrossBuilder:
    """Cross-builder dependencies via volume syntax."""

    def test_cross_builder_render(self):
        """Builder B reads from builder A's namespace via volume syntax."""

        class App(ReactiveManager):
            def on_init(self):
                self.a = self.register_builder("a", TestBuilder)
                self.b = self.register_builder("b", TestBuilder)
                self.run()

            def main_a(self, source):
                self.local_store()["price"] = 100

            def main_b(self, source):
                source.heading(value="^a:price")

        app = App()
        result = app.dep_graph.impacted_builders(["a.price"])
        assert "b" in result
