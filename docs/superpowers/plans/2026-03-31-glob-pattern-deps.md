# Glob Pattern Dependencies Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `depends_on` / `updates` の ID 指定で fnmatch glob パターンをサポートし、スキャン時に展開する。

**Architecture:** `scanner.py` を2パス構成に変更。Pass 1 で全ノードIDを収集し、Pass 2 でエッジ構築時に `_expand_pattern()` でglobを展開する。`graph.json` には展開済みエッジのみ保存し、下流（graph.py, status.py, cli.py）は変更なし。

**Tech Stack:** Python 3.10+, fnmatch (stdlib), pytest

---

## File Structure

- **Modify:** `src/sdcoh/scanner.py` — `_expand_pattern()` 追加、`scan_project()` を2パスに変更
- **Modify:** `tests/test_scanner.py` — glob パターンのテスト追加
- **Modify:** `tests/conftest.py` — glob テスト用 fixture 追加

---

### Task 1: `_expand_pattern()` のテストと実装

**Files:**
- Modify: `src/sdcoh/scanner.py:1-119`
- Modify: `tests/test_scanner.py`

- [ ] **Step 1: Write the failing test for `_expand_pattern` with a literal ID (no glob)**

`tests/test_scanner.py` に追加:

```python
from sdcoh.scanner import _expand_pattern


def test_expand_pattern_literal_returns_as_is() -> None:
    all_ids = {"design:characters", "design:beat-sheet", "episode:ep01"}
    result = _expand_pattern("design:characters", all_ids, "episode:ep01")
    assert result == ["design:characters"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/yoshida/src/work/sdcoh && python -m pytest tests/test_scanner.py::test_expand_pattern_literal_returns_as_is -v`
Expected: FAIL with `ImportError: cannot import name '_expand_pattern'`

- [ ] **Step 3: Write the failing test for glob pattern expansion**

```python
def test_expand_pattern_glob_matches() -> None:
    all_ids = {"design:characters", "design:beat-sheet", "design:style", "episode:ep01"}
    result = _expand_pattern("design:*", all_ids, "episode:ep01")
    assert result == ["design:beat-sheet", "design:characters", "design:style"]
```

- [ ] **Step 4: Write the failing test for self-exclusion**

```python
def test_expand_pattern_excludes_self() -> None:
    all_ids = {"design:characters", "design:beat-sheet", "design:style"}
    result = _expand_pattern("design:*", all_ids, "design:characters")
    assert result == ["design:beat-sheet", "design:style"]
```

- [ ] **Step 5: Write the failing test for zero matches**

```python
def test_expand_pattern_no_match_returns_empty() -> None:
    all_ids = {"design:characters", "episode:ep01"}
    result = _expand_pattern("brief:*", all_ids, "episode:ep01")
    assert result == []
```

- [ ] **Step 6: Implement `_expand_pattern`**

`src/sdcoh/scanner.py` の先頭 import に `from fnmatch import fnmatch` を追加し、`_process_file` の直前に関数を追加:

```python
from fnmatch import fnmatch


def _expand_pattern(
    pattern: str,
    all_node_ids: set[str],
    self_id: str,
) -> list[str]:
    """Expand a glob pattern against known node IDs.

    If pattern contains no glob characters, returns [pattern] as-is.
    Otherwise returns sorted matched IDs, excluding self_id.
    """
    if not any(c in pattern for c in ("*", "?", "[")):
        return [pattern]
    return sorted(
        nid for nid in all_node_ids
        if fnmatch(nid, pattern) and nid != self_id
    )
```

- [ ] **Step 7: Run all 4 new tests to verify they pass**

Run: `cd /Users/yoshida/src/work/sdcoh && python -m pytest tests/test_scanner.py -k "expand_pattern" -v`
Expected: 4 PASSED

- [ ] **Step 8: Commit**

