# tests/test_scanner.py
from pathlib import Path

from sdcoh.config import load_config
from sdcoh.scanner import scan_project, ScanResult


def test_scan_finds_all_nodes(sample_project: Path) -> None:
    cfg = load_config(sample_project)
    result = scan_project(cfg)
    ids = {n["id"] for n in result.nodes}
    assert ids == {
        "design:characters",
        "design:beat-sheet",
        "design:style",
        "episode:ep01",
        "brief:ep01",
    }


def test_scan_builds_edges(sample_project: Path) -> None:
    cfg = load_config(sample_project)
    result = scan_project(cfg)
    edges = {(e["source"], e["target"], e["relation"]) for e in result.edges}
    assert ("design:beat-sheet", "design:characters", "derives_from") in edges
    assert ("episode:ep01", "design:beat-sheet", "implements") in edges
    assert ("episode:ep01", "design:style", "constrained_by") in edges
    assert ("brief:ep01", "design:beat-sheet", "derives_from") in edges
    assert ("brief:ep01", "design:characters", "references") in edges


def test_scan_builds_update_edges(sample_project: Path) -> None:
    cfg = load_config(sample_project)
    result = scan_project(cfg)
    update_edges = [
        e for e in result.edges if e["direction"] == "updates"
    ]
    assert len(update_edges) == 1
    assert update_edges[0]["source"] == "episode:ep01"
    assert update_edges[0]["target"] == "design:characters"
    assert update_edges[0]["relation"] == "triggers_update"


def test_scan_reports_files_without_frontmatter(sample_project: Path) -> None:
    cfg = load_config(sample_project)
    result = scan_project(cfg)
    assert "design/no-frontmatter.md" in result.warnings


def test_scan_stores_mtime(sample_project: Path) -> None:
    cfg = load_config(sample_project)
    result = scan_project(cfg)
    node = next(n for n in result.nodes if n["id"] == "design:characters")
    assert "mtime" in node
    assert "path" in node


def test_scan_saves_graph_json(sample_project: Path) -> None:
    cfg = load_config(sample_project)
    result = scan_project(cfg)
    result.save(cfg.root)
    graph_path = cfg.root / ".sdcoh" / "graph.json"
    assert graph_path.exists()
