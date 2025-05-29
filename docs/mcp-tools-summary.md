# MCP Tools Summary

This document lists all available MCP tools in the zigi-amazon-mcp server.

## Authentication

### get_auth_token
- **Purpose**: Generate authentication token (MUST BE CALLED FIRST!)
- **Parameters**: None
- **Returns**: Authentication token for use with all other functions

## Core Utility Tools

### hello_world
- **Purpose**: Simple greeting tool for testing
- **Parameters**: `auth_token`, `name` (optional)

### process_text
- **Purpose**: Process text with various operations
- **Parameters**: `auth_token`, `text`, `operation`

### read_file / write_file
- **Purpose**: Read from or write to local files
- **Parameters**: `auth_token`, `file_path`, `content` (for write)

### json_process
- **Purpose**: Parse/format JSON data
- **Parameters**: `auth_token`, `data`, `operation`

### convert_data
- **Purpose**: Convert between formats (base64, hex, etc.)
- **Parameters**: `auth_token`, `data`, `from_format`, `to_format`

### store_session_data / get_session_data
- **Purpose**: Store and retrieve session data
- **Parameters**: `auth_token`, `session_id`, `data` (for store)

## Amazon Inventory Tools

### get_inventory_in_stock
- **Purpose**: Get all products currently in stock (FBA/FBM/ALL)
- **Parameters**: `auth_token`, `marketplace_ids`, `fulfillment_type`, `details`, `max_results`
- **Note**: Currently returns FBA inventory only

### get_orders
- **Purpose**: Retrieve Amazon orders with pagination
- **Parameters**: `auth_token`, `marketplace_ids`, `created_after`, `created_before`, `order_statuses`, `max_results`

### get_order
- **Purpose**: Retrieve single Amazon order details
- **Parameters**: `auth_token`, `order_id`

## FBM (Fulfilled by Merchant) Tools

### get_fbm_inventory
- **Purpose**: Get FBM inventory for a specific SKU (real-time data)
- **Parameters**: `auth_token`, `seller_id`, `seller_sku`, `marketplace_ids`, `include_inactive`
- **Returns**: Product details, pricing, fulfillment availability

### get_fbm_inventory_report
- **Purpose**: Generate bulk FBM inventory report
- **Parameters**: `auth_token`, `report_type` (ALL_DATA/ACTIVE/INACTIVE), `marketplace_ids`
- **Returns**: Report ID for asynchronous processing

### update_fbm_inventory
- **Purpose**: Update FBM inventory quantity and fulfillment details
- **Parameters**: `auth_token`, `seller_id`, `seller_sku`, `quantity`, `handling_time`, `restock_date`

### bulk_update_fbm_inventory
- **Purpose**: Bulk update FBM inventory using Feeds API
- **Parameters**: `auth_token`, `inventory_updates` (JSON array), `marketplace_id`

## Pricing Tools

### update_product_price ✨ NEW!
- **Purpose**: Update product price on Amazon (works for both FBA and FBM)
- **Parameters**: 
  - `auth_token` (required)
  - `seller_id` (required) 
  - `seller_sku` (required)
  - `new_price` (required) - e.g., "69.98"
  - `currency` (optional, default: "GBP")
  - `marketplace_ids` (optional, default: UK)
- **Example**: Update JL-BC002 to £69.98
- **Note**: Price changes typically take 5-15 minutes to reflect on Amazon

## Required Environment Variables

All Amazon SP-API tools require these environment variables:
- `LWA_CLIENT_ID` - Login with Amazon client ID
- `LWA_CLIENT_SECRET` - Login with Amazon client secret  
- `LWA_REFRESH_TOKEN` - Login with Amazon refresh token
- `AWS_ACCESS_KEY_ID` - AWS access key
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `AWS_ROLE_ARN` - AWS role ARN (optional, has default)

## Usage Pattern

1. Always call `get_auth_token()` first
2. Use the returned token in all subsequent calls
3. Handle errors appropriately - check `success` field in responses
4. Monitor rate limits - the server implements automatic rate limiting

## Testing

All tools have been tested and verified to work correctly with:
- Seller ID: A2C259Q0GU1WMI
- Test SKU: JL-BC002 (Maximuv Folding Wagon)
- Marketplace: A1F83G8C2ARO7P (UK)

The price update functionality has been successfully tested, changing the price from £69.99 to £69.98.