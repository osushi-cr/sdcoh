# tests/test_cli.py
import json
from pathlib import Path

from click.testing import CliRunner

from sdcoh.cli import cli


def test_cli_init(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["init", "--name", "Test Novel", "--path", str(tmp_path)], catch_exceptions=False)
    assert result.exit_code == 0
    assert (tmp_path / "sdcoh.yml").exists()
    assert "Created" in result.output
    # Template should include rules section
    yml = (tmp_path / "sdcoh.yml").read_text()
    assert "rules:" in yml
    assert "scan:" in yml
    # Scan entries use new dict format
    assert "path:" in yml and "type:" in yml


def test_cli_scan(sample_project: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli, ["scan", "--path", str(sample_project)], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "nodes" in result.output.lower() or "graph" in result.output.lower()
    assert (sample_project / ".sdcoh" / "graph.json").exists()


def test_cli_impact(sample_project: Path) -> None:
    runner = CliRunner()
    runner.invoke(cli, ["scan", "--path", str(sample_project)], catch_exceptions=False)
    result = runner.invoke(
        cli,
        ["impact", "design/characters.md", "--path", str(sample_project)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "episode:ep01" in result.output


def test_cli_status(sample_project: Path) -> None:
    runner = CliRunner()
    runner.invoke(cli, ["scan", "--path", str(sample_project)], catch_exceptions=False)
    result = runner.invoke(
        cli, ["status", "--path", str(sample_project)], catch_exceptions=False
    )
    assert result.exit_code == 0


def test_cli_validate(sample_project: Path) -> None:
    runner = CliRunner()
    runner.invoke(cli, ["scan", "--path", str(sample_project)], catch_exceptions=False)
    result = runner.invoke(
        cli, ["validate", "--path", str(sample_project)], catch_exceptions=False
    )
    assert result.exit_code == 0


def test_cli_graph(sample_project: Path) -> None:
    runner = CliRunner()
    runner.invoke(cli, ["scan", "--path", str(sample_project)], catch_exceptions=False)
    result = runner.invoke(
        cli, ["graph", "--path", str(sample_project)], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "design:characters" in result.output


def test_cli_load_graph_invalidates_old_version(sample_project: Path) -> None:
    """A cache file with a stale version must be ignored and rebuilt."""
    sdcoh_dir = sample_project / ".sdcoh"
    sdcoh_dir.mkdir(exist_ok=True)
    stale_cache = {
        "version": "1.0",
        "scanned_at": "2020-01-01T00:00:00+00:00",
        "nodes": [{"id": "legacy", "type": "design", "path": "x.md", "mtime": "2020-01-01T00:00:00+00:00"}],
        "edges": [],
    }
    (sdcoh_dir / "graph.json").write_text(json.dumps(stale_cache))

    runner = CliRunner()
    result = runner.invoke(
        cli, ["graph", "--path", str(sample_project)], catch_exceptions=False
    )
    assert result.exit_code == 0
    # Stale "legacy" node should NOT appear — cache was rebuilt
    assert "legacy" not in result.output
    assert "design:characters" in result.output
