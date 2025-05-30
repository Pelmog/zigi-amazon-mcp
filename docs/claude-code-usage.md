# Using Zigi Amazon MCP with Claude Code

This guide explains how to use the Zigi Amazon MCP server tools directly within Claude Code.

## Prerequisites

1. Ensure the MCP server is running. You should see "zigi-amazon-mcp: connected" in your MCP status.
2. The `.claude/settings.local.json` file must include permissions for all MCP tools.
3. Set up required environment variables for Amazon SP-API access.

## Authentication

**IMPORTANT**: All tools (except get_auth_token) require authentication. Always start by getting an auth token:

```
Use the mcp__zigi-amazon-mcp__get_auth_token tool to get an authentication token
```

Store the returned token and use it in all subsequent calls.

## Available MCP Tools

All tools are prefixed with `mcp__zigi-amazon-mcp__` when used in Claude Code:

### Authentication
- `mcp__zigi-amazon-mcp__get_auth_token` - Get authentication token (call this first!)

### Orders Management
- `mcp__zigi-amazon-mcp__get_orders` - Retrieve multiple orders
- `mcp__zigi-amazon-mcp__get_order` - Retrieve single order details

### Inventory Management
- `mcp__zigi-amazon-mcp__get_inventory_in_stock` - Get all products in stock
- `mcp__zigi-amazon-mcp__get_fbm_inventory` - Get FBM inventory for specific SKU
- `mcp__zigi-amazon-mcp__get_fbm_inventory_report` - Generate bulk FBM report
- `mcp__zigi-amazon-mcp__update_fbm_inventory` - Update single SKU inventory
- `mcp__zigi-amazon-mcp__bulk_update_fbm_inventory` - Bulk update inventory

### Product Management
- `mcp__zigi-amazon-mcp__update_product_price` - Update product pricing
- `mcp__zigi-amazon-mcp__get_listing` - Get product listing details
- `mcp__zigi-amazon-mcp__update_listing` - Update product listing attributes

## Usage Examples

### 1. Get Authentication Token
```
Use the mcp__zigi-amazon-mcp__get_auth_token tool
```

### 2. Get Recent Orders
```
Use the mcp__zigi-amazon-mcp__get_orders tool with:
- auth_token: <your_token>
- created_after: "2025-01-01T00:00:00Z"
- max_results: 50
```

### 3. Get Inventory in Stock
```
Use the mcp__zigi-amazon-mcp__get_inventory_in_stock tool with:
- auth_token: <your_token>
- fulfillment_type: "ALL"
- details: true
```

### 4. Update Product Price
```
Use the mcp__zigi-amazon-mcp__update_product_price tool with:
- auth_token: <your_token>
- seller_id: "A2C259Q0GU1WMI"
- seller_sku: "JL-BC002"
- new_price: "69.98"
- currency: "GBP"
```

### 5. Get Product Listing
```
Use the mcp__zigi-amazon-mcp__get_listing tool with:
- auth_token: <your_token>
- seller_id: "A2C259Q0GU1WMI"
- seller_sku: "JL-BC002"
```

### 6. Update Product Title
```
Use the mcp__zigi-amazon-mcp__update_listing tool with:
- auth_token: <your_token>
- seller_id: "A2C259Q0GU1WMI"
- seller_sku: "JL-BC002"
- title: "New Product Title"
```

## Response Handling

All tools return JSON responses. Check the `success` field to determine if the operation succeeded:

```json
{
  "success": true,
  "data": { ... }
}
```

For errors:
```json
{
  "success": false,
  "error": "error_code",
  "message": "Error description"
}
```

## Required Environment Variables

Ensure these are set before using SP-API tools:

- `LWA_CLIENT_ID` - Login with Amazon client ID
- `LWA_CLIENT_SECRET` - Login with Amazon client secret
- `LWA_REFRESH_TOKEN` - Login with Amazon refresh token
- `AWS_ACCESS_KEY_ID` - AWS access key
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `AWS_ROLE_ARN` - AWS role ARN (optional)

## Tips

1. Always get an auth token first before using any other tools
2. The server implements automatic rate limiting - you don't need to worry about it
3. Use marketplace ID "A1F83G8C2ARO7P" for UK marketplace
4. Price/listing updates typically take 5-15 minutes to reflect on Amazon
5. Check the `success` field in responses to handle errors appropriately