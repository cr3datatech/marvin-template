# Groot - Your AI Chief of Staff

**Groot** (formerly MARVIN) = Your personal AI assistant

An AI assistant that remembers your conversations, tracks your goals, and helps you stay organized. Like having a personal chief of staff who never forgets anything.

## Why Groot?

Groot extends Claude Code with capabilities designed for getting things done:

- **Session continuity** - Pick up where you left off, even days later. Every conversation builds on the last.
- **Goal tracking** - Set work and personal goals, Groot monitors progress and nudges you forward.
- **Tool integrations** - Connect to Google Workspace, Microsoft 365, Atlassian, Slack, Linear, Notion, Telegram, and more.
- **Extensibility** - Add commands, agents, and skills tailored to your workflow. Create new capabilities with simple markdown files.
- **Thought partner** - Groot pushes back on weak ideas, asks probing questions, and helps you think through decisions. Not just a yes-man.

## Quick Start with Claude Code

1. Clone this repository (or your fork):
   ```bash
   git clone https://github.com/cr3datatech/marvin-template.git
   cd marvin-template
   ```

2. Open in Claude Code:
   ```bash
   claude
   ```

3. Ask Groot to help you set up:
   > "Help me set up Groot"

That's it. Groot walks you through the rest: your profile, goals, workspace location, and optional integrations (including Atlassian for Jira/Confluence).

## Getting Started with GitHub Copilot CLI

Want to use Copilot CLI to set up Groot quickly? Here's how:

### Prerequisites

- [GitHub Copilot CLI](https://cli.github.com/) installed and authenticated

### Quick Setup

Use these Copilot commands to get started:

```bash
# Navigate to your projects directory
gh copilot suggest "clone marvin template repository"

# Run the setup script
gh copilot suggest "run setup script for groot"

# Start Groot
gh copilot suggest "start groot AI assistant"
```

The `.marvin/setup.sh` script handles the complete installation: prerequisites, workspace creation, profile setup, and shell aliases. Just follow the prompts to configure your AI Chief of Staff.

For additional integrations (Google Workspace, Atlassian, Slack, etc.), use:

```bash
gh copilot suggest "configure marvin integrations"
```

## What You Get

### Daily Workflow

Start your day with `/start` for a briefing: priorities, deadlines, progress toward goals. Work naturally throughout the day, Groot remembers everything. End with `/end` to save context for next time.

Between sessions, `/update` saves progress without ending. `/sync` pulls new features from this template into your workspace.

### Commands

| Command | What It Does |
|---------|--------------|
| `/start` | Start your day with a briefing |
| `/end` | End session and save everything |
| `/update` | Quick checkpoint (save progress) |
| `/report` | Generate a weekly summary |
| `/commit` | Review and commit git changes |
| `/code` | Open Groot in your IDE |
| `/status` | Check integration & workspace health |
| `/sync` | Get updates from the template |
| `/help` | Show all commands and integrations |

### Integrations

Groot connects to tools you already use:

| Integration | What It Provides |
|-------------|------------------|
| [Google Workspace](.marvin/integrations/google-workspace/) | Gmail, Calendar (full CRUD), Drive, Photos |
| [Microsoft 365](.marvin/integrations/ms365/) | Outlook, Calendar, OneDrive, Teams |
| [Atlassian](.marvin/integrations/atlassian/) | Jira (tickets, sprints, epics, comments), Confluence (pages, search) |
| [Slack](.marvin/integrations/slack/) | Channel monitoring, posting |
| [Linear](.marvin/integrations/linear/) | Issue tracking |
| [Notion](.marvin/integrations/notion/) | Page reading, database queries |
| [Telegram](.marvin/integrations/telegram/) | Chat with Groot from your phone |
| [Parallel Search](.marvin/integrations/parallel-search/) | Web search capabilities |
| Bitbucket | Repos, branches, PRs, pipelines |
| GitHub | Repos, create repos |

Each integration includes setup instructions in its directory.

### Skills and Agents

Groot uses a `.claude/` directory structure for extensibility:

- **Commands** (`.claude/commands/`) - User-triggered workflows you invoke with slash commands
- **Agents** (`.claude/agents/`) - Specialized subagents Groot spawns for delegated work
- **Skills** (`.claude/skills/`) - Reusable capabilities Claude Code invokes contextually

**Built-in skills:**

| Skill | When It Activates |
|-------|-------------------|
| `status` | `/status` command or "is everything connected?" |
| `daily-briefing` | Session start or "what's on today?" |
| `content-shipped` | Detects shipping language ("I published...", "just posted...") |
| `skill-creator` | "Give yourself the ability to..." or "create a skill for..." |

Templates are included for each type. Just say "create a skill for X" and Groot generates the file.

## How It Works

Groot separates your workspace from the template:

```
~/marvin/                    Your workspace (your data lives here)
├── CLAUDE.md               Your profile and preferences
├── state/                  Your goals and priorities
├── sessions/               Your daily session logs
└── ...

~/marvin-template/          Template (get updates here)
├── .marvin/                Setup scripts and integrations
├── .claude/                Command and agent templates
└── ...
```

Your workspace holds all personal data. The template provides updates. Run `/sync` from your workspace to pull new features without overwriting your data.

## Migrating from Older Versions

If you were using MARVIN before the workspace separation:

```bash
cd marvin-template
./.marvin/migrate.sh
```

The script copies your profile, goals, sessions, reports, and custom skills to a new workspace. Nothing is deleted from your old installation. Verify the new workspace works, then clean up the old one.

## Contributing

This template welcomes contributions in three areas:

1. **Integrations** - Add support for new tools. See [.marvin/integrations/CLAUDE.md](.marvin/integrations/CLAUDE.md) for patterns and security requirements.
2. **Commands, agents, skills** - Extend Groot's capabilities. Templates are in `.claude/commands/`, `.claude/agents/`, and `.claude/skills/`.
3. **Bug fixes** - Found an issue? Submit a PR with the fix and a test case.

Fork the repo, create a branch, and submit a PR. All contributions are reviewed.

## About

This project is based on the original MARVIN template by [Sterling Chin](https://sterlingchin.com), adapted into Groot as a personalized AI chief of staff workspace.

