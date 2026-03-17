# Google Workspace Integration

Connect Groot to your Google account for email, calendar, files, and photos.

## What It Does

- **Gmail** - Read, search, and send emails
- **Calendar** - View events, check availability, create meetings
- **Drive** - Search and read documents, spreadsheets, slides
- **Photos** - List albums, browse and search photos

## Who It's For

Anyone who uses Google Workspace (Gmail, Google Calendar, Google Drive) for work or personal use.

## Prerequisites

- A Google account
- A Google Cloud project with OAuth credentials (Client ID + Client Secret)
- The account added as a **test user** in the OAuth consent screen (if app is unverified)

## Setup

### Step 1: Groot (Claude Code)

```bash
./.marvin/integrations/google-workspace/setup.sh
```

Prompts for your Client ID and Secret, configures the MCP server, then opens a browser to log in.

### Step 2: Telegram & Slack Bots

The bots use a separate headless OAuth flow. Run once to generate a shared token:

```bash
# Get the auth URL
./.marvin/integrations/google-workspace/bot_auth.sh url

# After authorising in a browser, exchange the code:
./.marvin/integrations/google-workspace/bot_auth.sh exchange <code>
```

Token is saved to `~/.config/groot/google_token.json`. The bots refresh it automatically — you won't need to repeat this unless you revoke access.

After auth, restart both bots:
```bash
sudo systemctl restart groot-telegram groot-slack
```

## Try It

After setup, try these in Groot, Telegram, or Slack:

- "What's on my calendar today?"
- "Show me my unread emails"
- "Search my Drive for quarterly reports"
- "List my photo albums"
- "Send an email to [person] about [topic]"

## Danger Zone

This integration can perform actions that affect others or can't be easily undone:

| Action | Risk Level | Who's Affected |
|--------|------------|----------------|
| Send emails | **High** | Recipients see it immediately |
| Create/modify calendar events | **Medium** | Other attendees are notified |
| Delete emails | **Medium** | May be recoverable from trash |
| Read emails, calendar, Drive, Photos | Low | No external impact |

**Groot will always confirm before sending emails or modifying calendar events.**

## Troubleshooting

**"Access blocked: Authorization Error"**
Your Google account isn't added as a test user. Go to Google Cloud Console → APIs & Services → OAuth consent screen → Test users → Add your email.

**Wrong Google account shown**
Open the auth URL in an incognito window and sign in with the correct account.

**"Not authenticated" error in bots**
Run the bot auth flow: `.marvin/integrations/google-workspace/bot_auth.sh url` then exchange the code.

**Token expired / refresh failed**
Re-run the bot auth flow to generate a fresh token.

---

*Google Workspace integration for [Groot](https://github.com/cr3datatech/marvin-template)*
