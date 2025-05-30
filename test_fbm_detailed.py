#!/usr/bin/env python3
"""Detailed test of FBM functionality with enhanced output."""

import json
import os
import sys
from datetime import datetime, timedelta

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from zigi_amazon_mcp.server import (
    get_fbm_inventory,
    get_auth_token,
)

# Your seller information
SELLER_ID = "A2C259Q0GU1WMI"
TEST_SKU = "JL-BC002"
TEST_ASIN = "B0CY5RJ3CL"


def main():
    """Run detailed FBM test."""
    print("Detailed FBM Inventory Test")
    print("=" * 60)
    
    # Get auth token
    auth_result = get_auth_token()
    if "Your auth token is:" not in auth_result:
        print("Failed to get auth token")
        return
        
    auth_token = auth_result.split("Your auth token is: ")[1].strip()
    print(f"✓ Auth token obtained: {auth_token[:20]}...")
    
    # Test with more detailed output
    print(f"\nTesting FBM endpoint for SKU: {TEST_SKU}")
    print("-" * 60)
    
    try:
        # Get the raw result
        result = get_fbm_inventory(
            auth_token=auth_token,
            seller_id=SELLER_ID,
            seller_sku=TEST_SKU,
            marketplace_ids="A1F83G8C2ARO7P",
            include_inactive=True
        )
        
        # Pretty print the entire response
        result_data = json.loads(result)
        print("\nFull Response:")
        print(json.dumps(result_data, indent=2))
        
        # If successful, break down the data
        if result_data.get('success'):
            data = result_data.get('data', {})
            
            print("\n" + "=" * 60)
            print("Parsed Information:")
            print("=" * 60)
            
            print(f"\nProduct Identification:")
            print(f"  SKU: {data.get('sku', 'N/A')}")
            print(f"  ASIN: {data.get('asin', 'N/A')}")
            print(f"  Product Name: {data.get('product_name', 'N/A')}")
            print(f"  Condition: {data.get('condition', 'N/A')}")
            print(f"  Listing Status: {data.get('listing_status', 'N/A')}")
            
            print(f"\nDates:")
            print(f"  Created: {data.get('created_date', 'N/A')}")
            print(f"  Last Updated: {data.get('last_updated', 'N/A')}")
            
            fulfillment = data.get('fulfillment_availability', {})
            print(f"\nFulfillment Information:")
            print(f"  Channel Code: {fulfillment.get('fulfillment_channel_code', 'N/A')}")
            print(f"  Quantity Available: {fulfillment.get('quantity', 0)}")
            print(f"  Is Available: {fulfillment.get('is_available', False)}")
            print(f"  Handling Time: {fulfillment.get('handling_time', 'N/A')} days")
            print(f"  Restock Date: {fulfillment.get('restock_date', 'N/A')}")
            
            price = data.get('price', {})
            if price:
                print(f"\nPricing:")
                print(f"  Amount: {price.get('amount', 'N/A')}")
                print(f"  Currency: {price.get('currency', 'N/A')}")
            
            issues = data.get('issues', [])
            if issues:
                print(f"\nIssues/Warnings:")
                for issue in issues:
                    print(f"  - Code: {issue.get('code')}")
                    print(f"    Message: {issue.get('message')}")
                    print(f"    Severity: {issue.get('severity')}")
            
            print("\n" + "=" * 60)
            print("Analysis:")
            print("=" * 60)
            
            # Analysis
            if fulfillment.get('fulfillment_channel_code') == 'DEFAULT':
                print("✓ This is an FBM (Fulfilled by Merchant) listing")
            else:
                print(f"  Fulfillment channel: {fulfillment.get('fulfillment_channel_code')}")
            
            if fulfillment.get('quantity', 0) > 0:
                print(f"✓ Product is in stock with {fulfillment.get('quantity')} units")
            else:
                print("  Product appears to be out of stock")
            
            if not fulfillment.get('is_available'):
                print("⚠️  Product is marked as not available despite having quantity")
                print("  This might indicate the listing is inactive or has other issues")
            
            if data.get('asin') != TEST_ASIN:
                print(f"⚠️  ASIN mismatch: Expected {TEST_ASIN}, got {data.get('asin', 'None')}")
                print("  The listing might be missing ASIN information")
                
        else:
            print(f"\n✗ Error: {result_data.get('error')} - {result_data.get('message')}")
            
    except Exception as e:
        print(f"\n✗ Exception occurred: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()