# Current State

Last updated: 2026-04-27

## This Week (Apr 26 - May 2)

### Cr3Data Craig — BUILD
**Focus:** Alpaca API issues (trader)
- Proof/artifact for the week
- Sort out integration problems
- Publish-ready by end of week (LinkedIn post)

**Also this week:**
- ~~Publish LinkedIn post — SW Dev Bottleneck~~ ✅ **DONE** (2026-04-27)
- Reevaluate the exec presence schema

### Tourno — SHIP
**In Progress (2):**
- **TF-427** — Dashboard "small changes" (needs clarity on what changes)
- **TF-429** — Spinner keeps running with no invitations (UX decision needed)

### CGI — DELIVER
**Active:**
- CrowdStrike (AWS + Azure)
- Kubernetes (AWS + Azure)

### Certs
- **Parked** — no active study this week

---

## Active Priorities (Ongoing)

### Cloud Architect (Day Job — CGI)
- **Company:** CGI
- **Role:** Cloud Architect / Cloud Advisory
- See `state/cloud-architect.md`
- Confluence: `CDS` (CGI Documentation)
- This week: CrowdStrike + Kubernetes for AWS/Azure

### Professional Development
- AWS AI Developer Professional cert — parked
- Azure AI Architect cert — parked
- See `state/professional-dev.md`
- Confluence: `CLOUD` (Cr3Data)

### Tourno (Cr3Data)
- **Company:** Cr3Data
- Q1 2026 sprint active — 2 tickets In Progress, 3 To Do
- Jira project: `TF` | Confluence: `tourno`
- Bitbucket: Cr3Data workspace
- See `memory/project_tourno_jira.md`

## Open Threads

- Delete ticket/page confirmation step not yet added to bots (executes immediately)
- Slack bot system prompt is frozen at startup — state file changes not picked up until restart. `/reload` command not yet implemented.
- Morning briefing via Telegram/Slack not yet set up
- claude-mem parked for future consideration — full stack (worker, Chroma, hooks) deemed too heavy for now
- Bots could use Atlassian MCP via Claude API (not yet implemented)

## Recent Context

- **2026-04-27**: LinkedIn post — SW Dev Bottleneck published ✅
- **2026-04-26**: Added LinkedIn post task (SW Dev Bottleneck) to Cr3Data Craig week
- **2026-04-26**: Added exec presence schema reevaluation to Cr3Data Craig week
- **2026-04-26**: Week scoped — Alpaca API build, TF-427/429 In Progress, CrowdStrike/Kubernetes deliverables
- **2026-04-09**: Fixed bot errors — ANTHROPIC_API_KEY commented out (bots now use Pro plan). allowedTools wildcard fixed. Google Calendar re-authenticated (refresh token — no future expiry).
- Tourno error log automation built: Drive folders created, cron running Tue/Thu 9am, email to support@tourno.fi, files renamed after processing
- Full Groot setup completed 2026-03-17
- Jira, Confluence, Google Workspace, Slack MCP all connected and working
- Telegram and Slack bots running as systemd services

---

*This file is updated by Groot at the end of each session.*
