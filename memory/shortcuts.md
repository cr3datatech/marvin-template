---
name: shortcuts
description: User-defined shortcut commands for Groot
type: memory
---

# Shortcuts

## Tourno Pipelines

Repo: `tourno` | Branch: `master` (only branch)

| Shortcut | Pipeline Name |
|----------|--------------|
| `run tourno pipeline test` | `manual-deploy-test` |
| `run tourno pipeline prod` | `manual-deploy-production` |
| `run tourno pipeline both` | `manual-deploy-both` |

**Usage:** When Craig uses any of these shortcuts, immediately run the corresponding pipeline on `master` — no need to ask for confirmation.
