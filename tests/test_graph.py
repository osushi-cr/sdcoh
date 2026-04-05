# tests/test_graph.py
from pathlib import Path

from sdcoh.config import load_config
from sdcoh.scanner import scan_project, ScanResult
from sdcoh.graph import (
    find_impact,
    find_cycles,
    find_orphans,
    build_tree_text,
    validate_references,
)


def test_find_impact_direct(sample_project: Path) -> None:
    """design:characters → episode:ep01 (via 'informs' rule)."""
    cfg = load_config(sample_project)
    result = scan_project(cfg)
    impacted = find_impact(result, "design:characters")
    ids = {i["id"] for i in impacted}
    assert "episode:ep01" in ids


def test_find_impact_from_brief(sample_project: Path) -> None:
    """brief:ep01-brief → episode:ep01 (via 'feeds' rule)."""
    cfg = load_config(sample_project)
    result = scan_project(cfg)
    impacted = find_impact(result, "brief:ep01-brief")
    ids = {i["id"] for i in impacted}
    assert "episode:ep01" in ids


def test_find_impact_depth_limit(sample_project: Path) -> None:
    cfg = load_config(sample_project)
    result = scan_project(cfg)
    # depth=1 still includes direct targets
    impacted = find_impact(result, "design:characters", max_depth=1)
    ids = {i["id"] for i in impacted}
    assert "episode:ep01" in ids


def test_find_impact_unknown_node(sample_project: Path) -> None:
    cfg = load_config(sample_project)
    result = scan_project(cfg)
    impacted = find_impact(result, "design:nonexistent")
    assert impacted == []


def test_find_cycles_none(sample_project: Path) -> None:
    cfg = load_config(sample_project)
    result = scan_project(cfg)
    cycles = find_cycles(result)
    assert cycles == []


def test_find_orphans(sample_project: Path) -> None:
    """All nodes in sample_project are connected via rules."""
    cfg = load_config(sample_project)
    result = scan_project(cfg)
    orphans = find_orphans(result)
    assert orphans == []


def test_validate_references(sample_project: Path) -> None:
    cfg = load_config(sample_project)
    result = scan_project(cfg)
    broken = validate_references(result)
    assert broken == []


def test_build_tree_text(sample_project: Path) -> None:
    cfg = load_config(sample_project)
    result = scan_project(cfg)
    text = build_tree_text(result)
    assert "design:characters" in text
    assert "episode:ep01" in text


def test_find_cycles_detected() -> None:
    result = ScanResult()
    result.nodes = [
        {"id": "a", "type": "design", "path": "a.md", "mtime": "2026-01-01T00:00:00+00:00"},
        {"id": "b", "type": "design", "path": "b.md", "mtime": "2026-01-01T00:00:00+00:00"},
    ]
    result.edges = [
        {"source": "a", "target": "b", "relation": "r"},
        {"source": "b", "target": "a", "relation": "r"},
    ]
    cycles = find_cycles(result)
    assert len(cycles) > 0


def test_validate_references_broken() -> None:
    result = ScanResult()
    result.nodes = [
        {"id": "a", "type": "design", "path": "a.md", "mtime": "2026-01-01T00:00:00+00:00"},
    ]
    result.edges = [
        {"source": "a", "target": "nonexistent", "relation": "r"},
    ]
    broken = validate_references(result)
    assert len(broken) == 1
    assert "nonexistent" in broken[0]
