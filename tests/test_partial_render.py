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
    """Reference patch applier: replace-by-id on an element tree."""
    root = ET.fromstring(f"<R>{document}</R>")
    for patch in patches:
        target = next(el for el in root.iter() if el.get("id") == patch["id"])
        parent = next(p for p in root.iter() if target in list(p))
        index = list(parent).index(target)
        parent.remove(target)
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
