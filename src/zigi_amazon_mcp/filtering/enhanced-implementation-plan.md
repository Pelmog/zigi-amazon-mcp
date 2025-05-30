# Enhanced JSON Filtering Implementation Plan with Data Reduction

## Overview
This enhanced plan extends the JSON Query-based filtering functionality to include **data reduction filters** and **filter chaining** capabilities. The system will allow LLMs to:

1. **Filter records** - reduce the number of records returned
2. **Reduce field data** - select only specific fields from each record
3. **Chain filters** - combine multiple filters in a single MCP tool call
4. **Minimize response payload** - significantly reduce JSON data size

## 1. Enhanced Architecture

### 1.1 Directory Structure
```
src/zigi_amazon_mcp/filtering/
├── __init__.py
├── filtering-instruction.md          # Already exists
├── implementation-plan.md            # Original plan
├── enhanced-implementation-plan.md   # This enhanced plan
├── filter_library.py                # Filter database operations
├── filter_manager.py                # Filter application and chaining
├── filter_chain.py                  # Filter chaining logic
├── database.py                      # Database schema and connection
├── migrations/
│   ├── __init__.py
│   └── 001_initial_schema.sql       # Enhanced schema
└── seed_data/
    ├── __init__.py
    ├── order_filters.json           # Record filtering
    ├── order_field_filters.json     # Field reduction filters
    ├── inventory_filters.json       # Record filtering
    ├── inventory_field_filters.json # Field reduction filters
    ├── common_filters.json          # Generic record filters
    └── common_field_filters.json    # Generic field reduction
```

### 1.2 Enhanced Filter Types

#### A. Record Filters (Existing)
- Reduce the **number of records** returned
- Examples: high-value orders, low-stock items, recent orders

#### B. Field Filters (NEW)
- Reduce the **data within each record**
- Examples: order-summary (only ID and total), sku-and-quantity-only
- Significantly reduce payload size

#### C. Filter Chains (NEW)
- Combine multiple filters in sequence
- Apply record filtering first, then field filtering
- Support complex data reduction scenarios

## 2. Enhanced Database Schema

### 2.1 Updated Filter Categories
```sql
-- Enhanced filters table with filter type
CREATE TABLE filters (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,           -- 'orders', 'inventory', 'common'
    filter_type TEXT NOT NULL,        -- 'record', 'field', 'chain'
    query TEXT NOT NULL,              -- JSON Query expression
    author TEXT NOT NULL,
    version TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    estimated_reduction_percent INTEGER DEFAULT NULL  -- Expected data reduction %
);

-- Filter chains table (for chained filters)
CREATE TABLE filter_chains (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chain_filter_id TEXT NOT NULL,   -- References filters.id where filter_type='chain'
    step_order INTEGER NOT NULL,     -- Order of execution (1, 2, 3...)
    step_filter_id TEXT NOT NULL,    -- References filters.id for individual step
    FOREIGN KEY (chain_filter_id) REFERENCES filters(id) ON DELETE CASCADE,
    FOREIGN KEY (step_filter_id) REFERENCES filters(id) ON DELETE CASCADE,
    UNIQUE(chain_filter_id, step_order)
);

-- All other tables remain the same...
```

### 2.2 Filter Chain Data Model
```python
@dataclass
class FilterChain:
    chain_id: str
    name: str
    description: str
    steps: List[FilterStep]
    estimated_reduction: int  # Percentage reduction expected

@dataclass
class FilterStep:
    order: int
    filter_id: str
    filter_def: FilterDefinition
```

## 3. Amazon SP-API Response Analysis

