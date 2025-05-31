#!/usr/bin/env python3
"""MCP Server for Amazon Seller Central API integration using FastMCP.

This server provides authentication and comprehensive tools for interacting with
Amazon Seller Central through the SP-API, including inventory management,
order processing, and product listing management.
"""

import base64
import json
import os
import secrets
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional
from urllib.parse import urlencode

import boto3  # type: ignore[import-untyped]
import requests
from dotenv import load_dotenv
from fastmcp import FastMCP
from requests_aws4auth import AWS4Auth  # type: ignore[import-untyped]

from .api.feeds import FeedsAPIClient
from .api.inventory import InventoryAPIClient
from .api.listings import ListingsAPIClient
from .api.orders import OrdersAPIClient
from .api.reports import ReportsAPIClient
from .filtering import FilterManager
from .utils.decorators import cached_api_call, handle_sp_api_errors
from .utils.rate_limiter import RateLimiter
from .utils.validators import (
    validate_amazon_order_id,
    validate_bulk_inventory_updates,
    validate_fbm_quantity,
    validate_handling_time,
    validate_seller_sku,
)

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

# Filter manager for JSON filtering and data reduction
filter_manager = FilterManager()

# Rate limiter for SP-API calls
rate_limiter = RateLimiter()


def initialize_filter_database():
    """Initialize and seed the filter database with predefined filters."""
    try:
        from pathlib import Path

        from .filtering import FilterLibrary

        filter_lib = FilterLibrary()

        # Get the seed data directory
        seed_data_dir = Path(__file__).parent / "filtering" / "seed_data"

        # Import all seed data files
        seed_files = [
            "order_filters.json",
            "order_field_filters.json",
            "inventory_filters.json",
            "inventory_field_filters.json",
            "common_filters.json",
            "common_field_filters.json",
            "filter_chains.json",
        ]

        imported_total = 0
        for seed_file in seed_files:
            file_path = seed_data_dir / seed_file
            if file_path.exists():
                result = filter_lib.import_filters_from_json(str(file_path))
                if result["success"]:
                    imported_total += result["imported_count"]
                    print(f"Imported {result['imported_count']} filters from {seed_file}")
                else:
                    print(f"Warning: Failed to import {seed_file}: {result.get('error', 'Unknown error')}")
            else:
                print(f"Warning: Seed file {seed_file} not found")

        print(f"Filter database initialization complete. Total filters imported: {imported_total}")

        # Get database stats
        stats = filter_lib.get_database_stats()
        if stats.get("status") == "healthy":
            print(f"Database health check: {stats['total_filters']} total filters, {stats['chain_filters']} chains")

    except Exception as e:
        print(f"Warning: Failed to initialize filter database: {e}")


# Initialize the filter database on startup
initialize_filter_database()


def validate_auth_token(token: str) -> bool:
    """Validate if the provided auth token is valid."""
    return token in auth_tokens


def get_amazon_access_token() -> str | None:
    """Exchange refresh token for access token from Amazon LWA."""
    client_id = os.getenv("LWA_CLIENT_ID")  # "amzn1.application-oa2-client.f780ac6b975e4abe85bbd8ee2bb7b137"  #
    client_secret = os.getenv("LWA_CLIENT_SECRET")
    refresh_token = os.getenv("LWA_REFRESH_TOKEN")

    # Save environment variables to debug file
    with open("debug-nonsense.log", "w") as f:
        f.write(f"LWA_CLIENT_ID: {client_id}\n")
        f.write(f"LWA_CLIENT_SECRET: {client_secret}\n")
        f.write(f"LWA_REFRESH_TOKEN: {refresh_token}\n")

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
        raise ValueError(f"LWA token request failed: {response.status_code} - {response.text}")


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
        str,
        "Authentication token obtained from get_auth_token(). Required for this function to work.",
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
def get_available_filters(
    auth_token: Annotated[
        str,
        "Authentication token obtained from get_auth_token(). Required for this function to work.",
    ],
    endpoint: Annotated[
        str,
        "MCP endpoint name to filter by (e.g., 'get_orders', 'get_inventory_in_stock'). Leave empty for all endpoints.",
    ] = "",
    category: Annotated[
        str, "Filter category to filter by (e.g., 'orders', 'inventory', 'common'). Leave empty for all categories."
    ] = "",
    filter_type: Annotated[
        str,
        "Filter type to filter by: 'record' (reduce number of items), 'field' (reduce data per item), 'chain' (predefined combinations). Leave empty for all types.",
    ] = "",
    search_term: Annotated[
        str, "Search term to find relevant filters by name or description. Leave empty for no search filtering."
    ] = "",
) -> str:
    """Get available filters for discovering and applying data reduction to API responses.

    REQUIRES AUTHENTICATION: You must provide a valid auth_token obtained from get_auth_token().

    This tool helps you discover filters that can dramatically reduce API response sizes:
    - Record filters: Reduce the number of items returned (e.g., high-value orders only)
    - Field filters: Reduce data within each item (e.g., order summary with just ID, status, total)
    - Chain filters: Combine multiple filters for maximum data reduction (e.g., high-value orders + summary data = 98% reduction)

    Use the returned filter IDs with the filter_id or filter_chain parameters in other tools like get_orders() or get_inventory_in_stock().
    """
    if not validate_auth_token(auth_token):
        return "Error: Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token."

    try:
        result = filter_manager.get_available_filters(
            endpoint=endpoint, category=category, filter_type=filter_type, search_term=search_term
        )

        return json.dumps(result, indent=2)

    except Exception as e:
        return f"Error retrieving available filters: {e!s}"


