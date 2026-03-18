---
name: feedback_bot_updates
description: Always update both Slack and Telegram bots when making plugin changes
type: feedback
---

Always update BOTH bots when making any changes to plugins, tools, or system prompts. This is critical — both bots must always have identical functionality.

**Why:** The Slack and Telegram bots are separate services with their own tools directories. Changes to one are not automatically reflected in the other. Craig considers this a critical requirement.

**How to apply:**
- After editing any plugin in either bot's `tools/` directory, immediately copy it to the other bot's `tools/` directory
- After editing either bot's system prompt (`_build_system_prompt`), apply the same change to the other bot
- If the Slack bot auto-creates a new plugin via `create_tool`, always copy it to Telegram too
- Always restart both: `sudo systemctl restart groot-telegram groot-slack`
- Never leave one bot ahead of the other in functionality