### 3.1 Orders API - Typical Response Size
**Full Order Response** (~2KB per order):
```json
{
  "AmazonOrderId": "123-1234567-1234567",
  "SellerOrderId": "ORDER-001",
  "PurchaseDate": "2025-01-30T10:00:00Z",
  "LastUpdateDate": "2025-01-30T11:00:00Z",
  "OrderStatus": "Shipped",
  "FulfillmentChannel": "MFN",
  "SalesChannel": "Amazon.co.uk",
  "OrderChannel": "amazon.co.uk",
  "ShipServiceLevel": "Standard",
  "OrderTotal": {
    "CurrencyCode": "GBP",
    "Amount": "89.99"
  },
  "NumberOfItemsShipped": 2,
  "NumberOfItemsUnshipped": 0,
  "PaymentExecutionDetail": [...],
  "PaymentMethod": "Other",
  "PaymentMethodDetails": ["Standard"],
  "MarketplaceId": "A1F83G8C2ARO7P",
  "ShipmentServiceLevelCategory": "Standard",
  "EasyShipShipmentStatus": null,
  "CbaDisplayableShippingLabel": "",
  "OrderType": "StandardOrder",
  "EarliestShipDate": "2025-01-30T12:00:00Z",
  "LatestShipDate": "2025-01-31T12:00:00Z",
  "EarliestDeliveryDate": "2025-02-02T12:00:00Z",
  "LatestDeliveryDate": "2025-02-05T12:00:00Z",
  "IsBusinessOrder": false,
  "IsPrime": true,
  "IsGlobalExpressEnabled": false,
  "DefaultShipFromLocationAddress": {
    "Name": "Seller Name",
    "AddressLine1": "123 Business St",
    "AddressLine2": "Suite 100",
    "AddressLine3": "",
    "City": "London",
    "County": "",
    "District": "",
    "StateOrRegion": "",
    "Municipality": "",
    "PostalCode": "SW1A 1AA",
    "CountryCode": "GB",
    "Phone": "+44 20 1234 5678"
  },
  "BuyerInfo": {
    "BuyerEmail": "encrypted-email@amazon.com",
    "BuyerName": "John Smith",
    "BuyerCounty": "",
    "BuyerTaxInfo": {...},
    "PurchaseOrderNumber": ""
  },
  "OrderItems": [
    {
      "ASIN": "B08XYZ123",
      "SellerSKU": "SKU-001",
      "OrderItemId": "12345678901234",
      "Title": "Product Title Here",
      "QuantityOrdered": 2,
      "QuantityShipped": 2,
      "ProductInfo": {...},
      "PointsGranted": {...},
      "ItemPrice": {
        "CurrencyCode": "GBP",
        "Amount": "79.99"
      },
      "ShippingPrice": {
        "CurrencyCode": "GBP",
        "Amount": "9.99"
      },
      "ItemTax": {...},
      "ShippingTax": {...},
      "ShippingDiscount": {...},
      "PromotionDiscount": {...},
      "PromotionIds": [...],
      "CODFee": {...},
      "CODFeeDiscount": {...},
      "IsGift": false,
      "ConditionNote": "",
      "ConditionId": "New",
      "ConditionSubtypeId": "New",
      "ScheduledDeliveryStartDate": "",
      "ScheduledDeliveryEndDate": "",
      "PriceDesignation": "",
      "TaxCollection": {...},
      "SerialNumberRequired": false,
      "IsTransparency": false,
      "IossNumber": "",
      "StoreChainStoreId": "",
      "DeemedResellerCategory": "IOSS",
      "BuyerInfo": {...}
    }
  ]
}
```

### 3.2 Inventory API - Typical Response Size
**Full Inventory Response** (~1KB per item):
```json
{
  "inventorySummaries": [
    {
      "asin": "B08XYZ123",
      "fnSku": "X000ABC123",
      "sellerSku": "SKU-001",
      "condition": "NewItem",
      "inventoryDetails": {
        "fulfillableQuantity": 150,
        "inboundWorkingQuantity": 0,
        "inboundShippedQuantity": 25,
        "inboundReceivingQuantity": 0,
        "reservedQuantity": {
          "totalReservedQuantity": 5,
          "pendingCustomerOrderQuantity": 3,
          "pendingTransshipmentQuantity": 2,
          "fcProcessingQuantity": 0
        },
        "researchingQuantity": 0,
        "unfulfillableQuantity": 2
      },
      "totalQuantity": 180,
      "lastUpdatedTime": "2025-01-30T10:30:00Z",
      "productName": "Example Product Name",
      "estimatedValue": {
        "value": 1500.50,
        "currency": "GBP"
      }
    }
  ]
}
```

## 4. Field Reduction Filter Examples

### 4.1 Order Field Filters

#### A. Order Summary Filter
**Reduces ~2KB to ~100 bytes (95% reduction)**
```json
{
  "id": "order_summary",
  "name": "Order Summary Only",
  "description": "Return only order ID, status, and total amount",
  "filter_type": "field",
  "query": "map({orderId: .AmazonOrderId, status: .OrderStatus, total: .OrderTotal.Amount, currency: .OrderTotal.CurrencyCode})",
  "estimated_reduction_percent": 95
}
```

