# Setup Notes

## Atlassian MCP Connection Issue (2026-03-16)

### Problem
Unable to connect to the Atlassian MCP server.

### Config (`/.mcp.json`)
```json
{
  "mcpServers": {
    "Atlassian": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote@latest",
        "https://mcp.atlassian.com/v1/sse"
      ]
    }
  }
}
```

### Root Cause
The Atlassian MCP uses OAuth (browser-based auth), not an API key. No `~/.mcp-remote/` cache directory existed, meaning the OAuth flow was never completed.

### Fix
1. Run the following in a terminal to trigger the OAuth flow:
   ```bash
   npx -y mcp-remote@latest https://mcp.atlassian.com/v1/sse
   ```
2. A browser tab will open to `https://mcp.atlassian.com` — log in and authorize.
3. Token gets cached after auth completes.
4. Restart Groot — the MCP should connect automatically.

### Notes
- No `.env` config needed for Atlassian MCP — it's OAuth only.
- If browser doesn't open automatically, check terminal output for a manual auth URL.
