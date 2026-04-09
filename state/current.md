# Current State

Last updated: 2026-04-09

## Active Priorities

### Cloud Architect (Day Job — CGI)
- **Company:** CGI
- **Role:** Cloud Architect / Cloud Advisory
- See `state/cloud-architect.md`
- Confluence: `CDS` (CGI Documentation)

### Professional Development
- AWS AI Developer Professional cert — in progress
- Azure AI Architect cert — in progress
- See `state/professional-dev.md`
- Confluence: `CLOUD` (Cr3Data)

### Tourno (Cr3Data)
- **Company:** Cr3Data
- Q1 2026 sprint active — 5 tickets To Do
- Jira project: `TF` | Confluence: `tourno`
- Bitbucket: Cr3Data workspace
- See `memory/project_tourno_jira.md`

## Open Threads

- Delete ticket/page confirmation step not yet added to bots (executes immediately)
- Slack bot system prompt is frozen at startup — state file changes not picked up until restart. `/reload` command not yet implemented.
- Morning briefing via Telegram/Slack not yet set up
- claude-mem parked for future consideration — full stack (worker, Chroma, hooks) deemed too heavy for now
- Persona system live — needs real-world testing across all 6 personas
- More bot shortcuts to define (`cp` = change persona; others TBD)
- Bots could use Atlassian MCP via Claude API (not yet implemented)

## Recent Context

- **2026-04-09**: Persona system added to both bots — 6 personas (CGI, CR3Data, Family, Gym, Vacation, Misc). `cp` shortcut live.
- **2026-04-09**: Fixed bot errors — ANTHROPIC_API_KEY commented out (bots now use Pro plan). allowedTools wildcard fixed. Google Calendar re-authenticated (refresh token — no future expiry).
- Tourno error log automation built: Drive folders created, cron running Tue/Thu 9am, email to support@tourno.fi, files renamed after processing
- Full Groot setup completed 2026-03-17
- Jira, Confluence, Google Workspace, Slack MCP all connected and working
- Telegram and Slack bots running as systemd services

---

*This file is updated by Groot at the end of each session.*
