# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] - 2026-04-05

### ⚠️ Breaking Changes

- **Zero-frontmatter mode** — 依存関係を `sdcoh.yml` の `rules:` セクションに宣言する形式に全面移行。各 Markdown の `sdcoh:` frontmatter は廃止。
- **`scan:` フォーマット変更** — リストの文字列 (`- design/`) から dict (`- { path: "design/", type: "design" }`) へ。
- **エッジの `direction` 削除** — `depends_on` / `updates` の2方向を廃止、`source → target` の単一方向に統一 ("source が変わると target が陳腐化する")。
- **Graph JSON `version: 2.0`** — 旧 cache (`.sdcoh/graph.json` v1.x) は自動的に再生成される。

### Added

- `rules:` セクションでパターンベースの依存関係を宣言
  - `{name}` キャプチャ変数で1:1ペアリング (例: `briefs/{ep}-brief.md` → `drafts/{ep}.md`)
  - `*` グロブで fan-out (例: `design/*.md` → `drafts/ep*.md`)
- scanner で4種の検証追加: Node ID 衝突、未定義プレースホルダ、relation 衝突、自己ループ除外
- `ConfigFormatError` / `ScannerError` を新設

### Removed

- `python-frontmatter` 依存
- 旧 `_expand_pattern()` (fnmatch ベースのノードID展開)

### Migration

旧 `sdcoh.yml`:
```yaml
scan:
  - design/
  - drafts/
```

新 `sdcoh.yml`:
```yaml
scan:
  - { path: "design/", type: "design" }
  - { path: "drafts/", type: "episode" }
rules:
  - name: "design informs episodes"
    from: "design/*.md"
    to: "drafts/ep*.md"
    relation: informs
```

Markdown の `sdcoh:` frontmatter は全削除してOK。

## [0.1.1] - 2026-03-31

### Added

- **Glob pattern support in `depends_on` and `updates`** — Use fnmatch-style patterns like `episode:*` or `design:voice-*` to declare dependencies on multiple nodes at once. Patterns are expanded at scan time; `graph.json` contains only concrete edges, so downstream tools require no changes.
- New `_expand_pattern()` function using Python's `fnmatch` (stdlib, no new dependencies).
- Warning when a glob pattern matches zero nodes, helping catch typos early.

### Changed

- Scanner refactored from 1-pass to 2-pass architecture: Pass 1 collects all node IDs, Pass 2 builds edges with pattern expansion. This is necessary because glob patterns need the full set of node IDs to resolve against.
- Internal functions reorganized: `_process_file()` replaced by `_parse_frontmatter()` and `_build_edges()` for clearer separation of concerns.

## [0.1.0] - 2026-03-30

Initial release.

### Added

- `sdcoh.yml` configuration with scan directories and node types.
- Frontmatter-based dependency declarations (`depends_on`, `updates`) with 6 relation types.
- CLI commands: `init`, `scan`, `impact`, `graph`, `validate`, `status`.
- Graph operations: impact analysis, cycle detection, orphan detection, tree display, reference validation.
- Status checker: detect stale downstream documents via mtime comparison.
- OpenViking integration: auto-register documents and semantic search.
- Claude Code skills for `sdcoh-scan`, `sdcoh-impact`, `sdcoh-status`.
