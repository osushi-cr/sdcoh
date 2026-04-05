"""Load and validate sdcoh.yml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


class ConfigNotFoundError(FileNotFoundError):
    """Raised when sdcoh.yml is not found."""


class ConfigFormatError(ValueError):
    """Raised when sdcoh.yml uses an unsupported format."""


_DEFAULT_NODE_TYPES = {
    "research": {"layer": -1},
    "design": {"layer": 0},
    "brief": {"layer": 1},
    "episode": {"layer": 2},
    "review": {"layer": 3},
}


@dataclass
class ScanEntry:
    """A directory to scan with its node type."""

    path: str
    type: str


@dataclass
class Rule:
    """A dependency rule: when `from` changes, `to` becomes stale."""

    name: str
    from_pattern: str
    to_pattern: str
    relation: str


@dataclass
class SdcohConfig:
    """Parsed sdcoh.yml configuration."""

    root: Path
    project_name: str
    project_alias: str
    scan: list[ScanEntry] = field(default_factory=list)
    rules: list[Rule] = field(default_factory=list)
    node_types: dict[str, dict] = field(default_factory=lambda: dict(_DEFAULT_NODE_TYPES))
    openviking_enabled: bool = False
    openviking_endpoint: str = "http://localhost:1933"
    openviking_auto_register: bool = False


def load_config(root: Path) -> SdcohConfig:
    """Load sdcoh.yml from the given directory."""
    yml_path = root / "sdcoh.yml"
    if not yml_path.exists():
        raise ConfigNotFoundError(f"sdcoh.yml not found in {root}")

    data = yaml.safe_load(yml_path.read_text(encoding="utf-8")) or {}
    project = data.get("project", {})
    name = project.get("name", "Untitled")
    alias = project.get("alias", name.lower().replace(" ", "-"))

    scan_raw = data.get("scan", [])
    scan = _parse_scan(scan_raw)

    rules_raw = data.get("rules", [])
    rules = _parse_rules(rules_raw)

    ov = data.get("openviking", {})

    return SdcohConfig(
        root=root,
        project_name=name,
        project_alias=alias,
        scan=scan,
        rules=rules,
        node_types=data.get("node_types", dict(_DEFAULT_NODE_TYPES)),
        openviking_enabled=ov.get("enabled", False),
        openviking_endpoint=ov.get("endpoint", "http://localhost:1933"),
        openviking_auto_register=ov.get("auto_register", False),
    )


def _parse_scan(raw: object) -> list[ScanEntry]:
    if not isinstance(raw, list):
        raise ConfigFormatError("`scan:` must be a list of {path, type} entries")

    entries: list[ScanEntry] = []
    for i, item in enumerate(raw):
        if isinstance(item, str):
            raise ConfigFormatError(
                f"`scan:` entry #{i} is a bare string ({item!r}). "
                "v0.2 requires {path, type} dict entries. "
                "See docs for migration from v0.1."
            )
        if not isinstance(item, dict):
            raise ConfigFormatError(
                f"`scan:` entry #{i} must be a dict with path and type"
            )
        path = item.get("path")
        type_ = item.get("type")
        if not path or not type_:
            raise ConfigFormatError(
                f"`scan:` entry #{i} requires both `path` and `type`"
            )
        entries.append(ScanEntry(path=path, type=type_))
    return entries


def _parse_rules(raw: object) -> list[Rule]:
    if not isinstance(raw, list):
        raise ConfigFormatError("`rules:` must be a list")

    rules: list[Rule] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ConfigFormatError(f"`rules:` entry #{i} must be a dict")
        name = item.get("name")
        from_p = item.get("from")
        to_p = item.get("to")
        relation = item.get("relation")
        missing = [
            k for k, v in
            (("name", name), ("from", from_p), ("to", to_p), ("relation", relation))
            if not v
        ]
        if missing:
            raise ConfigFormatError(
                f"`rules:` entry #{i} missing fields: {', '.join(missing)}"
            )
        rules.append(Rule(
            name=name, from_pattern=from_p, to_pattern=to_p, relation=relation,
        ))
    return rules
