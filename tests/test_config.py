# tests/test_config.py
import pytest
from pathlib import Path

from sdcoh.config import (
    load_config,
    SdcohConfig,
    ConfigNotFoundError,
    ConfigFormatError,
    ScanEntry,
    Rule,
)


def test_load_config_from_yaml(tmp_path: Path) -> None:
    yml = tmp_path / "sdcoh.yml"
    yml.write_text(
        "project:\n"
        '  name: "Test Novel"\n'
        '  alias: "test"\n'
        "scan:\n"
        '  - { path: "design/", type: "design" }\n'
        '  - { path: "drafts/", type: "episode" }\n'
        "node_types:\n"
        "  design: { layer: 0 }\n"
        "  episode: { layer: 2 }\n"
    )
    cfg = load_config(tmp_path)
    assert cfg.project_name == "Test Novel"
    assert cfg.project_alias == "test"
    assert cfg.scan == [
        ScanEntry(path="design/", type="design"),
        ScanEntry(path="drafts/", type="episode"),
    ]
    assert cfg.node_types["design"]["layer"] == 0
    assert cfg.node_types["episode"]["layer"] == 2
    assert cfg.rules == []


def test_load_config_with_rules(tmp_path: Path) -> None:
    yml = tmp_path / "sdcoh.yml"
    yml.write_text(
        "project:\n"
        '  name: "Test"\n'
        "scan:\n"
        '  - { path: "design/", type: "design" }\n'
        '  - { path: "drafts/", type: "episode" }\n'
        "rules:\n"
        '  - name: "design informs episodes"\n'
        '    from: "design/*.md"\n'
        '    to: "drafts/ep*.md"\n'
        '    relation: informs\n'
    )
    cfg = load_config(tmp_path)
    assert len(cfg.rules) == 1
    r = cfg.rules[0]
    assert r.name == "design informs episodes"
    assert r.from_pattern == "design/*.md"
    assert r.to_pattern == "drafts/ep*.md"
    assert r.relation == "informs"


def test_load_config_minimal(tmp_path: Path) -> None:
    yml = tmp_path / "sdcoh.yml"
    yml.write_text(
        "project:\n"
        '  name: "Minimal"\n'
    )
    cfg = load_config(tmp_path)
    assert cfg.project_alias == "minimal"
    assert cfg.scan == []
    assert cfg.rules == []
    assert cfg.openviking_enabled is False


def test_load_config_not_found(tmp_path: Path) -> None:
    with pytest.raises(ConfigNotFoundError):
        load_config(tmp_path)


def test_load_config_rejects_legacy_scan_format(tmp_path: Path) -> None:
    """v0.1 style `scan: ["design/", ...]` must error out."""
    yml = tmp_path / "sdcoh.yml"
    yml.write_text(
        "project:\n"
        '  name: "Legacy"\n'
        "scan:\n"
        "  - design/\n"
        "  - drafts/\n"
    )
    with pytest.raises(ConfigFormatError, match="bare string"):
        load_config(tmp_path)


def test_load_config_scan_missing_fields(tmp_path: Path) -> None:
    yml = tmp_path / "sdcoh.yml"
    yml.write_text(
        "project:\n"
        '  name: "X"\n'
        "scan:\n"
        '  - { path: "design/" }\n'
    )
    with pytest.raises(ConfigFormatError, match="path.*type"):
        load_config(tmp_path)


def test_load_config_rule_missing_fields(tmp_path: Path) -> None:
    yml = tmp_path / "sdcoh.yml"
    yml.write_text(
        "project:\n"
        '  name: "X"\n'
        "rules:\n"
        '  - name: "bad"\n'
        '    from: "a/*.md"\n'
    )
    with pytest.raises(ConfigFormatError, match="missing fields"):
        load_config(tmp_path)


def test_load_config_with_openviking(tmp_path: Path) -> None:
    yml = tmp_path / "sdcoh.yml"
    yml.write_text(
        "project:\n"
        '  name: "OV Test"\n'
        "openviking:\n"
        "  enabled: true\n"
        '  endpoint: "http://localhost:1933"\n'
        "  auto_register: true\n"
    )
    cfg = load_config(tmp_path)
    assert cfg.openviking_enabled is True
    assert cfg.openviking_endpoint == "http://localhost:1933"
    assert cfg.openviking_auto_register is True
