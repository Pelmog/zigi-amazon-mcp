# Inventory In Stock Endpoint Documentation

## Overview

The `get_inventory_in_stock` endpoint retrieves all products currently in stock from Amazon FBA inventory, filtering out items with zero quantity and providing detailed inventory breakdowns.

## Endpoint Details

**MCP Tool Name**: `mcp__zigi-amazon-mcp__get_inventory_in_stock`

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `auth_token` | string | Required | Authentication token from `get_auth_token()` |
| `marketplace_ids` | string | "A1F83G8C2ARO7P" | Comma-separated marketplace IDs (UK default) |
| `fulfillment_type` | string | "ALL" | Filter by fulfillment type: 'FBA', 'FBM', or 'ALL' |
| `details` | boolean | true | Include detailed inventory breakdown |
| `region` | string | "eu-west-1" | AWS region for SP-API endpoint |
| `endpoint` | string | "https://sellingpartnerapi-eu.amazon.com" | SP-API endpoint URL |

### Response Format

```json
{
  "success": true,
  "summary": {
    "products_in_stock": 2,
    "total_units": 6,
    "marketplace": "A1F83G8C2ARO7P",
    "fulfillment_type": "ALL",
    "timestamp": "2025-01-29T12:30:00Z",
    "note": "Shows FBA inventory only"
  },
  "inventory": [
    {
      "asin": "B09VXWSTQK",
      "fn_sku": "X0001234567",
      "seller_sku": "MY-SKU-123",
      "product_name": "Product Name",
      "total_quantity": 3,
      "condition": "NewItem",
      "last_updated": "2025-01-29T10:00:00Z",
      "inventory_breakdown": {
        "fulfillable": 2,
        "unfulfillable": 0,
        "reserved": 1,
        "inbound": {
          "working": 0,
          "shipped": 0,
          "receiving": 0
        }
      }
    }
  ]
}
```

## Key Features

1. **Automatic Filtering**: Only returns products with `total_quantity > 0`
2. **Fulfillment Type Filter**: Filter by FBA, FBM, or ALL inventory
3. **Sorted Results**: Products are sorted by quantity (highest first)
4. **Detailed Breakdown**: Optional breakdown of inventory status
5. **Pagination Support**: Automatically handles paginated results
6. **Rate Limit Handling**: Returns proper error with retry_after on 429

## Important Notes

- **FBA Only**: The FBA Inventory API only returns FBA (Fulfilled by Amazon) inventory
- **FBM Limitation**: For FBM inventory, you would need to use the Inventory API v0 or Listings API
- **ALL Option**: When using 'ALL', only FBA inventory is returned due to API limitations

## Usage Examples

### Basic Usage (With Details)

```python
result = get_inventory_in_stock(
    auth_token=token,
    marketplace_ids="A1F83G8C2ARO7P"  # UK marketplace
)
```

### Without Detailed Breakdown

```python
result = get_inventory_in_stock(
    auth_token=token,
    marketplace_ids="A1F83G8C2ARO7P",
    details=False  # Only basic info
)
```

### FBA Inventory Only

```python
result = get_inventory_in_stock(
    auth_token=token,
    marketplace_ids="A1F83G8C2ARO7P",
    fulfillment_type="FBA"  # Only FBA inventory
)
```

### Multiple Marketplaces

```python
result = get_inventory_in_stock(
    auth_token=token,
    marketplace_ids="A1F83G8C2ARO7P,A1PA6795UKMFR9"  # UK and Germany
)
```

## Inventory Fields Explained

### Basic Fields
- **asin**: Amazon Standard Identification Number
- **fn_sku**: Fulfillment Network SKU (Amazon's internal SKU)
- **seller_sku**: Your product SKU
- **product_name**: Product title/name
- **total_quantity**: Total units in Amazon's fulfillment centers
- **condition**: Product condition (NewItem, UsedLikeNew, etc.)
- **last_updated**: When inventory data was last updated

### Inventory Breakdown (when details=True)
- **fulfillable**: Units available for immediate shipment
- **unfulfillable**: Damaged/defective units that cannot be sold
- **reserved**: Units allocated to pending orders
- **inbound**:
  - **working**: Units being prepared for shipment to Amazon
  - **shipped**: Units in transit to Amazon
  - **receiving**: Units at Amazon warehouse being processed

## Error Handling

### Rate Limit Error
```json
{
  "success": false,
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Please wait before making another request.",
  "retry_after": 60
}
```

### Authentication Error
```json
{
  "success": false,
  "error": "auth_failed",
  "message": "Failed to get Amazon access token. Check your LWA credentials."
}
```

### API Error
```json
{
  "success": false,
  "error": "api_error",
  "status_code": 400,
  "message": "SP-API request failed",
  "details": [...]
}
```

## Rate Limits

- **Endpoint**: `/fba/inventory/v1/summaries`
- **Rate**: 5 requests per second
- **Burst**: 10 requests

## Required Permissions

The SP-API application must have the following scope:
- `inventory:read` - Read access to inventory data

## Implementation Notes

1. **Granularity**: The API requires `granularityType` and `granularityId` parameters
2. **Pagination**: Results are paginated with 50 items per page by default
3. **UK Marketplace**: Default marketplace is UK (A1F83G8C2ARO7P)
4. **Zero Stock Filter**: Products with zero quantity are automatically filtered out
5. **Sorting**: Results are sorted by total_quantity in descending order

## Common Use Cases

1. **Stock Level Monitoring**: Check which products need restocking
2. **Inventory Alerts**: Identify products running low on stock
3. **FBA Health Check**: Monitor unfulfillable inventory levels
4. **Inbound Tracking**: Track inventory in transit to Amazon
5. **Multi-Marketplace**: Compare stock levels across different countries