```bash
cd /Users/yoshida/src/work/sdcoh && git add src/sdcoh/scanner.py tests/test_scanner.py
git commit -m "feat: add _expand_pattern with fnmatch glob support"
```

---

### Task 2: `scan_project` を2パスに変更しパターン展開を統合

**Files:**
- Modify: `src/sdcoh/scanner.py:44-119`
- Modify: `tests/conftest.py`
- Modify: `tests/test_scanner.py`

- [ ] **Step 1: Write the failing test — glob in `depends_on`**

`tests/conftest.py` に新しい fixture を追加:

```python
@pytest.fixture
def glob_project(tmp_path: Path) -> Path:
    """Project where dependencies use glob patterns."""
    (tmp_path / "sdcoh.yml").write_text(
        "project:\n"
        '  name: "Glob Test"\n'
        "scan:\n"
        "  - design/\n"
        "  - drafts/\n"
    )

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

    drafts = tmp_path / "drafts"
    drafts.mkdir()

    (drafts / "ep01.md").write_text(
        "---\n"
        "sdcoh:\n"
        '  id: "episode:ep01"\n'
        "  depends_on:\n"
        '    - id: "design:*"\n'
        '      relation: implements\n'
        "---\n"
        "# Episode 1\n"
    )

    return tmp_path
```

`tests/test_scanner.py` に追加:

```python
def test_scan_expands_glob_depends_on(glob_project: Path) -> None:
    cfg = load_config(glob_project)
    result = scan_project(cfg)
    deps_edges = [
        e for e in result.edges
        if e["source"] == "episode:ep01" and e["direction"] == "depends_on"
    ]
    targets = sorted(e["target"] for e in deps_edges)
    assert targets == ["design:beat-sheet", "design:characters", "design:style"]
    assert all(e["relation"] == "implements" for e in deps_edges)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/yoshida/src/work/sdcoh && python -m pytest tests/test_scanner.py::test_scan_expands_glob_depends_on -v`
Expected: FAIL — `design:*` がそのまま target に入る（マッチなし or リテラル扱い）

- [ ] **Step 3: Write the failing test — glob in `updates`**

```python
def test_scan_expands_glob_updates(glob_project: Path) -> None:
    # Add a design doc that updates all episodes
    design_dir = glob_project / "design"
    (design_dir / "beat-sheet.md").write_text(
        "---\n"
        "sdcoh:\n"
        '  id: "design:beat-sheet"\n'
        "  updates:\n"
        '    - id: "episode:*"\n'
        '      relation: triggers_update\n'
        "---\n"
        "# Beat Sheet\n"
    )
    cfg = load_config(glob_project)
    result = scan_project(cfg)
    update_edges = [
        e for e in result.edges
        if e["source"] == "design:beat-sheet" and e["direction"] == "updates"
    ]
    assert len(update_edges) == 1
    assert update_edges[0]["target"] == "episode:ep01"
```

- [ ] **Step 4: Write the failing test — zero-match glob produces warning**

```python
def test_scan_glob_no_match_warns(glob_project: Path) -> None:
    drafts = glob_project / "drafts"
    (drafts / "ep01.md").write_text(
        "---\n"
        "sdcoh:\n"
        '  id: "episode:ep01"\n'
        "  depends_on:\n"
        '    - id: "research:*"\n'
        '      relation: references\n'
        "---\n"
        "# Episode 1\n"
    )
    cfg = load_config(glob_project)
    result = scan_project(cfg)
    assert any("research:*" in w for w in result.warnings)
```

- [ ] **Step 5: Refactor `scan_project` to 2-pass and integrate `_expand_pattern`**

`src/sdcoh/scanner.py` の `scan_project` と `_process_file` を以下に置き換え:

