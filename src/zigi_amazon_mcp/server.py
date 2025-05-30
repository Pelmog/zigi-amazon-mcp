#!/usr/bin/env python3
"""MCP Server for Amazon Seller Central API integration using FastMCP.

This server provides authentication and comprehensive tools for interacting with
Amazon Seller Central through the SP-API, including inventory management,
order processing, and product listing management.
"""

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

from .api.inventory import InventoryAPIClient
from .api.listings import ListingsAPIClient
from .api.reports import ReportsAPIClient
from .api.feeds import FeedsAPIClient
from .utils.decorators import handle_sp_api_errors, cached_api_call
from .utils.rate_limiter import RateLimiter
from .utils.validators import (
    validate_seller_sku,
    validate_handling_time,
    validate_fbm_quantity,
    validate_bulk_inventory_updates,
)

# Load environment variables from .env file
load_dotenv()

mcp: FastMCP = FastMCP(
    "zigi-amazon-mcp",
    description="A comprehensive MCP server for Amazon Seller Central API integration, providing tools for e-commerce operations, inventory management, order processing, and data analytics.",
    version="1.0.0",
)


# Auth token storage - stores valid authentication tokens
auth_tokens: set[str] = set()

# Rate limiter instance for SP-API calls
rate_limiter = RateLimiter()


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


