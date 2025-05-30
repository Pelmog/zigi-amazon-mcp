<!-- @format -->

# JSON Query Filtering Instructions

## Overview

This document provides comprehensive instructions for using JSON Query to filter and process data, particularly useful for Amazon e-commerce operations, inventory management, and order processing.

## Getting Started

JSON Query is a small, flexible, and expandable query language that supports both human-friendly text format and JSON format for programmatic use.

### Basic Usage

```python
from jsonquerylang import jsonquery

# Basic filtering example
data = [
    {"name": "Product A", "price": 25.99, "stock": 100, "category": "Electronics"},
    {"name": "Product B", "price": 15.50, "stock": 0, "category": "Books"},
    {"name": "Product C", "price": 45.00, "stock": 25, "category": "Electronics"}
]

# Filter products in stock
in_stock = jsonquery(data, 'filter(.stock > 0)')
```

## Core Filtering Functions

### 1. Basic Filter Operations

#### Filter by Condition

```python
# Text format
query = 'filter(.price > 20)'

# JSON format equivalent
query = ["filter", ["gt", ["get", "price"], 20]]
```

#### Multiple Conditions

```python
# Products that are in stock AND expensive
query = 'filter((.stock > 0) and (.price > 30))'

# Products that are either Electronics OR Books
query = 'filter((.category == "Electronics") or (.category == "Books"))'
```

### 2. Comparison Operators

| Operator | Text Format                                | Description           |
| -------- | ------------------------------------------ | --------------------- |
| `==`     | `.price == 25`                             | Equal to              |
| `!=`     | `.price != 25`                             | Not equal to          |
| `>`      | `.price > 25`                              | Greater than          |
| `>=`     | `.price >= 25`                             | Greater than or equal |
| `<`      | `.price < 25`                              | Less than             |
| `<=`     | `.price <= 25`                             | Less than or equal    |
| `in`     | `.category in ["Electronics", "Books"]`    | Value in list         |
| `not in` | `.status not in ["cancelled", "refunded"]` | Value not in list     |

### 3. Complex Filtering Examples

#### Amazon Orders Filtering

```python
orders = [
    {"orderId": "123", "status": "Shipped", "total": 99.99, "date": "2025-01-15"},
    {"orderId": "124", "status": "Pending", "total": 45.50, "date": "2025-01-16"},
    {"orderId": "125", "status": "Delivered", "total": 120.00, "date": "2025-01-14"}
]

# Filter high-value shipped orders
query = '''
filter((.status == "Shipped") and (.total > 50))
| sort(.total, "desc")
'''

# Filter recent orders (using regex for date matching)
query = 'filter(regex(.date, "2025-01-1[5-6]"))'
```

#### Inventory Management

```python
inventory = [
    {"sku": "ELEC001", "quantity": 150, "reorderLevel": 50, "supplier": "TechCorp"},
    {"sku": "BOOK001", "quantity": 25, "reorderLevel": 100, "supplier": "BookDist"},
    {"sku": "ELEC002", "quantity": 5, "reorderLevel": 20, "supplier": "TechCorp"}
]

# Find items that need reordering
reorder_needed = jsonquery(inventory, '''
filter(.quantity <= .reorderLevel)
| sort(.quantity)
| pick(.sku, .quantity, .reorderLevel)
''')

# Group by supplier for bulk ordering
by_supplier = jsonquery(inventory, '''
filter(.quantity <= .reorderLevel)
| groupBy(.supplier)
''')
```

## Advanced Filtering Techniques

### 1. Chaining Operations (Pipes)

```python
# Complex multi-step filtering
query = '''
.products
| filter(.category == "Electronics")
| filter(.stock > 0)
| sort(.price)
| limit(10)
| pick(.name, .price, .stock)
'''
```

### 2. Creating Summary Objects

```python
# Sales analysis
sales_data = [
    {"product": "Widget A", "sales": 100, "revenue": 2500, "month": "Jan"},
    {"product": "Widget B", "sales": 75, "revenue": 1800, "month": "Jan"},
    {"product": "Widget A", "sales": 120, "revenue": 3000, "month": "Feb"}
]

summary = jsonquery(sales_data, '''
{
  totalSales: sum(.sales) | sum(),
  totalRevenue: sum(.revenue) | sum(),
  avgSalesPerProduct: map(.sales) | average(),
  topProducts: sort(.revenue, "desc") | limit(3) | map(.product)
}
''')
```

### 3. Exists and Conditional Filtering

```python
# Check for missing data
query = 'filter(not exists(.description))'

# Conditional logic
query = '''
map({
  name: .name,
  status: if(.stock > 100, "High Stock",
            if(.stock > 0, "Low Stock", "Out of Stock")),
  reorderSoon: .stock <= .reorderLevel
})
'''
```