```python
def scan_project(cfg: SdcohConfig) -> ScanResult:
    """Scan all Markdown files in configured directories and build the graph."""
    result = ScanResult()
    node_ids: set[str] = set()
    parsed_files: list[tuple[Path, dict]] = []

    # Pass 1: collect all nodes
    for scan_dir in cfg.scan_dirs:
        dir_path = cfg.root / scan_dir.rstrip("/")
        if not dir_path.exists():
            continue
        for md_file in sorted(dir_path.rglob("*.md")):
            sdcoh_meta = _parse_frontmatter(md_file, cfg.root, result)
            if sdcoh_meta is None:
                continue
            node_id = sdcoh_meta.get("id")
            if not node_id:
                rel_path = str(md_file.relative_to(cfg.root))
                result.warnings.append(rel_path)
                continue
            if node_id not in node_ids:
                node_type = node_id.split(":")[0] if ":" in node_id else "unknown"
                mtime = datetime.fromtimestamp(
                    md_file.stat().st_mtime, tz=timezone.utc
                ).isoformat()
                result.nodes.append(
                    {
                        "id": node_id,
                        "type": node_type,
                        "path": str(md_file.relative_to(cfg.root)),
                        "mtime": mtime,
                    }
                )
                node_ids.add(node_id)
            parsed_files.append((md_file, sdcoh_meta))

    # Pass 2: build edges with pattern expansion
    for md_file, sdcoh_meta in parsed_files:
        node_id = sdcoh_meta["id"]
        _build_edges(node_id, sdcoh_meta, node_ids, result)

    return result


def _parse_frontmatter(
    md_file: Path, root: Path, result: ScanResult
) -> dict | None:
    """Parse frontmatter and return sdcoh metadata, or None."""
    rel_path = str(md_file.relative_to(root))
    try:
        post = frontmatter.load(str(md_file))
    except Exception as e:
        result.warnings.append(f"{rel_path} (parse error: {e})")
        return None
    sdcoh_meta = post.metadata.get("sdcoh")
    if sdcoh_meta is None:
        result.warnings.append(rel_path)
        return None
    return sdcoh_meta


def _build_edges(
    node_id: str,
    sdcoh_meta: dict,
    all_node_ids: set[str],
    result: ScanResult,
) -> None:
    """Build edges from depends_on and updates, expanding glob patterns."""
    for dep in sdcoh_meta.get("depends_on", []):
        targets = _expand_pattern(dep["id"], all_node_ids, node_id)
        if not targets and any(c in dep["id"] for c in ("*", "?", "[")):
            result.warnings.append(
                f'{node_id}: pattern "{dep["id"]}" matched 0 nodes'
            )
        for target_id in targets:
            result.edges.append(
                {
                    "source": node_id,
                    "target": target_id,
                    "relation": dep["relation"],
                    "direction": "depends_on",
                }
            )

    for upd in sdcoh_meta.get("updates", []):
        targets = _expand_pattern(upd["id"], all_node_ids, node_id)
        if not targets and any(c in upd["id"] for c in ("*", "?", "[")):
            result.warnings.append(
                f'{node_id}: pattern "{upd["id"]}" matched 0 nodes'
            )
        for target_id in targets:
            result.edges.append(
                {
                    "source": node_id,
                    "target": target_id,
                    "relation": upd["relation"],
                    "direction": "updates",
                }
            )
```

旧 `_process_file` 関数は削除する。

- [ ] **Step 6: Run all tests**

Run: `cd /Users/yoshida/src/work/sdcoh && python -m pytest tests/test_scanner.py -v`
Expected: ALL PASSED（既存6テスト + 新規7テスト）

- [ ] **Step 7: Run full test suite to check for regressions**

Run: `cd /Users/yoshida/src/work/sdcoh && python -m pytest -v`
Expected: ALL PASSED

- [ ] **Step 8: Commit**

```bash
cd /Users/yoshida/src/work/sdcoh && git add src/sdcoh/scanner.py tests/test_scanner.py tests/conftest.py
git commit -m "feat: 2-pass scan with glob pattern expansion in depends_on/updates"
```
