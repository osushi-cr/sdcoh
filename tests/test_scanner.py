# tests/test_scanner.py
import pytest
from pathlib import Path

from sdcoh.config import load_config
from sdcoh.scanner import scan_project, ScannerError, _compile_pattern


def test_scan_finds_all_nodes(sample_project: Path) -> None:
    cfg = load_config(sample_project)
    result = scan_project(cfg)
    ids = {n["id"] for n in result.nodes}
    assert ids == {
        "design:characters",
        "design:beat-sheet",
        "design:style",
        "episode:ep01",
        "brief:ep01-brief",
    }


def test_scan_node_has_path_and_mtime(sample_project: Path) -> None:
    cfg = load_config(sample_project)
    result = scan_project(cfg)
    node = next(n for n in result.nodes if n["id"] == "design:characters")
    assert node["path"] == "design/characters.md"
    assert node["type"] == "design"
    assert "mtime" in node


def test_scan_fan_out_rule(sample_project: Path) -> None:
    """design/*.md → drafts/ep*.md creates 3 edges (3 designs × 1 episode)."""
    cfg = load_config(sample_project)
    result = scan_project(cfg)
    informs = [e for e in result.edges if e["relation"] == "informs"]
    assert len(informs) == 3
    targets = {(e["source"], e["target"]) for e in informs}
    assert targets == {
        ("design:characters", "episode:ep01"),
        ("design:beat-sheet", "episode:ep01"),
        ("design:style", "episode:ep01"),
    }


def test_scan_capture_rule(sample_project: Path) -> None:
    """briefs/{ep}-brief.md → drafts/{ep}.md pairs by ep name."""
    cfg = load_config(sample_project)
    result = scan_project(cfg)
    feeds = [e for e in result.edges if e["relation"] == "feeds"]
    assert len(feeds) == 1
    assert feeds[0]["source"] == "brief:ep01-brief"
    assert feeds[0]["target"] == "episode:ep01"


def test_scan_saves_graph_json(sample_project: Path) -> None:
    cfg = load_config(sample_project)
    result = scan_project(cfg)
    result.save(cfg.root)
    graph_path = cfg.root / ".sdcoh" / "graph.json"
    assert graph_path.exists()
    import json
    data = json.loads(graph_path.read_text(encoding="utf-8"))
    assert data["version"] == "2.0"


def test_scan_warns_on_unmatched_rule(tmp_path: Path) -> None:
    (tmp_path / "sdcoh.yml").write_text(
        "project: { name: X }\n"
        "scan:\n"
        '  - { path: "design/", type: "design" }\n'
        "rules:\n"
        '  - name: "orphan rule"\n'
        '    from: "design/*.md"\n'
        '    to: "drafts/*.md"\n'
        '    relation: informs\n'
    )
    (tmp_path / "design").mkdir()
    (tmp_path / "design" / "foo.md").write_text("# foo\n")
    cfg = load_config(tmp_path)
    result = scan_project(cfg)
    assert any("orphan rule" in w for w in result.warnings)


def test_scan_node_id_collision(tmp_path: Path) -> None:
    """Same {type}:{basename} from nested dirs must error."""
    (tmp_path / "sdcoh.yml").write_text(
        "project: { name: X }\n"
        "scan:\n"
        '  - { path: "design/", type: "design" }\n'
    )
    (tmp_path / "design").mkdir()
    (tmp_path / "design" / "sub").mkdir()
    (tmp_path / "design" / "foo.md").write_text("# a\n")
    (tmp_path / "design" / "sub" / "foo.md").write_text("# b\n")
    cfg = load_config(tmp_path)
    with pytest.raises(ScannerError, match="collision"):
        scan_project(cfg)


def test_scan_undefined_placeholder(tmp_path: Path) -> None:
    """`to` pattern referencing an undefined {name} must error."""
    (tmp_path / "sdcoh.yml").write_text(
        "project: { name: X }\n"
        "scan:\n"
        '  - { path: "design/", type: "design" }\n'
        "rules:\n"
        '  - name: "bad"\n'
        '    from: "design/*.md"\n'
        '    to: "drafts/{missing}.md"\n'
        '    relation: informs\n'
    )
    (tmp_path / "design").mkdir()
    (tmp_path / "design" / "x.md").write_text("# x\n")
    cfg = load_config(tmp_path)
    with pytest.raises(ScannerError, match="undefined placeholder"):
        scan_project(cfg)


