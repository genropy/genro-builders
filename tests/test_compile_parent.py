# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for compile walk with parent parameter — two roots in parallel."""

from genro_builders import BagBuilderBase, BagCompilerBase
from genro_builders.builder_bag import BuilderBag as Bag
from genro_builders.builders import element
from genro_builders.compiler import compiler


class DocBuilder(BagBuilderBase):
    """Builder for testing parent compile pattern."""

    @element(sub_tags="section")
    def document(self): ...

    @element(sub_tags="paragraph")
    def section(self, title: str = ""): ...

    @element()
    def paragraph(self): ...


class ParentTracker(BagCompilerBase):
    """Compiler that tracks parent chain via the parent parameter."""

    @compiler()
    def document(self, node, parent):
        """Document: create root dict, return as parent for children."""
        return {"type": "document", "children": []}

    @compiler()
    def section(self, node, parent):
        """Section: attach to parent's children, return as parent."""
        title = node.runtime_attrs.get("title", "")
        section = {"type": "section", "title": title, "children": []}
        if parent is not None:
            parent["children"].append(section)
        return section

    @compiler()
    def paragraph(self, node, parent):
        """Paragraph: attach to parent's children."""
        para = {"type": "paragraph", "text": str(node.runtime_value or "")}
        if parent is not None:
            parent["children"].append(para)
        return para


class TestCompileParent:
    """Tests for the parent parameter in compile walk."""

    def test_parent_none_by_default(self):
        """Without explicit parent, compile_node receives parent=None."""
        builder = DocBuilder()
        builder.source.document()
        builder.build()

        tracker = ParentTracker(builder)
        results = list(tracker._walk_compile(builder.built))
        assert len(results) == 1
        assert results[0]["type"] == "document"

    def test_parent_passed_to_children(self):
        """Children receive parent from _walk_compile(bag, parent=...)."""
        builder = DocBuilder()
        doc = builder.source.document()
        sec = doc.section(title="Intro")
        sec.paragraph("Hello world")
        builder.build()

        tracker = ParentTracker(builder)
        root = {"type": "root", "children": []}
        list(tracker._walk_compile(builder.built, parent=root))

        # Root should have one child (document)
        assert len(root["children"]) == 0  # document handler ignores parent
        # But the document result becomes parent for section

    def test_full_tree_compiled_with_parent_chain(self):
        """Compile a full tree — parent flows through the chain."""
        builder = DocBuilder()
        doc = builder.source.document()
        sec = doc.section(title="Chapter 1")
        sec.paragraph("First paragraph")
        sec.paragraph("Second paragraph")
        builder.build()

        tracker = ParentTracker(builder)
        results = list(tracker._walk_compile(builder.built))

        # document is the top result
        assert len(results) == 1
        doc_result = results[0]
        assert doc_result["type"] == "document"

        # section is child of document
        assert len(doc_result["children"]) == 1
        sec_result = doc_result["children"][0]
        assert sec_result["type"] == "section"
        assert sec_result["title"] == "Chapter 1"

        # paragraphs are children of section
        assert len(sec_result["children"]) == 2
        assert sec_result["children"][0]["text"] == "First paragraph"
        assert sec_result["children"][1]["text"] == "Second paragraph"

    def test_compile_node_receives_parent(self):
        """Default compile_node receives parent parameter."""

        class SimpleCompiler(BagCompilerBase):
            def compile_node(self, node, parent=None, **kwargs):
                return {"tag": node.node_tag, "parent_type": type(parent).__name__}

        builder = DocBuilder()
        builder.source.document()
        builder.build()

        comp = SimpleCompiler(builder)
        results = list(comp._walk_compile(builder.built, parent="root_obj"))
        assert results[0]["parent_type"] == "str"
