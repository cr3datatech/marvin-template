# Tourno Error Log Management — AI Agent Portfolio Piece

**Date:** 2026-04-16  
**Status:** Portfolio-ready, needs public release + documentation

---

## The Insight

Craig has built a production agentic system but hasn't positioned it as one. This is the headline portfolio piece for AI credibility.

---

## What It Actually Is

A **scheduled agentic workflow with human-in-the-loop approval gates**.

| Component | The Term | What It Does |
|-----------|----------|--------------|
| Cron-triggered execution | **Scheduled agentic workflow** | Runs weekly autonomously |
| FTP download + parse | **Tool use / data ingestion** | Fetches error logs from VPS |
| Unsolved errors list | **Persistent agent memory** | Tracks errors agent couldn't fix |
| Deduplication logic | **Pre-processing / context filtering** | Removes duplicates before processing |
| Claude Sonnet fixes errors | **Agentic loop with LLM reasoning** | Error by error, autonomous |
| Git clone → branch → commit → push | **Tool-augmented agent (code execution)** | Agent modifies codebase directly |
| FTP back with cleaned logs | **State mutation + feedback loop** | Writes state back to source |
| PR + Slack/Telegram notification | **Human-in-the-loop checkpoint** | Pause point for human review |
| Manual review → merge → test → deploy | **HITL approval gate** | Human validation before production |

---

## Full Technical Architecture

### Pipeline (9 stages)

```
1. DOWNLOAD
   FtpClient downloads error_log from frontend and backend via FTPS

2. PARSE & DEDUPLICATE
   ErrorLogParser converts raw log lines into structured entries
   Deduplicator removes duplicate errors (same type+file+line = one entry)
   UnresolvedLog filters out errors already known to be unfixable (skip retries)

3. JIRA TICKET
   JiraClient creates one Bug ticket listing all new errors

4. GIT BRANCH
   GitClient checks the workspace directory:
     - First run: clones the application repo fresh into workspace/
     - Subsequent runs: fetch origin, checkout master, reset --hard to origin/master
       (discards any local changes and forces the local branch to match remote)
       then deletes all stale local branches
   Creates a new fix branch: {ticket-id}/fix-auto-fix-{date}

5. AI FIX LOOP  (one iteration per unique file)
   ClaudeFixAgent runs Claude CLI with Read+Edit tools
   If Claude edits files → GitClient commits them (one commit per file)
   JiraClient posts a comment with the diff + revert link for that commit

6. TESTS
   TestRunner runs PHPUnit if the repo has tests
   If tests fail → branch is NOT pushed

7. PUBLISH
   GitClient pushes the fix branch
   BitbucketClient creates a PR targeting master

8. NOTIFY
   Notifier sends fix summary + Jira link + PR URL to Slack and Telegram

9. CLEANUP
   Unfixed errors saved to data/unresolved/{source}.json
   Raw error log uploaded back to FTP server (server reflects only what's still broken)
```

### Key Components

| Class | Responsibility |
|-------|----------------|
| `FtpClient` | FTPS download/upload of error log files |
| `ErrorLogParser` | Raw log lines → structured entries |
| `Deduplicator` | same type+file+line = one entry |
| `UnresolvedLog` | Skip known-unfixable errors (persistent memory) |
| `JiraClient` | Create bug ticket, post per-commit comments with diff |
| `GitClient` | Clone, branch, commit, push (workspace management) |
| `ClaudeFixAgent` | LLM reasoning loop — runs Claude CLI with Read+Edit tools |
| `TestRunner` | PHPUnit — gate before publishing (fail = no push) |
| `BitbucketClient` | Create PR targeting master |
| `Notifier` | Slack + Telegram summary message |

---

## Why This Matters

This is **not** a hobby project. This is:
- ✅ Production-grade agentic workflow
- ✅ Real error handling and persistent memory (unresolved log)
- ✅ Autonomous tool use (Git, FTP, GitHub API, Jira)
- ✅ Test-gated publishing (fail fast before bad code goes public)
- ✅ Human-in-the-loop safety gate (HITL PR review)
- ✅ Measurable business value (bugs fixed autonomously)
- ✅ Runs weekly, proven stability

---

## The Jargon Craig Was Missing

Craig thought he needed to learn jargon first. The truth: **he already built the concepts**. He just needs to name them.

- **Memory** → `UnresolvedLog` (persistent state across runs)
- **Tool use** → FTP, Git, Jira, Bitbucket, PHPUnit
- **Agentic loop** → per-file fix iteration via `ClaudeFixAgent`
- **Human-in-the-loop** → PR review gate before merge
- **State management** → cleaned logs sent back via FTP
- **Fail-safe / guardrail** → test gate (no push if PHPUnit fails)
- **Feedback loop** → Jira comment per commit with diff + revert link

---

## Making It Generic (To-Do Before Going Public)

Everything tourno-specific needs to move to `.env`. Likely variables:

**FTP / Hosting**
- `FTP_HOST`, `FTP_USER`, `FTP_PASSWORD`
- `FTP_FRONTEND_LOG_PATH`, `FTP_BACKEND_LOG_PATH`

**Source Control**
- `GITHUB_TOKEN` / `BITBUCKET_TOKEN`
- `REPO_OWNER`, `REPO_NAME`, `BASE_BRANCH`

**AI**
- `ANTHROPIC_API_KEY`
- `CLAUDE_MODEL`

**Jira**
- `JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`
- `JIRA_PROJECT_KEY`

**Notifications**
- `SLACK_WEBHOOK_URL` or `SLACK_BOT_TOKEN`, `SLACK_CHANNEL`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

**App Config**
- `WORKSPACE_DIR`
- `UNRESOLVED_LOG_PATH`
- `TEST_COMMAND` (e.g. `phpunit`, or make it pluggable)

Deliverables:
- [ ] `.env.example` with all keys as placeholders (goes in git)
- [ ] `.env` with real values (in `.gitignore`)
- [ ] Replace all hardcoded values with `os.getenv()` / equivalent
- [ ] Startup validation: fail fast if required vars are missing

---

## Portfolio Strategy (Next 8 Weeks)

### Week 1–2: Make It Public
- [ ] Make codebase generic (`.env` refactor)
- [ ] Write README with architecture diagram
- [ ] Draft LinkedIn post
- [ ] Make repo public

### Week 3–4: Add RAG System
- Build RAG on Tourno docs or CGI knowledge base
- Public repo + LinkedIn post on RAG patterns

### Week 5–6: Add Evaluation Layer
- Evaluate quality of AI-fixed errors (accuracy metrics)
- LinkedIn: "How I know my AI isn't lying to me"

### Week 7–8: System Design Doc
- Full architecture doc for a real problem (Confluence + LinkedIn)

---

## Action Items

1. **Next:** Refactor all hardcoded values into `.env` / `.env.example`
2. **Then:** Write README with architecture diagram + setup guide
3. **Then:** Draft LinkedIn post (Craig wants this)
4. **Result:** Public portfolio piece that opens AI conversations without job hunting

---

## Why This Lands Conversations

- **Specific:** Not "I work with AI," but "here's a real system running in production"
- **Named patterns:** Agentic workflow, tool use, HITL, fail-safe gates, persistent memory
- **Measurable impact:** "Fixed X bugs autonomously per week, 0 bad deploys"
- **Complete loop:** Ingestion → parse → deduplicate → AI fix → test gate → PR → human review → production

This is more impressive than most "AI engineer" portfolios because it's **real, deployed, and responsible**.