def test_scan_relation_conflict(tmp_path: Path) -> None:
    """Two rules producing the same (source,target) with different relations must error."""
    (tmp_path / "sdcoh.yml").write_text(
        "project: { name: X }\n"
        "scan:\n"
        '  - { path: "design/", type: "design" }\n'
        '  - { path: "drafts/", type: "episode" }\n'
        "rules:\n"
        '  - name: "r1"\n'
        '    from: "design/*.md"\n'
        '    to: "drafts/*.md"\n'
        '    relation: informs\n'
        '  - name: "r2"\n'
        '    from: "design/*.md"\n'
        '    to: "drafts/*.md"\n'
        '    relation: feeds\n'
    )
    (tmp_path / "design").mkdir()
    (tmp_path / "design" / "a.md").write_text("a\n")
    (tmp_path / "drafts").mkdir()
    (tmp_path / "drafts" / "b.md").write_text("b\n")
    cfg = load_config(tmp_path)
    with pytest.raises(ScannerError, match="Relation conflict"):
        scan_project(cfg)


def test_scan_no_self_loop(tmp_path: Path) -> None:
    """A file matching both from and to must not edge to itself."""
    (tmp_path / "sdcoh.yml").write_text(
        "project: { name: X }\n"
        "scan:\n"
        '  - { path: "design/", type: "design" }\n'
        "rules:\n"
        '  - name: "self"\n'
        '    from: "design/*.md"\n'
        '    to: "design/*.md"\n'
        '    relation: refs\n'
    )
    (tmp_path / "design").mkdir()
    (tmp_path / "design" / "a.md").write_text("a\n")
    (tmp_path / "design" / "b.md").write_text("b\n")
    cfg = load_config(tmp_path)
    result = scan_project(cfg)
    # No edge where source == target
    for e in result.edges:
        assert e["source"] != e["target"]
    # 2 files, fan-out: a↔b but no a→a or b→b → 2 edges
    assert len(result.edges) == 2


def test_scan_duplicate_edges_deduplicated(tmp_path: Path) -> None:
    """Two rules producing same (source,target,relation) should merge."""
    (tmp_path / "sdcoh.yml").write_text(
        "project: { name: X }\n"
        "scan:\n"
        '  - { path: "design/", type: "design" }\n'
        '  - { path: "drafts/", type: "episode" }\n'
        "rules:\n"
        '  - name: "r1"\n'
        '    from: "design/*.md"\n'
        '    to: "drafts/*.md"\n'
        '    relation: informs\n'
        '  - name: "r2"\n'
        '    from: "design/a.md"\n'
        '    to: "drafts/b.md"\n'
        '    relation: informs\n'
    )
    (tmp_path / "design").mkdir()
    (tmp_path / "design" / "a.md").write_text("a\n")
    (tmp_path / "drafts").mkdir()
    (tmp_path / "drafts" / "b.md").write_text("b\n")
    cfg = load_config(tmp_path)
    result = scan_project(cfg)
    assert len(result.edges) == 1


def test_compile_pattern_literal() -> None:
    r, names = _compile_pattern("design/a.md")
    assert names == []
    assert r.fullmatch("design/a.md")
    assert not r.fullmatch("design/b.md")


def test_compile_pattern_star() -> None:
    r, names = _compile_pattern("design/*.md")
    assert names == []
    assert r.fullmatch("design/foo.md")
    assert r.fullmatch("design/bar.md")
    assert not r.fullmatch("design/sub/foo.md")  # * doesn't match /


def test_compile_pattern_capture() -> None:
    r, names = _compile_pattern("briefs/{ep}-brief.md")
    assert names == ["ep"]
    m = r.fullmatch("briefs/ep01-brief.md")
    assert m is not None
    assert m.group("ep") == "ep01"


def test_compile_pattern_capture_non_greedy() -> None:
    """{ep} should match minimally, leaving suffix for the rest."""
    r, names = _compile_pattern("briefs/{ep}-kubota-brief.md")
    m = r.fullmatch("briefs/ep11-kubota-brief.md")
    assert m is not None
    assert m.group("ep") == "ep11"
