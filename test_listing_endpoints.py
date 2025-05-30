#!/usr/bin/env python3
"""Test script for the new get_listing and update_listing MCP endpoints."""

import json
import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from zigi_amazon_mcp.server import (
    get_auth_token,
    get_listing,
    update_listing,
)

# Configuration
SELLER_ID = os.getenv("SELLER_ID", "A2C259Q0GU1WMI")
TEST_SKU = "JL-BC002"


def test_get_listing():
    """Test the get_listing endpoint."""
    print("\n" + "="*60)
    print("Testing get_listing MCP Endpoint")
    print("="*60)
    
    # Get auth token
    auth_result = get_auth_token()
    if "Your auth token is:" not in auth_result:
        print("Failed to get auth token")
        return False
        
    auth_token = auth_result.split("Your auth token is: ")[1].strip()
    print("✓ Auth token obtained")
    
    # Test 1: Get basic listing information
    print("\n1. Getting basic listing information...")
    result = get_listing(
        auth_token=auth_token,
        seller_id=SELLER_ID,
        seller_sku=TEST_SKU,
        marketplace_ids="A1F83G8C2ARO7P"
    )
    
    result_data = json.loads(result)
    if result_data.get('success'):
        print(f"   ✓ Successfully retrieved listing for SKU: {TEST_SKU}")
        print("\n   === FULL RESPONSE DATA ===")
        print(json.dumps(result_data, indent=4))
        print("   === END RESPONSE DATA ===\n")
        
        data = result_data.get('data', {})
        print(f"   - Product Name: {data.get('product_name', 'N/A')}")
        print(f"   - ASIN: {data.get('asin', 'N/A')}")
        print(f"   - Condition: {data.get('condition', 'N/A')}")
        print(f"   - Status: {data.get('listing_status', 'N/A')}")
        
        # Check price
        price_info = data.get('price', {})
        if price_info:
            print(f"   - Price: {price_info.get('currency', '')} {price_info.get('amount', 'N/A')}")
        
        # Check fulfillment
        fulfillment = data.get('fulfillment_availability', {})
        if fulfillment:
            print(f"   - Available Quantity: {fulfillment.get('quantity', 0)}")
            print(f"   - Is Available: {fulfillment.get('is_available', False)}")
    else:
        print(f"   ✗ Failed: {result_data.get('message', 'Unknown error')}")
        print("\n   === ERROR RESPONSE ===")
        print(json.dumps(result_data, indent=4))
        print("   === END ERROR RESPONSE ===\n")
        return False
    
    # Test 2: Get listing with specific included data
    print("\n2. Getting listing with all available data...")
    result = get_listing(
        auth_token=auth_token,
        seller_id=SELLER_ID,
        seller_sku=TEST_SKU,
        marketplace_ids="A1F83G8C2ARO7P",
        included_data="attributes,issues,offers,fulfillmentAvailability"
    )
    
    result_data = json.loads(result)
    if result_data.get('success'):
        print(f"   ✓ Successfully retrieved detailed listing data")
        print("\n   === FULL DETAILED RESPONSE DATA ===")
        print(json.dumps(result_data, indent=4))
        print("   === END DETAILED RESPONSE DATA ===\n")
        
        # Check for any issues
        issues = result_data.get('data', {}).get('issues', [])
        if issues:
            print(f"   - Found {len(issues)} issue(s) with the listing")
            for issue in issues[:3]:  # Show first 3 issues
                print(f"     • {issue.get('message', 'N/A')} [{issue.get('severity', 'N/A')}]")
    else:
        print(f"   ✗ Failed: {result_data.get('message', 'Unknown error')}")
        print("\n   === ERROR RESPONSE ===")
        print(json.dumps(result_data, indent=4))
        print("   === END ERROR RESPONSE ===\n")
    
    return True


