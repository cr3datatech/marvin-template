#!/bin/bash
# Authenticate Groot bots with Google
# Run this once to generate the OAuth token used by Telegram and Slack bots.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GROOT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"

# Load .env
if [ -f "$GROOT_ROOT/.env" ]; then
    export $(grep -v '^#' "$GROOT_ROOT/.env" | grep -v '^$' | xargs)
fi

# Use telegram venv (or slack, both have the packages)
VENV="$GROOT_ROOT/.marvin/integrations/telegram/venv/bin/python"
if [ ! -f "$VENV" ]; then
    VENV="$GROOT_ROOT/.marvin/integrations/slack/venv/bin/python"
fi

if [ ! -f "$VENV" ]; then
    echo "ERROR: No bot venv found. Set up Telegram or Slack bot first."
    exit 1
fi

"$VENV" "$SCRIPT_DIR/bot_auth.py" "$@"