#### B. Order Essentials Filter
**Reduces ~2KB to ~300 bytes (85% reduction)**
```json
{
  "id": "order_essentials",
  "name": "Order Essentials",
  "description": "Key order information without addresses and detailed items",
  "filter_type": "field",
  "query": "map({orderId: .AmazonOrderId, status: .OrderStatus, purchaseDate: .PurchaseDate, total: .OrderTotal, itemCount: .NumberOfItemsShipped, isPrime: .IsPrime})",
  "estimated_reduction_percent": 85
}
```

#### C. Order Items Summary Filter
**Reduces order items to essentials only**
```json
{
  "id": "order_items_summary",
  "name": "Order Items Summary",
  "description": "Return only SKU, quantity, and price for order items",
  "filter_type": "field",
  "query": ".OrderItems | map({sku: .SellerSKU, quantity: .QuantityOrdered, price: .ItemPrice.Amount, title: .Title})",
  "estimated_reduction_percent": 80
}
```

#### D. Order Financial Filter
**Focus on financial data only**
```json
{
  "id": "order_financial",
  "name": "Order Financial Data",
  "description": "Extract only financial information from orders",
  "filter_type": "field",
  "query": "map({orderId: .AmazonOrderId, orderTotal: .OrderTotal, items: .OrderItems | map({sku: .SellerSKU, itemPrice: .ItemPrice, shippingPrice: .ShippingPrice})})",
  "estimated_reduction_percent": 75
}
```

### 4.2 Inventory Field Filters

#### A. Inventory Summary Filter
**Reduces ~1KB to ~80 bytes (92% reduction)**
```json
{
  "id": "inventory_summary",
  "name": "Inventory Summary Only",
  "description": "Return only SKU, ASIN, and total quantity",
  "filter_type": "field",
  "query": "map({sku: .sellerSku, asin: .asin, quantity: .totalQuantity})",
  "estimated_reduction_percent": 92
}
```

#### B. Inventory Stock Status Filter
**Focus on stock levels only**
```json
{
  "id": "inventory_stock_status",
  "name": "Inventory Stock Status",
  "description": "Stock levels and fulfillable quantities only",
  "filter_type": "field",
  "query": "map({sku: .sellerSku, totalQuantity: .totalQuantity, fulfillable: .inventoryDetails.fulfillableQuantity, reserved: .inventoryDetails.reservedQuantity.totalReservedQuantity, lastUpdated: .lastUpdatedTime})",
  "estimated_reduction_percent": 75
}
```

#### C. Inventory Value Filter
**Focus on inventory valuation**
```json
{
  "id": "inventory_value",
  "name": "Inventory Value Analysis",
  "description": "SKU, quantity, and estimated value only",
  "filter_type": "field",
  "query": "map({sku: .sellerSku, quantity: .totalQuantity, estimatedValue: .estimatedValue.value, currency: .estimatedValue.currency, valuePerUnit: (.estimatedValue.value / .totalQuantity)})",
  "estimated_reduction_percent": 85
}
```

### 4.3 Common Field Filters

#### A. ID and Name Only Filter
**Ultra-minimal response**
```json
{
  "id": "id_name_only",
  "name": "ID and Name Only",
  "description": "Extract only identifier and name fields",
  "filter_type": "field",
  "query": "map({id: (.id // .AmazonOrderId // .sellerSku // .asin), name: (.name // .Title // .productName)})",
  "estimated_reduction_percent": 95
}
```

#### B. Count Only Filter
**Just return the count of items**
```json
{
  "id": "count_only",
  "name": "Count Only",
  "description": "Return only the count of items",
  "filter_type": "field",
  "query": "{count: length(.)}",
  "estimated_reduction_percent": 99
}
```

## 5. Filter Chaining Implementation

### 5.1 Chain Definition Examples

#### A. High-Value Order Summary Chain
**Step 1**: Filter high-value orders (record filter)
**Step 2**: Extract summary fields only (field filter)
**Combined reduction**: ~98% data reduction
```json
{
  "id": "high_value_order_summary_chain",
  "name": "High-Value Order Summary Chain",
  "description": "Filter orders over £100 and return summary data only",
  "filter_type": "chain",
  "estimated_reduction_percent": 98,
  "chain_steps": [
    {"order": 1, "filter_id": "high_value_orders"},
    {"order": 2, "filter_id": "order_summary"}
  ]
}
```

