# Using Zigi Amazon MCP with Claude Code

This guide explains how to use the Zigi Amazon MCP server tools directly within Claude Code.

## Prerequisites

1. Ensure the MCP server is running. You should see "zigi-amazon-mcp: connected" in your MCP status.
2. The `.claude/settings.local.json` file must include permissions for all MCP tools.

## Available MCP Tools

All tools are prefixed with `mcp__zigi-amazon-mcp__` when used in Claude Code:

- `mcp__zigi-amazon-mcp__hello_world`
- `mcp__zigi-amazon-mcp__process_text`
- `mcp__zigi-amazon-mcp__read_file`
- `mcp__zigi-amazon-mcp__write_file`
- `mcp__zigi-amazon-mcp__json_process`
- `mcp__zigi-amazon-mcp__convert_data`

## Usage Examples

### 1. Hello World
```
Use the mcp__zigi-amazon-mcp__hello_world tool with name "Claude"
```

### 2. Process Text
```
Use the mcp__zigi-amazon-mcp__process_text tool to convert "Hello World" to uppercase
```

### 3. Read File
```
Use the mcp__zigi-amazon-mcp__read_file tool to read /path/to/file.txt
```

### 4. Write File
```
Use the mcp__zigi-amazon-mcp__write_file tool to write "Hello MCP" to /tmp/test.txt
```

### 5. JSON Processing
```
Use the mcp__zigi-amazon-mcp__json_process tool to format {"name": "test", "value": 42}
```

### 6. Data Conversion
```
Use the mcp__zigi-amazon-mcp__convert_data tool to convert "Hello" from text to base64
```

## Troubleshooting

If tools are not accessible:

1. **Check server status**: Ensure "zigi-amazon-mcp: connected" appears in MCP status
2. **Verify permissions**: Check `.claude/settings.local.json` includes all tool permissions
3. **Restart server**: If needed, restart Claude Code to reload permissions
4. **Check logs**: Look for error messages in the Claude Code output

## Direct Tool Invocation

Claude Code can invoke these tools directly when you ask it to perform tasks. For example:
- "Convert this text to base64 using the MCP server"
- "Read the contents of config.json using the MCP tool"
- "Process this JSON data with the MCP server"

The tools will be automatically selected based on your request.
