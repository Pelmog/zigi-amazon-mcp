#!/usr/bin/env python3
"""MCP Server with basic I/O functionality using FastMCP."""

import base64
import json
from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP

mcp: FastMCP = FastMCP("zigi-amazon-mcp")


@mcp.tool()
def hello_world(name: Annotated[str, "Name to greet"] = "World") -> str:
    """A simple hello world tool that greets the user."""
    return f"Hello, {name}! This is the Zigi Amazon MCP server."


@mcp.tool()
def process_text(
    text: Annotated[str, "The text to process"],
    operation: Annotated[
        str, "The operation to perform on the text: uppercase, lowercase, reverse, count_words, count_chars"
    ],
) -> str:
    """Process text with various operations."""
    if operation == "uppercase":
        return text.upper()
    elif operation == "lowercase":
        return text.lower()
    elif operation == "reverse":
        return text[::-1]
    elif operation == "count_words":
        return str(len(text.split()))
    elif operation == "count_chars":
        return str(len(text))
    else:
        raise ValueError(f"Invalid operation: {operation}")


@mcp.tool()
def read_file(
    file_path: Annotated[str, "Path to the file to read"], encoding: Annotated[str, "File encoding"] = "utf-8"
) -> str:
    """Read content from a local file."""
    try:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if not path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        return path.read_text(encoding=encoding)
    except Exception as e:
        return f"Error reading file: {e!s}"


@mcp.tool()
def write_file(
    file_path: Annotated[str, "Path to the file to write"],
    content: Annotated[str, "Content to write to the file"],
    encoding: Annotated[str, "File encoding"] = "utf-8",
    append: Annotated[bool, "Append to file instead of overwriting"] = False,
) -> str:
    """Write content to a local file."""
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if append:
            with open(path, "a", encoding=encoding) as f:
                f.write(content)
        else:
            path.write_text(content, encoding=encoding)

        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"Error writing file: {e!s}"


@mcp.tool()
def json_process(
    data: Annotated[str, "JSON string to parse or object to format"],
    operation: Annotated[str, "Operation to perform: parse, format, validate"],
    indent: Annotated[int, "Indentation for formatting"] = 2,
) -> str:
    """Parse JSON string or format object as JSON."""
    if operation not in ["parse", "format", "validate"]:
        raise ValueError(f"Invalid operation: {operation}")

    try:
        if operation == "parse":
            result = json.loads(data)
            return f"Parsed JSON: {result}"
        elif operation == "format":
            # Try to parse as JSON first, if it fails, assume it's a Python dict string
            try:
                obj = json.loads(data)
            except json.JSONDecodeError:
                # Simple eval for dict-like strings (unsafe in production!)
                obj = eval(data)
            return json.dumps(obj, indent=indent)
        elif operation == "validate":
            try:
                json.loads(data)
                return "Valid JSON"
            except json.JSONDecodeError as e:
                return f"Invalid JSON: {e!s}"
    except Exception as e:
        return f"Error processing JSON: {e!s}"
    return ""  # This should never be reached


@mcp.tool()
def convert_data(
    data: Annotated[str, "Data to convert"],
    from_format: Annotated[str, "Source format: text, base64, hex"],
    to_format: Annotated[str, "Target format: text, base64, hex"],
) -> str:
    """Convert data between different formats (base64, hex, etc.)."""
    try:
        # First, decode from source format
        if from_format == "text":
            decoded = data.encode("utf-8")
        elif from_format == "base64":
            decoded = base64.b64decode(data)
        elif from_format == "hex":
            decoded = bytes.fromhex(data)
        else:
            raise ValueError(f"Invalid source format: {from_format}")

        # Then, encode to target format
        if to_format == "text":
            result = decoded.decode("utf-8")
        elif to_format == "base64":
            result = base64.b64encode(decoded).decode("ascii")
        elif to_format == "hex":
            result = decoded.hex()
        else:
            raise ValueError(f"Invalid target format: {to_format}")

        return result
    except Exception as e:
        return f"Error converting data: {e!s}"


def main() -> None:
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
