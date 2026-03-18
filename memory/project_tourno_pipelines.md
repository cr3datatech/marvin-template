---
name: tourno_pipelines
description: Tourno Bitbucket pipeline shortcuts and behaviour rules
type: project
---

# Tourno — Pipeline Shortcuts

Repo: `tourno` | Bitbucket workspace: `cr3data`

## Shortcuts

| Shortcut phrase | Pipeline name |
|----------------|---------------|
| `run tourno pipeline test` | `manual-deploy-test` |
| `run tourno pipeline prod` | `manual-deploy-production` |
| `run tourno pipeline both` | `manual-deploy-both` |

## Behaviour Rules

- When a shortcut is used, always ask **"Which branch?"** before firing — even if only one branch exists, confirm it with the user.
- Available branches should be listed so the user can pick or confirm.
- Only trigger the pipeline after branch is confirmed.

## Available Pipelines (full list)

- `manual-deploy-test`
- `manual-deploy-production`
- `manual-deploy-both`
- `manual-full-sync-test`
- `manual-full-sync-production`
