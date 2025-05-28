#!/usr/bin/env python3
"""Basic Hello World MCP Server for testing."""

import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import ServerCapabilities, TextContent, Tool

app: Server = Server("zigi-amazon-mcp")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="hello_world",
            description="A simple hello world tool that greets the user",
            inputSchema={
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Name to greet", "default": "World"}},
                "required": [],
            },
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
    """Handle tool calls."""
    if name == "hello_world":
        user_name = (arguments or {}).get("name", "World")
        return [TextContent(type="text", text=f"Hello, {user_name}! This is the Zigi Amazon MCP server.")]

    msg = f"Unknown tool: {name}"
    raise ValueError(msg)


async def run() -> None:
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="zigi-amazon-mcp", server_version="0.1.0", capabilities=ServerCapabilities()
            ),
        )


def main() -> None:
    """Entry point for the MCP server."""
    asyncio.run(run())


if __name__ == "__main__":
    main()
