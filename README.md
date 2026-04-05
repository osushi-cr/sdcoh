# sdcoh — Story Design Coherence

[![PyPI](https://img.shields.io/pypi/v/sdcoh?style=flat-square&color=blue&v=2)](https://pypi.org/project/sdcoh/)
[![Python](https://img.shields.io/pypi/pyversions/sdcoh?style=flat-square&v=2)](https://pypi.org/project/sdcoh/)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)
[![Stars](https://img.shields.io/github/stars/ysttsu/sdcoh?style=flat-square)](https://github.com/ysttsu/sdcoh/stargazers)

[日本語版 README](README.ja.md)

**Manage dependency graphs between story design documents.** Detect change impact and stale downstream files.

When writing novels with AI, you end up with dozens of interconnected design documents: character sheets, beat sheets, foreshadowing ledgers, style guides, briefs, and episode drafts. Change one, and you need to update five others. Forget one, and your story has inconsistencies.

sdcoh makes these dependencies explicit and trackable.

## The Problem

```
You update the character sheet...
  → but forget to update the beat sheet
  → which means the brief is based on stale info
  → which means the AI writes the episode with wrong details
  → which means you spend an hour finding why the draft feels off
```

## The Solution

```bash
$ sdcoh status

⚠️ Updates needed (3):
  design:continuity      last updated 3/15 ← episode:ep07 updated 3/28
  design:expression-log  last updated 3/10 ← episode:ep05 updated 3/27
  brief:ep08             last updated 3/13 ← design:beat-sheet updated 3/25

✅ In sync (12)
```

## Install

```bash
pip install sdcoh
```

Optional OpenViking integration:
```bash
pip install sdcoh[openviking]
```

## Quick Start

### 1. Initialize your project

```bash
cd your-novel-project/
sdcoh init --name "My Novel" --alias my-novel
```

This creates `sdcoh.yml` and `.sdcoh/` directory.

### 2. Declare dependencies in `sdcoh.yml`

Starting with v0.2, dependencies are declared centrally in `sdcoh.yml` using patterns. **No frontmatter needed in your Markdown files.**

```yaml
rules:
  - name: "design informs episodes"
    from: "design/*.md"
    to: "drafts/ep*.md"
    relation: informs

  - name: "brief feeds episode"
    from: "briefs/{ep}-brief.md"
    to: "drafts/{ep}.md"
    relation: feeds
```

Edge semantic: `from → to` means **"when `from` changes, `to` becomes stale."**

### 3. Scan and check

```bash
sdcoh scan        # Build the dependency graph
sdcoh graph       # Visualize it
sdcoh validate    # Check for broken references
sdcoh status      # Find stale documents
```

### 4. Check impact before editing

```bash
$ sdcoh impact design/characters.md

Affected (4):
  🟡 design:beat-sheet          ← derives_from
  🟡 design:foreshadowing       ← references
  🟡 brief:ep02                 ← references
  🟡 episode:ep01               ← implements
```

## Project Config (sdcoh.yml)

```yaml
project:
  name: "My Novel"
  alias: "my-novel"

# Directories to scan, each with a node type
scan:
  - { path: "design/",  type: "design" }
  - { path: "drafts/",  type: "episode" }
  - { path: "briefs/",  type: "brief" }
  - { path: "reviews/", type: "review" }

# Node types with layer hierarchy (lower = upstream)
node_types:
  research: { layer: -1 }  # Most upstream
  design:   { layer: 0 }
  brief:    { layer: 1 }
  episode:  { layer: 2 }
  review:   { layer: 3 }   # Most downstream

# Dependency rules: when `from` changes, `to` is stale
rules:
  - name: "design informs episodes"
    from: "design/*.md"
    to: "drafts/ep*.md"
    relation: informs
  - name: "brief feeds episode"
    from: "briefs/{ep}-brief.md"
    to: "drafts/{ep}.md"
    relation: feeds

# Optional: OpenViking semantic search integration
openviking:
  enabled: false
  endpoint: "http://localhost:1933"
  auto_register: true
```

Node IDs are auto-generated as `{type}:{basename}` (e.g. `design/characters.md` → `design:characters`).

## Default Directory Structure

```
novel-project/
├── sdcoh.yml        # Project config
├── design/          # Character sheets, beat sheets, style guides, etc.
├── drafts/          # Episode manuscripts
├── briefs/          # Writing briefs for AI agents
├── reviews/         # Review results
├── research/        # Research materials
└── docs/            # Workflow documentation
```

## Rule Syntax

### Pattern tokens

| Token | Meaning |
|-------|---------|
| `*` | Any string (no `/`) |
| `?` | Single char (no `/`) |
| `{name}` | Named capture (non-greedy, no `/`) — bind once in `from`, substitute in `to` |
| literal | Matches exactly (regex metacharacters are escaped) |

### Examples

**Fan-out** — one file to many:
```yaml
- name: "design informs all episodes"
  from: "design/*.md"
  to: "drafts/ep*.md"
  relation: informs
```

**1-to-1 pairing** — match by shared capture:
```yaml
- name: "brief feeds episode"
  from: "briefs/{ep}-brief.md"
  to: "drafts/{ep}.md"
  relation: feeds
# briefs/ep01-brief.md → drafts/ep01.md
```

**Multiple variants** — any suffix after captured prefix:
```yaml
- name: "any brief revision feeds episode"
  from: "briefs/{ep}-*.md"
  to: "drafts/{ep}.md"
  relation: feeds
# briefs/ep01-kubota-brief.md → drafts/ep01.md
# briefs/ep01-revision2-brief.md → drafts/ep01.md
```

**Reverse flow** — episodes update review logs:
```yaml
- name: "episode updates expression log"
  from: "drafts/ep*.md"
  to: "design/expression-log.md"
  relation: extracts_from
```

### Validation

sdcoh catches common mistakes at scan time:

- **Node ID collision** — two files producing the same `{type}:{basename}` (e.g. from nested subdirectories)
- **Undefined placeholder** — `to: "drafts/{missing}.md"` when `from` has no `{missing}` capture
- **Relation conflict** — two rules producing the same edge with different relations
- **Self-loop** — a file matching both sides is silently excluded
- **Zero matches** — a rule that produces no edges warns during `sdcoh scan`

## CLI Reference

| Command | Description |
|---------|-------------|
| `sdcoh init` | Initialize project (`sdcoh.yml` + `.sdcoh/`) |
| `sdcoh scan` | Apply rules, build dependency graph |
| `sdcoh impact <path>` | Show what's affected by changing a file |
| `sdcoh graph` | Display dependency tree |
| `sdcoh validate` | Check for broken refs, cycles, orphans |
| `sdcoh status` | Find stale downstream documents |

### Options

```
sdcoh scan --quiet          # Minimal output (for hooks)
sdcoh scan --warn           # List rules that produced no edges
sdcoh impact <path> --depth N  # Limit traversal depth
sdcoh status --warn-only    # Only output if warnings exist
sdcoh status --json         # JSON output
```

## Claude Code Integration

### Install as Plugin

```bash
/plugin marketplace add ysttsu/sdcoh
/plugin install sdcoh@sdcoh
```

### Skills

| Skill | Trigger | Action |
|-------|---------|--------|
| `/sdcoh-scan` | "scan", "graph update" | `sdcoh scan` + `sdcoh validate` |
| `/sdcoh-impact` | "what's affected?" | `sdcoh impact` on recent file |
| `/sdcoh-status` | "stale check" | `sdcoh status` |

### PostToolUse Hook (auto-scan on edit)

Add to `.claude/settings.json`:

```jsonc
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write|Edit",
      "if": "Write(*/design/*)|Edit(*/design/*)",
      "hooks": [{
        "type": "command",
        "command": "sdcoh scan --quiet && sdcoh status --warn-only",
        "timeout": 10
      }]
    }]
  }
}
```

## Background: Why This Exists

This tool was inspired by [CoDD (Coherence-Driven Development)](https://zenn.dev/shio_shoppaize/articles/shogun-codd-coherence), which manages coherence between software design documents. sdcoh adapts the same principle for fiction writing workflows, where AI-assisted novel projects can accumulate 20-30+ interconnected design documents.

Built as part of an AI-assisted novel writing workflow where the author acts as "director" and AI agents handle drafting. The dependency graph ensures that when a design decision changes, all downstream documents are flagged for review — preventing the subtle inconsistencies that plague long-form fiction.

## License

MIT
