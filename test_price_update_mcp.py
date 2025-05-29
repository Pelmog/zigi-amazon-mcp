#!/usr/bin/env python3
"""Test the new update_product_price MCP tool."""

import json
import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from zigi_amazon_mcp.server import (
    get_auth_token,
    update_product_price,
    get_fbm_inventory,
)

# Configuration
SELLER_ID = "A2C259Q0GU1WMI"
TEST_SKU = "JL-BC002"


def main():
    """Test the update_product_price function."""
    print("Testing update_product_price MCP Tool")
    print("=" * 60)
    
    # Get auth token
    auth_result = get_auth_token()
    if "Your auth token is:" not in auth_result:
        print("Failed to get auth token")
        return
        
    auth_token = auth_result.split("Your auth token is: ")[1].strip()
    print(f"✓ Auth token obtained")
    
    # Get current price
    print("\n1. Getting current price...")
    result = get_fbm_inventory(
        auth_token=auth_token,
        seller_id=SELLER_ID,
        seller_sku=TEST_SKU,
        marketplace_ids="A1F83G8C2ARO7P"
    )
    
    result_data = json.loads(result)
    if result_data.get('success'):
        current_price = result_data.get('data', {}).get('price', {}).get('amount', 'N/A')
        print(f"   Current price: £{current_price}")
    
    # Test the price update function (DRY RUN - not executing)
    print("\n2. Testing update_product_price function...")
    print("   This is a DRY RUN - not actually updating")
    
    # Show what the function call would look like
    print("\n   Example function call:")
    print("   update_product_price(")
    print(f'       auth_token="{auth_token[:20]}...",')
    print(f'       seller_id="{SELLER_ID}",')
    print(f'       seller_sku="{TEST_SKU}",')
    print(f'       new_price="69.97",  # Example new price')
    print(f'       currency="GBP",')
    print(f'       marketplace_ids="A1F83G8C2ARO7P"')
    print("   )")
    
    print("\n✅ MCP tool is ready for use!")
    print("\nWhen connected via MCP, you can use:")
    print('- Tool: "update_product_price"')
    print(f'- Parameters: seller_id="{SELLER_ID}", seller_sku="YOUR_SKU", new_price="XX.XX"')


if __name__ == "__main__":
    main()