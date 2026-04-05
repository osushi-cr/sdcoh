# tests/test_e2e.py
"""End-to-end test simulating a real novel project workflow."""

import time
from pathlib import Path

from click.testing import CliRunner

from sdcoh.cli import cli


def _setup_novel_project(root: Path) -> None:
    """Create a mini novel project with rules-based config (v0.2)."""
    (root / "sdcoh.yml").write_text(
        'project:\n'
        '  name: "E2E Test Novel"\n'
        '  alias: "e2e"\n'
        'scan:\n'
        '  - { path: "design/", type: "design" }\n'
        '  - { path: "drafts/", type: "episode" }\n'
        '  - { path: "briefs/", type: "brief" }\n'
        'rules:\n'
        '  - name: "design informs episodes"\n'
        '    from: "design/*.md"\n'
        '    to: "drafts/ep*.md"\n'
        '    relation: informs\n'
        '  - name: "brief feeds episode"\n'
        '    from: "briefs/{ep}-brief.md"\n'
        '    to: "drafts/{ep}.md"\n'
        '    relation: feeds\n'
    )
    (root / "design").mkdir()
    (root / "drafts").mkdir()
    (root / "briefs").mkdir()

    (root / "design" / "characters.md").write_text("# Characters\n")
    (root / "design" / "beat-sheet.md").write_text("# Beat Sheet\n")
    (root / "design" / "style.md").write_text("# Style Guide\n")
    (root / "briefs" / "ep01-brief.md").write_text("# Brief ep01\n")
    (root / "drafts" / "ep01.md").write_text("# Episode 1\n")


def test_full_workflow(tmp_path: Path) -> None:
    """Test: scan → validate → graph → impact → status."""
    _setup_novel_project(tmp_path)
    runner = CliRunner()
    p = str(tmp_path)

    # scan
    r = runner.invoke(cli, ["scan", "--path", p], catch_exceptions=False)
    assert r.exit_code == 0
    assert "5 nodes" in r.output

    # validate
    r = runner.invoke(cli, ["validate", "--path", p], catch_exceptions=False)
    assert r.exit_code == 0
    assert "正常" in r.output

    # graph
    r = runner.invoke(cli, ["graph", "--path", p], catch_exceptions=False)
    assert r.exit_code == 0
    assert "design:characters" in r.output

    # impact: changing characters.md should impact episode:ep01
    r = runner.invoke(
        cli, ["impact", "design/characters.md", "--path", p], catch_exceptions=False
    )
    assert r.exit_code == 0
    assert "episode:ep01" in r.output

    # status (all fresh)
    r = runner.invoke(cli, ["status", "--path", p], catch_exceptions=False)
    assert r.exit_code == 0
    assert "整合" in r.output

    # Edit characters.md → episode:ep01 becomes stale
    time.sleep(0.1)
    (tmp_path / "design" / "characters.md").write_text("# Characters (edited)\n")

    r = runner.invoke(cli, ["status", "--path", p], catch_exceptions=False)
    assert r.exit_code == 0
    assert "更新が必要" in r.output
    assert "episode:ep01" in r.output
