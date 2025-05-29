#!/usr/bin/env python3
"""MCP Server with basic I/O functionality using FastMCP."""

import base64
import json
import os
import secrets
from pathlib import Path
from typing import Annotated
from urllib.parse import urlencode

import boto3  # type: ignore[import-untyped]
import requests
from dotenv import load_dotenv
from fastmcp import FastMCP
from requests_aws4auth import AWS4Auth  # type: ignore[import-untyped]

# Load environment variables from .env file
load_dotenv()

mcp: FastMCP = FastMCP(
    "zigi-amazon-mcp",
    description="A comprehensive MCP server for Amazon Seller Central API integration, providing tools for e-commerce operations, inventory management, order processing, and data analytics.",
    version="1.0.0",
)

# Session storage - in production, use a proper session store
session_store: dict[str, str] = {}

# Auth token storage - stores valid authentication tokens
auth_tokens: set[str] = set()


def validate_auth_token(token: str) -> bool:
    """Validate if the provided auth token is valid."""
    return token in auth_tokens


def get_amazon_access_token() -> str | None:
    """Exchange refresh token for access token from Amazon LWA."""
    client_id = os.getenv("LWA_CLIENT_ID")
    client_secret = os.getenv("LWA_CLIENT_SECRET")
    refresh_token = os.getenv("LWA_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        raise ValueError(
            "Missing required LWA credentials. Please set LWA_CLIENT_ID, LWA_CLIENT_SECRET, and LWA_REFRESH_TOKEN environment variables."
        )

    lwa_url = "https://api.amazon.com/auth/o2/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }

    response = requests.post(lwa_url, data=data, timeout=30)
    if response.status_code == 200:
        token_data = response.json()
        return str(token_data["access_token"])
    else:
        return None


def get_amazon_aws_credentials() -> dict[str, str] | None:
    """Get AWS temporary credentials by assuming role for Amazon SP-API."""
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")

    if not all([aws_access_key_id, aws_secret_access_key]):
        raise ValueError(
            "Missing required AWS credentials. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables."
        )

    role_arn = os.getenv(
        "AWS_ROLE_ARN",
        "arn:aws:iam::295290492609:role/SPapi-Role-2025",
    )

    sts_client = boto3.client(
        "sts",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )

    try:
        assume_response = sts_client.assume_role(RoleArn=role_arn, RoleSessionName="SPapi-Role-2025")

        credentials = assume_response["Credentials"]
        return {
            "AccessKeyId": credentials["AccessKeyId"],
            "SecretAccessKey": credentials["SecretAccessKey"],
            "SessionToken": credentials["SessionToken"],
        }
    except Exception:
        return None


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
    auth_token: Annotated[
        str, "Authentication token obtained from get_auth_token(). Required for this function to work."
    ],
    name: Annotated[str, "Name to greet"] = "World",
) -> str:
    """A simple hello world tool that greets the user.

    REQUIRES AUTHENTICATION: You must provide a valid auth_token obtained from get_auth_token().
    """
    if not validate_auth_token(auth_token):
        return "Error: Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token."

    return f"Hello, {name}! This is the Zigi Amazon MCP server."


