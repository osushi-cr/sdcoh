# tests/conftest.py
import pytest
from pathlib import Path


@pytest.fixture
def sample_project(tmp_path: Path) -> Path:
    """Create a minimal novel project with frontmatter."""
    # sdcoh.yml
    (tmp_path / "sdcoh.yml").write_text(
        "project:\n"
        '  name: "Test Novel"\n'
        "scan:\n"
        "  - design/\n"
        "  - drafts/\n"
        "  - briefs/\n"
    )

    # design docs
    design = tmp_path / "design"
    design.mkdir()

    (design / "characters.md").write_text(
        "---\n"
        "sdcoh:\n"
        '  id: "design:characters"\n'
        "---\n"
        "# Characters\n"
    )

    (design / "beat-sheet.md").write_text(
        "---\n"
        "sdcoh:\n"
        '  id: "design:beat-sheet"\n'
        "  depends_on:\n"
        '    - id: "design:characters"\n'
        '      relation: derives_from\n'
        "---\n"
        "# Beat Sheet\n"
    )

    (design / "style.md").write_text(
        "---\n"
        "sdcoh:\n"
        '  id: "design:style"\n'
        "---\n"
        "# Style\n"
    )

    (design / "no-frontmatter.md").write_text("# No frontmatter\n")

    # drafts
    drafts = tmp_path / "drafts"
    drafts.mkdir()

    (drafts / "ep01.md").write_text(
        "---\n"
        "sdcoh:\n"
        '  id: "episode:ep01"\n'
        "  depends_on:\n"
        '    - id: "design:beat-sheet"\n'
        '      relation: implements\n'
        '    - id: "design:style"\n'
        '      relation: constrained_by\n'
        "  updates:\n"
        '    - id: "design:characters"\n'
        '      relation: triggers_update\n'
        "---\n"
        "# Episode 1\n"
    )

    # briefs
    briefs = tmp_path / "briefs"
    briefs.mkdir()

    (briefs / "ep01-brief.md").write_text(
        "---\n"
        "sdcoh:\n"
        '  id: "brief:ep01"\n'
        "  depends_on:\n"
        '    - id: "design:beat-sheet"\n'
        '      relation: derives_from\n'
        '    - id: "design:characters"\n'
        '      relation: references\n'
        "---\n"
        "# Brief ep01\n"
    )

    return tmp_path
