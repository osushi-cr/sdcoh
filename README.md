# sdcoh — Story Design Coherence

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

### 2. Add frontmatter to your documents

Add YAML frontmatter to each Markdown file declaring its dependencies:

```yaml
---
sdcoh:
  id: "design:beat-sheet"
  depends_on:
    - id: "design:characters"
      relation: derives_from
---

# Beat Sheet
...
```

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

# Directories to scan for Markdown files
scan:
  - design/
  - drafts/
  - briefs/
  - reviews/
  - research/
  - docs/

# Node types with layer hierarchy (lower = upstream)
node_types:
  research: { layer: -1 }  # Most upstream
  design:   { layer: 0 }
  brief:    { layer: 1 }
  episode:  { layer: 2 }
  review:   { layer: 3 }   # Most downstream

# Optional: OpenViking semantic search integration
openviking:
  enabled: false
  endpoint: "http://localhost:1933"
  auto_register: true
```

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

## Frontmatter Spec

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Node ID in `{type}:{name}` format |
| `depends_on` | No | Upstream dependencies (if they change, I'm affected) |
| `updates` | No | Downstream targets (if I change, they need updating) |

### Relation Types

| Relation | Meaning | Example |
|----------|---------|---------|
| `derives_from` | Derived from this document | beat sheet ← characters |
| `implements` | Implements this design | episode ← beat sheet |
| `constrained_by` | Must follow these rules | episode ← style guide |
| `references` | References this document | brief ← foreshadowing ledger |
| `extracts_from` | Extracted from this source | expression log ← episode |
| `triggers_update` | Change triggers update | continuity ← episode |

### Bidirectional Dependencies

Some relationships go both ways. Use `depends_on` for upstream and `updates` for downstream:

```yaml
# episode extracts expressions into the log
# drafts/ep01.md
sdcoh:
  id: "episode:ep01"
  updates:
    - id: "design:expression-log"
      relation: extracts_from

# the log is referenced by briefs to avoid repetition
# design/expression-log.md
sdcoh:
  id: "design:expression-log"
  depends_on:
    - id: "episode:ep01"
      relation: extracts_from
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `sdcoh init` | Initialize project (`sdcoh.yml` + `.sdcoh/`) |
| `sdcoh scan` | Parse frontmatter, build dependency graph |
| `sdcoh impact <path>` | Show what's affected by changing a file |
| `sdcoh graph` | Display dependency tree |
| `sdcoh validate` | Check for broken refs, cycles, orphans |
| `sdcoh status` | Find stale downstream documents |

### Options

```
sdcoh scan --quiet          # Minimal output (for hooks)
sdcoh scan --warn           # List files without frontmatter
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
