# tests/test_status.py
import time
from pathlib import Path

from sdcoh.config import load_config
from sdcoh.scanner import scan_project
from sdcoh.status import check_status, StaleEntry


def test_status_all_fresh(sample_project: Path) -> None:
    """All files created at roughly the same time — no stale entries."""
    cfg = load_config(sample_project)
    result = scan_project(cfg)
    stale = check_status(result)
    assert stale == []


def test_status_detects_stale_downstream(sample_project: Path) -> None:
    """When upstream is newer than downstream, downstream is stale."""
    # Touch upstream to make it newer
    time.sleep(0.1)
    (sample_project / "design" / "characters.md").write_text(
        "---\n"
        "sdcoh:\n"
        '  id: "design:characters"\n'
        "---\n"
        "# Characters (updated)\n"
    )

    cfg = load_config(sample_project)
    result = scan_project(cfg)
    stale = check_status(result)
    stale_ids = {s.node_id for s in stale}
    # beat-sheet depends on characters → stale
    assert "design:beat-sheet" in stale_ids


def test_status_detects_stale_update_target(sample_project: Path) -> None:
    """When a node with updates edges is newer, targets are stale."""
    time.sleep(0.1)
    (sample_project / "drafts" / "ep01.md").write_text(
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
        "# Episode 1 (updated)\n"
    )

    cfg = load_config(sample_project)
    result = scan_project(cfg)
    stale = check_status(result)
    stale_ids = {s.node_id for s in stale}
    # ep01 updates characters → characters is stale
    assert "design:characters" in stale_ids
