# tests/test_e2e.py
"""End-to-end test simulating a real novel project workflow."""

import time
from pathlib import Path

from click.testing import CliRunner

from sdcoh.cli import cli


def _setup_novel_project(root: Path) -> None:
    """Create a mini novel project structure."""
    (root / "sdcoh.yml").write_text(
        'project:\n'
        '  name: "E2E Test Novel"\n'
        '  alias: "e2e"\n'
        'scan:\n'
        '  - design/\n'
        '  - drafts/\n'
        '  - briefs/\n'
    )
    (root / "design").mkdir()
    (root / "drafts").mkdir()
    (root / "briefs").mkdir()

    (root / "design" / "characters.md").write_text(
        '---\nsdcoh:\n  id: "design:characters"\n---\n# Characters\n'
    )
    (root / "design" / "beat-sheet.md").write_text(
        '---\nsdcoh:\n  id: "design:beat-sheet"\n  depends_on:\n'
        '    - id: "design:characters"\n      relation: derives_from\n---\n'
        '# Beat Sheet\n'
    )
    (root / "design" / "style.md").write_text(
        '---\nsdcoh:\n  id: "design:style"\n---\n# Style Guide\n'
    )
    (root / "briefs" / "ep01-brief.md").write_text(
        '---\nsdcoh:\n  id: "brief:ep01"\n  depends_on:\n'
        '    - id: "design:beat-sheet"\n      relation: derives_from\n'
        '    - id: "design:characters"\n      relation: references\n---\n'
        '# Brief ep01\n'
    )
    (root / "drafts" / "ep01.md").write_text(
        '---\nsdcoh:\n  id: "episode:ep01"\n  depends_on:\n'
        '    - id: "brief:ep01"\n      relation: implements\n'
        '    - id: "design:style"\n      relation: constrained_by\n'
        '  updates:\n'
        '    - id: "design:characters"\n      relation: triggers_update\n---\n'
        '# Episode 1\n'
    )


def test_full_workflow(tmp_path: Path) -> None:
    """Test: init → scan → validate → graph → impact → status."""
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

    # impact
    r = runner.invoke(
        cli, ["impact", "design/characters.md", "--path", p], catch_exceptions=False
    )
    assert r.exit_code == 0
    assert "beat-sheet" in r.output

    # status (all fresh)
    r = runner.invoke(cli, ["status", "--path", p], catch_exceptions=False)
    assert r.exit_code == 0
    assert "整合" in r.output

    # Now touch characters.md to simulate an edit
    time.sleep(0.1)
    (tmp_path / "design" / "characters.md").write_text(
        '---\nsdcoh:\n  id: "design:characters"\n---\n# Characters (edited)\n'
    )

    # status should now show stale
    r = runner.invoke(cli, ["status", "--path", p], catch_exceptions=False)
    assert r.exit_code == 0
    assert "更新が必要" in r.output
    assert "beat-sheet" in r.output