# Tool information dictionary for get_tool_info function
TOOL_INFO = {
    "get_auth_token": {
        "name": "get_auth_token",
        "category": "Authentication",
        "description": "Generate and return a new authentication token (session ID) that must be used for all other function calls. This is the FIRST function you must call before using any other functions in this MCP server.",
        "purpose": "Provides secure authentication for the MCP server session",
        "when_to_use": [
            "At the start of every new session",
            "When you receive an 'Invalid or missing auth token' error",
            "When switching between different users or sessions"
        ],
        "inputs": {
            "parameters": {},
            "required": [],
            "notes": "No parameters required - simply call the function"
        },
        "output_format": {
            "success": {
                "type": "string",
                "format": "Authentication successful. Your auth token is: <64-character-hex-token>",
                "example": "Authentication successful. Your auth token is: a1b2c3d4e5f6789012345678901234567890123456789012345678901234567"
            }
        },
        "examples": [
            {
                "description": "Basic authentication",
                "call": "get_auth_token()",
                "response": "Authentication successful. Your auth token is: 8f7d6c5b4a3928170615243342516273849506172839405162738495061728"
            }
        ],
        "important_notes": [
            "MUST be called before any other function",
            "Token remains valid for the server lifetime",
            "Store the token and reuse it for all subsequent calls",
            "Each call generates a new unique token"
        ],
        "errors": [],
        "rate_limits": "None",
        "required_env_vars": []
    },
    "get_orders": {
        "name": "get_orders",
        "category": "Order Management",
        "description": "Retrieve multiple orders from Amazon Seller Central using the SP-API with filtering and pagination support.",
        "purpose": "Fetch order data for analysis, fulfillment tracking, and order management",
        "when_to_use": [
            "To retrieve recent orders for processing",
            "To analyze order patterns over time periods",
            "To check order status updates",
            "For order reporting and analytics"
        ],
        "inputs": {
            "parameters": {
                "auth_token": {
                    "type": "string",
                    "description": "Authentication token from get_auth_token()",
                    "required": True
                },
                "marketplace_ids": {
                    "type": "string",
                    "description": "Comma-separated marketplace IDs",
                    "required": False,
                    "default": "A1F83G8C2ARO7P",
                    "example": "A1F83G8C2ARO7P (UK), ATVPDKIKX0DER (US)"
                },
                "created_after": {
                    "type": "string",
                    "description": "ISO 8601 date for orders after this date",
                    "required": False,
                    "default": "2025-01-01T00:00:00Z",
                    "format": "YYYY-MM-DDTHH:MM:SSZ"
                },
                "created_before": {
                    "type": "string",
                    "description": "ISO 8601 date for orders before this date",
                    "required": False,
                    "default": "",
                    "format": "YYYY-MM-DDTHH:MM:SSZ"
                },
                "order_statuses": {
                    "type": "string",
                    "description": "Comma-separated order statuses",
                    "required": False,
                    "default": "",
                    "example": "Pending,Unshipped,Shipped"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum orders to retrieve",
                    "required": False,
                    "default": 100,
                    "min": 1,
                    "max": 100
                }
            },
            "required": ["auth_token"]
        },
        "output_format": {
            "success": {
                "type": "object",
                "structure": {
                    "Orders": "Array of order objects",
                    "NextToken": "Token for pagination (if more results)",
                    "LastUpdatedBefore": "Timestamp of last update"
                },
                "example": {
                    "Orders": [
                        {
                            "AmazonOrderId": "123-4567890-1234567",
                            "PurchaseDate": "2025-01-29T10:30:00Z",
                            "OrderStatus": "Unshipped",
                            "OrderTotal": {
                                "Amount": "49.99",
                                "CurrencyCode": "GBP"
                            }
                        }
                    ]
                }
            },
            "error": {
                "type": "string",
                "examples": [
                    "Error: Invalid or missing auth token",
                    "Error: Failed to get Amazon access token",
                    "Error: API error - {details}"
                ]
            }
        },
        "examples": [
            {
                "description": "Get recent UK orders",
                "call": "get_orders(auth_token='your_token', created_after='2025-01-20T00:00:00Z')",
                "response": "JSON with order array"
            },
            {
                "description": "Get pending orders only",
                "call": "get_orders(auth_token='your_token', order_statuses='Pending,Unshipped')",
                "response": "JSON with filtered orders"
            }
        ],
        "important_notes": [
            "Results are paginated - check for NextToken",
            "Maximum 100 orders per request",
            "Date filters use ISO 8601 format with Z suffix",
            "Order data includes customer info - handle securely"
        ],
        "errors": [
            "Invalid auth token",
            "Missing environment variables",
            "API rate limit exceeded",
            "Invalid date format",
            "Network timeout"
        ],
        "rate_limits": "10 requests/second, burst of 30",
        "required_env_vars": [
            "LWA_CLIENT_ID",
            "LWA_CLIENT_SECRET",
            "LWA_REFRESH_TOKEN",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY"
        ]
    },
    "get_order": {
        "name": "get_order",
        "category": "Order Management",
        "description": "Retrieve detailed information for a single order from Amazon Seller Central.",
        "purpose": "Get complete details for a specific order including items, shipping, and buyer information",
        "when_to_use": [
            "To view full details of a specific order",
            "To check order item details",
            "To get shipping address information",
            "For customer service inquiries"
        ],
        "inputs": {
            "parameters": {
                "auth_token": {
                    "type": "string",
                    "description": "Authentication token from get_auth_token()",
                    "required": True
                },
                "order_id": {
                    "type": "string",
                    "description": "Amazon Order ID",
                    "required": True,
                    "format": "XXX-XXXXXXX-XXXXXXX",
                    "example": "123-4567890-1234567"
                }
            },
            "required": ["auth_token", "order_id"]
        },
        "output_format": {
            "success": {
                "type": "object",
                "structure": {
                    "AmazonOrderId": "Order ID",
                    "OrderStatus": "Current status",
                    "PurchaseDate": "Order timestamp",
                    "OrderItems": "Array of items (requires separate call)",
                    "ShippingAddress": "Delivery address details",
                    "BuyerInfo": "Customer information"
                }
            },
            "error": {
                "type": "string",
                "examples": [
                    "Error: Order not found",
                    "Error: Invalid order ID format"
                ]
            }
        },
        "important_notes": [
            "Order items require a separate API call",
            "Shipping address may be restricted based on order status",
            "PII data must be handled according to regulations"
        ],
        "rate_limits": "10 requests/second, burst of 30"
    },
    "get_inventory_in_stock": {
        "name": "get_inventory_in_stock",
        "category": "Inventory Management",
        "description": "Retrieve all products currently in stock with comprehensive inventory information, filterable by fulfillment type (FBA/FBM).",
        "purpose": "Monitor stock levels, identify low inventory items, and manage inventory across fulfillment channels",
        "when_to_use": [
            "To check current stock levels across all products",
            "To identify products running low on inventory",
            "To compare FBA vs FBM inventory levels",
            "For inventory reporting and analytics"
        ],
        "inputs": {
            "parameters": {
                "auth_token": {
                    "type": "string",
                    "description": "Authentication token",
                    "required": True
                },
                "fulfillment_type": {
                    "type": "string",
                    "description": "Filter by fulfillment type",
                    "required": False,
                    "default": "ALL",
                    "options": ["FBA", "FBM", "ALL"]
                },
                "marketplace_ids": {
                    "type": "string",
                    "description": "Marketplace to check",
                    "required": False,
                    "default": "A1F83G8C2ARO7P"
                },
                "details": {
                    "type": "boolean",
                    "description": "Include detailed inventory breakdown",
                    "required": False,
                    "default": True
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum items to return",
                    "required": False,
                    "default": 1000
                }
            }
        },
        "output_format": {
            "success": {
                "type": "object",
                "structure": {
                    "inventoryItems": [
                        {
                            "asin": "Product ASIN",
                            "sellerSku": "Your SKU",
                            "productName": "Product title",
                            "totalQuantity": "Total available",
                            "fulfillableQuantity": "Ready to ship",
                            "reservedQuantity": "Reserved for orders",
                            "inboundQuantity": "Incoming to FBA"
                        }
                    ],
                    "summary": {
                        "totalItems": "Number of products",
                        "totalQuantity": "Total units in stock",
                        "lowStockItems": "Products with <10 units"
                    }
                }
            }
        },
        "examples": [
            {
                "description": "Get all FBA inventory",
                "call": "get_inventory_in_stock(auth_token='token', fulfillment_type='FBA')",
                "response": "JSON with FBA inventory items"
            }
        ],
        "important_notes": [
            "FBM data is limited through FBA Inventory API",
            "Use get_fbm_inventory for detailed FBM data",
            "Results include reserved quantities",
            "Low stock threshold is 10 units"
        ],
        "rate_limits": "5 requests/second, burst of 10"
    },
    "get_fbm_inventory": {
        "name": "get_fbm_inventory",
        "category": "Inventory Management",
        "description": "Get real-time FBM (Fulfilled by Merchant) inventory data for a specific SKU using the Listings API.",
        "purpose": "Check current stock levels and fulfillment settings for individual FBM products",
        "when_to_use": [
            "To check specific FBM product availability",
            "To verify handling time settings",
            "Before updating FBM inventory",
            "For real-time stock verification"
        ],
        "inputs": {
            "parameters": {
                "auth_token": {
                    "type": "string",
                    "required": True
                },
                "seller_id": {
                    "type": "string",
                    "description": "Your Seller ID",
                    "required": True,
                    "example": "A1XXXXXXXXXXXXX"
                },
                "seller_sku": {
                    "type": "string",
                    "description": "SKU to check",
                    "required": True
                },
                "include_inactive": {
                    "type": "boolean",
                    "description": "Include inactive listings",
                    "required": False,
                    "default": False
                }
            }
        },
        "output_format": {
            "success": {
                "type": "object",
                "structure": {
                    "sku": "Seller SKU",
                    "status": "ACTIVE/INACTIVE",
                    "fulfillment_availability": {
                        "fulfillment_channel_code": "DEFAULT",
                        "quantity": "Available units",
                        "lead_time_to_ship_max_days": "Handling time"
                    }
                }
            }
        },
        "important_notes": [
            "Real-time data from Listings API",
            "For bulk operations use get_fbm_inventory_report",
            "Handling time affects Buy Box eligibility"
        ],
        "rate_limits": "5 requests/second, burst of 10"
    },
    "get_fbm_inventory_report": {
        "name": "get_fbm_inventory_report",
        "category": "Inventory Management",
        "description": "Generate comprehensive FBM inventory reports for bulk data analysis.",
        "purpose": "Get bulk FBM inventory data for all products, useful for large catalogs",
        "when_to_use": [
            "For inventory audits",
            "To export all FBM data",
            "For bulk inventory analysis",
            "When real-time data isn't critical"
        ],
        "inputs": {
            "parameters": {
                "auth_token": {
                    "type": "string",
                    "required": True
                },
                "report_type": {
                    "type": "string",
                    "description": "Type of report",
                    "required": False,
                    "default": "ALL_DATA",
                    "options": {
                        "ALL_DATA": "All listings",
                        "ACTIVE": "Active listings only",
                        "INACTIVE": "Inactive listings only"
                    }
                },
                "start_date": {
                    "type": "string",
                    "description": "Report start date",
                    "required": False,
                    "format": "ISO 8601"
                },
                "end_date": {
                    "type": "string",
                    "description": "Report end date",
                    "required": False,
                    "format": "ISO 8601"
                }
            }
        },
        "output_format": {
            "success": {
                "type": "object",
                "structure": {
                    "reportId": "Report ID for tracking",
                    "reportType": "Report type requested",
                    "processingStatus": "SUBMITTED/IN_QUEUE/IN_PROGRESS/DONE",
                    "dataStartTime": "Report period start",
                    "dataEndTime": "Report period end"
                }
            }
        },
        "important_notes": [
            "Reports are generated asynchronously",
            "Check status and download when ready",
            "Not real-time - use get_fbm_inventory for current data",
            "CSV format when downloaded"
        ],
        "rate_limits": "15 requests/second, burst of 30"
    },
    "update_fbm_inventory": {
        "name": "update_fbm_inventory",
        "category": "Inventory Management",
        "description": "Update FBM inventory quantity and fulfillment settings for a single SKU.",
        "purpose": "Adjust stock levels, handling time, and restock dates for individual FBM products",
        "when_to_use": [
            "After receiving new stock",
            "To mark items out of stock",
            "To update handling time",
            "To set restock dates"
        ],
        "inputs": {
            "parameters": {
                "auth_token": {
                    "type": "string",
                    "required": True
                },
                "seller_id": {
                    "type": "string",
                    "required": True
                },
                "seller_sku": {
                    "type": "string",
                    "required": True
                },
                "quantity": {
                    "type": "integer",
                    "description": "New quantity (0 for out of stock)",
                    "required": True,
                    "min": 0,
                    "max": 999999
                },
                "handling_time": {
                    "type": "integer",
                    "description": "Days to ship (1-30)",
                    "required": False,
                    "min": 1,
                    "max": 30
                },
                "restock_date": {
                    "type": "string",
                    "description": "When item will be back",
                    "required": False,
                    "format": "ISO 8601"
                }
            }
        },
        "output_format": {
            "success": {
                "type": "object",
                "structure": {
                    "sku": "Updated SKU",
                    "submissionId": "Update tracking ID",
                    "status": "ACCEPTED",
                    "updates": {
                        "quantity": "New quantity",
                        "handling_time": "New handling time",
                        "restock_date": "New restock date"
                    }
                }
            }
        },
        "examples": [
            {
                "description": "Mark item out of stock",
                "call": "update_fbm_inventory(auth_token='token', seller_id='A1XXX', seller_sku='SKU123', quantity=0)",
                "response": "Success with quantity: 0"
            },
            {
                "description": "Update stock and handling time",
                "call": "update_fbm_inventory(..., quantity=50, handling_time=2)",
                "response": "Success with both updates"
            }
        ],
        "important_notes": [
            "Changes take 5-15 minutes to reflect",
            "Quantity 0 marks as out of stock",
            "Handling time affects Buy Box",
            "For bulk updates use bulk_update_fbm_inventory"
        ],
        "errors": [
            "Invalid SKU",
            "Quantity out of range",
            "Invalid handling time (1-30 days)",
            "Invalid date format"
        ],
        "rate_limits": "5 requests/second, burst of 10"
    },
    "bulk_update_fbm_inventory": {
        "name": "bulk_update_fbm_inventory",
        "category": "Inventory Management",
        "description": "Bulk update FBM inventory for multiple SKUs in a single operation using the Feeds API.",
        "purpose": "Efficiently update inventory for large numbers of products",
        "when_to_use": [
            "Updating 10+ products at once",
            "Daily inventory synchronization",
            "After bulk stock receipt",
            "For catalog-wide updates"
        ],
        "inputs": {
            "parameters": {
                "auth_token": {
                    "type": "string",
                    "required": True
                },
                "inventory_updates": {
                    "type": "string",
                    "description": "JSON array of updates",
                    "required": True,
                    "format": "JSON array",
                    "structure": [
                        {
                            "sku": "SKU to update",
                            "quantity": "New quantity",
                            "handling_time": "Optional: 1-30 days",
                            "restock_date": "Optional: ISO 8601"
                        }
                    ]
                },
                "marketplace_id": {
                    "type": "string",
                    "required": False,
                    "default": "A1F83G8C2ARO7P"
                }
            }
        },
        "output_format": {
            "success": {
                "type": "object",
                "structure": {
                    "feedId": "Feed tracking ID",
                    "feedType": "POST_INVENTORY_AVAILABILITY_DATA",
                    "submittedDate": "Submission timestamp",
                    "processingStatus": "SUBMITTED",
                    "itemCount": "Number of SKUs updated"
                }
            }
        },
        "examples": [
            {
                "description": "Update 3 products",
                "call": "bulk_update_fbm_inventory(auth_token='token', inventory_updates='[{\"sku\":\"A1\",\"quantity\":10},{\"sku\":\"A2\",\"quantity\":20},{\"sku\":\"A3\",\"quantity\":0}]')",
                "response": "Feed submitted with 3 items"
            }
        ],
        "important_notes": [
            "Maximum 10,000 items per feed",
            "Processing is asynchronous",
            "Check feed status for completion",
            "More efficient than individual updates for 10+ items"
        ],
        "errors": [
            "Invalid JSON format",
            "Missing required fields",
            "Too many items (>10,000)",
            "Invalid marketplace"
        ],
        "rate_limits": "15 requests/second, burst of 30"
    },
    "update_product_price": {
        "name": "update_product_price",
        "category": "Pricing Management",
        "description": "Update the selling price of a product on Amazon for both FBA and FBM listings.",
        "purpose": "Adjust product pricing to remain competitive or reflect cost changes",
        "when_to_use": [
            "For competitive repricing",
            "During sales or promotions",
            "To adjust for cost changes",
            "For dynamic pricing strategies"
        ],
        "inputs": {
            "parameters": {
                "auth_token": {
                    "type": "string",
                    "required": True
                },
                "seller_id": {
                    "type": "string",
                    "required": True
                },
                "seller_sku": {
                    "type": "string",
                    "required": True
                },
                "new_price": {
                    "type": "string",
                    "description": "New price (numbers only)",
                    "required": True,
                    "format": "XX.XX",
                    "example": "29.99"
                },
                "currency": {
                    "type": "string",
                    "description": "Currency code",
                    "required": False,
                    "default": "GBP",
                    "options": ["GBP", "USD", "EUR", "CAD"]
                }
            }
        },
        "output_format": {
            "success": {
                "type": "object",
                "structure": {
                    "sku": "Updated SKU",
                    "submissionId": "Tracking ID",
                    "status": "ACCEPTED",
                    "priceUpdate": {
                        "previousPrice": "Old price if available",
                        "newPrice": "New price set",
                        "currency": "Currency code"
                    }
                }
            }
        },
        "examples": [
            {
                "description": "Update UK price",
                "call": "update_product_price(auth_token='token', seller_id='A1XXX', seller_sku='SKU123', new_price='19.99')",
                "response": "Success with new price £19.99"
            }
        ],
        "important_notes": [
            "Price updates take 5-15 minutes",
            "Works for both FBA and FBM",
            "Affects Buy Box eligibility",
            "Consider competitive pricing",
            "VAT inclusive for EU markets"
        ],
        "errors": [
            "Invalid price format",
            "Price too low/high",
            "Invalid SKU",
            "Currency mismatch with marketplace"
        ],
        "rate_limits": "10 requests/second, burst of 20"
    },
    "get_listing": {
        "name": "get_listing",
        "category": "Product Management",
        "description": "Retrieve comprehensive product listing details including title, description, bullet points, images, and attributes.",
        "purpose": "View complete product information as it appears on Amazon",
        "when_to_use": [
            "To review current listing content",
            "Before making listing updates",
            "For content quality checks",
            "To export product data"
        ],
        "inputs": {
            "parameters": {
                "auth_token": {
                    "type": "string",
                    "required": True
                },
                "seller_id": {
                    "type": "string",
                    "required": True
                },
                "seller_sku": {
                    "type": "string",
                    "required": True
                },
                "included_data": {
                    "type": "string",
                    "description": "Data to include",
                    "required": False,
                    "default": "All available",
                    "options": ["summaries", "attributes", "issues", "offers", "fulfillmentAvailability"]
                }
            }
        },
        "output_format": {
            "success": {
                "type": "object",
                "structure": {
                    "sku": "Seller SKU",
                    "summaries": {
                        "productTitle": "Current title",
                        "manufacturer": "Brand/manufacturer",
                        "brandName": "Brand"
                    },
                    "attributes": {
                        "bullet_point": ["Feature 1", "Feature 2"],
                        "product_description": "Full description",
                        "generic_keyword": ["search", "terms"]
                    },
                    "mainImage": {
                        "link": "Primary image URL"
                    },
                    "issues": "Any listing problems"
                }
            }
        },
        "important_notes": [
            "Returns all content as shown on Amazon",
            "Includes any listing issues/warnings",
            "Image URLs are temporary",
            "Some fields may be empty"
        ],
        "rate_limits": "5 requests/second, burst of 10"
    },
    "update_listing": {
        "name": "update_listing",
        "category": "Product Management",
        "description": "Update product listing content including title, bullet points, description, search terms, brand, and manufacturer.",
        "purpose": "Optimize product listings for better visibility and conversion",
        "when_to_use": [
            "To improve product title",
            "To enhance bullet points",
            "To update product description",
            "To optimize search terms",
            "To correct brand information"
        ],
        "inputs": {
            "parameters": {
                "auth_token": {
                    "type": "string",
                    "required": True
                },
                "seller_id": {
                    "type": "string",
                    "required": True
                },
                "seller_sku": {
                    "type": "string",
                    "required": True
                },
                "title": {
                    "type": "string",
                    "description": "New product title",
                    "required": False,
                    "max_length": 200
                },
                "bullet_points": {
                    "type": "string",
                    "description": "Comma-separated features",
                    "required": False,
                    "format": "Feature 1, Feature 2, ...",
                    "max_items": 5
                },
                "description": {
                    "type": "string",
                    "description": "Product description",
                    "required": False,
                    "max_length": 2000
                },
                "search_terms": {
                    "type": "string",
                    "description": "Comma-separated keywords",
                    "required": False,
                    "format": "term1, term2, ...",
                    "max_items": 5
                },
                "brand": {
                    "type": "string",
                    "description": "Brand name",
                    "required": False
                },
                "manufacturer": {
                    "type": "string",
                    "description": "Manufacturer name",
                    "required": False
                }
            }
        },
        "output_format": {
            "success": {
                "type": "object",
                "structure": {
                    "sku": "Updated SKU",
                    "submissionId": "Tracking ID",
                    "status": "ACCEPTED",
                    "listing_update": {
                        "fields_updated": ["title", "bullet_points"],
                        "marketplace": "A1F83G8C2ARO7P",
                        "note": "Updates take 5-15 minutes"
                    }
                }
            }
        },
        "examples": [
            {
                "description": "Update title and bullets",
                "call": "update_listing(auth_token='token', seller_id='A1X', seller_sku='SKU1', title='New Title', bullet_points='Feature 1, Feature 2, Feature 3')",
                "response": "Success with fields_updated: ['title', 'bullet_points']"
            }
        ],
        "important_notes": [
            "Only provide fields you want to change",
            "Uses PATCH for partial updates",
            "Changes take 5-15 minutes",
            "Maximum 5 bullet points",
            "Maximum 5 search terms",
            "Follow Amazon's style guidelines"
        ],
        "errors": [
            "Title too long (>200 chars)",
            "Too many bullet points (>5)",
            "Invalid characters in content",
            "Restricted words used"
        ],
        "rate_limits": "5 requests/second, burst of 10"
    },
    "get_tool_info": {
        "name": "get_tool_info",
        "category": "Information",
        "description": "Get detailed information about any tool available in this MCP server, including usage instructions, parameters, output formats, and examples.",
        "purpose": "Help AI agents understand and correctly use the available tools",
        "when_to_use": [
            "Before using an unfamiliar tool",
            "To understand tool parameters",
            "To see example usage",
            "To check error handling"
        ],
        "inputs": {
            "parameters": {
                "tool_name": {
                    "type": "string",
                    "description": "Name of the tool to get info about",
                    "required": True,
                    "options": ["get_auth_token", "get_orders", "get_order", "get_inventory_in_stock", "get_fbm_inventory", "get_fbm_inventory_report", "update_fbm_inventory", "bulk_update_fbm_inventory", "update_product_price", "get_listing", "update_listing", "get_tool_info"]
                }
            }
        },
        "output_format": {
            "success": {
                "type": "object",
                "description": "Comprehensive tool information including all details needed for correct usage"
            },
            "error": {
                "type": "string",
                "example": "Error: Unknown tool name 'invalid_tool'. Available tools: get_auth_token, get_orders, ..."
            }
        }
    }
}