@mcp.tool()
def process_text(
    auth_token: Annotated[
        str,
        "Authentication token obtained from get_auth_token(). Required for this function to work.",
    ],
    text: Annotated[str, "The text to process"],
    operation: Annotated[
        str,
        "The operation to perform on the text: uppercase, lowercase, reverse, count_words, count_chars",
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
        str,
        "Authentication token obtained from get_auth_token(). Required for this function to work.",
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
        str,
        "Authentication token obtained from get_auth_token(). Required for this function to work.",
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
        str,
        "Authentication token obtained from get_auth_token(). Required for this function to work.",
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
        str,
        "Authentication token obtained from get_auth_token(). Required for this function to work.",
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
        str,
        "Authentication token obtained from get_auth_token(). Required for this function to work.",
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
        str,
        "Authentication token obtained from get_auth_token(). Required for this function to work.",
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
    filter_id: Annotated[
        str,
        "Filter ID from database to apply to results (use get_available_filters to discover). Reduces response size dramatically.",
    ] = "",
    filter_chain: Annotated[
        str,
        "Comma-separated chain of filter IDs for complex data reduction (e.g., 'high_value_orders,order_summary' for 98% reduction)",
    ] = "",
    custom_filter: Annotated[str, "Custom JSON Query expression for advanced filtering"] = "",
    filter_params: Annotated[str, "JSON string of filter parameters (e.g., '{\"threshold\": 100.0}')"] = "{}",
    reduce_response: Annotated[bool, "Apply default data reduction filter to minimize response size"] = False,
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

        # Prepare response data
        response_data = {
            "success": True,
            "orders_retrieved": len(all_orders),
            "orders": all_orders,
        }

        # Save JSON to received-json folder
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            received_json_dir = Path("received-json")
            received_json_dir.mkdir(exist_ok=True)

            filename = f"orders_{timestamp}.json"
            file_path = received_json_dir / filename

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(response_data, f, indent=2)

        except Exception as e:
            # Log error but don't fail the main operation
            print(f"Warning: Failed to save JSON file: {e}")

        # Apply filtering if requested
        if filter_id or filter_chain or custom_filter or reduce_response:
            try:
                filter_result = filter_manager.apply_enhanced_filtering(
                    data=response_data["orders"],
                    filter_id=filter_id,
                    filter_chain=filter_chain,
                    custom_filter=custom_filter,
                    filter_params=filter_params,
                    reduce_response=reduce_response,
                    endpoint="get_orders",
                )

                if filter_result["success"]:
                    # Update response with filtered data and metadata
                    response_data["orders"] = filter_result["data"]
                    response_data["orders_retrieved"] = (
                        len(filter_result["data"]) if isinstance(filter_result["data"], list) else 1
                    )
                    response_data["filtering"] = filter_result["metadata"]
                else:
                    # Include filtering error but don't fail the request
                    response_data["filtering_error"] = filter_result.get("message", "Unknown filtering error")

            except Exception as e:
                # Include filtering error but don't fail the request
                response_data["filtering_error"] = f"Filter application failed: {e!s}"

        return json.dumps(response_data, indent=2)

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

        # Prepare response data
        response_data = {"success": True, "order": order_data}

        # Save JSON to received-json folder
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            received_json_dir = Path("received-json")
            received_json_dir.mkdir(exist_ok=True)

            filename = f"order_{order_id}_{timestamp}.json"
            file_path = received_json_dir / filename

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(response_data, f, indent=2)

        except Exception as e:
            # Log error but don't fail the main operation
            print(f"Warning: Failed to save JSON file: {e}")

        return json.dumps(response_data, indent=2)

    except Exception as e:
        return f"Error retrieving order {order_id}: {e!s}"


@mcp.tool()
@handle_sp_api_errors
def get_order_items(
    auth_token: Annotated[
        str,
        "Authentication token obtained from get_auth_token(). Required for this function to work.",
    ],
    order_id: Annotated[str, "Amazon Order ID to retrieve items for (e.g., '206-8645991-0289149')"],
    marketplace_ids: Annotated[
        str, "Comma-separated marketplace IDs (e.g., 'A1F83G8C2ARO7P' for UK)"
    ] = "A1F83G8C2ARO7P",
    filter_id: Annotated[
        str,
        "Filter ID from database to apply to results (use get_available_filters to discover). Reduces response size dramatically.",
    ] = "",
    filter_chain: Annotated[
        str,
        "Comma-separated chain of filter IDs for complex data reduction (e.g., 'high_value_items,order_items_summary' for 98% reduction)",
    ] = "",
    custom_filter: Annotated[str, "Custom JSON Query expression for advanced filtering"] = "",
    filter_params: Annotated[str, "JSON string of filter parameters (e.g., '{\"threshold\": 100.0}')"] = "{}",
    reduce_response: Annotated[bool, "Apply default data reduction filter to minimize response size"] = False,
    region: Annotated[str, "AWS region for the SP-API endpoint"] = "eu-west-1",
    endpoint: Annotated[str, "SP-API endpoint URL"] = "https://sellingpartnerapi-eu.amazon.com",
) -> str:
    """Retrieve detailed items (products) for a specific Amazon order.

    REQUIRES AUTHENTICATION: You must provide a valid auth_token obtained from get_auth_token().

    This endpoint retrieves the actual products within an Amazon order, including:
    - Product identifiers (ASIN, SKU)
    - Product titles and descriptions
    - Quantities ordered and shipped
    - Pricing breakdown (item price, shipping, taxes)
    - Gift information and promotional discounts
    - Product condition and fulfillment details

    CRITICAL RATE LIMITING: This endpoint has strict rate limits of 0.5 requests/second
    with a burst capacity of 30. For bulk analysis, use the filtering system to reduce
    data size and implement proper delays between calls.

    FILTERING SYSTEM: Supports comprehensive data reduction:
    - Field filters: Reduce item data by 85-95% (summary, financial, inventory views)
    - Record filters: Filter items by criteria (high-value, gifts, bulk quantities)
    - Chain filters: Combine filtering for 95-99% reduction

    Examples:
    - Basic call: get_order_items(auth_token, "206-8645991-0289149")
    - Summary data: get_order_items(auth_token, order_id, filter_id="order_items_summary")
    - High-value items: get_order_items(auth_token, order_id, filter_id="high_value_items",
                                       filter_params='{"threshold": 100}')
    - Maximum reduction: get_order_items(auth_token, order_id,
                                        filter_chain="high_value_items,order_items_summary")

    Also requires environment variables:
    - LWA_CLIENT_ID: Login with Amazon client ID
    - LWA_CLIENT_SECRET: Login with Amazon client secret
    - LWA_REFRESH_TOKEN: Login with Amazon refresh token
    - AWS_ACCESS_KEY_ID: AWS access key
    - AWS_SECRET_ACCESS_KEY: AWS secret key
    - AWS_ROLE_ARN: AWS role ARN (optional, has default)
    """
    # 1. Validate authentication
    if not validate_auth_token(auth_token):
        return json.dumps(
            {
                "success": False,
                "error": "invalid_auth",
                "message": "Invalid or missing auth token. Call get_auth_token() first.",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # 2. Validate order ID format
    if not validate_amazon_order_id(order_id):
        return json.dumps(
            {
                "success": False,
                "error": "invalid_input",
                "message": "Invalid Amazon Order ID format. Expected format: XXX-XXXXXXX-XXXXXXX",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # 3. Apply rate limiting (critical for this endpoint)
    api_path = "get_order_items"
    if not rate_limiter.check_available(api_path):
        wait_time = rate_limiter.get_wait_time(api_path)
        return json.dumps(
            {
                "success": False,
                "error": "rate_limit_exceeded",
                "message": f"Rate limit exceeded. Please wait {wait_time:.1f} seconds before retry.",
                "retry_after": wait_time,
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                    "rate_limit_info": {
                        "endpoint": "getOrderItems",
                        "rate_limit": "0.5 requests/second",
                        "burst_capacity": 30,
                    },
                },
            },
            indent=2,
        )

    try:
        # 4. Get SP-API credentials
        access_token = get_amazon_access_token()
        if not access_token:
            return json.dumps(
                {
                    "success": False,
                    "error": "auth_failed",
                    "message": "Failed to get Amazon access token. Check your LWA credentials.",
                    "metadata": {
                        "timestamp": datetime.now().isoformat() + "Z",
                        "request_id": str(uuid.uuid4()),
                    },
                },
                indent=2,
            )

        aws_creds = get_amazon_aws_credentials()
        if not aws_creds:
            return json.dumps(
                {
                    "success": False,
                    "error": "auth_failed",
                    "message": "Failed to get AWS credentials. Check your AWS credentials and role.",
                    "metadata": {
                        "timestamp": datetime.now().isoformat() + "Z",
                        "request_id": str(uuid.uuid4()),
                    },
                },
                indent=2,
            )

        # 5. Initialize OrdersAPIClient
        client = OrdersAPIClient(access_token, aws_creds, region, endpoint)

        # 6. Make API call with proper rate limiting
        start_time = datetime.now()

        # Apply rate limiting before the call
        rate_limiter.wait_if_needed(api_path)

        # Convert marketplace_ids to list
        marketplace_list = [mid.strip() for mid in marketplace_ids.split(",")]

        api_response = client.get_order_items(
            order_id=order_id, marketplace_ids=marketplace_list if marketplace_ids else None
        )

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        # 7. Extract order items from response
        if not api_response.get("success"):
            return json.dumps(api_response, indent=2)

        order_items = api_response.get("data", {}).get("OrderItems", [])
        original_size = len(json.dumps(api_response, default=str))

        # 8. Apply filtering if requested
        filtered_data = order_items
        filters_applied = []

        if custom_filter:
            try:
                filter_result = filter_manager.apply_enhanced_filtering(
                    data=filtered_data,
                    custom_filter=custom_filter,
                    endpoint="get_order_items",
                )
                if filter_result["success"]:
                    filtered_data = filter_result["data"]
                    filters_applied.append("custom_filter")
            except Exception as e:
                print(f"Custom filter failed: {e}")
                # Include filtering error but don't fail the request

        elif filter_chain:
            try:
                filter_result = filter_manager.apply_enhanced_filtering(
                    data=filtered_data,
                    filter_chain=filter_chain,
                    filter_params=filter_params,
                    endpoint="get_order_items",
                )
                if filter_result["success"]:
                    filtered_data = filter_result["data"]
                    filters_applied.extend(filter_chain.split(","))
            except Exception as e:
                print(f"Filter chain failed: {e}")
                # Include filtering error but don't fail the request

        elif filter_id:
            try:
                filter_result = filter_manager.apply_enhanced_filtering(
                    data=filtered_data,
                    filter_id=filter_id,
                    filter_params=filter_params,
                    endpoint="get_order_items",
                )
                if filter_result["success"]:
                    filtered_data = filter_result["data"]
                    filters_applied.append(filter_id)
            except Exception as e:
                print(f"Filter by ID failed: {e}")
                # Include filtering error but don't fail the request

        elif reduce_response:
            # Apply default summary filter
            try:
                filter_result = filter_manager.apply_enhanced_filtering(
                    data=filtered_data, filter_id="order_items_summary", endpoint="get_order_items"
                )
                if filter_result["success"]:
                    filtered_data = filter_result["data"]
                    filters_applied.append("order_items_summary")
            except Exception as e:
                print(f"Response reduction failed: {e}")
                # Include filtering error but don't fail the request

        final_size = len(json.dumps(filtered_data, default=str))
        reduction_percent = ((original_size - final_size) / original_size * 100) if original_size > 0 else 0

        # 9. Build response
        response_data = {
            "success": True,
            "order_id": order_id,
            "items_count": len(filtered_data),
            "order_items": filtered_data,
            "filtering": {
                "original_size_bytes": original_size,
                "final_size_bytes": final_size,
                "reduction_percent": round(reduction_percent, 1),
                "execution_time_ms": round(execution_time, 2),
                "filters_applied": filters_applied,
                "timestamp": datetime.now().isoformat() + "Z",
            },
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
                "rate_limit_info": {
                    "endpoint": "getOrderItems",
                    "rate_limit": "0.5 requests/second",
                    "burst_capacity": 30,
                    "next_request_available_in": rate_limiter.get_wait_time(api_path),
                },
            },
        }

        # 10. Save JSON to received-json folder
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            received_json_dir = Path("received-json")
            received_json_dir.mkdir(exist_ok=True)

            filename = f"order_items_{order_id}_{timestamp}.json"
            file_path = received_json_dir / filename

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(response_data, f, indent=2, default=str)

        except Exception as e:
            # Log error but don't fail the main operation
            print(f"Warning: Failed to save JSON file: {e}")

        return json.dumps(response_data, indent=2, default=str)

    except Exception as e:
        error_response = {
            "success": False,
            "error": "unexpected_error",
            "message": f"An unexpected error occurred: {e!s}",
            "order_id": order_id,
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            },
        }
        return json.dumps(error_response, indent=2)


@mcp.tool()
@handle_sp_api_errors
def get_bulk_order_items(
    auth_token: Annotated[
        str,
        "Authentication token obtained from get_auth_token(). Required for this function to work.",
    ],
    order_ids: Annotated[str, "Comma-separated list of Amazon Order IDs to retrieve items for"],
    filter_id: Annotated[str, "Filter to apply for data reduction (highly recommended)"] = "order_items_summary",
    max_concurrent: Annotated[int, "Maximum concurrent requests (max 5 recommended)"] = 3,
    delay_between_batches: Annotated[float, "Delay between batches in seconds"] = 10.0,
    marketplace_ids: Annotated[
        str, "Comma-separated marketplace IDs (e.g., 'A1F83G8C2ARO7P' for UK)"
    ] = "A1F83G8C2ARO7P",
    region: Annotated[str, "AWS region for the SP-API endpoint"] = "eu-west-1",
    endpoint: Annotated[str, "SP-API endpoint URL"] = "https://sellingpartnerapi-eu.amazon.com",
) -> str:
    """Retrieve order items for multiple orders with intelligent rate limiting.

    REQUIRES AUTHENTICATION: You must provide a valid auth_token obtained from get_auth_token().

    This function handles bulk retrieval of order items across multiple orders
    while respecting SP-API rate limits. It processes orders in batches with
    delays to prevent rate limit violations.

    CRITICAL: This function can take significant time for large order sets.
    Example: 100 orders = ~200 seconds minimum (due to 0.5 req/sec limit).

    RECOMMENDED: Always use a filter (default: order_items_summary) to reduce
    response size and improve performance. Without filtering, responses can be
    extremely large and slow to process.

    Rate Limiting Strategy:
    - Enforces 0.5 requests/second limit (2+ second delays)
    - Processes orders in small batches
    - Provides progress updates and time estimates
    - Handles rate limit errors gracefully

    Args:
        auth_token: Authentication token
        order_ids: Comma-separated list of Amazon Order IDs
        filter_id: Filter to apply for data reduction (highly recommended)
        max_concurrent: Maximum concurrent requests (max 5 recommended)
        delay_between_batches: Delay between batches in seconds

    Also requires environment variables:
    - LWA_CLIENT_ID: Login with Amazon client ID
    - LWA_CLIENT_SECRET: Login with Amazon client secret
    - LWA_REFRESH_TOKEN: Login with Amazon refresh token
    - AWS_ACCESS_KEY_ID: AWS access key
    - AWS_SECRET_ACCESS_KEY: AWS secret key
    - AWS_ROLE_ARN: AWS role ARN (optional, has default)
    """
    # 1. Validate authentication
    if not validate_auth_token(auth_token):
        return json.dumps(
            {
                "success": False,
                "error": "invalid_auth",
                "message": "Invalid or missing auth token. Call get_auth_token() first.",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # 2. Parse and validate order IDs
    order_list = [oid.strip() for oid in order_ids.split(",") if oid.strip()]

    if not order_list:
        return json.dumps(
            {
                "success": False,
                "error": "invalid_input",
                "message": "No valid order IDs provided.",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    if len(order_list) > 100:
        return json.dumps(
            {
                "success": False,
                "error": "too_many_orders",
                "message": "Maximum 100 orders per bulk request. Use pagination for larger sets.",
                "provided_count": len(order_list),
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # 3. Validate order ID formats
    invalid_orders = [oid for oid in order_list if not validate_amazon_order_id(oid)]
    if invalid_orders:
        return json.dumps(
            {
                "success": False,
                "error": "invalid_input",
                "message": f"Invalid order ID format(s): {', '.join(invalid_orders[:5])}",
                "invalid_orders": invalid_orders,
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # 4. Process orders with rate limiting
    results = []
    errors = []
    total_start_time = datetime.now()

    # Calculate time estimates
    estimated_time_seconds = len(order_list) * 2.1  # 2.1 seconds per request (0.5 req/sec + buffer)

    # Process in batches to respect rate limits
    batch_size = min(max_concurrent, 3)  # Conservative batch size
    processed_count = 0

    try:
        for i in range(0, len(order_list), batch_size):
            batch = order_list[i : i + batch_size]
            datetime.now()

            for order_id in batch:
                try:
                    # Call get_order_items with rate limiting
                    result_json = get_order_items(
                        auth_token=auth_token,
                        order_id=order_id,
                        filter_id=filter_id,
                        marketplace_ids=marketplace_ids,
                        region=region,
                        endpoint=endpoint,
                    )

                    result = json.loads(result_json)
                    if result.get("success"):
                        results.append({
                            "order_id": order_id,
                            "items": result.get("order_items", []),
                            "items_count": result.get("items_count", 0),
                            "filtering": result.get("filtering", {}),
                        })
                    else:
                        errors.append({
                            "order_id": order_id,
                            "error": result.get("error"),
                            "message": result.get("message"),
                        })

                    processed_count += 1

                    # Rate limiting: 0.5 req/sec = 2+ seconds between requests
                    if processed_count < len(order_list):  # Don't wait after the last request
                        import time

                        time.sleep(2.1)  # Slightly more than 2 seconds to be safe

                except Exception as e:
                    errors.append({"order_id": order_id, "error": "unexpected_error", "message": str(e)})
                    processed_count += 1

            # Progress update (could be logged or returned in streaming response)
            (processed_count / len(order_list)) * 100
            elapsed_time = (datetime.now() - total_start_time).total_seconds()
            (estimated_time_seconds - elapsed_time) if elapsed_time < estimated_time_seconds else 0

            # Delay between batches (in addition to per-request delays)
            if i + batch_size < len(order_list):
                import time

                time.sleep(delay_between_batches)

    except KeyboardInterrupt:
        # Handle graceful shutdown if interrupted
        return json.dumps(
            {
                "success": False,
                "error": "interrupted",
                "message": "Bulk processing was interrupted",
                "partial_results": {
                    "orders_processed": len(results),
                    "orders_failed": len(errors),
                    "results": results,
                    "errors": errors,
                },
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # 5. Calculate final statistics
    total_time = (datetime.now() - total_start_time).total_seconds()
    total_items = sum(r["items_count"] for r in results)

    # 6. Calculate data reduction statistics
    if results:
        total_original_size = sum(r["filtering"].get("original_size_bytes", 0) for r in results if "filtering" in r)
        total_final_size = sum(r["filtering"].get("final_size_bytes", 0) for r in results if "filtering" in r)
        overall_reduction = (
            ((total_original_size - total_final_size) / total_original_size * 100) if total_original_size > 0 else 0
        )
    else:
        total_original_size = total_final_size = overall_reduction = 0

    # 7. Build comprehensive response
    response_data = {
        "success": True,
        "summary": {
            "orders_requested": len(order_list),
            "orders_processed": len(results),
            "orders_failed": len(errors),
            "total_items": total_items,
            "processing_time_seconds": round(total_time, 1),
            "filter_applied": filter_id,
        },
        "performance": {
            "average_time_per_order": round(total_time / len(order_list), 2),
            "rate_limit_compliance": "0.5 requests/second maintained",
            "estimated_vs_actual": {
                "estimated_seconds": round(estimated_time_seconds, 1),
                "actual_seconds": round(total_time, 1),
                "variance": round(((total_time - estimated_time_seconds) / estimated_time_seconds * 100), 1),
            },
        },
        "data_reduction": {
            "total_original_size_bytes": total_original_size,
            "total_final_size_bytes": total_final_size,
            "overall_reduction_percent": round(overall_reduction, 1),
            "filter_effectiveness": "High" if overall_reduction > 80 else "Medium" if overall_reduction > 50 else "Low",
        },
        "results": results,
        "errors": errors if errors else None,
        "metadata": {
            "timestamp": datetime.now().isoformat() + "Z",
            "request_id": str(uuid.uuid4()),
            "rate_limit_info": {
                "endpoint": "getOrderItems (bulk)",
                "rate_limit": "0.5 requests/second",
                "total_requests_made": len(results) + len(errors),
                "estimated_time_for_100_orders": "~210 seconds (3.5 minutes)",
            },
        },
    }

    # 8. Save bulk results to received-json folder
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        received_json_dir = Path("received-json")
        received_json_dir.mkdir(exist_ok=True)

        filename = f"bulk_order_items_{len(order_list)}_orders_{timestamp}.json"
        file_path = received_json_dir / filename

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(response_data, f, indent=2, default=str)

    except Exception as e:
        # Log error but don't fail the main operation
        print(f"Warning: Failed to save bulk results JSON file: {e}")

    return json.dumps(response_data, indent=2, default=str)


@mcp.tool()
@handle_sp_api_errors
@cached_api_call(cache_type="inventory")
def get_inventory_in_stock(
    auth_token: Annotated[
        str,
        "Authentication token obtained from get_auth_token(). Required for this function to work.",
    ],
    marketplace_ids: Annotated[
        str, "Comma-separated marketplace IDs (e.g., 'A1F83G8C2ARO7P' for UK)"
    ] = "A1F83G8C2ARO7P",
    fulfillment_type: Annotated[
        str,
        "Filter by fulfillment type: 'FBA' (Fulfilled by Amazon), 'FBM' (Fulfilled by Merchant), or 'ALL' (both)",
    ] = "ALL",
    details: Annotated[
        bool,
        "Include detailed inventory breakdown (fulfillable, unfulfillable, reserved, inbound)",
    ] = True,
    max_results: Annotated[int, "Maximum number of inventory items to return (default 1000)"] = 1000,
    region: Annotated[str, "AWS region for the SP-API endpoint"] = "eu-west-1",
    endpoint: Annotated[str, "SP-API endpoint URL"] = "https://sellingpartnerapi-eu.amazon.com",
    filter_id: Annotated[
        str,
        "Filter ID from database to apply to results (use get_available_filters to discover). Reduces response size dramatically.",
    ] = "",
    filter_chain: Annotated[
        str,
        "Comma-separated chain of filter IDs for complex data reduction (e.g., 'low_stock_alert,inventory_summary' for 95% reduction)",
    ] = "",
    custom_filter: Annotated[str, "Custom JSON Query expression for advanced filtering"] = "",
    filter_params: Annotated[str, "JSON string of filter parameters (e.g., '{\"threshold\": 10}')"] = "{}",
    reduce_response: Annotated[bool, "Apply default data reduction filter to minimize response size"] = False,
) -> str:
    """Retrieve all products currently in stock with their inventory information.

    REQUIRES AUTHENTICATION: You must provide a valid auth_token obtained from get_auth_token().

    This endpoint fetches inventory data and filters to show only products with available stock.
    You can filter by fulfillment type:
    - 'FBA': Only show Fulfilled by Amazon inventory
    - 'FBM': Only show Fulfilled by Merchant inventory (Note: Limited data available via FBA Inventory API)
    - 'ALL': Show both FBA and FBM inventory (default)

    Returns interesting information including quantities, product identifiers, and inventory status.

    Also requires environment variables:
    - LWA_CLIENT_ID: Login with Amazon client ID
    - LWA_CLIENT_SECRET: Login with Amazon client secret
    - LWA_REFRESH_TOKEN: Login with Amazon refresh token
    - AWS_ACCESS_KEY_ID: AWS access key
    - AWS_SECRET_ACCESS_KEY: AWS secret key
    - AWS_ROLE_ARN: AWS role ARN (optional, has default)
    """
    # 1. Validate auth token
    if not validate_auth_token(auth_token):
        return json.dumps(
            {
                "success": False,
                "error": "auth_failed",
                "message": "Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token.",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # 2. Get credentials
    access_token = get_amazon_access_token()
    if not access_token:
        return json.dumps(
            {
                "success": False,
                "error": "auth_failed",
                "message": "Failed to get Amazon access token. Check your LWA credentials.",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    aws_creds = get_amazon_aws_credentials()
    if not aws_creds:
        return json.dumps(
            {
                "success": False,
                "error": "auth_failed",
                "message": "Failed to get AWS credentials. Check your AWS credentials and role.",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # 3. Use InventoryAPIClient
    client = InventoryAPIClient(access_token, aws_creds, region, endpoint)

    # 4. Make API call
    result = client.get_inventory_summaries(
        marketplace_ids=marketplace_ids,
        fulfillment_type=fulfillment_type,
        details=details,
        max_results=max_results,
    )

    # 5. Apply filtering if requested
    if filter_id or filter_chain or custom_filter or reduce_response:
        try:
            # Extract inventory data for filtering
            inventory_data = result.get("data", {}).get("inventorySummaries", [])

            filter_result = filter_manager.apply_enhanced_filtering(
                data=inventory_data,
                filter_id=filter_id,
                filter_chain=filter_chain,
                custom_filter=custom_filter,
                filter_params=filter_params,
                reduce_response=reduce_response,
                endpoint="get_inventory_in_stock",
            )

            if filter_result["success"]:
                # Update result with filtered data and metadata
                if "data" in result and "inventorySummaries" in result["data"]:
                    result["data"]["inventorySummaries"] = filter_result["data"]
                    result["data"]["totalCount"] = (
                        len(filter_result["data"]) if isinstance(filter_result["data"], list) else 1
                    )
                result["filtering"] = filter_result["metadata"]
            else:
                # Include filtering error but don't fail the request
                result["filtering_error"] = filter_result.get("message", "Unknown filtering error")

        except Exception as e:
            # Include filtering error but don't fail the request
            result["filtering_error"] = f"Filter application failed: {e!s}"

    # 6. Return formatted JSON
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_sp_api_errors
@cached_api_call(cache_type="listings")
def get_fbm_inventory(
    auth_token: Annotated[
        str,
        "Authentication token obtained from get_auth_token(). Required for this function to work.",
    ],
    seller_id: Annotated[str, "The seller ID for the merchant account"],
    seller_sku: Annotated[
        str,
        "Specific SKU to retrieve. If not provided, use get_fbm_inventory_report for bulk data",
    ],
    marketplace_ids: Annotated[
        str, "Comma-separated marketplace IDs (e.g., 'A1F83G8C2ARO7P' for UK)"
    ] = "A1F83G8C2ARO7P",
    include_inactive: Annotated[bool, "Include inactive listings in the results"] = False,
    region: Annotated[str, "AWS region for the SP-API endpoint"] = "eu-west-1",
    endpoint: Annotated[str, "SP-API endpoint URL"] = "https://sellingpartnerapi-eu.amazon.com",
) -> str:
    """Get FBM (Fulfilled by Merchant) inventory using Listings API for real-time data.

    REQUIRES AUTHENTICATION: You must provide a valid auth_token obtained from get_auth_token().

    This endpoint retrieves individual FBM product listings with real-time fulfillment availability,
    handling time, and stock levels. Use this for checking specific SKUs.

    For bulk inventory data, use get_fbm_inventory_report instead.

    Also requires environment variables:
    - LWA_CLIENT_ID: Login with Amazon client ID
    - LWA_CLIENT_SECRET: Login with Amazon client secret
    - LWA_REFRESH_TOKEN: Login with Amazon refresh token
    - AWS_ACCESS_KEY_ID: AWS access key
    - AWS_SECRET_ACCESS_KEY: AWS secret key
    - AWS_ROLE_ARN: AWS role ARN (optional, has default)
    """
    # 1. Validate auth token
    if not validate_auth_token(auth_token):
        return json.dumps(
            {
                "success": False,
                "error": "auth_failed",
                "message": "Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token.",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # 2. Validate inputs
    if not seller_id:
        return json.dumps(
            {
                "success": False,
                "error": "invalid_input",
                "message": "seller_id is required",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    if not validate_seller_sku(seller_sku):
        return json.dumps(
            {
                "success": False,
                "error": "invalid_input",
                "message": "Invalid SKU format",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # 3. Get credentials
    access_token = get_amazon_access_token()
    if not access_token:
        return json.dumps(
            {
                "success": False,
                "error": "auth_failed",
                "message": "Failed to get Amazon access token. Check your LWA credentials.",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    aws_creds = get_amazon_aws_credentials()
    if not aws_creds:
        return json.dumps(
            {
                "success": False,
                "error": "auth_failed",
                "message": "Failed to get AWS credentials. Check your AWS credentials and role.",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # 4. Use ListingsAPIClient
    client = ListingsAPIClient(access_token, aws_creds, region, endpoint)

    # 5. Make API call
    result = client.get_listings_item(
        seller_id=seller_id,
        sku=seller_sku,
        marketplace_ids=marketplace_ids,
        included_data=["summaries", "attributes", "offers", "fulfillmentAvailability"],
    )

    # 6. Return formatted JSON
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_sp_api_errors
def get_fbm_inventory_report(
    auth_token: Annotated[
        str,
        "Authentication token obtained from get_auth_token(). Required for this function to work.",
    ],
    report_type: Annotated[
        str,
        "Report type: 'ALL_DATA' (all listings), 'ACTIVE' (active only), or 'INACTIVE' (inactive only)",
    ] = "ALL_DATA",
    marketplace_ids: Annotated[
        str, "Comma-separated marketplace IDs (e.g., 'A1F83G8C2ARO7P' for UK)"
    ] = "A1F83G8C2ARO7P",
    start_date: Annotated[Optional[str], "ISO 8601 format start date for the report data"] = None,
    end_date: Annotated[Optional[str], "ISO 8601 format end date for the report data"] = None,
    region: Annotated[str, "AWS region for the SP-API endpoint"] = "eu-west-1",
    endpoint: Annotated[str, "SP-API endpoint URL"] = "https://sellingpartnerapi-eu.amazon.com",
) -> str:
    """Generate and retrieve FBM inventory report for bulk data.

    REQUIRES AUTHENTICATION: You must provide a valid auth_token obtained from get_auth_token().

    This endpoint creates a report request for comprehensive FBM inventory data.
    Reports provide bulk data for all FBM listings but are not real-time.

    Report types:
    - 'ALL_DATA': GET_MERCHANT_LISTINGS_ALL_DATA - All listings
    - 'ACTIVE': GET_MERCHANT_LISTINGS_DATA - Active listings only
    - 'INACTIVE': GET_MERCHANT_LISTINGS_INACTIVE_DATA - Inactive listings only

    Note: This function creates the report request. The report generation is asynchronous.
    You'll need to check the report status and download it when ready.

    Also requires environment variables:
    - LWA_CLIENT_ID: Login with Amazon client ID
    - LWA_CLIENT_SECRET: Login with Amazon client secret
    - LWA_REFRESH_TOKEN: Login with Amazon refresh token
    - AWS_ACCESS_KEY_ID: AWS access key
    - AWS_SECRET_ACCESS_KEY: AWS secret key
    - AWS_ROLE_ARN: AWS role ARN (optional, has default)
    """
    # 1. Validate auth token
    if not validate_auth_token(auth_token):
        return json.dumps(
            {
                "success": False,
                "error": "auth_failed",
                "message": "Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token.",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # 2. Map report type
    report_type_map = {
        "ALL_DATA": "GET_MERCHANT_LISTINGS_ALL_DATA",
        "ACTIVE": "GET_MERCHANT_LISTINGS_DATA",
        "INACTIVE": "GET_MERCHANT_LISTINGS_INACTIVE_DATA",
    }

    if report_type not in report_type_map:
        return json.dumps(
            {
                "success": False,
                "error": "invalid_input",
                "message": f"Invalid report_type. Must be one of: {', '.join(report_type_map.keys())}",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # 3. Get credentials
    access_token = get_amazon_access_token()
    if not access_token:
        return json.dumps(
            {
                "success": False,
                "error": "auth_failed",
                "message": "Failed to get Amazon access token. Check your LWA credentials.",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    aws_creds = get_amazon_aws_credentials()
    if not aws_creds:
        return json.dumps(
            {
                "success": False,
                "error": "auth_failed",
                "message": "Failed to get AWS credentials. Check your AWS credentials and role.",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # 4. Use ReportsAPIClient
    client = ReportsAPIClient(access_token, aws_creds, region, endpoint)

    # 5. Make API call
    result = client.create_report(
        report_type=report_type_map[report_type],
        marketplace_ids=marketplace_ids,
        start_date=start_date,
        end_date=end_date,
    )

    # 6. Return formatted JSON
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_sp_api_errors
def update_fbm_inventory(
    auth_token: Annotated[
        str,
        "Authentication token obtained from get_auth_token(). Required for this function to work.",
    ],
    seller_id: Annotated[str, "The seller ID for the merchant account"],
    seller_sku: Annotated[str, "SKU to update"],
    quantity: Annotated[int, "New quantity available (must be >= 0)"],
    handling_time: Annotated[
        Optional[int],
        "Days to ship (1-30). If not provided, existing value is retained",
    ] = None,
    restock_date: Annotated[Optional[str], "ISO 8601 format restock date (must be in the future)"] = None,
    marketplace_ids: Annotated[
        str, "Comma-separated marketplace IDs (e.g., 'A1F83G8C2ARO7P' for UK)"
    ] = "A1F83G8C2ARO7P",
    region: Annotated[str, "AWS region for the SP-API endpoint"] = "eu-west-1",
    endpoint: Annotated[str, "SP-API endpoint URL"] = "https://sellingpartnerapi-eu.amazon.com",
) -> str:
    """Update FBM inventory quantity and fulfillment details.

    REQUIRES AUTHENTICATION: You must provide a valid auth_token obtained from get_auth_token().

    This endpoint updates individual FBM product inventory levels and fulfillment settings.
    Use this for single SKU updates. For bulk updates, use bulk_update_fbm_inventory.

    Parameters:
    - quantity: Must be >= 0. Set to 0 to mark as out of stock.
    - handling_time: Days needed to ship (1-30 days)
    - restock_date: Future date when item will be back in stock

    Also requires environment variables:
    - LWA_CLIENT_ID: Login with Amazon client ID
    - LWA_CLIENT_SECRET: Login with Amazon client secret
    - LWA_REFRESH_TOKEN: Login with Amazon refresh token
    - AWS_ACCESS_KEY_ID: AWS access key
    - AWS_SECRET_ACCESS_KEY: AWS secret key
    - AWS_ROLE_ARN: AWS role ARN (optional, has default)
    """
    # 1. Validate auth token
    if not validate_auth_token(auth_token):
        return json.dumps(
            {
                "success": False,
                "error": "auth_failed",
                "message": "Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token.",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # 2. Validate inputs
    validation_errors = []

    if not seller_id:
        validation_errors.append("seller_id is required")

    if not validate_seller_sku(seller_sku):
        validation_errors.append("Invalid SKU format")

    if not validate_fbm_quantity(quantity):
        validation_errors.append("Quantity must be >= 0")

    if handling_time is not None and not validate_handling_time(handling_time):
        validation_errors.append("Handling time must be between 1-30 days")

    if validation_errors:
        return json.dumps(
            {
                "success": False,
                "error": "invalid_input",
                "message": "Input validation failed",
                "details": validation_errors,
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # 3. Get credentials
    access_token = get_amazon_access_token()
    if not access_token:
        return json.dumps(
            {
                "success": False,
                "error": "auth_failed",
                "message": "Failed to get Amazon access token. Check your LWA credentials.",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    aws_creds = get_amazon_aws_credentials()
    if not aws_creds:
        return json.dumps(
            {
                "success": False,
                "error": "auth_failed",
                "message": "Failed to get AWS credentials. Check your AWS credentials and role.",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # 4. Build patch operations
    patches = []

    # Update fulfillment availability
    fulfillment_data = {
        "fulfillmentChannelCode": "DEFAULT",  # FBM
        "quantity": quantity,
        "isAvailable": quantity > 0,
    }

    if handling_time is not None:
        fulfillment_data["handlingTime"] = {"max": handling_time}

    if restock_date is not None:
        fulfillment_data["restockDate"] = restock_date

    patches.append({
        "op": "replace",
        "path": "/attributes/fulfillment_availability",
        "value": [fulfillment_data],
    })

    # 5. Use ListingsAPIClient
    client = ListingsAPIClient(access_token, aws_creds, region, endpoint)

    # 6. Make API call
    result = client.patch_listings_item(
        seller_id=seller_id,
        sku=seller_sku,
        marketplace_ids=marketplace_ids,
        patches=patches,
    )

    # 7. Return formatted JSON
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_sp_api_errors
def bulk_update_fbm_inventory(
    auth_token: Annotated[
        str,
        "Authentication token obtained from get_auth_token(). Required for this function to work.",
    ],
    inventory_updates: Annotated[
        str,
        "JSON array of inventory updates. Each item must have: sku, quantity, and optionally handling_time and restock_date",
    ],
    marketplace_id: Annotated[str, "Target marketplace ID (e.g., 'A1F83G8C2ARO7P' for UK)"] = "A1F83G8C2ARO7P",
    region: Annotated[str, "AWS region for the SP-API endpoint"] = "eu-west-1",
    endpoint: Annotated[str, "SP-API endpoint URL"] = "https://sellingpartnerapi-eu.amazon.com",
) -> str:
    """Bulk update FBM inventory using Feeds API.

    REQUIRES AUTHENTICATION: You must provide a valid auth_token obtained from get_auth_token().

    This endpoint enables bulk updates of FBM inventory for multiple SKUs in a single operation.
    More efficient than individual updates for large catalogs.

    The inventory_updates parameter should be a JSON array like:
    [
        {
            "sku": "SKU123",
            "quantity": 50,
            "handling_time": 2,  // optional, days to ship (1-30)
            "restock_date": "2025-06-01T00:00:00Z"  // optional, ISO 8601 format
        },
        ...
    ]

    Maximum 10,000 items per feed.

    Also requires environment variables:
    - LWA_CLIENT_ID: Login with Amazon client ID
    - LWA_CLIENT_SECRET: Login with Amazon client secret
    - LWA_REFRESH_TOKEN: Login with Amazon refresh token
    - AWS_ACCESS_KEY_ID: AWS access key
    - AWS_SECRET_ACCESS_KEY: AWS secret key
    - AWS_ROLE_ARN: AWS role ARN (optional, has default)
    """
    # 1. Validate auth token
    if not validate_auth_token(auth_token):
        return json.dumps(
            {
                "success": False,
                "error": "auth_failed",
                "message": "Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token.",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # 2. Parse and validate inventory updates
    try:
        updates = json.loads(inventory_updates)
    except json.JSONDecodeError:
        return json.dumps(
            {
                "success": False,
                "error": "invalid_input",
                "message": "inventory_updates must be a valid JSON array",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # Validate updates
    is_valid, errors = validate_bulk_inventory_updates(updates)
    if not is_valid:
        return json.dumps(
            {
                "success": False,
                "error": "invalid_input",
                "message": "Validation failed for inventory updates",
                "details": errors,
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # 3. Get credentials
    access_token = get_amazon_access_token()
    if not access_token:
        return json.dumps(
            {
                "success": False,
                "error": "auth_failed",
                "message": "Failed to get Amazon access token. Check your LWA credentials.",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    aws_creds = get_amazon_aws_credentials()
    if not aws_creds:
        return json.dumps(
            {
                "success": False,
                "error": "auth_failed",
                "message": "Failed to get AWS credentials. Check your AWS credentials and role.",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # 4. Use FeedsAPIClient
    client = FeedsAPIClient(access_token, aws_creds, region, endpoint)

    # 5. Create feed document
    doc_result = client.create_feed_document(content_type="XML")
    if not doc_result.get("success"):
        return json.dumps(doc_result, indent=2)

    feed_document_id = doc_result["data"]["feedDocumentId"]
    upload_url = doc_result["data"]["url"]

    # 6. Build and upload XML feed content
    xml_content = client.build_inventory_feed_xml(updates)

    # Upload to S3
    upload_response = requests.put(
        upload_url,
        data=xml_content.encode("utf-8"),
        headers={"Content-Type": "text/xml; charset=UTF-8"},
        timeout=60,
    )
    upload_response.raise_for_status()

    # 7. Create feed
    feed_result = client.create_feed(
        feed_type="POST_INVENTORY_AVAILABILITY_DATA",
        marketplace_ids=marketplace_id,
        feed_document_id=feed_document_id,
    )

    # 8. Return formatted JSON
    return json.dumps(feed_result, indent=2)


@mcp.tool()
@handle_sp_api_errors
def update_product_price(
    auth_token: Annotated[
        str,
        "Authentication token obtained from get_auth_token(). Required for this function to work.",
    ],
    seller_id: Annotated[str, "The seller ID for the merchant account"],
    seller_sku: Annotated[str, "SKU of the product to update"],
    new_price: Annotated[str, "New price value (e.g., '69.98' for £69.98)"],
    currency: Annotated[str, "Currency code (e.g., 'GBP', 'EUR', 'USD')"] = "GBP",
    marketplace_ids: Annotated[
        str, "Comma-separated marketplace IDs (e.g., 'A1F83G8C2ARO7P' for UK)"
    ] = "A1F83G8C2ARO7P",
    region: Annotated[str, "AWS region for the SP-API endpoint"] = "eu-west-1",
    endpoint: Annotated[str, "SP-API endpoint URL"] = "https://sellingpartnerapi-eu.amazon.com",
) -> str:
    """Update product price on Amazon.

    REQUIRES AUTHENTICATION: You must provide a valid auth_token obtained from get_auth_token().

    This endpoint updates the price of a product listing on Amazon.
    Works for both FBA and FBM products.

    Parameters:
    - seller_sku: The SKU of the product to update
    - new_price: The new price (number only, e.g., '69.98')
    - currency: Currency code (default: GBP for UK marketplace)

    Note: Price updates typically take 5-15 minutes to reflect on Amazon.

    Also requires environment variables:
    - LWA_CLIENT_ID: Login with Amazon client ID
    - LWA_CLIENT_SECRET: Login with Amazon client secret
    - LWA_REFRESH_TOKEN: Login with Amazon refresh token
    - AWS_ACCESS_KEY_ID: AWS access key
    - AWS_SECRET_ACCESS_KEY: AWS secret key
    - AWS_ROLE_ARN: AWS role ARN (optional, has default)
    """
    # 1. Validate auth token
    if not validate_auth_token(auth_token):
        return json.dumps(
            {
                "success": False,
                "error": "auth_failed",
                "message": "Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token.",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # 2. Validate inputs
    validation_errors = []

    if not seller_id:
        validation_errors.append("seller_id is required")

    if not validate_seller_sku(seller_sku):
        validation_errors.append("Invalid SKU format")

    # Validate price format
    try:
        price_float = float(new_price)
        if price_float < 0:
            validation_errors.append("Price must be positive")
    except ValueError:
        validation_errors.append("Invalid price format. Use numeric value like '69.98'")

    if currency not in ["GBP", "EUR", "USD", "CAD", "AUD", "JPY"]:
        validation_errors.append(f"Unsupported currency: {currency}")

    if validation_errors:
        return json.dumps(
            {
                "success": False,
                "error": "invalid_input",
                "message": "Input validation failed",
                "details": validation_errors,
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # 3. Get credentials
    access_token = get_amazon_access_token()
    if not access_token:
        return json.dumps(
            {
                "success": False,
                "error": "auth_failed",
                "message": "Failed to get Amazon access token. Check your LWA credentials.",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    aws_creds = get_amazon_aws_credentials()
    if not aws_creds:
        return json.dumps(
            {
                "success": False,
                "error": "auth_failed",
                "message": "Failed to get AWS credentials. Check your AWS credentials and role.",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # 4. Build patch operations for price update
    patches = [
        {
            "op": "replace",
            "path": "/attributes/purchasable_offer",
            "value": [
                {
                    "audience": "ALL",
                    "our_price": [{"schedule": [{"value_with_tax": new_price}]}],
                }
            ],
        }
    ]

    # 5. Use ListingsAPIClient
    client = ListingsAPIClient(access_token, aws_creds, region, endpoint)

    # 6. Make API call
    result = client.patch_listings_item(
        seller_id=seller_id,
        sku=seller_sku,
        marketplace_ids=marketplace_ids,
        patches=patches,
    )

    # 7. Add price info to success response
    if result.get("success"):
        result["price_update"] = {
            "sku": seller_sku,
            "new_price": f"{currency} {new_price}",
            "marketplace": marketplace_ids,
            "note": "Price updates typically take 5-15 minutes to reflect on Amazon",
        }

    # 8. Return formatted JSON
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_sp_api_errors
@cached_api_call(cache_type="reports")
def get_sales_and_traffic_report(
    auth_token: Annotated[
        str,
        "Authentication token obtained from get_auth_token(). Required for this function to work.",
    ],
    start_date: Annotated[str, "Start date in ISO 8601 format (e.g., '2025-01-01T00:00:00Z')"],
    end_date: Annotated[str, "End date in ISO 8601 format (e.g., '2025-01-31T23:59:59Z')"],
    marketplace_ids: Annotated[
        str, "Comma-separated marketplace IDs (e.g., 'A1F83G8C2ARO7P' for UK)"
    ] = "A1F83G8C2ARO7P",
    report_period: Annotated[str, "Report period: 'DAILY', 'WEEKLY', 'MONTHLY', or 'YEARLY'"] = "MONTHLY",
    aggregation_level: Annotated[str, "Aggregation level: 'SKU', 'PARENT', or 'CHILD'"] = "SKU",
    region: Annotated[str, "AWS region for the SP-API endpoint"] = "eu-west-1",
    endpoint: Annotated[str, "SP-API endpoint URL"] = "https://sellingpartnerapi-eu.amazon.com",
) -> str:
    """Get sales and traffic analytics report from Amazon Seller Central.

    REQUIRES AUTHENTICATION: You must provide a valid auth_token obtained from get_auth_token().

    This endpoint provides comprehensive sales and traffic analytics data including:
    - Sales metrics (units ordered, revenue, conversion rates)
    - Traffic metrics (page views, sessions, click-through rates)
    - Customer behavior analytics

    Also requires environment variables:
    - LWA_CLIENT_ID: Login with Amazon client ID
    - LWA_CLIENT_SECRET: Login with Amazon client secret
    - LWA_REFRESH_TOKEN: Login with Amazon refresh token
    - AWS_ACCESS_KEY_ID: AWS access key
    - AWS_SECRET_ACCESS_KEY: AWS secret key
    - AWS_ROLE_ARN: AWS role ARN (optional, has default)
    """
    # 1. Validate auth token
    if not validate_auth_token(auth_token):
        return json.dumps(
            {
                "success": False,
                "error": "auth_failed",
                "message": "Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token.",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # 2. Apply rate limiting
    rate_limiter.wait_if_needed("sales_and_traffic")

    # 3. Get credentials
    access_token = get_amazon_access_token()
    aws_creds = get_amazon_aws_credentials()

    # 4. Use ReportsAPIClient
    client = ReportsAPIClient(access_token, aws_creds, region, endpoint)

    # 5. Create sales and traffic report
    result = client.create_sales_and_traffic_report(
        marketplace_ids=marketplace_ids,
        report_period=report_period,
        start_date=start_date,
        end_date=end_date,
        aggregation_level=aggregation_level,
    )

    # 6. Return formatted JSON
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_sp_api_errors
@cached_api_call(cache_type="reports")
def create_report(
    auth_token: Annotated[
        str,
        "Authentication token obtained from get_auth_token(). Required for this function to work.",
    ],
    report_type: Annotated[
        str,
        "Report type (e.g., 'GET_SALES_AND_TRAFFIC_REPORT', 'GET_MERCHANT_LISTINGS_ALL_DATA')",
    ],
    marketplace_ids: Annotated[
        str, "Comma-separated marketplace IDs (e.g., 'A1F83G8C2ARO7P' for UK)"
    ] = "A1F83G8C2ARO7P",
    start_date: Annotated[Optional[str], "Start date in ISO 8601 format (optional)"] = None,
    end_date: Annotated[Optional[str], "End date in ISO 8601 format (optional)"] = None,
    report_options: Annotated[str, "JSON string of additional report options"] = "{}",
    region: Annotated[str, "AWS region for the SP-API endpoint"] = "eu-west-1",
    endpoint: Annotated[str, "SP-API endpoint URL"] = "https://sellingpartnerapi-eu.amazon.com",
) -> str:
    """Create a report request in Amazon Seller Central.

    REQUIRES AUTHENTICATION: You must provide a valid auth_token obtained from get_auth_token().

    This endpoint creates various types of reports including:
    - Sales reports
    - Inventory reports
    - Order reports
    - Performance reports

    Also requires environment variables:
    - LWA_CLIENT_ID: Login with Amazon client ID
    - LWA_CLIENT_SECRET: Login with Amazon client secret
    - LWA_REFRESH_TOKEN: Login with Amazon refresh token
    - AWS_ACCESS_KEY_ID: AWS access key
    - AWS_SECRET_ACCESS_KEY: AWS secret key
    - AWS_ROLE_ARN: AWS role ARN (optional, has default)
    """
    # 1. Validate auth token
    if not validate_auth_token(auth_token):
        return json.dumps(
            {
                "success": False,
                "error": "auth_failed",
                "message": "Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token.",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # 2. Apply rate limiting
    rate_limiter.wait_if_needed("create_report")

    # 3. Get credentials
    access_token = get_amazon_access_token()
    aws_creds = get_amazon_aws_credentials()

    # 4. Use ReportsAPIClient
    client = ReportsAPIClient(access_token, aws_creds, region, endpoint)

    # 5. Parse report options
    try:
        options = json.loads(report_options) if report_options else {}
    except json.JSONDecodeError:
        return json.dumps(
            {
                "success": False,
                "error": "invalid_input",
                "message": "Invalid JSON format for report_options",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # 6. Create report
    result = client.create_report(
        report_type=report_type,
        marketplace_ids=marketplace_ids,
        start_date=start_date,
        end_date=end_date,
        report_options=options,
    )

    # 7. Return formatted JSON
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_sp_api_errors
@cached_api_call(cache_type="reports")
def get_report_status(
    auth_token: Annotated[
        str,
        "Authentication token obtained from get_auth_token(). Required for this function to work.",
    ],
    report_id: Annotated[str, "Report ID returned from create_report"],
    region: Annotated[str, "AWS region for the SP-API endpoint"] = "eu-west-1",
    endpoint: Annotated[str, "SP-API endpoint URL"] = "https://sellingpartnerapi-eu.amazon.com",
) -> str:
    """Get the status of a report request.

    REQUIRES AUTHENTICATION: You must provide a valid auth_token obtained from get_auth_token().

    This endpoint checks the processing status of a previously created report.
    Report statuses include: 'IN_QUEUE', 'IN_PROGRESS', 'DONE', 'CANCELLED', 'FATAL'

    Also requires environment variables:
    - LWA_CLIENT_ID: Login with Amazon client ID
    - LWA_CLIENT_SECRET: Login with Amazon client secret
    - LWA_REFRESH_TOKEN: Login with Amazon refresh token
    - AWS_ACCESS_KEY_ID: AWS access key
    - AWS_SECRET_ACCESS_KEY: AWS secret key
    - AWS_ROLE_ARN: AWS role ARN (optional, has default)
    """
    # 1. Validate auth token
    if not validate_auth_token(auth_token):
        return json.dumps(
            {
                "success": False,
                "error": "auth_failed",
                "message": "Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token.",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # 2. Apply rate limiting
    rate_limiter.wait_if_needed("get_report_status")

    # 3. Get credentials
    access_token = get_amazon_access_token()
    aws_creds = get_amazon_aws_credentials()

    # 4. Use ReportsAPIClient
    client = ReportsAPIClient(access_token, aws_creds, region, endpoint)

    # 5. Get report status
    result = client.get_report(report_id)

    # 6. Return formatted JSON
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_sp_api_errors
@cached_api_call(cache_type="reports")
def get_report_document(
    auth_token: Annotated[
        str,
        "Authentication token obtained from get_auth_token(). Required for this function to work.",
    ],
    report_document_id: Annotated[str, "Report document ID from a completed report"],
    region: Annotated[str, "AWS region for the SP-API endpoint"] = "eu-west-1",
    endpoint: Annotated[str, "SP-API endpoint URL"] = "https://sellingpartnerapi-eu.amazon.com",
) -> str:
    """Download and retrieve the content of a completed report.

    REQUIRES AUTHENTICATION: You must provide a valid auth_token obtained from get_auth_token().

    This endpoint downloads the actual report data once the report is in 'DONE' status.
    The report content is typically in CSV or JSON format.

    Also requires environment variables:
    - LWA_CLIENT_ID: Login with Amazon client ID
    - LWA_CLIENT_SECRET: Login with Amazon client secret
    - LWA_REFRESH_TOKEN: Login with Amazon refresh token
    - AWS_ACCESS_KEY_ID: AWS access key
    - AWS_SECRET_ACCESS_KEY: AWS secret key
    - AWS_ROLE_ARN: AWS role ARN (optional, has default)
    """
    # 1. Validate auth token
    if not validate_auth_token(auth_token):
        return json.dumps(
            {
                "success": False,
                "error": "auth_failed",
                "message": "Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token.",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # 2. Apply rate limiting
    rate_limiter.wait_if_needed("get_report_document")

    # 3. Get credentials
    access_token = get_amazon_access_token()
    aws_creds = get_amazon_aws_credentials()

    # 4. Use ReportsAPIClient
    client = ReportsAPIClient(access_token, aws_creds, region, endpoint)

    # 5. Get report document
    result = client.get_report_document(report_document_id)

    # 6. Return formatted JSON
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_sp_api_errors
@cached_api_call(cache_type="reports")
def get_inventory_analytics_report(
    auth_token: Annotated[
        str,
        "Authentication token obtained from get_auth_token(). Required for this function to work.",
    ],
    start_date: Annotated[str, "Start date in ISO 8601 format (e.g., '2025-01-01T00:00:00Z')"],
    end_date: Annotated[str, "End date in ISO 8601 format (e.g., '2025-01-31T23:59:59Z')"],
    marketplace_ids: Annotated[
        str, "Comma-separated marketplace IDs (e.g., 'A1F83G8C2ARO7P' for UK)"
    ] = "A1F83G8C2ARO7P",
    aggregation_level: Annotated[str, "Aggregation level: 'SKU', 'PARENT', or 'CHILD'"] = "SKU",
    include_forecasting: Annotated[bool, "Include inventory forecasting data"] = False,
    region: Annotated[str, "AWS region for the SP-API endpoint"] = "eu-west-1",
    endpoint: Annotated[str, "SP-API endpoint URL"] = "https://sellingpartnerapi-eu.amazon.com",
) -> str:
    """Get inventory analytics and performance metrics.

    REQUIRES AUTHENTICATION: You must provide a valid auth_token obtained from get_auth_token().

    This endpoint provides detailed inventory analytics including:
    - Inventory turnover rates
    - Stock-out frequency
    - Inventory performance metrics
    - Restock recommendations (if forecasting enabled)

    Also requires environment variables:
    - LWA_CLIENT_ID: Login with Amazon client ID
    - LWA_CLIENT_SECRET: Login with Amazon client secret
    - LWA_REFRESH_TOKEN: Login with Amazon refresh token
    - AWS_ACCESS_KEY_ID: AWS access key
    - AWS_SECRET_ACCESS_KEY: AWS secret key
    - AWS_ROLE_ARN: AWS role ARN (optional, has default)
    """
    # 1. Validate auth token
    if not validate_auth_token(auth_token):
        return json.dumps(
            {
                "success": False,
                "error": "auth_failed",
                "message": "Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token.",
                "metadata": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "request_id": str(uuid.uuid4()),
                },
            },
            indent=2,
        )

    # 2. Apply rate limiting
    rate_limiter.wait_if_needed("inventory_analytics")

    # 3. Get credentials
    access_token = get_amazon_access_token()
    aws_creds = get_amazon_aws_credentials()

    # 4. Use ReportsAPIClient
    client = ReportsAPIClient(access_token, aws_creds, region, endpoint)

    # 5. Create inventory analytics report
    result = client.create_inventory_analytics_report(
        marketplace_ids=marketplace_ids,
        start_date=start_date,
        end_date=end_date,
        aggregation_level=aggregation_level,
        include_forecasting=include_forecasting,
    )

    # 6. Return formatted JSON
    return json.dumps(result, indent=2)


def main() -> None:
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
