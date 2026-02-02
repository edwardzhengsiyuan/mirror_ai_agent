"""Node dependency graph and helpers."""

from __future__ import annotations

from typing import Dict, Iterable, List, Set

COMMON_PREREQS = [
    "PAIPAN",
    "OVERALL",
    "SHISHEN",
    "GEJU_ROUTER",
    "GEJU_ANALYSIS",
    "GEJU_LEVEL",
    "WUXING_PREFS",
]

# Persistent nodes: cached in profile.node_cache, user-level lifetime
PERSISTENT_NODES = [
    "PAIPAN",
    "OVERALL",
    "SHISHEN",
    "GEJU_ROUTER",
    "GEJU_ANALYSIS",
    "GEJU_LEVEL",
    "WUXING_PREFS",
    "CAREER",
    "RELATIONSHIP",
    "HEALTH",
    "GUIREN",
    "LIUQIN",
    "XINGGE",
    "OTHER",
]

# Conversation-level tools: stored in conversation JSONL, per-invocation
CONVERSATION_TOOLS = ["PLANNER", "TIME_CONTEXT"]

# Aspect nodes that depend on COMMON_PREREQS
ASPECT_NODES = [
    "CAREER",
    "RELATIONSHIP",
    "HEALTH",
    "GUIREN",
    "LIUQIN",
    "XINGGE",
    "OTHER",
]

DEPS: Dict[str, List[str]] = {
    "PAIPAN": [],
    "OVERALL": ["PAIPAN"],
    "SHISHEN": ["PAIPAN"],
    "GEJU_ROUTER": ["PAIPAN", "OVERALL"],
    "GEJU_ANALYSIS": ["PAIPAN", "OVERALL", "GEJU_ROUTER"],
    "GEJU_LEVEL": ["PAIPAN", "OVERALL", "GEJU_ROUTER", "GEJU_ANALYSIS"],
    "WUXING_PREFS": ["PAIPAN", "OVERALL", "SHISHEN", "GEJU_LEVEL"],
    "CAREER": COMMON_PREREQS,
    "RELATIONSHIP": COMMON_PREREQS,
    "HEALTH": COMMON_PREREQS,
    "GUIREN": COMMON_PREREQS,
    "LIUQIN": COMMON_PREREQS,
    "XINGGE": COMMON_PREREQS,
    "OTHER": COMMON_PREREQS,
    # Note: FINAL removed from DEPS - it's now a "response", not a node
}


def _visit(node: str, deps: Dict[str, List[str]], visiting: Set[str], visited: Set[str], order: List[str]) -> None:
    if node in visited:
        return
    if node in visiting:
        raise ValueError(f"Dependency cycle detected at {node}")
    visiting.add(node)
    for dep in deps.get(node, []):
        _visit(dep, deps, visiting, visited, order)
    visiting.remove(node)
    visited.add(node)
    order.append(node)


def toposort(nodes: Iterable[str], deps: Dict[str, List[str]] | None = None) -> List[str]:
    graph = deps or DEPS
    order: List[str] = []
    visiting: Set[str] = set()
    visited: Set[str] = set()
    for node in nodes:
        _visit(node, graph, visiting, visited, order)
    return order
