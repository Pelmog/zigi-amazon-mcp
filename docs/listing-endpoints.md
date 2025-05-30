# Amazon SP-API Listing Management Endpoints

This document describes the MCP endpoints for managing Amazon product listings through the SP-API.

## Authentication

All endpoints require authentication. You must first obtain an auth token:

```python
auth_token = get_auth_token()
```

## Endpoints

### 1. get_listing

Retrieve comprehensive product listing information from Amazon.

**Description:**
This endpoint retrieves detailed product listing data including title, description, bullet points, pricing, fulfillment availability, and any listing issues.

**Parameters:**
- `auth_token` (string, required): Authentication token from get_auth_token()
- `seller_id` (string, required): The seller ID for the merchant account
- `seller_sku` (string, required): SKU of the product to retrieve
- `marketplace_ids` (string, optional): Comma-separated marketplace IDs. Default: "A1F83G8C2ARO7P" (UK)
- `included_data` (string, optional): Comma-separated data to include: "attributes,issues,offers,fulfillmentAvailability"
- `region` (string, optional): AWS region. Default: "eu-west-1"
- `endpoint` (string, optional): SP-API endpoint URL. Default: "https://sellingpartnerapi-eu.amazon.com"

**Example Request:**
```python
result = get_listing(
    auth_token=auth_token,
    seller_id="A2C259Q0GU1WMI",
    seller_sku="JL-BC002",
    marketplace_ids="A1F83G8C2ARO7P",
    included_data="attributes,offers,fulfillmentAvailability"
)
```

**Example Response:**
```json
{
    "success": true,
    "data": {
        "sku": "JL-BC002",
        "asin": "B08XYZ123",
        "product_name": "Premium Widget Set",
        "condition": "NEW",
        "listing_status": ["DISCOVERABLE", "BUYABLE"],
        "created_date": "2023-01-15T10:30:00Z",
        "last_updated": "2024-03-20T14:45:00Z",
        "price": {
            "amount": "69.99",
            "currency": "GBP"
        },
        "fulfillment_availability": {
            "fulfillment_channel_code": "DEFAULT",
            "quantity": 150,
            "is_available": true,
            "handling_time": 2,
            "restock_date": null
        }
    },
    "metadata": {
        "timestamp": "2025-05-29T15:30:00Z",
        "marketplace": "A1F83G8C2ARO7P",
        "seller_id": "A2C259Q0GU1WMI",
        "request_id": "abc123-def456"
    }
}
```

### 2. update_listing

Update product listing information on Amazon using partial updates (PATCH method).

**Description:**
This endpoint allows you to update specific attributes of a product listing without providing all data. You can update title, bullet points, description, search terms, brand, and manufacturer.

**Parameters:**
- `auth_token` (string, required): Authentication token from get_auth_token()
- `seller_id` (string, required): The seller ID for the merchant account
- `seller_sku` (string, required): SKU of the product to update
- `title` (string, optional): New product title
- `bullet_points` (string, optional): Comma-separated list of bullet points (max 5)
- `description` (string, optional): New product description
- `search_terms` (string, optional): Comma-separated search terms/keywords (max 5)
- `brand` (string, optional): Product brand name
- `manufacturer` (string, optional): Product manufacturer name
- `marketplace_ids` (string, optional): Comma-separated marketplace IDs. Default: "A1F83G8C2ARO7P" (UK)
- `region` (string, optional): AWS region. Default: "eu-west-1"
- `endpoint` (string, optional): SP-API endpoint URL. Default: "https://sellingpartnerapi-eu.amazon.com"

**Example Request:**
```python
result = update_listing(
    auth_token=auth_token,
    seller_id="A2C259Q0GU1WMI",
    seller_sku="JL-BC002",
    title="Premium Widget Set - Professional Edition",
    bullet_points="High quality materials,Easy to use,Durable design,Eco-friendly,Great value",
    search_terms="widget,premium,professional,quality,durable",
    marketplace_ids="A1F83G8C2ARO7P"
)
```

**Example Response:**
```json
{
    "success": true,
    "data": {
        "sku": "JL-BC002",
        "status": "ACCEPTED",
        "submissionId": "xyz789-abc123"
    },
    "metadata": {
        "timestamp": "2025-05-29T15:35:00Z",
        "marketplace": "A1F83G8C2ARO7P",
        "seller_id": "A2C259Q0GU1WMI",
        "sku": "JL-BC002",
        "request_id": "def789-ghi012"
    },
    "listing_update": {
        "sku": "JL-BC002",
        "fields_updated": ["title", "bullet_points", "search_terms"],
        "marketplace": "A1F83G8C2ARO7P",
        "note": "Listing updates typically take 5-15 minutes to reflect on Amazon"
    }
}
```

## Error Responses

All endpoints return consistent error responses:

```json
{
    "success": false,
    "error": "error_code",
    "message": "Human-readable error message",
    "details": [...],
    "metadata": {
        "timestamp": "2025-05-29T15:40:00Z",
        "request_id": "error-123-456"
    }
}
```

### Common Error Codes:
- `auth_failed`: Authentication issues (invalid token, missing credentials)
- `invalid_input`: Validation failures (invalid SKU, missing required fields)
- `rate_limit_exceeded`: API rate limit hit
- `api_error`: SP-API returned an error
- `unexpected_error`: Unhandled exceptions

## Important Notes

1. **Authentication**: Always call `get_auth_token()` first to obtain a valid auth token
2. **Rate Limiting**: The Listings API has rate limits. The client implements automatic rate limiting
3. **Update Delays**: Changes typically take 5-15 minutes to reflect on Amazon
4. **Partial Updates**: The update_listing endpoint uses PATCH, so you only need to provide fields you want to change
5. **Field Limits**: 
   - Bullet points: Maximum 5
   - Search terms: Maximum 5
   - Title: Check Amazon's category-specific requirements
6. **Marketplace Support**: Currently optimized for UK marketplace (A1F83G8C2ARO7P)

## Required Environment Variables

```bash
# Login with Amazon (LWA)
LWA_CLIENT_ID=your_client_id
LWA_CLIENT_SECRET=your_client_secret
LWA_REFRESH_TOKEN=your_refresh_token

# AWS Credentials
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_ROLE_ARN=arn:aws:iam::account:role/role-name  # Optional

# Seller Information
SELLER_ID=your_seller_id
```

## Testing

A test script is provided at `test_listing_endpoints.py` that demonstrates:
- Getting basic listing information
- Getting detailed listing data with all available fields
- Updating listing fields (dry run by default)
- Input validation testing

Run the test script:
```bash
python test_listing_endpoints.py
```