#### B. Low Stock Inventory Alert Chain
**Step 1**: Filter low stock items (record filter)
**Step 2**: Return stock status only (field filter)
```json
{
  "id": "low_stock_alert_chain",
  "name": "Low Stock Alert Chain",
  "description": "Find low stock items and return essential stock data",
  "filter_type": "chain",
  "estimated_reduction_percent": 95,
  "chain_steps": [
    {"order": 1, "filter_id": "low_stock_alert"},
    {"order": 2, "filter_id": "inventory_stock_status"}
  ]
}
```

### 5.2 Chain Execution Logic
```python
class FilterChainManager:
    """Execute filter chains with proper sequencing."""

    def execute_chain(self, data: Any, chain_def: FilterChain) -> Any:
        """Execute a chain of filters in sequence."""
        result = data

        for step in sorted(chain_def.steps, key=lambda x: x.order):
            filter_def = self.filter_db.get_filter_by_id(step.filter_id)
            if not filter_def:
                raise ValueError(f"Filter '{step.filter_id}' not found in chain")

            # Apply filter to current result
            result = self.apply_filter(result, filter_def)

            # Log reduction for monitoring
            original_size = len(json.dumps(data))
            current_size = len(json.dumps(result))
            reduction = ((original_size - current_size) / original_size) * 100
            logger.info(f"Chain step {step.order}: {reduction:.1f}% reduction")

        return result
```

## 6. Enhanced MCP Tool Implementation

### 6.1 Enhanced Tool Parameters
```python
@mcp.tool()
def get_orders(
    auth_token: Annotated[str, "Authentication token"],
    # ... existing parameters ...
    filter_id: Annotated[str, "Single filter ID to apply"] = "",
    filter_chain: Annotated[str, "Comma-separated chain of filter IDs"] = "",
    custom_filter: Annotated[str, "Custom JSON Query expression"] = "",
    filter_params: Annotated[str, "JSON string of filter parameters"] = "{}",
    reduce_response: Annotated[bool, "Apply default data reduction"] = False
) -> str:
    """Enhanced get_orders with chaining and data reduction support."""
```

### 6.2 Filter Chain Execution
```python
def apply_enhanced_filtering(filter_db: FilterDatabase,
                           data: Any,
                           filter_id: str = "",
                           filter_chain: str = "",
                           custom_filter: str = "",
                           filter_params: str = "{}",
                           reduce_response: bool = False) -> Dict[str, Any]:
    """Apply filtering with chaining and data reduction support."""

    original_size = len(json.dumps(data))
    result = data

    try:
        params = json.loads(filter_params) if filter_params else {}

        if filter_chain:
            # Execute filter chain
            chain_ids = [id.strip() for id in filter_chain.split(',')]
            for chain_filter_id in chain_ids:
                filter_def = filter_db.get_filter_by_id(chain_filter_id)
                if filter_def.filter_type == 'chain':
                    # Execute predefined chain
                    chain_def = filter_db.get_filter_chain(chain_filter_id)
                    result = FilterChainManager().execute_chain(result, chain_def)
                else:
                    # Execute individual filter
                    result = apply_filter_with_parameters(filter_def, result, params)

        elif filter_id:
            # Single filter
            filter_def = filter_db.get_filter_by_id(filter_id)
            result = apply_filter_with_parameters(filter_def, result, params)

        elif custom_filter:
            # Custom filter
            result = jsonquery(result, custom_filter)

        elif reduce_response:
            # Apply default reduction filter based on endpoint
            default_filter = filter_db.get_default_reduction_filter(endpoint_type)
            result = apply_filter_with_parameters(default_filter, result, {})

        # Calculate reduction
        final_size = len(json.dumps(result))
        reduction_percent = ((original_size - final_size) / original_size) * 100

        return {
            "success": True,
            "data": result,
            "metadata": {
                "original_size_bytes": original_size,
                "final_size_bytes": final_size,
                "reduction_percent": round(reduction_percent, 1),
                "filters_applied": filter_chain or filter_id or "custom"
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": "filter_application_failed",
            "message": str(e),
            "original_data": data
        }
```

## 7. Enhanced Seed Data Structure