def test_update_listing():
    """Test the update_listing endpoint."""
    print("\n" + "="*60)
    print("Testing update_listing MCP Endpoint")
    print("="*60)
    
    # Get auth token
    auth_result = get_auth_token()
    if "Your auth token is:" not in auth_result:
        print("Failed to get auth token")
        return False
        
    auth_token = auth_result.split("Your auth token is: ")[1].strip()
    print("✓ Auth token obtained")
    
    # Test 1: DRY RUN - Show what would be sent for title update
    print("\n1. DRY RUN - Title Update")
    print("-" * 40)
    print("Would send the following patch operation:")
    title_patch = {
        "op": "replace",
        "path": "/attributes/item_name",
        "value": [{"value": "Updated Product Title - Test", "marketplace_id": "A1F83G8C2ARO7P"}]
    }
    print(json.dumps(title_patch, indent=2))
    
    # Test 2: DRY RUN - Show what would be sent for multiple updates
    print("\n2. DRY RUN - Multiple Field Update")
    print("-" * 40)
    print("Would send the following patch operations:")
    
    patches = []
    
    # Title patch
    patches.append({
        "op": "replace",
        "path": "/attributes/item_name",
        "value": [{"value": "Professional Heavy-Duty Folding Wagon - Premium Edition", "marketplace_id": "A1F83G8C2ARO7P"}]
    })
    
    # Bullet points patch
    bullet_values = []
    new_bullets = [
        "PREMIUM 120KG CAPACITY - Professional-grade construction for demanding outdoor use",
        "ALL-TERRAIN EXCELLENCE - Engineered wheels conquer sand, grass, gravel with ease",
        "SMART FOLDING DESIGN - Collapses in seconds for compact storage and transport",
        "BUILT-IN COOLER LID - Keep beverages cold during outdoor adventures",
        "LIFETIME WARRANTY - Backed by our commitment to quality and customer satisfaction"
    ]
    for bullet in new_bullets:
        bullet_values.append({
            "value": bullet,
            "marketplace_id": "A1F83G8C2ARO7P"
        })
    
    patches.append({
        "op": "replace",
        "path": "/attributes/bullet_point",
        "value": bullet_values
    })
    
    # Search terms patch
    search_values = []
    new_terms = ["heavy duty wagon", "folding cart", "beach wagon", "camping trolley", "outdoor cart"]
    for term in new_terms:
        search_values.append({
            "value": term,
            "marketplace_id": "A1F83G8C2ARO7P"
        })
    
    patches.append({
        "op": "replace",
        "path": "/attributes/generic_keyword",
        "value": search_values
    })
    
    # Brand patch
    patches.append({
        "op": "replace",
        "path": "/attributes/brand",
        "value": [{"value": "RACKIT PRO", "marketplace_id": "A1F83G8C2ARO7P"}]
    })
    
    print(json.dumps({"patches": patches}, indent=2))
    
    print("\n   This would update:")
    print("   ✓ Title")
    print("   ✓ 5 Bullet Points")
    print("   ✓ 5 Search Terms")
    print("   ✓ Brand")
    
    # Test 3: Actually test the update with a minimal change (DRY RUN - commented)
    print("\n3. Testing actual update call (DRY RUN - not executing)...")
    print("   Would call update_listing with minimal changes to verify functionality")
    
    # Uncomment to actually test:
    """
    result = update_listing(
        auth_token=auth_token,
        seller_id=SELLER_ID,
        seller_sku=TEST_SKU,
        search_terms="heavy duty wagon, folding cart, beach wagon, camping trolley, outdoor cart",
        marketplace_ids="A1F83G8C2ARO7P"
    )
    
    result_data = json.loads(result)
    if result_data.get('success'):
        print(f"   ✓ Successfully updated listing")
        update_info = result_data.get('listing_update', {})
        print(f"   - Fields updated: {', '.join(update_info.get('fields_updated', []))}")
        print(f"   - Note: {update_info.get('note', '')}")
        print("\n   Response details:")
        print(json.dumps(result_data, indent=4))
    else:
        print(f"   ✗ Failed: {result_data.get('message', 'Unknown error')}")
        print("\n   Error details:")
        print(json.dumps(result_data, indent=4))
    """
    
    # Test 4: Validation test - no fields provided
    print("\n4. Testing validation - no fields provided...")
    result = update_listing(
        auth_token=auth_token,
        seller_id=SELLER_ID,
        seller_sku=TEST_SKU,
        marketplace_ids="A1F83G8C2ARO7P"
    )
    
    result_data = json.loads(result)
    if not result_data.get('success'):
        print(f"   ✓ Validation working correctly: {result_data.get('message', '')}")
    else:
        print(f"   ✗ Validation failed - should have rejected empty update")
    
    return True


def main():
    """Run all tests."""
    print("Testing Listing Management MCP Endpoints")
    print("========================================")
    print(f"Seller ID: {SELLER_ID}")
    print(f"Test SKU: {TEST_SKU}")
    
    # Check environment variables
    required_vars = [
        "LWA_CLIENT_ID",
        "LWA_CLIENT_SECRET", 
        "LWA_REFRESH_TOKEN",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"\n⚠️  Missing environment variables: {', '.join(missing_vars)}")
        print("Please set these in your .env file")
        return
    
    # Run tests
    test_get_listing()
    test_update_listing()
    
    print("\n" + "="*60)
    print("Testing complete!")
    print("="*60)
    print("\nNOTE: Update operations are commented out to avoid accidental changes.")
    print("Uncomment the update code blocks to test actual updates.")


if __name__ == "__main__":
    main()