# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for iterate on components."""
from __future__ import annotations

from genro_bag import Bag

from genro_builders.builder import BagBuilderBase, component, element
from genro_builders.manager import BuilderManager

from .helpers import TestRenderer


class IterableBuilder(BagBuilderBase):
    """Builder with a component that uses iterate."""

    _renderers = {"test": TestRenderer}

    @element()
    def heading(self): ...

    @element()
    def span(self): ...

    @component(sub_tags='')
    def person_card(self, comp, **kwargs):
        comp.span(value='^.?nome')
        comp.span(value='^.?cognome')


class TestIterateBasic:
    """Basic iterate expansion tests."""

    def test_iterate_creates_n_children(self):
        """iterate='^persone' creates one sub-component per data child."""

        class App(BuilderManager):
            def on_init(self):
                self.page = self.register_builder("page", IterableBuilder)

            def main(self, source):
                persone = Bag()
                persone.set_item("r0", None, nome="Mario", cognome="Rossi")
                persone.set_item("r1", None, nome="Anna", cognome="Verdi")
                persone.set_item("r2", None, nome="Luca", cognome="Bianchi")
                self.local_store()["persone"] = persone
                source.person_card(iterate='^persone')

        app = App()
        app.setup()
        app.build()

        # The built should contain person_card_0 as a container
        # with 3 children (r0, r1, r2), each expanded from person_card
        built = app.page.built
        container = built.get_item("person_card_0")
        assert isinstance(container, Bag)
        assert len(container) == 3

    def test_iterate_resolves_relative_pointers(self):
        """^.?nome resolves to each child's attribute."""

        class App(BuilderManager):
            def on_init(self):
                self.page = self.register_builder("page", IterableBuilder)

            def main(self, source):
                persone = Bag()
                persone.set_item("r0", None, nome="Mario", cognome="Rossi")
                persone.set_item("r1", None, nome="Anna", cognome="Verdi")
                self.local_store()["persone"] = persone
                source.person_card(iterate='^persone')

        app = App()
        app.setup()
        app.build()

        output = app.page.render()
        assert "Mario" in output
        assert "Rossi" in output
        assert "Anna" in output
        assert "Verdi" in output

    def test_iterate_empty_bag(self):
        """iterate on empty bag produces empty container."""

        class App(BuilderManager):
            def on_init(self):
                self.page = self.register_builder("page", IterableBuilder)

            def main(self, source):
                self.local_store()["persone"] = Bag()
                source.person_card(iterate='^persone')

        app = App()
        app.setup()
        app.build()

        built = app.page.built
        container = built.get_item("person_card_0")
        assert isinstance(container, Bag)
        assert len(container) == 0

    def test_iterate_missing_data(self):
        """iterate on non-existent data path produces empty container."""

        class App(BuilderManager):
            def on_init(self):
                self.page = self.register_builder("page", IterableBuilder)

            def main(self, source):
                source.person_card(iterate='^nonexistent')

        app = App()
        app.setup()
        app.build()

        built = app.page.built
        container = built.get_item("person_card_0")
        assert isinstance(container, Bag)
        assert len(container) == 0

    def test_without_iterate_unchanged(self):
        """Component without iterate works as before."""

        class App(BuilderManager):
            def on_init(self):
                self.page = self.register_builder("page", IterableBuilder)

            def main(self, source):
                source.person_card()

        app = App()
        app.setup()
        app.build()

        built = app.page.built
        container = built.get_item("person_card_0")
        assert isinstance(container, Bag)
        # Normal component: expanded content, not iterate children
        # Should have span_0, span_1 (the component body)
        tags = [n.node_tag for n in container]
        assert "span" in tags
