# Current State

Last updated: 2026-05-11

## This Week (May 11 - May 17)

### Certs — STUDY
**Focus:** AWS CloudOps Engineer - Associate (exam May 27)
- Study plan: 18 × 2-hour sessions across May 11–27
- Week 1 target: S3 (EC2 remaining 16 lessons) + S4 (AMI, 9 lessons) + S5 (SSM, 20 lessons) — ~6h
- Currently: S3 in progress (2/18 done)

### CGI — DELIVER
**Active:**
- CrowdStrike (AWS + Azure)
- Kubernetes (AWS + Azure)

### Tourno — SHIP
**Active Sprint (Non-Closed):**
- **TF-441** — Use Playwright to test Tourno flows (To Do)
- **TF-407** — Marketing tourno (To Do)

---

## Active Priorities (Ongoing)

### Cloud Architect (Day Job — CGI)
- **Company:** CGI
- **Role:** Cloud Architect / Cloud Advisory
- See `state/cloud-architect.md`
- Confluence: `CDS` (CGI Documentation)
- This week: CrowdStrike + Kubernetes for AWS/Azure

### Professional Development
- **AWS CloudOps Engineer - Associate** — ACTIVE, exam May 27
- AWS AI Developer Professional cert — parked
- Azure AI Architect cert — parked
- See `state/professional-dev.md` / `state/cert-cloudops-associate.md`
- Confluence: `CLOUD` (Cr3Data)

### Tourno (Cr3Data)
- **Company:** Cr3Data
- Q1 2026 sprint active — 2 tickets To Do (TF-441, TF-407)
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

- **2026-05-11**: CloudOps study plan locked in — 9-week schedule, 18 sessions, exam booked May 27 @ 07:00
- **2026-04-27**: LinkedIn post — SW Dev Bottleneck published ✅
- **2026-04-26**: Added LinkedIn post task (SW Dev Bottleneck) to Cr3Data Craig week
- **2026-04-26**: Added exec presence schema reevaluation to Cr3Data Craig week
- **2026-04-26**: Week scoped — Alpaca API build, TF-427/429 now closed, CrowdStrike/Kubernetes deliverables
- **2026-04-09**: Fixed bot errors — ANTHROPIC_API_KEY commented out (bots now use Pro plan). allowedTools wildcard fixed. Google Calendar re-authenticated (refresh token — no future expiry).
- Tourno error log automation built: Drive folders created, cron running Tue/Thu 9am, email to support@tourno.fi, files renamed after processing
- Full Groot setup completed 2026-03-17
- Jira, Confluence, Google Workspace, Slack MCP all connected and working
- Telegram and Slack bots running as systemd services

---

*This file is updated by Groot at the end of each session.*
