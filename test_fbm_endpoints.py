#!/usr/bin/env python3
"""Test script for FBM inventory endpoints."""

import json
import os
import sys
from datetime import datetime, timedelta

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from zigi_amazon_mcp.server import (
    get_fbm_inventory,
    get_fbm_inventory_report,
    update_fbm_inventory,
    bulk_update_fbm_inventory,
    get_auth_token,
)


def test_auth_flow():
    """Test authentication flow."""
    print("\n=== Testing Authentication ===")
    
    # Get auth token
    auth_result = get_auth_token()
    print(f"Auth result: {auth_result}")
    
    # Extract token
    if "Your auth token is:" in auth_result:
        token = auth_result.split("Your auth token is: ")[1].strip()
        print(f"Extracted token: {token[:20]}...")
        return token
    else:
        print("Failed to get auth token")
        return None


def test_get_fbm_inventory(auth_token: str):
    """Test get_fbm_inventory endpoint."""
    print("\n=== Testing get_fbm_inventory ===")
    
    # Test with valid parameters
    result = get_fbm_inventory(
        auth_token=auth_token,
        seller_id="A1TESTSELLERID",
        seller_sku="TEST-SKU-001",
        marketplace_ids="A1F83G8C2ARO7P",
        include_inactive=False
    )
    
    result_data = json.loads(result)
    print(f"Success: {result_data.get('success')}")
    if result_data.get('success'):
        print(f"Data: {json.dumps(result_data.get('data'), indent=2)}")
    else:
        print(f"Error: {result_data.get('error')} - {result_data.get('message')}")
    
    # Test with missing credentials (should fail)
    print("\n--- Testing without environment variables ---")
    # Temporarily remove env var
    old_client_id = os.environ.get('LWA_CLIENT_ID')
    if old_client_id:
        del os.environ['LWA_CLIENT_ID']
    
    result = get_fbm_inventory(
        auth_token=auth_token,
        seller_id="A1TESTSELLERID",
        seller_sku="TEST-SKU-001",
        marketplace_ids="A1F83G8C2ARO7P"
    )
    
    result_data = json.loads(result)
    print(f"Expected error: {result_data.get('error')} - {result_data.get('message')}")
    
    # Restore env var
    if old_client_id:
        os.environ['LWA_CLIENT_ID'] = old_client_id


def test_get_fbm_inventory_report(auth_token: str):
    """Test get_fbm_inventory_report endpoint."""
    print("\n=== Testing get_fbm_inventory_report ===")
    
    # Test with valid parameters
    result = get_fbm_inventory_report(
        auth_token=auth_token,
        report_type="ALL_DATA",  # Changed from ALL_LISTINGS
        marketplace_ids="A1F83G8C2ARO7P"
        # Removed max_wait_time - not a parameter
    )
    
    result_data = json.loads(result)
    print(f"Success: {result_data.get('success')}")
    if result_data.get('success'):
        print(f"Full data: {json.dumps(result_data.get('data'), indent=2)}")
    else:
        print(f"Error: {result_data.get('error')} - {result_data.get('message')}")
    
    # Test with invalid report type
    print("\n--- Testing with invalid report type ---")
    result = get_fbm_inventory_report(
        auth_token=auth_token,
        report_type="INVALID_TYPE",
        marketplace_ids="A1F83G8C2ARO7P"
    )
    
    result_data = json.loads(result)
    print(f"Expected error: {result_data.get('error')} - {result_data.get('message')}")


def test_update_fbm_inventory(auth_token: str):
    """Test update_fbm_inventory endpoint."""
    print("\n=== Testing update_fbm_inventory ===")
    
    # Test with valid parameters
    result = update_fbm_inventory(
        auth_token=auth_token,
        seller_id="A1TESTSELLERID",
        seller_sku="TEST-SKU-001",
        quantity=100,
        marketplace_ids="A1F83G8C2ARO7P",
        handling_time=2,
        restock_date=(datetime.now() + timedelta(days=7)).isoformat()
    )
    
    result_data = json.loads(result)
    print(f"Success: {result_data.get('success')}")
    if result_data.get('success'):
        print(f"Data: {json.dumps(result_data.get('data'), indent=2)}")
    else:
        print(f"Error: {result_data.get('error')} - {result_data.get('message')}")
    
    # Test with invalid handling time
    print("\n--- Testing with invalid handling time ---")
    result = update_fbm_inventory(
        auth_token=auth_token,
        seller_id="A1TESTSELLERID",
        seller_sku="TEST-SKU-001",
        quantity=100,
        marketplace_ids="A1F83G8C2ARO7P",
        handling_time=50  # Too high
    )
    
    result_data = json.loads(result)
    print(f"Expected error: {result_data.get('error')} - {result_data.get('message')}")


def test_bulk_update_fbm_inventory(auth_token: str):
    """Test bulk_update_fbm_inventory endpoint."""
    print("\n=== Testing bulk_update_fbm_inventory ===")
    
    # Test with valid parameters
    inventory_updates = [
        {
            "sku": "TEST-SKU-001",
            "quantity": 100,
            "handling_time": 2,
            "restock_date": (datetime.now() + timedelta(days=7)).isoformat()
        },
        {
            "sku": "TEST-SKU-002",
            "quantity": 50,
            "handling_time": 1
        }
    ]
    
    result = bulk_update_fbm_inventory(
        auth_token=auth_token,
        inventory_updates=json.dumps(inventory_updates),
        marketplace_id="A1F83G8C2ARO7P"
    )
    
    result_data = json.loads(result)
    print(f"Success: {result_data.get('success')}")
    if result_data.get('success'):
        # Print the full data structure to see what's returned
        print(f"Full data: {json.dumps(result_data.get('data'), indent=2)}")
    else:
        print(f"Error: {result_data.get('error')} - {result_data.get('message')}")
    
    # Test with invalid data
    print("\n--- Testing with invalid inventory data ---")
    invalid_updates = [
        {
            "sku": "TEST-SKU-001",
            "quantity": -10,  # Negative quantity
            "handling_time": 2
        }
    ]
    
    result = bulk_update_fbm_inventory(
        auth_token=auth_token,
        inventory_updates=json.dumps(invalid_updates),
        marketplace_id="A1F83G8C2ARO7P"
    )
    
    result_data = json.loads(result)
    print(f"Expected error: {result_data.get('error')} - {result_data.get('message')}")


def main():
    """Run all tests."""
    print("Starting FBM Endpoint Tests")
    print("=" * 50)
    
    # Get auth token
    auth_token = test_auth_flow()
    if not auth_token:
        print("Failed to get auth token, exiting")
        return
    
    # Test each endpoint
    test_get_fbm_inventory(auth_token)
    test_get_fbm_inventory_report(auth_token)
    test_update_fbm_inventory(auth_token)
    test_bulk_update_fbm_inventory(auth_token)
    
    print("\n" + "=" * 50)
    print("All tests completed!")


if __name__ == "__main__":
    main()