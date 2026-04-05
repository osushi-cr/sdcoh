"""DAG operations: impact analysis, cycle detection, tree display, validation."""

from __future__ import annotations

from collections import defaultdict

from sdcoh.scanner import ScanResult


def _build_forward_adj(result: ScanResult) -> dict[str, list[dict]]:
    """Build forward adjacency: source → list of outgoing edges."""
    adj: dict[str, list[dict]] = defaultdict(list)
    for edge in result.edges:
        adj[edge["source"]].append(edge)
    return adj


def _build_reverse_adj(result: ScanResult) -> dict[str, list[dict]]:
    """Build reverse adjacency: target → list of incoming edges."""
    rev: dict[str, list[dict]] = defaultdict(list)
    for edge in result.edges:
        rev[edge["target"]].append(edge)
    return rev


def find_impact(
    result: ScanResult,
    node_id: str,
    max_depth: int = 0,
) -> list[dict]:
    """Find all nodes impacted by a change to node_id.

    Walks forward edges: if node_id changes, every target reachable from it
    via source→target edges becomes stale.
    Returns list of dicts with 'id' and 'relation' keys.
    """
    node_ids = {n["id"] for n in result.nodes}
    if node_id not in node_ids:
        return []

    adj = _build_forward_adj(result)

    visited: set[str] = {node_id}
    impacted: list[dict] = []

    def walk(nid: str, depth: int) -> None:
        if max_depth > 0 and depth > max_depth:
            return
        for edge in adj.get(nid, []):
            tgt = edge["target"]
            if tgt not in visited:
                visited.add(tgt)
                impacted.append({"id": tgt, "relation": edge["relation"]})
                walk(tgt, depth + 1)

    walk(node_id, 1)
    return impacted


def find_cycles(result: ScanResult) -> list[list[str]]:
    """Detect cycles using DFS over forward edges."""
    adj: dict[str, list[str]] = defaultdict(list)
    for edge in result.edges:
        adj[edge["source"]].append(edge["target"])

    all_ids = {n["id"] for n in result.nodes}
    visited: set[str] = set()
    on_stack: set[str] = set()
    cycles: list[list[str]] = []

    def dfs(nid: str, path: list[str]) -> None:
        visited.add(nid)
        on_stack.add(nid)
        path.append(nid)
        for neighbor in adj.get(nid, []):
            if neighbor in on_stack:
                idx = path.index(neighbor)
                cycles.append(path[idx:] + [neighbor])
            elif neighbor not in visited and neighbor in all_ids:
                dfs(neighbor, path)
        path.pop()
        on_stack.discard(nid)

    for nid in all_ids:
        if nid not in visited:
            dfs(nid, [])

    return cycles


def find_orphans(result: ScanResult) -> list[str]:
    """Find nodes that are not touched by any edge."""
    referenced: set[str] = set()
    for edge in result.edges:
        referenced.add(edge["source"])
        referenced.add(edge["target"])
    return sorted(n["id"] for n in result.nodes if n["id"] not in referenced)


def validate_references(result: ScanResult) -> list[str]:
    """Find edges that reference non-existent node IDs."""
    node_ids = {n["id"] for n in result.nodes}
    broken = []
    for edge in result.edges:
        if edge["target"] not in node_ids:
            broken.append(f'{edge["source"]} → {edge["target"]} (not found)')
        if edge["source"] not in node_ids:
            broken.append(f'{edge["source"]} (not found) → {edge["target"]}')
    return broken


def build_tree_text(result: ScanResult) -> str:
    """Build a text tree from roots (no incoming edges) to leaves."""
    has_incoming: set[str] = set()
    for edge in result.edges:
        has_incoming.add(edge["target"])

    roots = sorted(n["id"] for n in result.nodes if n["id"] not in has_incoming)

    adj = _build_forward_adj(result)
    lines: list[str] = []

    def render(nid: str, prefix: str, is_last: bool, visited: set[str]) -> None:
        connector = "└→ " if is_last else "├→ "
        if prefix:
            lines.append(f"{prefix}{connector}{nid}")
        else:
            lines.append(nid)

        if nid in visited:
            return
        visited.add(nid)

        children = sorted({e["target"] for e in adj.get(nid, [])})
        child_prefix = prefix + ("   " if is_last else "│  ")
        for i, child in enumerate(children):
            render(child, child_prefix, i == len(children) - 1, visited)

    visited: set[str] = set()
    for root in roots:
        render(root, "", True, visited)
        if root != roots[-1]:
            lines.append("")

    return "\n".join(lines)
