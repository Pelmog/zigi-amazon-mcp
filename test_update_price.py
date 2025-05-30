#!/usr/bin/env python3
"""Test script to update the price of JL-BC002 from £69.99 to £69.98."""

import json
import os
import sys
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from zigi_amazon_mcp.api.listings import ListingsAPIClient
from zigi_amazon_mcp.server import (
    get_amazon_access_token,
    get_amazon_aws_credentials,
    get_auth_token,
    get_fbm_inventory,
    validate_auth_token,
)

# Your seller information
SELLER_ID = "A2C259Q0GU1WMI"
TEST_SKU = "JL-BC002"
TEST_ASIN = "B0CY5RJ3CL"
CURRENT_PRICE = "69.99"
NEW_PRICE = "69.98"


def get_current_listing_details(auth_token: str):
    """Get current listing details to verify price."""
    print("\n1. Getting current listing details...")
    print("-" * 60)
    
    result = get_fbm_inventory(
        auth_token=auth_token,
        seller_id=SELLER_ID,
        seller_sku=TEST_SKU,
        marketplace_ids="A1F83G8C2ARO7P"
    )
    
    result_data = json.loads(result)
    if result_data.get('success'):
        data = result_data.get('data', {})
        current_price = data.get('price', {}).get('amount', 'N/A')
        print(f"✓ Current listing found")
        print(f"  SKU: {TEST_SKU}")
        print(f"  ASIN: {data.get('asin')}")
        print(f"  Product: {data.get('product_name', 'N/A')[:50]}...")
        print(f"  Current Price: £{current_price}")
        print(f"  Quantity: {data.get('fulfillment_availability', {}).get('quantity', 0)}")
        return current_price == CURRENT_PRICE
    else:
        print(f"✗ Error: {result_data.get('error')} - {result_data.get('message')}")
        return False


def update_price_direct_api(access_token: str, aws_creds: dict):
    """Update price using direct API call with proper patch structure."""
    print("\n2. Preparing price update...")
    print("-" * 60)
    
    # Create API client
    client = ListingsAPIClient(
        access_token,
        aws_creds,
        region="eu-west-1",
        endpoint="https://sellingpartnerapi-eu.amazon.com"
    )
    
    # Prepare patch operations for price update
    # According to SP-API docs, price updates use a specific path structure
    patches = [
        {
            "op": "replace",
            "path": "/attributes/purchasable_offer",
            "value": [
                {
                    "audience": "ALL",
                    "our_price": [
                        {
                            "schedule": [
                                {
                                    "value_with_tax": NEW_PRICE
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ]
    
    print(f"  Patch operation prepared:")
    print(f"  - Operation: replace")
    print(f"  - Path: /attributes/purchasable_offer")
    print(f"  - New Price: £{NEW_PRICE}")
    print(f"  - Change: £{CURRENT_PRICE} → £{NEW_PRICE} (1p reduction)")
    
    return client, patches


def main():
    """Main test function."""
    print("Amazon FBM Price Update Test Script")
    print("=" * 60)
    print(f"Target: {TEST_SKU} - Maximuv Folding Wagon")
    print(f"Price Change: £{CURRENT_PRICE} → £{NEW_PRICE}")
    
    # Get auth token
    auth_result = get_auth_token()
    if "Your auth token is:" not in auth_result:
        print("Failed to get auth token")
        return
        
    auth_token = auth_result.split("Your auth token is: ")[1].strip()
    print(f"✓ Auth token obtained")
    
    # Verify current price
    if not get_current_listing_details(auth_token):
        print("\n⚠️  Current price doesn't match expected value or listing not found")
        return
    
    # Get Amazon credentials
    try:
        access_token = get_amazon_access_token()
        aws_creds = get_amazon_aws_credentials()
        print("\n✓ Amazon credentials obtained")
    except Exception as e:
        print(f"\n✗ Failed to get credentials: {e}")
        return
    
    # Prepare the update
    client, patches = update_price_direct_api(access_token, aws_creds)
    
    # Show what would be sent
    print("\n3. API Request Details:")
    print("-" * 60)
    print(f"  Endpoint: PATCH /sellers/v1/{SELLER_ID}/{TEST_SKU}")
    print(f"  Marketplace: A1F83G8C2ARO7P (UK)")
    print(f"  Request Body:")
    print(json.dumps({
        "productType": "PRODUCT",
        "patches": patches
    }, indent=2))
    
    print("\n" + "=" * 60)
    print("READY TO UPDATE PRICE")
    print("=" * 60)
    print(f"\n⚠️  This will change the price of {TEST_SKU} from £{CURRENT_PRICE} to £{NEW_PRICE}")
    print("\nTo execute the price update, uncomment the following code:")
    print("-" * 60)
    print("""
    # UNCOMMENT TO EXECUTE:
    # result = client.patch_listings_item(
    #     seller_id=SELLER_ID,
    #     sku=TEST_SKU,
    #     marketplace_ids="A1F83G8C2ARO7P",
    #     patches=patches,
    # )
    # 
    # result_json = json.dumps(result, indent=2)
    # print("\\nUpdate Result:")
    # print(result_json)
    # 
    # if result.get('success'):
    #     print("\\n✓ Price update submitted successfully!")
    #     print("Note: Price changes may take a few minutes to reflect on Amazon")
    # else:
    #     print(f"\\n✗ Update failed: {result.get('error')} - {result.get('message')}")
    """)
    
    print("\n" + "=" * 60)
    print("Script prepared. Please review and confirm before executing.")


if __name__ == "__main__":
    main()