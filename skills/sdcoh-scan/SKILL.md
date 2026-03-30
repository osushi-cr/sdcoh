---
name: sdcoh-scan
description: Scan story design documents and rebuild the dependency graph. Use when user says "スキャン", "グラフ更新", "sdcoh scan", or after updating design documents.
---

# /sdcoh-scan — Scan & Validate Dependency Graph

## Prerequisites
- `pip install sdcoh` must be installed
- `sdcoh.yml` must exist in the project root

## Instructions

1. Run scan:
```bash
sdcoh scan --path <project-root>
```

2. Run validation:
```bash
sdcoh validate --path <project-root>
```

3. Report results to user:
   - Number of nodes and edges
   - Any validation errors (broken references, cycles)
   - Any orphaned nodes
   - Files without frontmatter
