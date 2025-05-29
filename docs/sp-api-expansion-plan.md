# Amazon SP-API Expansion Plan

## Overview
This document outlines the expansion of the zigi-amazon-mcp server to include comprehensive Amazon SP-API functionality, with a focus on inventory management.

## Current Implementation
- ✅ Authentication (LWA + AWS STS)
- ✅ Orders API (get_orders, get_order)

## Phase 1: Core Inventory Management (Priority: HIGH)

### 1.1 FBA Inventory API
```python
@mcp.tool()
def get_inventory_summaries(
    auth_token: str,
    marketplace_ids: str = "A1F83G8C2ARO7P",
    granularity_type: str = "Marketplace",  # Marketplace or ASIN
    granularity_id: str = "",
    start_date: str = "",
    seller_skus: str = "",  # Comma-separated
    max_results: int = 50
) -> str:
    """Get inventory summaries with quantities by marketplace, ASIN, or SKU."""
```

### 1.2 Listings Items API
```python
@mcp.tool()
def get_listings_item(
    auth_token: str,
    seller_sku: str,
    marketplace_ids: str = "A1F83G8C2ARO7P",
    include_data: str = "attributes,identifiers,productTypes,summaries"
) -> str:
    """Get detailed listing information including inventory quantity."""

@mcp.tool()
def update_listings_item(
    auth_token: str,
    seller_sku: str,
    marketplace_ids: str,
    product_type: str,
    patches: str  # JSON array of patch operations
) -> str:
    """Update listing attributes including price and quantity."""
```

### 1.3 Inventory Health API
```python
@mcp.tool()
def get_inventory_health(
    auth_token: str,
    marketplace_ids: str = "A1F83G8C2ARO7P",
    seller_skus: str = "",
    asins: str = "",
    inventory_health_status: str = ""  # SELLABLE, DEFECTIVE, etc.
) -> str:
    """Get FBA inventory health metrics including stranded inventory."""
```

## Phase 2: Advanced Inventory Features (Priority: HIGH)

### 2.1 Feeds API for Bulk Updates
```python
@mcp.tool()
def create_inventory_feed(
    auth_token: str,
    feed_type: str = "POST_FLAT_FILE_INVLOADER_DATA",
    content: str,  # CSV or XML content
    marketplace_ids: str = "A1F83G8C2ARO7P"
) -> str:
    """Submit bulk inventory updates via feed."""

@mcp.tool()
def get_feed_status(
    auth_token: str,
    feed_id: str
) -> str:
    """Check status of submitted feed."""
```

### 2.2 Reports API
```python
@mcp.tool()
def request_inventory_report(
    auth_token: str,
    report_type: str = "GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA",
    marketplace_ids: str = "A1F83G8C2ARO7P",
    start_date: str = "",
    end_date: str = ""
) -> str:
    """Request inventory reports (FBA, FBM, etc.)."""

@mcp.tool()
def get_report(
    auth_token: str,
    report_id: str
) -> str:
    """Download completed report data."""
```

## Phase 3: Fulfillment & Shipments (Priority: MEDIUM)

### 3.1 FBA Inbound API
```python
@mcp.tool()
def get_shipments(
    auth_token: str,
    shipment_status_list: str = "",  # WORKING, SHIPPED, RECEIVING, etc.
    marketplace_ids: str = "A1F83G8C2ARO7P"
) -> str:
    """Get FBA inbound shipments."""

@mcp.tool()
def create_inbound_shipment_plan(
    auth_token: str,
    ship_from_address: str,  # JSON
    items: str,  # JSON array of items
    marketplace_ids: str = "A1F83G8C2ARO7P"
) -> str:
    """Create FBA shipment plan."""
```

### 3.2 FBA Outbound API
```python
@mcp.tool()
def create_fulfillment_order(
    auth_token: str,
    seller_fulfillment_order_id: str,
    items: str,  # JSON array
    destination_address: str,  # JSON
    shipping_speed: str = "Standard"
) -> str:
    """Create multi-channel fulfillment order."""
```

## Phase 4: Pricing & Competition (Priority: MEDIUM)

### 4.1 Product Pricing API
```python
@mcp.tool()
def get_competitive_pricing(
    auth_token: str,
    asins: str,  # Comma-separated
    marketplace_id: str = "A1F83G8C2ARO7P"
) -> str:
    """Get competitive pricing for products."""

@mcp.tool()
def get_pricing_offers(
    auth_token: str,
    asin: str,
    marketplace_id: str = "A1F83G8C2ARO7P",
    item_condition: str = "New"
) -> str:
    """Get current offers and Buy Box information."""
```

