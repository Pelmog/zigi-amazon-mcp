#!/usr/bin/env python3
"""Debug filtering system to identify the disconnect."""

import sys

# Add src to path
sys.path.insert(0, "src")

from zigi_amazon_mcp.filtering import FilterManager


def simulate_server_environment():
    """Simulate the exact server environment."""

    # Initialize filter manager like the server does
    filter_manager = FilterManager()
    print("✅ FilterManager initialized")

    # Test data similar to what comes from Amazon API
    test_orders = [
        {
            "AmazonOrderId": "123-4567890-1234567",
            "OrderStatus": "Shipped",
            "OrderTotal": {"Amount": 150.75, "CurrencyCode": "GBP"},
            "PurchaseDate": "2025-01-29T10:30:00Z",
            "BuyerInfo": {"BuyerEmail": "test@example.com"},
            "MarketplaceId": "A1F83G8C2ARO7P",
            "FulfillmentChannel": "AFN",
        },
        {
            "AmazonOrderId": "123-4567890-7654321",
            "OrderStatus": "Pending",
            "OrderTotal": {"Amount": 35.99, "CurrencyCode": "GBP"},
            "PurchaseDate": "2025-01-30T14:15:00Z",
            "BuyerInfo": {"BuyerEmail": "test2@example.com"},
            "MarketplaceId": "A1F83G8C2ARO7P",
            "FulfillmentChannel": "MFN",
        },
    ]

    print(f"📊 Test data: {len(test_orders)} orders")

    # Test scenarios that should work but reportedly fail
    test_cases = [
        {"name": "Single filter ID", "filter_id": "high_value_orders", "filter_params": '{"threshold": 100.0}'},
        {"name": "Order summary filter", "filter_id": "order_summary", "filter_params": "{}"},
        {
            "name": "Filter chain",
            "filter_chain": "high_value_orders,order_summary",
            "filter_params": '{"threshold": 100.0}',
        },
        {
            "name": "Custom filter (should work)",
            "custom_filter": "filter(.OrderTotal.Amount > 100)",
            "filter_params": "{}",
        },
    ]

    for test_case in test_cases:
        print(f"\n🧪 Testing: {test_case['name']}")

        try:
            # Replicate exact server call pattern
            result = filter_manager.apply_enhanced_filtering(
                data=test_orders,
                filter_id=test_case.get("filter_id", ""),
                filter_chain=test_case.get("filter_chain", ""),
                custom_filter=test_case.get("custom_filter", ""),
                filter_params=test_case.get("filter_params", "{}"),
                reduce_response=False,
                endpoint="get_orders",
            )

            if result["success"]:
                print(f"  ✅ SUCCESS: {result['metadata']['reduction_percent']:.1f}% reduction")
                print(f"     Filters applied: {result['metadata']['filters_applied']}")
                print(f"     Execution time: {result['metadata']['execution_time_ms']:.2f}ms")
            else:
                print(f"  ❌ FAILED: {result.get('error', 'Unknown error')}")
                print(f"     Message: {result.get('message', 'No message')}")

        except Exception as e:
            print(f"  💥 EXCEPTION: {e}")
            import traceback

            traceback.print_exc()

    # Test filter discovery
    print("\n🔍 Testing filter discovery...")
    try:
        filters = filter_manager.get_available_filters(endpoint="get_orders", filter_type="field")
        print(f"  ✅ Found {filters['total_filters']} filters")

        if filters["total_filters"] > 0:
            sample_filter = filters["filters"]["field"][0] if filters["filters"]["field"] else None
            if sample_filter:
                print(f"  📋 Sample filter: {sample_filter['id']} - {sample_filter['name']}")

                # Test this specific filter
                print(f"  🧪 Testing sample filter: {sample_filter['id']}")
                result = filter_manager.apply_enhanced_filtering(
                    data=test_orders, filter_id=sample_filter["id"], filter_params="{}", endpoint="get_orders"
                )

                if result["success"]:
                    print(f"     ✅ Sample filter SUCCESS: {result['metadata']['reduction_percent']:.1f}% reduction")
                else:
                    print(f"     ❌ Sample filter FAILED: {result.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"  💥 Filter discovery EXCEPTION: {e}")

    # Database health check
    print("\n🏥 Database health check...")
    try:
        health = filter_manager.filter_library.get_database_stats()
        print(f"  📊 Status: {health['status']}")
        print(f"  📁 Database: {health['database_path']}")
        print(f"  📏 Size: {health['database_size_bytes']} bytes")
        print(f"  📦 Total filters: {health['total_filters']}")
        print(f"  ⛓️  Chain filters: {health['chain_filters']}")

    except Exception as e:
        print(f"  💥 Health check EXCEPTION: {e}")


if __name__ == "__main__":
    simulate_server_environment()
