---
name: tourno_jira_sprint
description: Tourno Jira project metadata — tickets are fetched live on /start, not stored here
type: project
originSessionId: 9ebe1cab-7bb4-4dc9-acfa-d816570be088
---
# Tourno — Jira Project

Project key: `TF` | Board ID: `6` | Instance: `https://cr3data.atlassian.net`

Ticket data is fetched live at `/start` using JQL: `project = TF AND sprint in openSprints() ORDER BY status ASC`

Do not rely on this file for ticket status — always query Jira directly.

**Why:** Static ticket snapshots go stale quickly. Live fetch ensures the briefing reflects actual sprint state.
**How to apply:** When discussing Tourno work, use the live data from the most recent `/start` or query Jira directly.
