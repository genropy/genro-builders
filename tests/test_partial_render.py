# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Partial render — the total render is the oracle.

A live section collects patches (id = source-relative path, op =
replace, html = the re-rendered node). Applying the patches to the
previous full document must yield byte-for-byte (canonicalized) the
same document a fresh full render produces. Any future optimization
of the partial pipeline stays pinned to this equivalence.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from genro_builders.builder import BuilderHandler, TargetWrapper
from genro_builders.contrib.html import HtmlBuilder


class _Probe(TargetWrapper):
    """Collects full documents and patch batches."""

    accepts_partial = True
    render_opts = {"include_datapath": True}

    def __init__(self):
        self.full_docs: list[str] = []
        self.batches: list[list[dict]] = []

    def full(self, document):
        self.full_docs.append(document)

    def partial(self, patches):
        self.batches.append(patches)


def _apply_patches(document: str, patches: list[dict]) -> str:
    """Reference patch applier: replace/insert/remove by id on a tree."""
    root = ET.fromstring(f"<R>{document}</R>")
    for patch in patches:
        if patch["op"] == "insert":
            container = (
                root if patch["id"] is None
                else next(el for el in root.iter() if el.get("id") == patch["id"])
            )
            fragment = ET.fromstring(patch["html"])
            if patch["before"] is None:
                container.append(fragment)
            else:
                ref = next(
                    el for el in container if el.get("id") == patch["before"]
                )
                container.insert(list(container).index(ref), fragment)
            continue
        target = next(el for el in root.iter() if el.get("id") == patch["id"])
        parent = next(p for p in root.iter() if target in list(p))
        index = list(parent).index(target)
        parent.remove(target)
        if patch["op"] == "replace":
            parent.insert(index, ET.fromstring(patch["html"]))
    return "".join(ET.tostring(child, encoding="unicode") for child in root)


def _canon(document: str) -> str:
    root = ET.fromstring(f"<R>{document}</R>")
    return "".join(ET.tostring(child, encoding="unicode") for child in root)


class _Page(HtmlBuilder):
    def setup(self, data):
        data.set_item("name", "John")
        data.set_item("css", "color: red")

    def main(self, root):
        body = root.body()
        body.h1("static title")
        body.div("^name", style="^css")


def _mounted():
    probe = _Probe()
    page = _Page(name="p")
    page.set_render_target(probe)
    handler = BuilderHandler(application=object())
    handler.add_builder(page)
    handler.activate()
    return handler, page, probe


def test_patches_equal_full_render():
    handler, page, probe = _mounted()
    before = probe.full_docs[-1]

    with handler.live():
        handler.data.set_item("p.name", "Martin")
        handler.data.set_item("p.css", "color: blue")

    patched = _apply_patches(before, probe.batches[-1])
    fresh = page.render(target=False, include_datapath=True)
    assert _canon(patched) == _canon(fresh)
    assert "Martin" in patched and "color: blue" in patched


def test_full_only_wrapper_gets_the_whole_document():
    class FullOnly(TargetWrapper):
        def __init__(self):
            self.full_docs: list[str] = []

        def full(self, document):
            self.full_docs.append(document)

    wrapper = FullOnly()
    page = _Page(name="p")
    page.set_render_target(wrapper)
    handler = BuilderHandler(application=object())
    handler.add_builder(page)
    handler.activate()
    n = len(wrapper.full_docs)
    with handler.live():
        handler.data.set_item("p.name", "Martin")
    assert len(wrapper.full_docs) == n + 1          # flush = one full render
    assert "Martin" in wrapper.full_docs[-1]


class _NestedPage(HtmlBuilder):
    def setup(self, data):
        data.set_item("name", "John")
        data.set_item("css", "color: red")

    def main(self, root):
        card = root.body().div(style="^css")
        card.span("^name")


def _mounted_nested():
    probe = _Probe()
    page = _NestedPage(name="p")
    page.set_render_target(probe)
    handler = BuilderHandler(application=object())
    handler.add_builder(page)
    handler.activate()
    return handler, page, probe


def test_exact_dedup_one_patch_per_node():
    """O1: N mutations read by the same node = ONE patch."""
    handler, page, probe = _mounted()
    with handler.live():
        handler.data.set_item("p.name", "Martin")
        handler.data.set_item("p.css", "color: blue")   # same reader node
    assert len(probe.batches[-1]) == 1


def test_ancestor_covers_descendant():
    """O2: ancestor and descendant both queued -> the ancestor's patch
    contains the descendant; one patch, equivalence intact."""
    handler, page, probe = _mounted_nested()
    before = probe.full_docs[-1]
    with handler.live():
        handler.data.set_item("p.css", "color: blue")   # the card (ancestor)
        handler.data.set_item("p.name", "Martin")       # the span (inside)
    batch = probe.batches[-1]
    assert len(batch) == 1
    card = page.source.get_node("body.div_0")           # the ancestor
    assert batch[0]["id"] == page.target_id(card)
    patched = _apply_patches(before, batch)
    fresh = page.render(target=False, include_datapath=True)
    assert _canon(patched) == _canon(fresh)


class _ListPage(HtmlBuilder):
    def setup(self, data):
        data.set_item("title", "Todo")

    def main(self, root):
        body = root.body()
        body.h1("^title")
        ul = body.ul(node_id="list")
        ul.li("alpha")
        ul.li("beta")


