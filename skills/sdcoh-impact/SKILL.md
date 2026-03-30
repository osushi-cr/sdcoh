---
name: sdcoh-impact
description: Show which documents are affected by a file change. Use when user says "影響は？", "何に響く？", "sdcoh impact", or after editing a design document.
argument-hint: "[file-path]"
---

# /sdcoh-impact — Change Impact Analysis

## Prerequisites
- `pip install sdcoh` must be installed
- Run `sdcoh scan` first if `.sdcoh/graph.json` doesn't exist

## Instructions

1. Determine the target file:
   - If the user specifies a file, use that
   - If not, check the most recently edited file in this session

2. Run impact analysis:
```bash
sdcoh impact <file-path> --path <project-root>
```

3. Report the impacted nodes to the user with their relation types
