# tests/conftest.py
import pytest
from pathlib import Path


@pytest.fixture
def sample_project(tmp_path: Path) -> Path:
    """Create a minimal novel project with rules (no frontmatter)."""
    (tmp_path / "sdcoh.yml").write_text(
        "project:\n"
        '  name: "Test Novel"\n'
        "scan:\n"
        '  - { path: "design/",  type: "design" }\n'
        '  - { path: "drafts/",  type: "episode" }\n'
        '  - { path: "briefs/",  type: "brief" }\n'
        "rules:\n"
        '  - name: "design informs episodes"\n'
        '    from: "design/*.md"\n'
        '    to: "drafts/ep*.md"\n'
        '    relation: informs\n'
        '  - name: "brief feeds episode"\n'
        '    from: "briefs/{ep}-brief.md"\n'
        '    to: "drafts/{ep}.md"\n'
        '    relation: feeds\n'
    )

    design = tmp_path / "design"
    design.mkdir()
    (design / "characters.md").write_text("# Characters\n")
    (design / "beat-sheet.md").write_text("# Beat Sheet\n")
    (design / "style.md").write_text("# Style\n")

    drafts = tmp_path / "drafts"
    drafts.mkdir()
    (drafts / "ep01.md").write_text("# Episode 1\n")

    briefs = tmp_path / "briefs"
    briefs.mkdir()
    (briefs / "ep01-brief.md").write_text("# Brief ep01\n")

    return tmp_path


@pytest.fixture
def glob_project(tmp_path: Path) -> Path:
    """Project where a rule fans out from one design to many episodes."""
    (tmp_path / "sdcoh.yml").write_text(
        "project:\n"
        '  name: "Glob Test"\n'
        "scan:\n"
        '  - { path: "design/", type: "design" }\n'
        '  - { path: "drafts/", type: "episode" }\n'
        "rules:\n"
        '  - name: "design informs all episodes"\n'
        '    from: "design/*.md"\n'
        '    to: "drafts/ep*.md"\n'
        '    relation: informs\n'
    )

    design = tmp_path / "design"
    design.mkdir()
    (design / "characters.md").write_text("# Characters\n")
    (design / "beat-sheet.md").write_text("# Beat Sheet\n")
    (design / "style.md").write_text("# Style\n")

    drafts = tmp_path / "drafts"
    drafts.mkdir()
    (drafts / "ep01.md").write_text("# Episode 1\n")

    return tmp_path
