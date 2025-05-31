<!-- @format -->

```markdown
# Retrieving Amazon Order Items Using the Selling Partner API (SP-API)

This guide details how to retrieve the items (products) contained within an Amazon order using the SP-API, including endpoint URLs, usage, rate limits, and practical considerations.

---

## Overview

- The **getOrders** endpoint retrieves order metadata (order IDs, buyer info, status), but _does not_ return the items in the order.
- To retrieve the products in an order, you must use **getOrderItems** for each order ID.
- There is no single endpoint that returns both order and item details in one call; you must combine results programmatically[^5].

---

## Key Endpoints

| Endpoint               | Purpose                         | Returns Order Items? | Documentation URL                                                                              |
| ---------------------- | ------------------------------- | -------------------- | ---------------------------------------------------------------------------------------------- |
| getOrders              | List orders (metadata only)     | No                   | `https://developer-docs.amazon.com/sp-api/docs/orders-api-v0-reference#getorders`              |
| getOrder               | Get details for a single order  | No                   | `https://developer-docs.amazon.com/sp-api/docs/orders-api-v0-reference#getorder`               |
| getOrderItems          | List items for a specific order | Yes                  | `https://developer-docs.amazon.com/sp-api/docs/orders-api-v0-reference#getorderitems`          |
| getOrderItemsBuyerInfo | Get buyer info for order items  | No (only buyer info) | `https://developer-docs.amazon.com/sp-api/docs/orders-api-v0-reference#getorderitemsbuyerinfo` |

---

## Workflow Example

1. **List Orders**

   - Use `GET /orders/v0/orders` to obtain a list of order IDs.
   - [API Docs](https://developer-docs.amazon.com/sp-api/docs/orders-api-v0-reference#getorders)

2. **Retrieve Order Items**
   - For each `AmazonOrderId`, use `GET /orders/v0/orders/{orderId}/orderItems` to get the products in the order.
   - [API Docs](https://developer-docs.amazon.com/sp-api/docs/orders-api-v0-reference#getorderitems)

---

## Example: Python Usage

Using the [python-amazon-sp-api](https://python-amazon-sp-api.readthedocs.io/en/v1.0.4/endpoints/orders.html) library:
```

from sp_api.api import Orders

# Step 1: Get orders

orders_response = Orders().get_orders(MarketplaceIds=["ATVPDKIKX0DER"], CreatedAfter='2024-01-01T00:00:00Z')
for order in orders_response.payload['Orders']:
order_id = order['AmazonOrderId']

    # Step 2: Get order items for each order
    items_response = Orders().get_order_items(order_id)
    for item in items_response.payload['OrderItems']:
        print(f"Order {order_id} contains ASIN {item['ASIN']} (SKU: {item['SellerSKU']}) x {item['QuantityOrdered']}")
    ```

[^1][^4]

---

## getOrderItems Response Example

```

{
"payload": {
"AmazonOrderId": "903-1671087-0812628",
"OrderItems": [
{
"ASIN": "BT0093TELA",
"OrderItemId": "68828574383266",
"SellerSKU": "CBA_OTF_1",
"Title": "Example item name",
"QuantityOrdered": 1,
"QuantityShipped": 1,
"ItemPrice": {
"CurrencyCode": "JPY",
"Amount": "25.99"
},
"ShippingPrice": {
"CurrencyCode": "JPY",
"Amount": "1.26"
}
// ... more fields
}
// ... more items
]
}
}

```

[^2]

---

## Rate Limits

| Endpoint      | Rate (requests/sec) | Burst |
| ------------- | ------------------- | ----- |
| getOrders     | 0.0167              | 20    |
| getOrderItems | 0.5                 | 30    |

[^2]

> **Note:** If you need to retrieve items for many orders, you must respect these rate limits to avoid throttling. Implement waiting/backoff logic as needed[^5].

---

## Important Notes

- **Shipping Address:** The shipping address is _not_ returned by `getOrderItems`. Retrieve it using `getOrders` or `getOrder` with appropriate permissions[^3].
- **Pending Orders:** For orders in the "Pending" state (payment not authorized), `getOrderItems` will not return pricing, taxes, or shipping charges. These details become available once the order status is Unshipped, Partially Shipped, or Shipped[^1][^2][^4].
- **Order Item IDs:** There may be inconsistencies in `OrderItemId` values across different endpoints; use SKU or ASIN as a fallback for matching[^6].

---

## References

- [Orders API Reference (Official)](https://developer-docs.amazon.com/sp-api/docs/orders-api-v0-reference)
- [python-amazon-sp-api Documentation](https://python-amazon-sp-api.readthedocs.io/en/v1.0.4/endpoints/orders.html)
- [Stack Overflow: Order Items Retrieval](https://stackoverflow.com/questions/70990453/amazon-sp-api-getting-order-items-in-order-list-api)

---

## Summary Table

| API Endpoint  | Returns Order Items? | Notes                                           |
| ------------- | -------------------- | ----------------------------------------------- |
| getOrders     | No                   | Only general order info, not item-level details |
| getOrder      | No                   | Single order metadata, not item-level details   |
| getOrderItems | Yes                  | Returns all products/items in a specific order  |

---

## FAQ

**Q: Can I get all orders and their items in one call?**
A: No. You must first get orders, then call `getOrderItems` for each order[^5].

**Q: How do I get the shipping address?**
A: Use `getOrders` or `getOrder` with the appropriate data elements and PII access[^3].

**Q: What if I hit rate limits?**
A: Implement delay/backoff logic between calls and monitor the `x-amzn-RateLimit-Limit` response header[^2][^5].

```

<div style="text-align: center">⁂</div>

[^1]: https://python-amazon-sp-api.readthedocs.io/en/v0.9.2/endpoints/orders/

[^2]: https://cleo-infoeng.s3.us-east-2.amazonaws.com/cic-userguide/AWS-SP-API+Connector/API-References/ordersV0.html

[^3]: https://github.com/jlevers/selling-partner-api/issues/582

[^4]: https://python-amazon-sp-api.readthedocs.io/en/v1.0.4/endpoints/orders.html

[^5]: https://stackoverflow.com/questions/70990453/amazon-sp-api-getting-order-items-in-order-list-api

[^6]: https://github.com/amzn/selling-partner-api-docs/issues/2848

[^7]: https://developer-docs.amazon.com/sp-api/docs/orders-api-v0-reference

[^8]: https://developer-docs.amazon.com/sp-api/reference/getorderitems

[^9]: https://developer-docs.amazon.com/sp-api/docs/orders-api-v0-use-case-guide

[^10]: https://developer-docs.amazon.com/sp-api/docs/orders-api-rate-limits

```
