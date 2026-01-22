"""Unit tests for agent/deps.py - DAG topological sort."""

from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from agent.deps import toposort, DEPS, PERSISTENT_NODES, COMMON_PREREQS, ASPECT_NODES


class TestToposort:
    """Tests for toposort function."""

    def test_linear_chain(self):
        """Linear dependency chain A→B→C should return [A, B, C]."""
        deps = {"A": [], "B": ["A"], "C": ["B"]}
        result = toposort(["A", "B", "C"], deps)
        assert result == ["A", "B", "C"]

    def test_diamond_dependency(self):
        """Diamond: A→B, A→C, B→D, C→D should return valid topological order."""
        deps = {"A": [], "B": ["A"], "C": ["A"], "D": ["B", "C"]}
        result = toposort(["A", "B", "C", "D"], deps)
        # A must come first, D must come last
        assert result[0] == "A"
        assert result[-1] == "D"
        # B and C can be in any order but must come before D
        assert result.index("B") < result.index("D")
        assert result.index("C") < result.index("D")

    def test_single_node(self):
        """Single node with no deps returns [node]."""
        deps = {"A": []}
        result = toposort(["A"], deps)
        assert result == ["A"]

    def test_empty_list(self):
        """Empty node list returns empty list."""
        deps = {"A": []}
        result = toposort([], deps)
        assert result == []

    def test_multiple_independent_nodes(self):
        """Independent nodes can be in any order."""
        deps = {"A": [], "B": [], "C": []}
        result = toposort(["A", "B", "C"], deps)
        assert set(result) == {"A", "B", "C"}
        assert len(result) == 3

    def test_partial_nodes_from_deps(self):
        """Only requested nodes are included in output."""
        deps = {"A": [], "B": ["A"], "C": ["B"], "D": ["C"]}
        result = toposort(["B", "C"], deps)
        # Should include A as dependency, but not D
        assert "A" in result
        assert "B" in result
        assert "C" in result
        assert "D" not in result

    def test_missing_node_in_deps(self):
        """Node not in deps dict uses empty dependency list."""
        deps = {"A": []}
        result = toposort(["A", "B"], deps)
        assert "A" in result
        assert "B" in result

    def test_circular_dependency_raises(self):
        """Circular dependency A→B→A should raise ValueError."""
        deps = {"A": ["B"], "B": ["A"]}
        with pytest.raises(ValueError, match="[Cc]ycle"):
            toposort(["A", "B"], deps)

    def test_self_loop_raises(self):
        """Self-loop A→A should raise ValueError."""
        deps = {"A": ["A"]}
        with pytest.raises(ValueError, match="[Cc]ycle"):
            toposort(["A"], deps)

    def test_three_node_cycle_raises(self):
        """Three-node cycle A→B→C→A should raise ValueError."""
        deps = {"A": ["C"], "B": ["A"], "C": ["B"]}
        with pytest.raises(ValueError, match="[Cc]ycle"):
            toposort(["A", "B", "C"], deps)


class TestDepsConstants:
    """Tests for DEPS constant and related constants."""

    def test_deps_has_no_cycles(self):
        """The real DEPS constant should have no cycles."""
        # Should not raise
        result = toposort(PERSISTENT_NODES, DEPS)
        assert len(result) >= len(PERSISTENT_NODES)

    def test_paipan_has_no_deps(self):
        """PAIPAN should have no dependencies."""
        assert DEPS.get("PAIPAN", []) == []

    def test_overall_depends_on_paipan(self):
        """OVERALL should depend on PAIPAN."""
        assert "PAIPAN" in DEPS.get("OVERALL", [])

    def test_aspect_nodes_depend_on_common_prereqs(self):
        """All aspect nodes should depend on COMMON_PREREQS."""
        for node in ASPECT_NODES:
            deps = DEPS.get(node, [])
            for prereq in COMMON_PREREQS:
                assert prereq in deps, f"{node} missing dependency on {prereq}"

    def test_common_prereqs_order(self):
        """COMMON_PREREQS should be in valid topological order."""
        result = toposort(COMMON_PREREQS, DEPS)
        # PAIPAN must come first
        assert result[0] == "PAIPAN"

    def test_all_persistent_nodes_in_deps(self):
        """All PERSISTENT_NODES should be keys in DEPS."""
        for node in PERSISTENT_NODES:
            assert node in DEPS, f"{node} missing from DEPS"
