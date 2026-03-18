---
name: feedback_bot_updates
description: Always update both Slack and Telegram bots when making plugin changes
type: feedback
---

Always update both bots when making changes to bot plugins or tools.

**Why:** The Slack and Telegram bots are separate services with their own tools directories. Changes to one are not automatically reflected in the other.

**How to apply:** After editing any file in `.marvin/integrations/telegram/tools/`, immediately copy it to `.marvin/integrations/slack/tools/` (or vice versa), then restart both services: `sudo systemctl restart groot-telegram groot-slack`.