## Phase 5: Product Catalog (Priority: LOW)

### 5.1 Catalog Items API
```python
@mcp.tool()
def search_catalog_items(
    auth_token: str,
    keywords: str = "",
    marketplace_ids: str = "A1F83G8C2ARO7P",
    brand: str = "",
    classification_ids: str = ""
) -> str:
    """Search Amazon catalog."""

@mcp.tool()
def get_catalog_item(
    auth_token: str,
    asin: str,
    marketplace_ids: str = "A1F83G8C2ARO7P",
    included_data: str = "attributes,identifiers,images,productTypes,salesRanks"
) -> str:
    """Get detailed catalog information."""
```

## Architectural Improvements

### 1. Rate Limiting Handler
```python
class RateLimiter:
    def __init__(self):
        self.buckets = {}
    
    def check_rate_limit(self, api_path: str) -> bool:
        # Implement token bucket algorithm
        pass
```

### 2. Response Caching
```python
from functools import lru_cache
from datetime import datetime, timedelta

@lru_cache(maxsize=1000)
def cached_api_call(endpoint: str, params: str, cache_duration: int = 300):
    # Cache frequently accessed data
    pass
```

### 3. Error Recovery
```python
def retry_with_backoff(func, max_retries=3, backoff_factor=2):
    """Exponential backoff for rate limit errors."""
    pass
```

### 4. Marketplace Configuration
```python
MARKETPLACE_CONFIG = {
    "UK": {
        "id": "A1F83G8C2ARO7P",
        "endpoint": "https://sellingpartnerapi-eu.amazon.com",
        "region": "eu-west-1"
    },
    "US": {
        "id": "ATVPDKIKX0DER",
        "endpoint": "https://sellingpartnerapi-na.amazon.com",
        "region": "us-east-1"
    },
    # Add more marketplaces
}
```

## Implementation Best Practices

1. **Consistent Error Handling**
   - Return structured JSON with success/error status
   - Include SP-API error codes and messages
   - Provide actionable error messages

2. **Parameter Validation**
   - Validate marketplace IDs
   - Check date formats (ISO 8601)
   - Validate enum values (statuses, types)

3. **Response Formatting**
   - Always return JSON
   - Include metadata (timestamp, marketplace, etc.)
   - Standardize field names across endpoints

4. **Security Considerations**
   - Never log sensitive data (tokens, addresses)
   - Validate all input parameters
   - Use parameterized queries for any data storage

5. **Testing Strategy**
   - Mock SP-API responses for unit tests
   - Integration tests with sandbox environment
   - Load testing for rate limit handling

## Example Usage Flow

```python
# 1. Authenticate
auth_token = get_auth_token()

# 2. Get inventory overview
inventory = get_inventory_summaries(
    auth_token=auth_token,
    marketplace_ids="A1F83G8C2ARO7P",
    granularity_type="Marketplace"
)

# 3. Check specific product
product = get_listings_item(
    auth_token=auth_token,
    seller_sku="MY-SKU-123",
    marketplace_ids="A1F83G8C2ARO7P"
)

# 4. Update inventory
result = update_listings_item(
    auth_token=auth_token,
    seller_sku="MY-SKU-123",
    marketplace_ids="A1F83G8C2ARO7P",
    product_type="PRODUCT",
    patches='[{"op": "replace", "path": "/attributes/fulfillment_availability", "value": [{"quantity": 100}]}]'
)

# 5. Create bulk update feed
feed_result = create_inventory_feed(
    auth_token=auth_token,
    feed_type="POST_FLAT_FILE_INVLOADER_DATA",
    content="sku,quantity\nMY-SKU-123,100\nMY-SKU-456,50"
)
```

## Monitoring & Analytics

Consider adding:
- Request/response logging
- Performance metrics
- Error rate tracking
- Usage analytics per endpoint
- Alert system for critical failures

## Next Steps

1. **Immediate Actions**
   - Implement Phase 1 inventory endpoints
   - Add rate limiting handler
   - Create integration tests

2. **Short-term Goals**
   - Complete Phase 2 (Feeds & Reports)
   - Add marketplace configuration
   - Implement caching layer

3. **Long-term Vision**
   - Full SP-API coverage
   - Multi-marketplace support
   - Advanced analytics dashboard
   - Webhook support for real-time updates