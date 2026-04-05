"""CLI entry point using Click."""

from __future__ import annotations

from pathlib import Path

import click

from sdcoh.config import load_config, ConfigNotFoundError
from sdcoh.scanner import scan_project, ScanResult, GRAPH_VERSION
from sdcoh.graph import (
    find_impact,
    find_cycles,
    find_orphans,
    validate_references,
    build_tree_text,
)
from sdcoh.status import check_status


def _resolve_root(path: str | None) -> Path:
    return Path(path) if path else Path.cwd()


def _load_graph(root: Path) -> ScanResult:
    """Load previously saved graph, or scan fresh. Invalidates on version mismatch."""
    import json

    graph_path = root / ".sdcoh" / "graph.json"
    if graph_path.exists():
        data = json.loads(graph_path.read_text(encoding="utf-8"))
        if data.get("version") == GRAPH_VERSION:
            result = ScanResult()
            result.nodes = data.get("nodes", [])
            result.edges = data.get("edges", [])
            return result

    cfg = load_config(root)
    result = scan_project(cfg)
    result.save(root)
    return result


def _node_id_from_path(result: ScanResult, file_path: str) -> str | None:
    """Resolve a file path to a node ID."""
    for node in result.nodes:
        if node["path"] == file_path:
            return node["id"]
    for node in result.nodes:
        if node["path"].endswith("/" + file_path):
            return node["id"]
    return None


@click.group()
@click.version_option()
def cli() -> None:
    """sdcoh — Story Design Coherence."""


@cli.command()
@click.option("--name", required=True, help="Project name")
@click.option("--alias", default=None, help="Short alias")
@click.option("--path", default=None, help="Project root directory")
def init(name: str, alias: str | None, path: str | None) -> None:
    """Initialize a new sdcoh project."""
    root = _resolve_root(path)
    if alias is None:
        alias = name.lower().replace(" ", "-")

    yml_path = root / "sdcoh.yml"
    yml_path.write_text(
        f'project:\n'
        f'  name: "{name}"\n'
        f'  alias: "{alias}"\n'
        f'\n'
        f'scan:\n'
        f'  - {{ path: "design/",  type: "design" }}\n'
        f'  - {{ path: "drafts/",  type: "episode" }}\n'
        f'  - {{ path: "briefs/",  type: "brief" }}\n'
        f'  - {{ path: "reviews/", type: "review" }}\n'
        f'\n'
        f'node_types:\n'
        f'  research: {{ layer: -1 }}\n'
        f'  design: {{ layer: 0 }}\n'
        f'  brief: {{ layer: 1 }}\n'
        f'  episode: {{ layer: 2 }}\n'
        f'  review: {{ layer: 3 }}\n'
        f'\n'
        f'rules:\n'
        f'  - name: "design informs episodes"\n'
        f'    from: "design/*.md"\n'
        f'    to: "drafts/ep*.md"\n'
        f'    relation: informs\n'
        f'  - name: "brief feeds episode"\n'
        f'    from: "briefs/{{ep}}-brief.md"\n'
        f'    to: "drafts/{{ep}}.md"\n'
        f'    relation: feeds\n',
        encoding="utf-8",
    )
    (root / ".sdcoh").mkdir(exist_ok=True)
    click.echo(f"Created sdcoh.yml")
    click.echo(f"Created .sdcoh/")


@cli.command()
@click.option("--path", default=None, help="Project root directory")
@click.option("--quiet", is_flag=True, help="Minimal output")
@click.option("--warn", is_flag=True, help="List rules with no matches")
def scan(path: str | None, quiet: bool, warn: bool) -> None:
    """Scan project and build dependency graph."""
    root = _resolve_root(path)
    try:
        cfg = load_config(root)
    except ConfigNotFoundError as e:
        raise click.ClickException(str(e))

    result = scan_project(cfg)
    result.save(root)

    if quiet:
        if result.warnings:
            click.echo(f"⚠️ {len(result.warnings)} rule(s) with no matches")
        return

    click.echo(f"  Graph: {len(result.nodes)} nodes, {len(result.edges)} edges")

    if result.warnings:
        click.echo(f"  ⚠️ {len(result.warnings)} rule(s) with no matches"
                   + (" (use --warn to list)" if not warn else ""))
        if warn:
            for w in result.warnings:
                click.echo(f"    - {w}")


@cli.command()
@click.argument("file_path")
@click.option("--path", default=None, help="Project root directory")
@click.option("--depth", default=0, type=int, help="Max traversal depth (0=unlimited)")
def impact(file_path: str, path: str | None, depth: int) -> None:
    """Show which nodes are affected by changing a file."""
    root = _resolve_root(path)
    result = _load_graph(root)

    node_id = _node_id_from_path(result, file_path)
    if not node_id:
        raise click.ClickException(f"No node found for path: {file_path}")

    impacted = find_impact(result, node_id, max_depth=depth)
    if not impacted:
        click.echo(f"No impacts detected for {node_id}")
        return

    click.echo(f"\n影響先（{len(impacted)}件）:")
    for item in impacted:
        click.echo(f"  🟡 {item['id']:30s} ← {item['relation']}")


@cli.command()
@click.option("--path", default=None, help="Project root directory")
def graph(path: str | None) -> None:
    """Display the dependency graph as a tree."""
    root = _resolve_root(path)
    result = _load_graph(root)
    text = build_tree_text(result)
    click.echo(f"\n{text}")


@cli.command()
@click.option("--path", default=None, help="Project root directory")
def validate(path: str | None) -> None:
    """Validate graph integrity."""
    root = _resolve_root(path)
    result = _load_graph(root)

    broken = validate_references(result)
    cycles = find_cycles(result)
    orphans = find_orphans(result)

    has_errors = bool(broken or cycles)

    if broken or cycles:
        click.echo(f"\n❌ エラー（{len(broken) + len(cycles)}件）:")
        for b in broken:
            click.echo(f"  {b}")
        for c in cycles:
            click.echo(f"  循環依存: {' → '.join(c)}")

    if orphans:
        click.echo(f"\n⚠️ 警告（{len(orphans)}件）:")
        for o in orphans:
            click.echo(f"  {o}: どこからも参照されていない（孤立ノード）")

    if not has_errors and not orphans:
        click.echo("✅ グラフは正常です")


@cli.command()
@click.option("--path", default=None, help="Project root directory")
@click.option("--warn-only", is_flag=True, help="Only output if warnings exist")
@click.option("--json", "as_json", is_flag=True, help="JSON output")
def status(path: str | None, warn_only: bool, as_json: bool) -> None:
    """Check for stale downstream documents."""
    root = _resolve_root(path)

    try:
        cfg = load_config(root)
    except ConfigNotFoundError as e:
        raise click.ClickException(str(e))

    result = scan_project(cfg)
    stale = check_status(result)

    if as_json:
        import json as json_mod
        click.echo(json_mod.dumps(
            [{"node": s.node_id, "cause": s.cause_id, "relation": s.relation}
             for s in stale],
            ensure_ascii=False, indent=2,
        ))
        return

    if warn_only and not stale:
        return

    if stale:
        click.echo(f"\n⚠️ 更新が必要（{len(stale)}件）:")
        for s in stale:
            click.echo(f"  {s.node_id:30s} ← {s.cause_id} が新しい ({s.relation})")
    else:
        fresh = len(result.nodes)
        click.echo(f"\n✅ 整合（{fresh}件）")
