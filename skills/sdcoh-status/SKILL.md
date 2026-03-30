---
name: sdcoh-status
description: Check for stale downstream documents that need updating. Use when user says "更新漏れ", "整合性チェック", "sdcoh status", or before starting a writing session.
---

# /sdcoh-status — Staleness Check

## Prerequisites
- `pip install sdcoh` must be installed
- `sdcoh.yml` must exist in the project root

## Instructions

1. Run status check:
```bash
sdcoh status --path <project-root>
```

2. Report results:
   - List stale documents with their cause
   - Suggest which documents to update first (upstream before downstream)
