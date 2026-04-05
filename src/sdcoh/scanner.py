"""Scan directories and build dependency graph from rules."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from sdcoh.config import SdcohConfig, Rule

GRAPH_VERSION = "2.0"


class ScannerError(RuntimeError):
    """Raised on scanner configuration/validation errors."""


@dataclass
class ScanResult:
    """Result of scanning a project."""

    nodes: list[dict] = field(default_factory=list)
    edges: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def save(self, root: Path) -> Path:
        """Save graph to .sdcoh/graph.json."""
        out_dir = root / ".sdcoh"
        out_dir.mkdir(exist_ok=True)
        graph_path = out_dir / "graph.json"
        graph_path.write_text(
            json.dumps(
                {
                    "version": GRAPH_VERSION,
                    "scanned_at": datetime.now(timezone.utc).isoformat(),
                    "nodes": self.nodes,
                    "edges": self.edges,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return graph_path


def scan_project(cfg: SdcohConfig) -> ScanResult:
    """Scan files and build the dependency graph from rules."""
    result = ScanResult()

    # 1. Collect nodes from scan entries
    path_to_node: dict[str, dict] = {}
    id_to_node: dict[str, dict] = {}

    for entry in cfg.scan:
        dir_path = cfg.root / entry.path.rstrip("/")
        if not dir_path.exists():
            continue
        for md_file in sorted(dir_path.rglob("*.md")):
            basename = md_file.stem
            node_id = f"{entry.type}:{basename}"
            rel_path = str(md_file.relative_to(cfg.root))
            if node_id in id_to_node:
                existing = id_to_node[node_id]
                raise ScannerError(
                    f'Node ID collision: "{node_id}" produced by both '
                    f'"{existing["path"]}" and "{rel_path}". '
                    f"Rename one or split into distinct scan entries."
                )
            mtime = datetime.fromtimestamp(
                md_file.stat().st_mtime, tz=timezone.utc
            ).isoformat()
            node = {
                "id": node_id,
                "type": entry.type,
                "path": rel_path,
                "mtime": mtime,
            }
            id_to_node[node_id] = node
            path_to_node[rel_path] = node
            result.nodes.append(node)

    # 2. Apply rules to build edges
    # Deduplicate by (source, target); error on relation conflict.
    edge_map: dict[tuple[str, str], dict] = {}

    for rule in cfg.rules:
        _validate_rule_placeholders(rule)
        from_regex, capture_names = _compile_pattern(rule.from_pattern)
        matched_any = False

        for src_path, src_node in path_to_node.items():
            m = from_regex.fullmatch(src_path)
            if not m:
                continue
            captures = {name: m.group(name) for name in capture_names}
            target_glob = _substitute_captures(rule.to_pattern, captures)
            target_regex, _ = _compile_pattern(target_glob)

            for tgt_path, tgt_node in path_to_node.items():
                if tgt_path == src_path:
                    continue
                if not target_regex.fullmatch(tgt_path):
                    continue
                matched_any = True
                key = (src_node["id"], tgt_node["id"])
                if key in edge_map:
                    existing = edge_map[key]
                    if existing["relation"] != rule.relation:
                        raise ScannerError(
                            f'Relation conflict on edge '
                            f'{src_node["id"]} → {tgt_node["id"]}: '
                            f'"{existing["relation"]}" vs "{rule.relation}"'
                        )
                    continue
                edge_map[key] = {
                    "source": src_node["id"],
                    "target": tgt_node["id"],
                    "relation": rule.relation,
                }

        if not matched_any:
            result.warnings.append(
                f'rule "{rule.name}": no edges created'
            )

    result.edges = list(edge_map.values())
    return result


def _validate_rule_placeholders(rule: Rule) -> None:
    """Ensure all {name} in `to` also appear in `from`."""
    from_names = set(re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", rule.from_pattern))
    to_names = set(re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", rule.to_pattern))
    undefined = to_names - from_names
    if undefined:
        raise ScannerError(
            f'Rule "{rule.name}": `to` references undefined placeholder(s): '
            f'{", ".join(sorted(undefined))}'
        )


def _compile_pattern(pattern: str) -> tuple[re.Pattern[str], list[str]]:
    """Compile a glob+capture pattern to a regex.

    Syntax:
        {name} → named capture (non-greedy, no slashes)
        *      → [^/]*
        ?      → [^/]
        other  → escaped

    Returns (compiled_regex, capture_names_in_order).
    """
    capture_names: list[str] = []
    out: list[str] = []
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "{":
            end = pattern.find("}", i)
            if end == -1:
                raise ScannerError(f"Unclosed {{ in pattern: {pattern!r}")
            name = pattern[i + 1:end]
            if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", name):
                raise ScannerError(
                    f"Invalid placeholder name {name!r} in pattern: {pattern!r}"
                )
            capture_names.append(name)
            out.append(f"(?P<{name}>[^/]+?)")
            i = end + 1
        elif c == "*":
            out.append("[^/]*")
            i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("".join(out)), capture_names


def _substitute_captures(pattern: str, captures: dict[str, str]) -> str:
    """Replace {name} in pattern with captured values."""
    def repl(m: re.Match[str]) -> str:
        name = m.group(1)
        if name not in captures:
            raise ScannerError(f"Undefined placeholder {{{name}}}")
        return captures[name]

    return re.sub(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", repl, pattern)
