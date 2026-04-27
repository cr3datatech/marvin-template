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

---

## Daily Briefing

| Shortcut | Action |
|----------|--------|
| `daily` | Pull open items across all areas (Cr3Data, Cloud/CGI, Certs) + today's calendar and present as unified briefing |

---

## Health

| Shortcut | Action |
|----------|--------|
| `health` | Read `memory/health_craig.md`, get today's date/day, identify if it's a HYROX day, training day, or rest day, and print today's eating plan summary |
