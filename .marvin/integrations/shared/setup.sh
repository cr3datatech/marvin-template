#!/bin/bash
# Groot Shared Tools MCP Server Setup
# Registers the shared tools MCP server with Claude Code

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GROOT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Groot Shared Tools MCP Server Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Workspace root: $GROOT_ROOT"
echo ""

# Check Claude Code
if command -v claude &> /dev/null; then
    echo -e "${GREEN}✓ Claude Code installed${NC}"
else
    echo -e "${RED}✗ Claude Code not found${NC}"
    echo "Install with: npm install -g @anthropic-ai/claude-code"
    exit 1
fi

# Check Python
if command -v python3 &> /dev/null; then
    echo -e "${GREEN}✓ Python 3 found${NC}"
else
    echo -e "${RED}✗ Python 3 not found${NC}"
    exit 1
fi

# Scope selection
echo ""
echo "Where should this MCP server be available?"
echo "  1) All projects (user-scoped)"
echo "  2) This project only (project-scoped)"
echo ""
echo -e "${YELLOW}Choice [1]:${NC}"
read -r SCOPE_CHOICE
SCOPE_CHOICE=${SCOPE_CHOICE:-1}

if [[ "$SCOPE_CHOICE" == "1" ]]; then
    SCOPE_FLAG="-s user"
else
    SCOPE_FLAG=""
fi

# Install Python dependencies
echo ""
echo -e "${BLUE}Installing Python dependencies...${NC}"
pip3 install -q -r "$SCRIPT_DIR/requirements.txt"
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Optional: service names
echo ""
echo -e "${YELLOW}Systemd service names for bot restarts (comma-separated) [groot-slack,groot-telegram]:${NC}"
read -r SERVICE_NAMES
SERVICE_NAMES=${SERVICE_NAMES:-"groot-slack,groot-telegram"}

# Register MCP server
echo ""
echo -e "${BLUE}Registering MCP server with Claude Code...${NC}"

claude mcp remove groot-tools 2>/dev/null || true

claude mcp add groot-tools $SCOPE_FLAG \
    --command "python3" \
    --args "$SCRIPT_DIR/mcp_server.py" \
    --env "GROOT_ROOT=$GROOT_ROOT" \
    --env "GROOT_SERVICE_NAMES=$SERVICE_NAMES"

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}  Setup Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "The groot-tools MCP server is now available to the Claude CLI."
echo ""
echo -e "${GREEN}You're all set!${NC}"
echo ""
