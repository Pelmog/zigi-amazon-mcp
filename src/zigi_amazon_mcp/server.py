#!/usr/bin/env python3
"""MCP Server with basic I/O functionality using FastMCP."""

import base64
import json
import secrets
from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP

mcp: FastMCP = FastMCP("zigi-amazon-mcp")

# Session storage - in production, use a proper session store
session_store: dict[str, str] = {}

# Auth token storage - stores valid authentication tokens
auth_tokens: set[str] = set()


def validate_auth_token(token: str) -> bool:
    """Validate if the provided auth token is valid."""
    return token in auth_tokens


@mcp.tool()
def get_auth_token() -> str:
    """Generate and return a new authentication token (session ID) that must be used for all other function calls.
    
    This is the FIRST function you must call before using any other functions in this MCP server.
    The returned token is a secure, randomly generated session ID that serves as your authentication credential.
    
    IMPORTANT FOR AI AGENTS:
    - You MUST call this function first to obtain an auth token before calling any other function
    - Store the returned token and include it as the 'auth_token' parameter in ALL subsequent function calls
    - Each token is unique and represents a new session
    - Tokens remain valid for the lifetime of the server (in production, tokens would expire)
    - If you receive an 'Invalid or missing auth token' error, you need to call get_auth_token() again
    
    Returns:
        str: A secure, randomly generated authentication token (session ID) to be used for all other function calls
    
    Example workflow:
        1. Call get_auth_token() -> returns "a1b2c3d4e5f6..."
        2. Use this token in all other calls: hello_world(auth_token="a1b2c3d4e5f6...", name="World")
    """
    # Generate a secure random token
    token = secrets.token_hex(32)
    auth_tokens.add(token)
    return f"Authentication successful. Your auth token is: {token}"


@mcp.tool()
def hello_world(
    auth_token: Annotated[str, "Authentication token obtained from get_auth_token(). Required for this function to work."],
    name: Annotated[str, "Name to greet"] = "World"
) -> str:
    """A simple hello world tool that greets the user.
    
    REQUIRES AUTHENTICATION: You must provide a valid auth_token obtained from get_auth_token().
    """
    if not validate_auth_token(auth_token):
        return "Error: Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token."
    
    return f"Hello, {name}! This is the Zigi Amazon MCP server."


@mcp.tool()
def process_text(
    auth_token: Annotated[str, "Authentication token obtained from get_auth_token(). Required for this function to work."],
    text: Annotated[str, "The text to process"],
    operation: Annotated[
        str, "The operation to perform on the text: uppercase, lowercase, reverse, count_words, count_chars"
    ],
) -> str:
    """Process text with various operations.
    
    REQUIRES AUTHENTICATION: You must provide a valid auth_token obtained from get_auth_token().
    """
    if not validate_auth_token(auth_token):
        return "Error: Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token."
    
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
    auth_token: Annotated[str, "Authentication token obtained from get_auth_token(). Required for this function to work."],
    file_path: Annotated[str, "Path to the file to read"], 
    encoding: Annotated[str, "File encoding"] = "utf-8"
) -> str:
    """Read content from a local file.
    
    REQUIRES AUTHENTICATION: You must provide a valid auth_token obtained from get_auth_token().
    """
    if not validate_auth_token(auth_token):
        return "Error: Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token."
    
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
    auth_token: Annotated[str, "Authentication token obtained from get_auth_token(). Required for this function to work."],
    file_path: Annotated[str, "Path to the file to write"],
    content: Annotated[str, "Content to write to the file"],
    encoding: Annotated[str, "File encoding"] = "utf-8",
    append: Annotated[bool, "Append to file instead of overwriting"] = False,
) -> str:
    """Write content to a local file.
    
    REQUIRES AUTHENTICATION: You must provide a valid auth_token obtained from get_auth_token().
    """
    if not validate_auth_token(auth_token):
        return "Error: Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token."
    
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
    auth_token: Annotated[str, "Authentication token obtained from get_auth_token(). Required for this function to work."],
    data: Annotated[str, "JSON string to parse or object to format"],
    operation: Annotated[str, "Operation to perform: parse, format, validate"],
    indent: Annotated[int, "Indentation for formatting"] = 2,
) -> str:
    """Parse JSON string or format object as JSON.
    
    REQUIRES AUTHENTICATION: You must provide a valid auth_token obtained from get_auth_token().
    """
    if not validate_auth_token(auth_token):
        return "Error: Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token."
    
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
    auth_token: Annotated[str, "Authentication token obtained from get_auth_token(). Required for this function to work."],
    data: Annotated[str, "Data to convert"],
    from_format: Annotated[str, "Source format: text, base64, hex"],
    to_format: Annotated[str, "Target format: text, base64, hex"],
) -> str:
    """Convert data between different formats (base64, hex, etc.).
    
    REQUIRES AUTHENTICATION: You must provide a valid auth_token obtained from get_auth_token().
    """
    if not validate_auth_token(auth_token):
        return "Error: Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token."
    
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


@mcp.tool()
def store_session_data(
    auth_token: Annotated[str, "Authentication token obtained from get_auth_token(). Required for this function to work."],
    session_id: Annotated[str, "Unique session identifier for data storage"],
    data: Annotated[str, "Data to store in the session"],
) -> str:
    """Store a string in the session that can be retrieved later.
    
    REQUIRES AUTHENTICATION: You must provide a valid auth_token obtained from get_auth_token().
    
    Note: The session_id is separate from the auth_token and is used to organize stored data.
    You can use any string as a session_id to store different pieces of data under the same auth token.
    """
    if not validate_auth_token(auth_token):
        return "Error: Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token."
    
    session_store[session_id] = data
    return f"Successfully stored data for session: {session_id}"


@mcp.tool()
def get_session_data(
    auth_token: Annotated[str, "Authentication token obtained from get_auth_token(). Required for this function to work."],
    session_id: Annotated[str, "Unique session identifier to retrieve data for"]
) -> str:
    """Retrieve previously stored session data.
    
    REQUIRES AUTHENTICATION: You must provide a valid auth_token obtained from get_auth_token().
    
    Note: The session_id is separate from the auth_token and is used to organize stored data.
    """
    if not validate_auth_token(auth_token):
        return "Error: Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token."
    
    if session_id in session_store:
        return session_store[session_id]
    else:
        return f"No data found for session: {session_id}"


def main() -> None:
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()