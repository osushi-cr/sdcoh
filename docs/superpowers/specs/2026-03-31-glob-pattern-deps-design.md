# Glob Pattern Dependencies

## Summary

`depends_on` / `updates` の ID 指定で fnmatch glob パターンをサポートする。
スキャン時にパターンを展開し、`graph.json` には具体的エッジのみ保存する。

## Motivation

現状、各ファイルのfrontmatterで依存先を1つずつ明示指定する必要がある。
設計書が増えると原稿側のfrontmatterが肥大化し、メンテが面倒になる。

glob パターンで `design:*` のようにまとめて指定できれば：
- 設計書側で下流を一括カバーできる
- 原稿側のfrontmatterがほぼ空になる
- 例外的な依存だけ原稿に追記すればよい

## Design

### パターン判定

`*`, `?`, `[` のいずれかを含む ID をパターンとして扱う。

### 変更箇所: `scanner.py` のみ

新規関数 `_expand_pattern()` を追加：

```python
from fnmatch import fnmatch

def _expand_pattern(
    pattern: str,
    all_node_ids: set[str],
    self_id: str,
) -> list[str]:
    """Expand a glob pattern against known node IDs.
    
    Returns matched IDs (excluding self_id).
    If pattern contains no glob chars, returns [pattern] as-is.
    """
    if not any(c in pattern for c in ("*", "?", "[")):
        return [pattern]
    
    matched = sorted(
        nid for nid in all_node_ids
        if fnmatch(nid, pattern) and nid != self_id
    )
    return matched
```

`_process_file()` の `depends_on` / `updates` ループで `_expand_pattern()` を呼び、
マッチした各IDに対してエッジを生成する。

### スキャン順序の変更

現状は1パスで処理しているが、パターン展開には全ノードIDが必要。
**2パス構成に変更する：**

1. Pass 1: 全ファイルからノードを収集（`node_ids` 確定）
2. Pass 2: 全ファイルからエッジを構築（パターン展開あり）

### Warning

パターンが0件マッチの場合、`result.warnings` に追加する。

### 下流への影響

`graph.json` には展開済みエッジのみ保存されるため、
`graph.py`, `status.py`, `cli.py` は変更不要。

## Examples

```yaml
# 設計書側: 全エピソードを下流として指定
sdcoh:
  id: "design:beat-sheet"
  updates:
    - id: "episode:*"
      relation: triggers_update

# 原稿側: 例外的な依存だけ追記
sdcoh:
  id: "episode:ep05"
  depends_on:
    - id: "design:foreshadow-ledger"
      relation: references
```

## Test Plan

- パターンなしの既存動作が壊れないこと
- `design:*` が全 design ノードにマッチすること
- 自分自身がマッチから除外されること
- 0件マッチで warning が出ること
- `depends_on` と `updates` 両方でパターンが動くこと
- 2パススキャンで既存テストが全て通ること