@mcp.tool()
def get_tool_info(
    tool_name: Annotated[
        str,
        "Name of the tool to get information about. Options: get_auth_token, get_orders, get_order, get_inventory_in_stock, get_fbm_inventory, get_fbm_inventory_report, update_fbm_inventory, bulk_update_fbm_inventory, update_product_price, get_listing, update_listing, get_tool_info"
    ]
) -> str:
    """Get detailed information about any tool available in this MCP server.
    
    This function provides comprehensive information about each tool including:
    - Purpose and when to use it
    - Detailed parameter descriptions with types and examples
    - Output format with example responses
    - Important notes and limitations
    - Error scenarios
    - Rate limits
    - Required environment variables
    
    This helps AI agents understand and correctly use the available tools before calling them.
    """
    if tool_name not in TOOL_INFO:
        available_tools = ", ".join(sorted(TOOL_INFO.keys()))
        return f"Error: Unknown tool name '{tool_name}'. Available tools: {available_tools}"
    
    return json.dumps(TOOL_INFO[tool_name], indent=2)


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
        str, "Filter by fulfillment type: 'FBA' (Fulfilled by Amazon), 'FBM' (Fulfilled by Merchant), or 'ALL' (both)"
    ] = "ALL",
    details: Annotated[
        bool, "Include detailed inventory breakdown (fulfillable, unfulfillable, reserved, inbound)"
    ] = True,
    max_results: Annotated[int, "Maximum number of inventory items to return (default 1000)"] = 1000,
    region: Annotated[str, "AWS region for the SP-API endpoint"] = "eu-west-1",
    endpoint: Annotated[str, "SP-API endpoint URL"] = "https://sellingpartnerapi-eu.amazon.com",
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
        return json.dumps({
            "success": False,
            "error": "auth_failed",
            "message": "Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token.",
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

    # 2. Get credentials
    access_token = get_amazon_access_token()
    if not access_token:
        return json.dumps({
            "success": False,
            "error": "auth_failed",
            "message": "Failed to get Amazon access token. Check your LWA credentials.",
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

    aws_creds = get_amazon_aws_credentials()
    if not aws_creds:
        return json.dumps({
            "success": False,
            "error": "auth_failed",
            "message": "Failed to get AWS credentials. Check your AWS credentials and role.",
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

    # 3. Use InventoryAPIClient
    client = InventoryAPIClient(access_token, aws_creds, region, endpoint)

    # 4. Make API call
    result = client.get_inventory_summaries(
        marketplace_ids=marketplace_ids,
        fulfillment_type=fulfillment_type,
        details=details,
        max_results=max_results,
    )

    # 5. Return formatted JSON
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
        str, "Specific SKU to retrieve. If not provided, use get_fbm_inventory_report for bulk data"
    ],
    marketplace_ids: Annotated[
        str, "Comma-separated marketplace IDs (e.g., 'A1F83G8C2ARO7P' for UK)"
    ] = "A1F83G8C2ARO7P",
    include_inactive: Annotated[
        bool, "Include inactive listings in the results"
    ] = False,
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
        return json.dumps({
            "success": False,
            "error": "auth_failed",
            "message": "Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token.",
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

    # 2. Validate inputs
    if not seller_id:
        return json.dumps({
            "success": False,
            "error": "invalid_input",
            "message": "seller_id is required",
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

    if not validate_seller_sku(seller_sku):
        return json.dumps({
            "success": False,
            "error": "invalid_input",
            "message": "Invalid SKU format",
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

    # 3. Get credentials
    access_token = get_amazon_access_token()
    if not access_token:
        return json.dumps({
            "success": False,
            "error": "auth_failed",
            "message": "Failed to get Amazon access token. Check your LWA credentials.",
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

    aws_creds = get_amazon_aws_credentials()
    if not aws_creds:
        return json.dumps({
            "success": False,
            "error": "auth_failed",
            "message": "Failed to get AWS credentials. Check your AWS credentials and role.",
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

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
        "Report type: 'ALL_DATA' (all listings), 'ACTIVE' (active only), or 'INACTIVE' (inactive only)"
    ] = "ALL_DATA",
    marketplace_ids: Annotated[
        str, "Comma-separated marketplace IDs (e.g., 'A1F83G8C2ARO7P' for UK)"
    ] = "A1F83G8C2ARO7P",
    start_date: Annotated[
        Optional[str], "ISO 8601 format start date for the report data"
    ] = None,
    end_date: Annotated[
        Optional[str], "ISO 8601 format end date for the report data"
    ] = None,
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
        return json.dumps({
            "success": False,
            "error": "auth_failed",
            "message": "Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token.",
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

    # 2. Map report type
    report_type_map = {
        "ALL_DATA": "GET_MERCHANT_LISTINGS_ALL_DATA",
        "ACTIVE": "GET_MERCHANT_LISTINGS_DATA",
        "INACTIVE": "GET_MERCHANT_LISTINGS_INACTIVE_DATA",
    }

    if report_type not in report_type_map:
        return json.dumps({
            "success": False,
            "error": "invalid_input",
            "message": f"Invalid report_type. Must be one of: {', '.join(report_type_map.keys())}",
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

    # 3. Get credentials
    access_token = get_amazon_access_token()
    if not access_token:
        return json.dumps({
            "success": False,
            "error": "auth_failed",
            "message": "Failed to get Amazon access token. Check your LWA credentials.",
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

    aws_creds = get_amazon_aws_credentials()
    if not aws_creds:
        return json.dumps({
            "success": False,
            "error": "auth_failed",
            "message": "Failed to get AWS credentials. Check your AWS credentials and role.",
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

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
        Optional[int], "Days to ship (1-30). If not provided, existing value is retained"
    ] = None,
    restock_date: Annotated[
        Optional[str], "ISO 8601 format restock date (must be in the future)"
    ] = None,
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
        return json.dumps({
            "success": False,
            "error": "auth_failed",
            "message": "Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token.",
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

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
        return json.dumps({
            "success": False,
            "error": "invalid_input",
            "message": "Input validation failed",
            "details": validation_errors,
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

    # 3. Get credentials
    access_token = get_amazon_access_token()
    if not access_token:
        return json.dumps({
            "success": False,
            "error": "auth_failed",
            "message": "Failed to get Amazon access token. Check your LWA credentials.",
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

    aws_creds = get_amazon_aws_credentials()
    if not aws_creds:
        return json.dumps({
            "success": False,
            "error": "auth_failed",
            "message": "Failed to get AWS credentials. Check your AWS credentials and role.",
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

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
        "value": [fulfillment_data]
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
        "JSON array of inventory updates. Each item must have: sku, quantity, and optionally handling_time and restock_date"
    ],
    marketplace_id: Annotated[
        str, "Target marketplace ID (e.g., 'A1F83G8C2ARO7P' for UK)"
    ] = "A1F83G8C2ARO7P",
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
        return json.dumps({
            "success": False,
            "error": "auth_failed",
            "message": "Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token.",
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

    # 2. Parse and validate inventory updates
    try:
        updates = json.loads(inventory_updates)
    except json.JSONDecodeError:
        return json.dumps({
            "success": False,
            "error": "invalid_input",
            "message": "inventory_updates must be a valid JSON array",
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

    # Validate updates
    is_valid, errors = validate_bulk_inventory_updates(updates)
    if not is_valid:
        return json.dumps({
            "success": False,
            "error": "invalid_input",
            "message": "Validation failed for inventory updates",
            "details": errors,
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

    # 3. Get credentials
    access_token = get_amazon_access_token()
    if not access_token:
        return json.dumps({
            "success": False,
            "error": "auth_failed",
            "message": "Failed to get Amazon access token. Check your LWA credentials.",
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

    aws_creds = get_amazon_aws_credentials()
    if not aws_creds:
        return json.dumps({
            "success": False,
            "error": "auth_failed",
            "message": "Failed to get AWS credentials. Check your AWS credentials and role.",
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

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
        return json.dumps({
            "success": False,
            "error": "auth_failed",
            "message": "Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token.",
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

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
        return json.dumps({
            "success": False,
            "error": "invalid_input",
            "message": "Input validation failed",
            "details": validation_errors,
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

    # 3. Get credentials
    access_token = get_amazon_access_token()
    if not access_token:
        return json.dumps({
            "success": False,
            "error": "auth_failed",
            "message": "Failed to get Amazon access token. Check your LWA credentials.",
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

    aws_creds = get_amazon_aws_credentials()
    if not aws_creds:
        return json.dumps({
            "success": False,
            "error": "auth_failed",
            "message": "Failed to get AWS credentials. Check your AWS credentials and role.",
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

    # 4. Build patch operations for price update
    patches = [
        {
            "op": "replace",
            "path": "/attributes/purchasable_offer",
            "value": [
                {
                    "audience": "ALL",
                    "our_price": [
                        {
                            "schedule": [
                                {
                                    "value_with_tax": new_price
                                }
                            ]
                        }
                    ]
                }
            ]
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
    if result.get('success'):
        result['price_update'] = {
            "sku": seller_sku,
            "new_price": f"{currency} {new_price}",
            "marketplace": marketplace_ids,
            "note": "Price updates typically take 5-15 minutes to reflect on Amazon"
        }

    # 8. Return formatted JSON
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_sp_api_errors
# @cached_api_call(cache_type="listings")  # TODO: Enable when caching is fully implemented
def get_listing(
    auth_token: Annotated[
        str,
        "Authentication token obtained from get_auth_token(). Required for this function to work.",
    ],
    seller_id: Annotated[str, "The seller ID for the merchant account"],
    seller_sku: Annotated[str, "SKU of the product to retrieve"],
    marketplace_ids: Annotated[
        str, "Comma-separated marketplace IDs (e.g., 'A1F83G8C2ARO7P' for UK)"
    ] = "A1F83G8C2ARO7P",
    included_data: Annotated[
        Optional[str], 
        "Comma-separated data to include: attributes, issues, offers, fulfillmentAvailability"
    ] = None,
    region: Annotated[str, "AWS region for the SP-API endpoint"] = "eu-west-1",
    endpoint: Annotated[str, "SP-API endpoint URL"] = "https://sellingpartnerapi-eu.amazon.com",
) -> str:
    """Get detailed listing information for a product including title, bullet points, description, etc.

    REQUIRES AUTHENTICATION: You must provide a valid auth_token obtained from get_auth_token().

    This endpoint retrieves comprehensive product listing details from Amazon including:
    - Product title and description
    - Bullet points (product features)
    - Images
    - Pricing information
    - Fulfillment availability
    - Product attributes
    - Any issues with the listing

    Parameters:
    - seller_sku: The SKU of the product to retrieve
    - included_data: Optional data to include (defaults to all available data)
    
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
        return json.dumps({
            "success": False,
            "error": "auth_failed",
            "message": "Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token.",
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

    # 2. Validate inputs
    validation_errors = []

    if not seller_id:
        validation_errors.append("seller_id is required")

    if not validate_seller_sku(seller_sku):
        validation_errors.append("Invalid SKU format")

    if validation_errors:
        return json.dumps({
            "success": False,
            "error": "invalid_input",
            "message": "Input validation failed",
            "details": validation_errors,
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

    # 3. Get credentials
    access_token = get_amazon_access_token()
    if not access_token:
        return json.dumps({
            "success": False,
            "error": "auth_failed",
            "message": "Failed to get Amazon access token. Check your LWA credentials.",
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

    aws_creds = get_amazon_aws_credentials()
    if not aws_creds:
        return json.dumps({
            "success": False,
            "error": "auth_failed",
            "message": "Failed to get AWS credentials. Check your AWS credentials and role.",
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

    # 4. Apply rate limiting
    rate_limiter.wait_if_needed("/listings/2021-08-01/items")

    # 5. Parse included_data
    included_data_list = None
    if included_data:
        included_data_list = [item.strip() for item in included_data.split(",")]

    # 6. Use ListingsAPIClient
    client = ListingsAPIClient(access_token, aws_creds, region, endpoint)

    # 7. Make API call
    result = client.get_listings_item(
        seller_id=seller_id,
        sku=seller_sku,
        marketplace_ids=marketplace_ids,
        included_data=included_data_list,
    )

    # 8. Return formatted JSON
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_sp_api_errors
# Note: Caching not recommended for update operations as they modify data
def update_listing(
    auth_token: Annotated[
        str,
        "Authentication token obtained from get_auth_token(). Required for this function to work.",
    ],
    seller_id: Annotated[str, "The seller ID for the merchant account"],
    seller_sku: Annotated[str, "SKU of the product to update"],
    title: Annotated[Optional[str], "New product title (optional)"] = None,
    bullet_points: Annotated[
        Optional[str], 
        "Comma-separated list of bullet points/features (optional)"
    ] = None,
    description: Annotated[Optional[str], "New product description (optional)"] = None,
    search_terms: Annotated[
        Optional[str], 
        "Comma-separated search terms/keywords (optional)"
    ] = None,
    brand: Annotated[Optional[str], "Product brand (optional)"] = None,
    manufacturer: Annotated[Optional[str], "Product manufacturer (optional)"] = None,
    marketplace_ids: Annotated[
        str, "Comma-separated marketplace IDs (e.g., 'A1F83G8C2ARO7P' for UK)"
    ] = "A1F83G8C2ARO7P",
    region: Annotated[str, "AWS region for the SP-API endpoint"] = "eu-west-1",
    endpoint: Annotated[str, "SP-API endpoint URL"] = "https://sellingpartnerapi-eu.amazon.com",
) -> str:
    """Update product listing information including title, bullet points, description, etc.

    REQUIRES AUTHENTICATION: You must provide a valid auth_token obtained from get_auth_token().

    This endpoint updates various attributes of a product listing on Amazon using the PATCH
    method, which allows partial updates. You only need to provide the fields you want to change.

    Parameters:
    - seller_sku: The SKU of the product to update
    - title: New product title
    - bullet_points: Comma-separated list of product features/bullet points
    - description: New product description
    - search_terms: Comma-separated keywords for search optimization
    - brand: Product brand name
    - manufacturer: Product manufacturer name
    
    Note: Changes typically take 5-15 minutes to reflect on Amazon.
    
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
        return json.dumps({
            "success": False,
            "error": "auth_failed",
            "message": "Invalid or missing auth token. Please call get_auth_token() first to obtain a valid token.",
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

    # 2. Validate inputs
    validation_errors = []

    if not seller_id:
        validation_errors.append("seller_id is required")

    if not validate_seller_sku(seller_sku):
        validation_errors.append("Invalid SKU format")

    # Check if at least one field to update is provided
    if not any([title, bullet_points, description, search_terms, brand, manufacturer]):
        validation_errors.append("At least one field to update must be provided")

    # Additional validation for character limits and count limits
    if bullet_points:
        bullet_list = [bp.strip() for bp in bullet_points.split(",")]
        if len(bullet_list) > 5:
            validation_errors.append("Maximum 5 bullet points allowed")

    if search_terms:
        terms_list = [term.strip() for term in search_terms.split(",")]
        if len(terms_list) > 5:
            validation_errors.append("Maximum 5 search terms allowed")

    if title and len(title) > 200:  # Amazon title limit
        validation_errors.append("Title must be 200 characters or less")

    if validation_errors:
        return json.dumps({
            "success": False,
            "error": "invalid_input",
            "message": "Input validation failed",
            "details": validation_errors,
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

    # 3. Get credentials
    access_token = get_amazon_access_token()
    if not access_token:
        return json.dumps({
            "success": False,
            "error": "auth_failed",
            "message": "Failed to get Amazon access token. Check your LWA credentials.",
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

    aws_creds = get_amazon_aws_credentials()
    if not aws_creds:
        return json.dumps({
            "success": False,
            "error": "auth_failed",
            "message": "Failed to get AWS credentials. Check your AWS credentials and role.",
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "request_id": str(uuid.uuid4()),
            }
        }, indent=2)

    # 4. Apply rate limiting
    rate_limiter.wait_if_needed("/listings/2021-08-01/items")

    # 5. Build patch operations
    patches = []
    
    if title:
        patches.append({
            "op": "replace",
            "path": "/attributes/item_name",
            "value": [{"value": title, "marketplace_id": marketplace_ids.split(",")[0]}]
        })
    
    if bullet_points:
        # Convert comma-separated string to list of bullet points
        bullet_list = [bp.strip() for bp in bullet_points.split(",")]
        bullet_values = []
        for i, bullet in enumerate(bullet_list[:5]):  # Amazon typically allows up to 5 bullet points
            bullet_values.append({
                "value": bullet,
                "marketplace_id": marketplace_ids.split(",")[0]
            })
        
        patches.append({
            "op": "replace",
            "path": "/attributes/bullet_point",
            "value": bullet_values
        })
    
    if description:
        patches.append({
            "op": "replace",
            "path": "/attributes/product_description",
            "value": [{"value": description, "marketplace_id": marketplace_ids.split(",")[0]}]
        })
    
    if search_terms:
        # Convert comma-separated string to list of search terms
        terms_list = [term.strip() for term in search_terms.split(",")]
        search_values = []
        for term in terms_list[:5]:  # Amazon typically allows up to 5 search terms
            search_values.append({
                "value": term,
                "marketplace_id": marketplace_ids.split(",")[0]
            })
        
        patches.append({
            "op": "replace",
            "path": "/attributes/generic_keyword",
            "value": search_values
        })
    
    if brand:
        patches.append({
            "op": "replace",
            "path": "/attributes/brand",
            "value": [{"value": brand, "marketplace_id": marketplace_ids.split(",")[0]}]
        })
    
    if manufacturer:
        patches.append({
            "op": "replace",
            "path": "/attributes/manufacturer",
            "value": [{"value": manufacturer, "marketplace_id": marketplace_ids.split(",")[0]}]
        })

    # 6. Use ListingsAPIClient
    client = ListingsAPIClient(access_token, aws_creds, region, endpoint)

    # 7. Make API call
    result = client.patch_listings_item(
        seller_id=seller_id,
        sku=seller_sku,
        marketplace_ids=marketplace_ids,
        patches=patches,
    )

    # 8. Add update summary to success response
    if result.get('success'):
        updates_made = []
        if title:
            updates_made.append("title")
        if bullet_points:
            updates_made.append("bullet_points")
        if description:
            updates_made.append("description")
        if search_terms:
            updates_made.append("search_terms")
        if brand:
            updates_made.append("brand")
        if manufacturer:
            updates_made.append("manufacturer")
            
        result['listing_update'] = {
            "sku": seller_sku,
            "fields_updated": updates_made,
            "marketplace": marketplace_ids,
            "note": "Listing updates typically take 5-15 minutes to reflect on Amazon"
        }

    # 9. Return formatted JSON
    return json.dumps(result, indent=2)


def main() -> None:
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