### 7.1 Order Field Filters JSON
```json
{
  "metadata": {
    "version": "1.0.0",
    "description": "Field reduction filters for Amazon Orders API",
    "category": "field_filters"
  },
  "filters": [
    {
      "id": "order_summary",
      "name": "Order Summary Only",
      "description": "Return only order ID, status, and total amount - 95% data reduction",
      "category": "orders",
      "filter_type": "field",
      "query": "map({orderId: .AmazonOrderId, status: .OrderStatus, total: .OrderTotal.Amount, currency: .OrderTotal.CurrencyCode})",
      "author": "system",
      "version": "1.0.0",
      "estimated_reduction_percent": 95,
      "compatible_endpoints": ["get_orders", "get_order"],
      "parameters": {},
      "examples": [
        {
          "name": "Basic order summary",
          "description": "Extract just the essential order information",
          "parameters": {}
        }
      ],
      "tags": ["summary", "minimal", "essential", "reduction"],
      "test_cases": [
        {
          "name": "single_order_test",
          "test_data": {
            "AmazonOrderId": "123-1234567-1234567",
            "OrderStatus": "Shipped",
            "OrderTotal": {"Amount": "89.99", "CurrencyCode": "GBP"},
            "PurchaseDate": "2025-01-30T10:00:00Z"
          },
          "expected_result": {
            "orderId": "123-1234567-1234567",
            "status": "Shipped",
            "total": "89.99",
            "currency": "GBP"
          }
        }
      ]
    }
  ]
}
```

### 7.2 Filter Chains JSON
```json
{
  "metadata": {
    "version": "1.0.0",
    "description": "Predefined filter chains for complex data reduction",
    "category": "chains"
  },
  "chains": [
    {
      "id": "high_value_summary_chain",
      "name": "High-Value Order Summary",
      "description": "Filter high-value orders and return summary data - 98% reduction",
      "filter_type": "chain",
      "estimated_reduction_percent": 98,
      "steps": [
        {"order": 1, "filter_id": "high_value_orders"},
        {"order": 2, "filter_id": "order_summary"}
      ],
      "compatible_endpoints": ["get_orders"],
      "examples": [
        {
          "name": "Orders over £100 summary",
          "description": "Find expensive orders and show only key details",
          "parameters": {"threshold": 100.0}
        }
      ]
    }
  ]
}
```

## 8. Performance Benefits

### 8.1 Expected Data Reduction
| Filter Type | Use Case | Original Size | Reduced Size | Reduction % |
|-------------|----------|---------------|--------------|-------------|
| Order Summary | Essential order data | ~2KB | ~100 bytes | 95% |
| Order Essentials | Key order info | ~2KB | ~300 bytes | 85% |
| Inventory Summary | Basic stock info | ~1KB | ~80 bytes | 92% |
| Count Only | Just count items | ~100KB | ~20 bytes | 99.98% |
| High-Value Chain | Filtered + reduced | ~100KB | ~500 bytes | 99.5% |

### 8.2 Network and Processing Benefits
- **Faster API responses**: 90%+ smaller payloads
- **Reduced bandwidth**: Significant cost savings
- **Faster LLM processing**: Less data to analyze
- **Improved user experience**: Quicker response times
- **Lower storage costs**: Smaller cached responses

## 9. Implementation Timeline

### Enhanced Timeline (15-20 days):
- **Phase 1** (Database Infrastructure): 3-4 days
- **Phase 2** (Enhanced Seed Data): 3-4 days (includes field filters)
- **Phase 3** (Filter Manager + Chaining): 3-4 days
- **Phase 4** (MCP Integration): 2-3 days
- **Phase 5** (Documentation and Testing): 3-4 days

## 10. Usage Examples

### 10.1 Simple Field Reduction
```python
# Get orders with summary data only
result = get_orders(
    auth_token="...",
    filter_id="order_summary"
)
# Returns 95% smaller response
```

### 10.2 Filter Chaining
```python
# Get high-value orders with summary data
result = get_orders(
    auth_token="...",
    filter_chain="high_value_orders,order_summary",
    filter_params='{"threshold": 100.0}'
)
# Returns 98% smaller response
```

### 10.3 Complex Chain
```python
# Low stock inventory with minimal data
result = get_inventory_in_stock(
    auth_token="...",
    filter_chain="low_stock_alert,inventory_summary",
    filter_params='{"threshold": 10}'
)
# Returns 95% smaller response
```

This enhanced plan provides powerful data reduction capabilities while maintaining all filtering functionality, resulting in dramatically smaller API responses and improved performance.
