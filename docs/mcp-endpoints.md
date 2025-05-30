# MCP Server Endpoints Documentation

The Zigi Amazon MCP server provides comprehensive tools for Amazon Seller Central API integration.

## Authentication

### get_auth_token
Generate an authentication token that must be used for all other function calls.

**Parameters:**
- None

**Returns:**
- Authentication token string

**Example:**
```json
{
  "tool": "get_auth_token",
  "arguments": {}
}
```

**Response:**
```
Authentication successful. Your auth token is: a1b2c3d4e5f6...
```

## Amazon SP-API Tools

All SP-API tools require:
1. A valid `auth_token` obtained from `get_auth_token()`
2. Environment variables for Amazon API credentials:
   - `LWA_CLIENT_ID`
   - `LWA_CLIENT_SECRET` 
   - `LWA_REFRESH_TOKEN`
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_ROLE_ARN` (optional)

### Orders Management

#### get_orders
Retrieve multiple orders from Amazon Seller Central with pagination support.

**Parameters:**
- `auth_token` (string, required): Authentication token
- `marketplace_ids` (string, optional): Comma-separated marketplace IDs. Default: "A1F83G8C2ARO7P" (UK)
- `created_after` (string, optional): ISO 8601 date string. Default: "2025-01-01T00:00:00Z"
- `created_before` (string, optional): ISO 8601 date string
- `order_statuses` (string, optional): Comma-separated order statuses
- `max_results` (int, optional): Maximum orders to retrieve. Default: 100

#### get_order
Retrieve details for a single order.

**Parameters:**
- `auth_token` (string, required): Authentication token
- `order_id` (string, required): Amazon Order ID

### Inventory Management

#### get_inventory_in_stock
Get all products currently in stock with inventory details.

**Parameters:**
- `auth_token` (string, required): Authentication token
- `marketplace_ids` (string, optional): Default: "A1F83G8C2ARO7P" (UK)
- `fulfillment_type` (string, optional): "FBA", "FBM", or "ALL". Default: "ALL"
- `details` (bool, optional): Include detailed breakdown. Default: true
- `max_results` (int, optional): Maximum items to return. Default: 1000

#### get_fbm_inventory
Get real-time FBM inventory for a specific SKU.

**Parameters:**
- `auth_token` (string, required): Authentication token
- `seller_id` (string, required): Seller ID
- `seller_sku` (string, required): SKU to retrieve
- `marketplace_ids` (string, optional): Default: "A1F83G8C2ARO7P" (UK)
- `include_inactive` (bool, optional): Include inactive listings. Default: false

#### get_fbm_inventory_report
Generate bulk FBM inventory report (asynchronous).

**Parameters:**
- `auth_token` (string, required): Authentication token
- `report_type` (string, optional): "ALL_DATA", "ACTIVE", or "INACTIVE". Default: "ALL_DATA"
- `marketplace_ids` (string, optional): Default: "A1F83G8C2ARO7P" (UK)
- `start_date` (string, optional): ISO 8601 format
- `end_date` (string, optional): ISO 8601 format

#### update_fbm_inventory
Update FBM inventory for a single SKU.

**Parameters:**
- `auth_token` (string, required): Authentication token
- `seller_id` (string, required): Seller ID
- `seller_sku` (string, required): SKU to update
- `quantity` (int, required): New quantity (>= 0)
- `handling_time` (int, optional): Days to ship (1-30)
- `restock_date` (string, optional): ISO 8601 format future date

#### bulk_update_fbm_inventory
Bulk update FBM inventory using Feeds API.

**Parameters:**
- `auth_token` (string, required): Authentication token
- `inventory_updates` (string, required): JSON array of updates
- `marketplace_id` (string, optional): Default: "A1F83G8C2ARO7P" (UK)

**Example inventory_updates:**
```json
[
  {
    "sku": "SKU123",
    "quantity": 50,
    "handling_time": 2,
    "restock_date": "2025-06-01T00:00:00Z"
  }
]
```

### Product Management

#### update_product_price
Update product price on Amazon (works for both FBA and FBM).

**Parameters:**
- `auth_token` (string, required): Authentication token
- `seller_id` (string, required): Seller ID
- `seller_sku` (string, required): SKU of product
- `new_price` (string, required): New price value (e.g., "69.98")
- `currency` (string, optional): Currency code. Default: "GBP"

#### get_listing
Get detailed product listing information.

**Parameters:**
- `auth_token` (string, required): Authentication token
- `seller_id` (string, required): Seller ID
- `seller_sku` (string, required): SKU of product
- `marketplace_ids` (string, optional): Default: "A1F83G8C2ARO7P" (UK)
- `included_data` (string, optional): Comma-separated data types: attributes, issues, offers, fulfillmentAvailability

#### update_listing
Update product listing attributes.

**Parameters:**
- `auth_token` (string, required): Authentication token
- `seller_id` (string, required): Seller ID
- `seller_sku` (string, required): SKU of product
- `title` (string, optional): New product title
- `bullet_points` (string, optional): Comma-separated bullet points (max 5)
- `description` (string, optional): New product description
- `search_terms` (string, optional): Comma-separated keywords (max 5)
- `brand` (string, optional): Product brand
- `manufacturer` (string, optional): Product manufacturer

## Response Format

All endpoints return JSON responses with consistent structure:

**Success Response:**
```json
{
  "success": true,
  "data": { ... },
  "metadata": {
    "timestamp": "2025-01-30T10:30:00Z",
    "marketplace": "UK",
    "request_id": "abc-123"
  }
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "error_code",
  "message": "Human-readable error message",
  "details": [...],
  "metadata": { ... }
}
```

## Rate Limiting

The server implements automatic rate limiting for all SP-API endpoints to comply with Amazon's rate limits. You don't need to implement rate limiting in your client code.