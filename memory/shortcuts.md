---
name: shortcuts
description: User-defined shortcut commands for Groot
type: memory
---

# Shortcuts

Shortcuts are trigger words or phrases. Append `/` to trigger via the bots (e.g. `daily/`).

---

## Meta

| Shortcut | Action |
|----------|--------|
| `shortcuts` | Read `memory/shortcuts.md` and present all available shortcuts in a clean list with their descriptions. |

---

## Daily Briefing

| Shortcut | Action |
|----------|--------|
| `daily` | Read `state/current.md`, `state/goals.md`, and `memory/health.md`. Get today's date and day. Also call `calendar_list_events` with days_ahead=7 to fetch upcoming calendar events. Present: (1) this week's focus areas from current.md (Cr3Data, Tourno, CGI — everything before the first ---); (2) cert goals from goals.md — always show each cert with its current status even if parked; (3) today's meal plan from health.md based on the day type; (4) upcoming calendar events for the next 7 days. Keep it concise. |

---

## Health

| Shortcut | Action |
|----------|--------|
| `health` | Read `memory/health.md`, get today's date/day, identify if it's a HYROX day, training day, or rest day, and print today's eating plan summary. |

---

## Cr3Data

| Shortcut | Action |
|----------|--------|
| `cr3data` | Pull a live snapshot of all Cr3Data-related work: Tourno Jira (TF) active tickets by status (To Do + In Progress), recent Confluence pages in the tourno space, open threads from state files related to Cr3Data, and call `calendar_list_events` with days_ahead=7 to show upcoming calendar events for the next 7 days. |

---

## Tourno Pipelines

Repo: `tourno` | Branch: `master` (only branch)

| Shortcut | Pipeline Name |
|----------|--------------|
| `run tourno pipeline test` | `manual-deploy-test` |
| `run tourno pipeline prod` | `manual-deploy-production` |
| `run tourno pipeline both` | `manual-deploy-both` |

**Usage:** When Craig uses any of these shortcuts, immediately run the corresponding pipeline on `master` — no need to ask for confirmation.
