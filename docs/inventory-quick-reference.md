# Amazon SP-API Inventory Management Quick Reference

## Essential Inventory Operations

### 1. Check Total Inventory Levels
```python
# Get overall inventory summary for all products
inventory = get_inventory_summaries(
    auth_token=token,
    marketplace_ids="A1F83G8C2ARO7P",
    granularity_type="Marketplace"
)
```

### 2. Check Specific Product Inventory
```python
# By ASIN
inventory = get_inventory_summaries(
    auth_token=token,
    granularity_type="ASIN",
    granularity_id="B001234567"
)

# By SKU
inventory = get_inventory_summaries(
    auth_token=token,
    seller_skus="MY-SKU-123,MY-SKU-456"
)
```

### 3. Update Inventory Quantity (MFN)
```python
# For Merchant Fulfilled items
result = update_listings_item(
    auth_token=token,
    seller_sku="MY-SKU-123",
    marketplace_ids="A1F83G8C2ARO7P",
    product_type="PRODUCT",
    patches=json.dumps([{
        "op": "replace",
        "path": "/attributes/fulfillment_availability",
        "value": [{
            "fulfillment_channel_code": "MFN",
            "quantity": 150
        }]
    }])
)
```

### 4. Bulk Inventory Update
```python
# Create CSV content
csv_content = """sku,quantity
MY-SKU-001,100
MY-SKU-002,50
MY-SKU-003,0
"""

# Submit feed
feed_result = create_inventory_feed(
    auth_token=token,
    feed_type="POST_FLAT_FILE_INVLOADER_DATA",
    content=csv_content
)

# Check feed status
status = get_feed_status(
    auth_token=token,
    feed_id=feed_result["feed_id"]
)
```

### 5. Download Inventory Report
```python
# Request FBA inventory report
report = request_inventory_report(
    auth_token=token,
    report_type="GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA"
)

# Download when ready
report_data = get_report(
    auth_token=token,
    report_id=report["report_id"]
)
```

## Key Inventory Metrics

### FBA Inventory Components
- **Fulfillable Quantity**: Available for immediate shipment
- **Unfulfillable Quantity**: Damaged, expired, or customer returns
- **Reserved Quantity**: Allocated to pending orders
- **Inbound Quantity**: In transit to Amazon warehouses
  - Working: Being prepared
  - Shipped: In transit
  - Receiving: At warehouse, being processed

### Inventory Health Indicators
- **Stranded Inventory**: Has listing issues
- **Excess Inventory**: Over 90 days of supply
- **Aged Inventory**: In warehouse > 365 days
- **IPI Score**: Inventory Performance Index (400+ is good)

## Common Inventory Scenarios

### Scenario 1: Low Stock Alert
```python
def check_low_stock(auth_token, threshold=10):
    inventory = get_inventory_summaries(auth_token=auth_token)
    low_stock_items = []
    
    for item in inventory["inventory"]:
        if item["fulfillableQuantity"] < threshold:
            low_stock_items.append({
                "sku": item["sellerSku"],
                "asin": item["asin"],
                "quantity": item["fulfillableQuantity"],
                "product": item["productName"]
            })
    
    return low_stock_items
```

### Scenario 2: Restock Planning
```python
def calculate_restock_quantity(auth_token, sku, days_of_supply=30):
    # Get current inventory
    current = get_inventory_summaries(
        auth_token=auth_token,
        seller_skus=sku
    )
    
    # Get sales velocity (would need order history)
    orders = get_orders(
        auth_token=auth_token,
        created_after=(datetime.now() - timedelta(days=30)).isoformat()
    )
    
    # Calculate daily velocity and restock amount
    # ... calculation logic ...
```

### Scenario 3: Multi-Marketplace Inventory Sync
```python
def sync_inventory_across_marketplaces(auth_token, sku, quantity):
    marketplaces = {
        "UK": "A1F83G8C2ARO7P",
        "DE": "A1PA6795UKMFR9",
        "FR": "A13V1IB3VIYZZH"
    }
    
    results = {}
    for country, marketplace_id in marketplaces.items():
        result = update_listings_item(
            auth_token=auth_token,
            seller_sku=sku,
            marketplace_ids=marketplace_id,
            quantity=quantity
        )
        results[country] = result
    
    return results
```

## Feed Templates

### Inventory Loader Feed (CSV)
```csv
sku,quantity,fulfillment-channel
MY-SKU-001,100,DEFAULT
MY-SKU-002,50,DEFAULT
MY-SKU-003,0,DEFAULT
```

### Price & Quantity Feed (Tab-delimited)
```
sku	price	quantity
MY-SKU-001	19.99	100
MY-SKU-002	24.99	50
MY-SKU-003	29.99	0
```

## Error Handling

### Common Errors and Solutions

1. **Rate Limit (429)**
   - Solution: Implement exponential backoff
   - Check x-amzn-RateLimit-Limit header

2. **Invalid SKU**
   - Solution: Verify SKU exists in catalog
   - Use get_listings_item() to check

3. **Feed Processing Error**
   - Solution: Check feed processing report
   - Validate data format before submission

4. **Insufficient Permissions**
   - Solution: Verify app has inventory management scope
   - Check IAM role permissions

## Performance Tips

1. **Batch Operations**: Use feeds for bulk updates (>10 items)
2. **Cache Results**: Cache inventory data for 5-15 minutes
3. **Paginate Large Results**: Use next_token for large datasets
4. **Async Processing**: Process feed results asynchronously
5. **Regional Endpoints**: Use closest endpoint for better latency

## Monitoring Checklist

- [ ] Set up low stock alerts
- [ ] Monitor stranded inventory daily
- [ ] Check IPI score weekly
- [ ] Review aged inventory monthly
- [ ] Track inbound shipment status
- [ ] Monitor unfulfillable quantity trends
- [ ] Verify feed processing success rates