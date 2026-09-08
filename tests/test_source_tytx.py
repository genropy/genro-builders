# Copyright 2026 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Contract: SourceBag decodes detached, preserving ordinary data branches."""
import pytest
from genro_bag import Bag
from genro_tytx import to_tytx, from_tytx
from genro_builders.builder import SourceBag, SourceBagNode


class TestSourceTytx:
    @pytest.mark.parametrize("transport", ["json", "msgpack"])
    def test_source_in_envelope(self, transport):
        source = SourceBag()
        source.set_item("branch", SourceBag(), node_tag="div")
        source.set_item("branch.data", Bag({"value": 42}), node_tag="data")
        result = from_tytx(to_tytx({"source": source}, transport), transport)["source"]
        assert type(result) is SourceBag
        assert result._builder is None
        assert type(result["branch"]) is SourceBag
        assert isinstance(result.get_node("branch"), SourceBagNode)
        assert type(result["branch.data"]) is Bag
        assert result["branch.data.value"] == 42
