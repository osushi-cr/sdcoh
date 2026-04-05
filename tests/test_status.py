# tests/test_status.py
import time
from pathlib import Path

from sdcoh.config import load_config
from sdcoh.scanner import scan_project
from sdcoh.status import check_status


def test_status_all_fresh(sample_project: Path) -> None:
    """All files created at roughly the same time — no stale entries."""
    cfg = load_config(sample_project)
    result = scan_project(cfg)
    stale = check_status(result)
    assert stale == []


def test_status_detects_stale_downstream(sample_project: Path) -> None:
    """When upstream (edge source) is newer than downstream, target is stale."""
    time.sleep(0.1)
    (sample_project / "design" / "characters.md").write_text(
        "# Characters (updated)\n"
    )

    cfg = load_config(sample_project)
    result = scan_project(cfg)
    stale = check_status(result)
    stale_ids = {s.node_id for s in stale}
    # design:characters → episode:ep01 (informs). characters newer → ep01 stale.
    assert "episode:ep01" in stale_ids
    entry = next(s for s in stale if s.node_id == "episode:ep01")
    assert entry.cause_id == "design:characters"
    assert entry.relation == "informs"


def test_status_from_brief(sample_project: Path) -> None:
    """Updating a brief marks the paired episode as stale."""
    time.sleep(0.1)
    (sample_project / "briefs" / "ep01-brief.md").write_text(
        "# Brief ep01 (updated)\n"
    )

    cfg = load_config(sample_project)
    result = scan_project(cfg)
    stale = check_status(result)
    stale_ids = {s.node_id for s in stale}
    assert "episode:ep01" in stale_ids