@mcp.tool()
def process_text(
    auth_token: Annotated[
        str, "Authentication token obtained from get_auth_token(). Required for this function to work."
    ],
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
    auth_token: Annotated[
        str, "Authentication token obtained from get_auth_token(). Required for this function to work."
    ],
    file_path: Annotated[str, "Path to the file to read"],
    encoding: Annotated[str, "File encoding"] = "utf-8",
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
    auth_token: Annotated[
        str, "Authentication token obtained from get_auth_token(). Required for this function to work."
    ],
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
    auth_token: Annotated[
        str, "Authentication token obtained from get_auth_token(). Required for this function to work."
    ],
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
    auth_token: Annotated[
        str, "Authentication token obtained from get_auth_token(). Required for this function to work."
    ],
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
    auth_token: Annotated[
        str, "Authentication token obtained from get_auth_token(). Required for this function to work."
    ],
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
    auth_token: Annotated[
        str, "Authentication token obtained from get_auth_token(). Required for this function to work."
    ],
    session_id: Annotated[str, "Unique session identifier to retrieve data for"],
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


@mcp.tool()
def get_orders(
    auth_token: Annotated[
        str,
        "Authentication token obtained from get_auth_token(). Required for this function to work.",
    ],
    marketplace_ids: Annotated[
        str, "Comma-separated marketplace IDs (e.g., 'A1F83G8C2ARO7P' for UK)"
    ] = "A1F83G8C2ARO7P",
    created_after: Annotated[
        str,
        "ISO 8601 date string for orders created after this date (e.g., '2025-01-01T00:00:00Z')",
    ] = "2025-01-01T00:00:00Z",
    created_before: Annotated[str, "ISO 8601 date string for orders created before this date (optional)"] = "",
    order_statuses: Annotated[str, "Comma-separated order statuses to filter by (optional)"] = "",
    max_results: Annotated[int, "Maximum number of orders to retrieve (default 100)"] = 100,
    region: Annotated[str, "AWS region for the SP-API endpoint"] = "eu-west-1",
    endpoint: Annotated[str, "SP-API endpoint URL"] = "https://sellingpartnerapi-eu.amazon.com",
) -> str:
    """Retrieve multiple orders from Amazon Seller Central using the SP-API.

    REQUIRES AUTHENTICATION: You must provide a valid auth_token obtained from get_auth_token().

    Also requires environment variables:
    - LWA_CLIENT_ID: Login with Amazon client ID
    - LWA_CLIENT_SECRET: Login with Amazon client secret
    - LWA_REFRESH_TOKEN: Login with Amazon refresh token
    - AWS_ACCESS_KEY_ID: AWS access key
    - AWS_SECRET_ACCESS_KEY: AWS secret key
    - AWS_ROLE_ARN: AWS role ARN (optional, has default)
    """
    if not validate_auth_token(auth_token):
        return "Error: Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token."

    try:
        # Get Amazon access token
        access_token = get_amazon_access_token()
        if not access_token:
            return "Error: Failed to get Amazon access token. Check your LWA credentials."

        # Get AWS credentials
        creds = get_amazon_aws_credentials()
        if not creds:
            return "Error: Failed to get AWS credentials. Check your AWS credentials and role."

        # Set up AWS4Auth
        aws_auth = AWS4Auth(
            creds["AccessKeyId"],
            creds["SecretAccessKey"],
            region,
            "execute-api",
            session_token=creds["SessionToken"],
        )

        # Prepare request parameters
        params = {
            "MarketplaceIds": marketplace_ids.split(","),
            "CreatedAfter": created_after,
        }

        if created_before:
            params["CreatedBefore"] = created_before

        if order_statuses:
            params["OrderStatuses"] = order_statuses.split(",")

        # Headers
        headers = {
            "x-amz-access-token": access_token,
            "user-agent": "ZigiAmazonMCP/1.0 (Language=Python)",
            "content-type": "application/json",
        }

        # Fetch orders with pagination
        api_path = "/orders/v0/orders"
        all_orders = []
        next_token = None
        retrieved_count = 0

        while retrieved_count < max_results:
            # Build URL
            if next_token:
                url = f"{endpoint}{api_path}?NextToken={next_token}"
            else:
                url = f"{endpoint}{api_path}?{urlencode(params, doseq=True)}"

            # Make request
            response = requests.get(url, headers=headers, auth=aws_auth, timeout=30)
            response.raise_for_status()

            result = response.json()
            orders = result.get("payload", {}).get("Orders", [])

            # Add orders but don't exceed max_results
            remaining_slots = max_results - retrieved_count
            orders_to_add = orders[:remaining_slots]
            all_orders.extend(orders_to_add)
            retrieved_count += len(orders_to_add)

            # Check for next page
            next_token = result.get("payload", {}).get("NextToken")
            if not next_token or retrieved_count >= max_results:
                break

        return json.dumps(
            {
                "success": True,
                "orders_retrieved": len(all_orders),
                "orders": all_orders,
            },
            indent=2,
        )

    except Exception as e:
        return f"Error retrieving orders: {e!s}"


@mcp.tool()
def get_order(
    auth_token: Annotated[
        str,
        "Authentication token obtained from get_auth_token(). Required for this function to work.",
    ],
    order_id: Annotated[str, "Amazon Order ID to retrieve"],
    region: Annotated[str, "AWS region for the SP-API endpoint"] = "eu-west-1",
    endpoint: Annotated[str, "SP-API endpoint URL"] = "https://sellingpartnerapi-eu.amazon.com",
) -> str:
    """Retrieve a single order from Amazon Seller Central using the SP-API.

    REQUIRES AUTHENTICATION: You must provide a valid auth_token obtained from get_auth_token().

    Also requires environment variables:
    - LWA_CLIENT_ID: Login with Amazon client ID
    - LWA_CLIENT_SECRET: Login with Amazon client secret
    - LWA_REFRESH_TOKEN: Login with Amazon refresh token
    - AWS_ACCESS_KEY_ID: AWS access key
    - AWS_SECRET_ACCESS_KEY: AWS secret key
    - AWS_ROLE_ARN: AWS role ARN (optional, has default)
    """
    if not validate_auth_token(auth_token):
        return "Error: Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token."

    try:
        # Get Amazon access token
        access_token = get_amazon_access_token()
        if not access_token:
            return "Error: Failed to get Amazon access token. Check your LWA credentials."

        # Get AWS credentials
        creds = get_amazon_aws_credentials()
        if not creds:
            return "Error: Failed to get AWS credentials. Check your AWS credentials and role."

        # Set up AWS4Auth
        aws_auth = AWS4Auth(
            creds["AccessKeyId"],
            creds["SecretAccessKey"],
            region,
            "execute-api",
            session_token=creds["SessionToken"],
        )

        # Headers
        headers = {
            "x-amz-access-token": access_token,
            "user-agent": "ZigiAmazonMCP/1.0 (Language=Python)",
            "content-type": "application/json",
        }

        # Make request
        url = f"{endpoint}/orders/v0/orders/{order_id}"
        response = requests.get(url, headers=headers, auth=aws_auth, timeout=30)
        response.raise_for_status()

        result = response.json()
        order_data = result.get("payload", {})

        return json.dumps({"success": True, "order": order_data}, indent=2)

    except Exception as e:
        return f"Error retrieving order {order_id}: {e!s}"


def main() -> None:
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