## String and Date Filtering

### 1. Text Pattern Matching

```python
# Using regex for pattern matching
products = [
    {"name": "iPhone 15 Pro", "model": "A2848"},
    {"name": "Samsung Galaxy S24", "model": "SM-S921"},
    {"name": "Google Pixel 8", "model": "G9BQD"}
]

# Find all iPhone products
iphones = jsonquery(products, 'filter(regex(.name, "iPhone", "i"))')

# Find products with specific model patterns
samsung_models = jsonquery(products, 'filter(regex(.model, "^SM-"))')
```

### 2. Date and Time Filtering

```python
# Date-based filtering (assuming ISO date strings)
orders = [
    {"id": "1", "date": "2025-01-15T10:30:00Z", "amount": 99.99},
    {"id": "2", "date": "2025-01-20T14:15:00Z", "amount": 45.50}
]

# Extract date part and filter
recent_orders = jsonquery(orders, '''
filter(substring(.date, 0, 10) >= "2025-01-18")
''')
```

## Performance Optimization Tips

### 1. Efficient Filtering Order

```python
# Good: Filter early, sort later
query = '''
filter(.category == "Electronics")
| filter(.stock > 0)
| sort(.price, "desc")
| limit(20)
'''

# Less efficient: Sort everything first
query = '''
sort(.price, "desc")
| filter(.category == "Electronics")
| filter(.stock > 0)
| limit(20)
'''
```

### 2. Using Pick for Large Datasets

```python
# Only select needed fields early
query = '''
pick(.id, .name, .price, .stock)
| filter(.stock > 0)
| sort(.price)
'''
```

## Common Use Cases for Amazon Operations

### 1. Order Processing

```python
# Filter orders needing attention
orders_to_process = jsonquery(orders, '''
filter(.status in ["Pending", "Processing"])
| filter(.total > 100)
| sort(.date)
''')
```

### 2. Inventory Alerts

```python
# Low Stock Alert
low_stock = jsonquery(inventory, '''
filter(.quantity < .minQuantity)
| map({
  sku: .sku,
  current: .quantity,
  minimum: .minQuantity,
  shortage: (.minQuantity - .quantity)
})
| sort(.shortage, "desc")
''')
```

### 3. Customer Analysis

```python
# High-value customers
vip_customers = jsonquery(customers, '''
filter(.totalOrders > 10)
| filter(.totalSpent > 1000)
| sort(.totalSpent, "desc")
| pick(.customerId, .name, .totalSpent, .totalOrders)
''')
```

## Error Handling and Debugging

### 1. Common Gotchas

- **Array vs Object Operations**: Remember to use `map()` when applying operations to each item in an array
- **Property Access**: Use quotes for properties with spaces: `."first name"`
- **Type Coercion**: JSON Query does strict comparison (`"2" != 2`)

### 2. Debugging Tips

```python
# Step-by-step debugging
data = [{"name": "Test", "value": 10}]

# Test each step
step1 = jsonquery(data, 'filter(.value > 5)')  # Should return the item
step2 = jsonquery(step1, 'map(.name)')         # Should return ["Test"]
```

## Custom Functions and Extensions

You can extend JSON Query with custom functions:

```python
from jsonquerylang import jsonquery, JsonQueryOptions

def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

def fn_is_prime(value):
    return lambda data: is_prime(value)

options = {"functions": {"isPrime": fn_is_prime}}
result = jsonquery([1, 2, 3, 4, 5], 'filter(isPrime(get()))', options)
# Returns [2, 3, 5]
```

## Best Practices

1. **Start Simple**: Begin with basic filters and gradually add complexity
2. **Use Pipes**: Chain operations for readability and maintainability
3. **Filter Early**: Apply most restrictive filters first to reduce data size
4. **Pick Wisely**: Select only needed fields to improve performance
5. **Test Incrementally**: Test each step of complex queries separately
6. **Document Complex Queries**: Add comments explaining business logic

## Integration with Amazon MCP Server

When using with the Amazon MCP server, filtering is particularly useful for:

- Processing large order datasets
- Filtering inventory by various criteria
- Analyzing sales performance
- Managing product catalogs
- Customer segmentation
- Financial reporting

Example integration:

```python
# After fetching orders from Amazon API
orders_json = get_orders(auth_token, ...)
orders_data = json.loads(orders_json)

# Filter and analyze
high_value_orders = jsonquery(orders_data['orders'], '''
filter(.OrderTotal.Amount > 100)
| sort(.PurchaseDate, "desc")
| limit(50)
''')
```

This filtering system provides powerful capabilities for data processing and analysis in e-commerce operations.