def _mounted_list():
    probe = _Probe()
    page = _ListPage(name="p")
    page.set_render_target(probe)
    handler = BuilderHandler(application=object())
    handler.add_builder(page)
    handler.activate()
    return handler, page, probe


def test_source_append_emits_insert():
    """A node attached to the source travels as an insert patch: the
    container id, no anchor (append), the new fragment only — the
    sibling elements are never touched."""
    handler, page, probe = _mounted_list()
    before = probe.full_docs[-1]
    with handler.live():
        page.node_by_id("list").li("gamma")
    batch = probe.batches[-1]
    assert len(batch) == 1
    assert batch[0]["op"] == "insert"
    assert batch[0]["id"] == page.target_id(page.node_by_id("list"))
    assert batch[0]["before"] is None
    patched = _apply_patches(before, batch)
    fresh = page.render(target=False, include_datapath=True)
    assert _canon(patched) == _canon(fresh)
    assert "gamma" in patched


def test_positioned_insert_carries_the_anchor():
    """node_position decides where the node lands; the patch expresses
    it as the id of the following sibling (``before``)."""
    handler, page, probe = _mounted_list()
    before_doc = probe.full_docs[-1]
    with handler.live():
        page.node_by_id("list").li("first", node_position="<")
    batch = probe.batches[-1]
    assert len(batch) == 1
    assert batch[0]["op"] == "insert"
    first_li = page.source.get_node("body.ul_0.li_0")
    assert batch[0]["before"] == page.target_id(first_li)
    patched = _apply_patches(before_doc, batch)
    fresh = page.render(target=False, include_datapath=True)
    assert _canon(patched) == _canon(fresh)


def test_source_delete_emits_remove():
    handler, page, probe = _mounted_list()
    before = probe.full_docs[-1]
    li1_id = page.target_id(page.source.get_node("body.ul_0.li_1"))
    with handler.live():
        page.node_by_id("list").value.pop("li_1")
    batch = probe.batches[-1]
    assert batch == [{"id": li1_id, "op": "remove"}]
    patched = _apply_patches(before, batch)
    fresh = page.render(target=False, include_datapath=True)
    assert _canon(patched) == _canon(fresh)
    assert "beta" not in patched


def test_ephemeral_node_nets_to_nothing():
    """Born and died inside the same section: the DOM never saw the
    node, no patch travels."""
    handler, page, probe = _mounted_list()
    n_batches = len(probe.batches)
    with handler.live():
        page.node_by_id("list").li("ghost")
        page.node_by_id("list").value.pop("li_2")
    assert probe.batches[n_batches:] in ([], [[]])


def test_delete_and_reinsert_travels_as_remove_plus_insert():
    """The same label deleted and re-created in one section: the old
    element leaves, the fresh one enters at its FINAL position (the
    auto-label reuses the freed slot, the node lands at the end)."""
    handler, page, probe = _mounted_list()
    before = probe.full_docs[-1]
    with handler.live():
        page.node_by_id("list").value.pop("li_0")
        page.node_by_id("list").li("omega")
    batch = probe.batches[-1]
    assert [p["op"] for p in batch] == ["remove", "insert"]
    patched = _apply_patches(before, batch)
    fresh = page.render(target=False, include_datapath=True)
    assert _canon(patched) == _canon(fresh)
    assert "omega" in patched and "alpha" not in patched


def test_insert_then_data_mutation_one_fresh_insert():
    """A data mutation read by the freshly inserted node is absorbed:
    the insert renders the FINAL state, equivalence holds."""
    handler, page, probe = _mounted_list()
    before = probe.full_docs[-1]
    with handler.live():
        page.node_by_id("list").li("^title")
        handler.data.set_item("p.title", "Groceries")
    patched = _apply_patches(before, probe.batches[-1])
    fresh = page.render(target=False, include_datapath=True)
    assert _canon(patched) == _canon(fresh)
    assert "Groceries" in patched


def test_iterate_component_patch_is_applicable():
    """A mutation inside an iterated collection must produce a patch the
    reference applier can apply: the replacement unit of an iterate
    component is its enclosing element (the caller's container), which
    is a real DOM node with an id."""
    from genro_builders.builder import component

    class Components:
        @component
        def row(self, root, node_label=None):
            tr = root.tr(datapath="." + node_label)
            tr.td("^.sku")
            tr.td("^.qty")

    class Page(HtmlBuilder, Components):
        def setup(self, data):
            data.set_item("rows.r1.sku", "A")
            data.set_item("rows.r1.qty", 2)
            data.set_item("rows.r2.sku", "B")
            data.set_item("rows.r2.qty", 5)

        def main(self, root):
            root.body().table().tbody().row(iterate="^rows")

    probe = _Probe()
    page = Page(name="p")
    page.set_render_target(probe)
    handler = BuilderHandler(application=object())
    handler.add_builder(page)
    handler.activate()
    before = probe.full_docs[-1]

    with handler.live():
        handler.data.set_item("p.rows.r1.qty", 99)

    patched = _apply_patches(before, probe.batches[-1])
    fresh = page.render(target=False, include_datapath=True)
    assert _canon(patched) == _canon(fresh)
    assert "99" in patched
