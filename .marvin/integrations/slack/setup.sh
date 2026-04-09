#!/bin/bash
# Slack Bot Setup Script
# Run the Groot Slack bot in your workspace

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script lives
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GROOT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Slack Bot Setup for Groot${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    echo -e "${GREEN}✓ Python installed (${PYTHON_VERSION})${NC}"
else
    echo -e "${RED}✗ Python 3 not found${NC}"
    echo "  Install Python 3.10+ from https://python.org"
    exit 1
fi

# Check pip
if command -v pip3 &> /dev/null; then
    echo -e "${GREEN}✓ pip installed${NC}"
else
    echo -e "${YELLOW}! pip not found — installing...${NC}"
    if command -v apt-get &> /dev/null; then
        apt-get install -y python3-pip
    elif command -v apt &> /dev/null; then
        apt install -y python3-pip
    else
        echo -e "${RED}✗ Cannot install pip automatically${NC}"
        echo "  Run: apt install python3-pip"
        exit 1
    fi
    echo -e "${GREEN}✓ pip installed${NC}"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Step 1: Create a Slack App${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "You need a Slack app with Socket Mode enabled."
echo ""
echo "1. Go to: https://api.slack.com/apps"
echo "2. Click 'Create New App' → 'From scratch'"
echo "3. Name it 'Groot' and select your workspace"
echo ""
echo -e "${YELLOW}Press Enter when you've created the app...${NC}"
read -r

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Step 2: Enable Socket Mode${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "1. In your app settings, go to 'Socket Mode' (under Settings)"
echo "2. Toggle 'Enable Socket Mode' on"
echo "3. You'll be prompted to create an App-Level Token"
echo "   - Name it anything (e.g. 'groot-socket')"
echo "   - Add the scope: connections:write"
echo "   - Click 'Generate'"
echo "   - Copy the token starting with xapp-"
echo ""
echo -e "${YELLOW}Paste your App-Level Token (xapp-...):${NC}"
read -rs APP_TOKEN
echo ""

if [[ ! "$APP_TOKEN" =~ ^xapp- ]]; then
    echo -e "${RED}✗ Token should start with 'xapp-'${NC}"
    exit 1
fi
echo -e "${GREEN}✓ App-Level Token looks good${NC}"

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Step 3: Add Bot Permissions${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "1. Go to 'OAuth & Permissions' in the sidebar"
echo "2. Under 'Bot Token Scopes', add:"
echo ""
echo -e "   ${YELLOW}app_mentions:read${NC}    - Respond when mentioned"
echo -e "   ${YELLOW}channels:history${NC}     - Read channel messages"
echo -e "   ${YELLOW}chat:write${NC}           - Send messages"
echo -e "   ${YELLOW}im:history${NC}           - Read DMs"
echo -e "   ${YELLOW}im:read${NC}              - View DM info"
echo -e "   ${YELLOW}im:write${NC}             - Open DM channels"
echo ""
echo "3. Click 'Install to Workspace' at the top and authorize"
echo "4. Copy the 'Bot User OAuth Token' (starts with xoxb-)"
echo ""
echo -e "${YELLOW}Paste your Bot Token (xoxb-...):${NC}"
read -rs BOT_TOKEN
echo ""

if [[ ! "$BOT_TOKEN" =~ ^xoxb- ]]; then
    echo -e "${RED}✗ Token should start with 'xoxb-'${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Bot Token looks good${NC}"

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Step 4: Enable Events${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "1. Go to 'Event Subscriptions' in the sidebar"
echo "2. Toggle 'Enable Events' on"
echo "3. Under 'Subscribe to bot events', add:"
echo -e "   ${YELLOW}message.im${NC}      - Receive DMs"
echo -e "   ${YELLOW}app_mention${NC}     - Receive @mentions"
echo "4. Click 'Save Changes'"
echo ""
echo -e "${YELLOW}Press Enter when done...${NC}"
read -r

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Step 5: Install Dependencies${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Create virtual environment
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$SCRIPT_DIR/venv"
fi

echo "Activating virtual environment..."
source "$SCRIPT_DIR/venv/bin/activate"

echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r "$SCRIPT_DIR/requirements.txt"

echo -e "${GREEN}✓ Dependencies installed${NC}"

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Step 6: Save Configuration${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Create or update .env file
ENV_FILE="$SCRIPT_DIR/.env"

cat > "$ENV_FILE" << EOF
# Slack Bot Configuration
# Generated by setup.sh

SLACK_BOT_TOKEN=$BOT_TOKEN
SLACK_APP_TOKEN=$APP_TOKEN
EOF

echo -e "${GREEN}✓ Configuration saved to .env${NC}"

# Create run script
cat > "$SCRIPT_DIR/run.sh" << 'EOF'
#!/bin/bash
# Start the Groot Slack bot

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Load environment variables
if [ -f "$SCRIPT_DIR/.env" ]; then
    export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
fi

# Run the bot
cd "$SCRIPT_DIR"
python slack_bot.py "$@"
EOF

chmod +x "$SCRIPT_DIR/run.sh"

echo -e "${GREEN}✓ Run script created${NC}"

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}  Setup Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "To start your bot:"
echo ""
echo -e "  ${YELLOW}./.marvin/integrations/slack/run.sh${NC}"
echo ""
echo "Then in Slack:"
echo -e "  ${YELLOW}DM Groot directly${NC}       - Just message the bot"
echo -e "  ${YELLOW}@Groot in a channel${NC}     - Mention the bot"
echo ""
echo -e "${GREEN}You're all set!${NC}"
echo ""
