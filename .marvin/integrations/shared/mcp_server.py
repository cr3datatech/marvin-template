"""Groot MCP Server — exposes shared tools to the Claude CLI.

Runs as a stdio MCP server. Register with:
    claude mcp add groot-tools --command "python /path/to/mcp_server.py"

Required env vars:
    GROOT_ROOT            Absolute path to the Groot workspace root
    GROOT_SERVICE_NAMES   Comma-separated systemd service names (optional,
                          default: groot-slack,groot-telegram)
"""

import asyncio
import importlib.util
import logging
import os
import sys
from pathlib import Path

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

# ---------------------------------------------------------------------------
# Paths & environment
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
SHARED_TOOLS_DIR = SCRIPT_DIR / "tools"

if "GROOT_ROOT" not in os.environ:
    sys.exit("GROOT_ROOT environment variable is required")

GROOT_ROOT = Path(os.environ["GROOT_ROOT"]).resolve()
SERVICE_NAMES = os.environ.get(
    "GROOT_SERVICE_NAMES", "groot-slack,groot-telegram"
).split(",")

# ---------------------------------------------------------------------------
# Path validation (sandbox to GROOT_ROOT)
# ---------------------------------------------------------------------------


def validate_path(path: str) -> Path:
    resolved = (GROOT_ROOT / path).resolve()
    try:
        resolved.relative_to(GROOT_ROOT)
    except ValueError:
        raise ValueError("Access denied: path outside workspace")
    if resolved.is_symlink():
        target = resolved.resolve()
        try:
            target.relative_to(GROOT_ROOT)
        except ValueError:
            raise ValueError("Access denied: symlink points outside workspace")
    return resolved


# ---------------------------------------------------------------------------
# ContentFetcher (optional — graceful degradation if deps missing)
# ---------------------------------------------------------------------------

try:
    sys.path.insert(0, str(SCRIPT_DIR))
    from content_fetcher import ContentFetcher
    fetcher = ContentFetcher()
except Exception:
    fetcher = None

# ---------------------------------------------------------------------------
# Tool context (replaces per-call injection)
# ---------------------------------------------------------------------------

CONTEXT = {
    "groot_root": GROOT_ROOT,
    "validate_path": validate_path,
    "fetcher": fetcher,
    "service_names": SERVICE_NAMES,
    "tools_dirs": [SHARED_TOOLS_DIR],
    "bot_type": "mcp",
}

# ---------------------------------------------------------------------------
# Dynamically load tool plugins from shared/tools/
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# plugins: tool_name -> (execute_fn, definition_dict)
plugins: dict[str, tuple] = {}

for _path in sorted(SHARED_TOOLS_DIR.glob("*.py")):
    if _path.name.startswith("_"):
        continue
    try:
        _spec = importlib.util.spec_from_file_location(f"groot_tools.{_path.stem}", _path)
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        if hasattr(_mod, "TOOL_DEFINITIONS") and hasattr(_mod, "execute"):
            for _defn in _mod.TOOL_DEFINITIONS:
                plugins[_defn["name"]] = (_mod.execute, _defn)
    except Exception as e:
        logger.error(f"Failed to load plugin {_path.name}: {e}")

# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

server = Server("groot-tools")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name=defn["name"],
            description=defn["description"],
            inputSchema=defn["input_schema"],
        )
        for _, (_, defn) in plugins.items()
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.Content]:
    if name not in plugins:
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
    execute_fn, _ = plugins[name]
    try:
        result = execute_fn(name, arguments, CONTEXT)
    except ValueError as e:
        result = f"Error: {e}"
    except Exception as e:
        logger.error(f"Tool error in {name}: {e}", exc_info=True)
        result = f"Error executing {name}."
    return [types.TextContent(type="text", text=str(result))]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
