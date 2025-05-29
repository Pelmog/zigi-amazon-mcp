#!/usr/bin/env python3
"""Read-only test script for FBM inventory endpoints - no data modification."""

import json
import os
import sys
import time
from datetime import datetime, timedelta

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from zigi_amazon_mcp.server import (
    get_fbm_inventory,
    get_fbm_inventory_report,
    get_auth_token,
    get_inventory_in_stock,
)


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"{title}")
    print(f"{'=' * 60}")


def test_auth_flow():
    """Test authentication flow."""
    print_section("Testing Authentication")
    
    # Get auth token
    auth_result = get_auth_token()
    print(f"Auth result: {auth_result[:100]}...")
    
    # Extract token
    if "Your auth token is:" in auth_result:
        token = auth_result.split("Your auth token is: ")[1].strip()
        print(f"✓ Successfully obtained auth token: {token[:20]}...")
        return token
    else:
        print("✗ Failed to get auth token")
        return None


def test_environment_setup():
    """Check if environment variables are set."""
    print_section("Checking Environment Setup")
    
    required_vars = [
        "LWA_CLIENT_ID",
        "LWA_CLIENT_SECRET", 
        "LWA_REFRESH_TOKEN",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY"
    ]
    
    all_set = True
    for var in required_vars:
        if os.getenv(var):
            print(f"✓ {var} is set")
        else:
            print(f"✗ {var} is NOT set")
            all_set = False
    
    optional_var = "AWS_ROLE_ARN"
    if os.getenv(optional_var):
        print(f"✓ {optional_var} is set (optional)")
    else:
        print(f"  {optional_var} is not set (optional - will use default)")
    
    return all_set


def test_get_current_inventory(auth_token: str):
    """Test getting current FBA inventory to compare with FBM."""
    print_section("Current FBA Inventory (for comparison)")
    
    try:
        result = get_inventory_in_stock(
            auth_token=auth_token,
            marketplace_ids="A1F83G8C2ARO7P",
            fulfillment_type="FBA",
            details=True,
            max_results=5  # Just show first 5 items
        )
        
        result_data = json.loads(result)
        if result_data.get('success'):
            summary = result_data.get('data', {}).get('summary', {})
            inventory = result_data.get('data', {}).get('inventory', [])
            
            print(f"✓ Successfully retrieved FBA inventory")
            print(f"  Products in stock: {summary.get('products_in_stock', 0)}")
            print(f"  Total units: {summary.get('total_units', 0)}")
            
            if inventory:
                print("\n  Sample items:")
                for item in inventory[:3]:
                    print(f"  - SKU: {item.get('seller_sku')}, Qty: {item.get('total_quantity')}")
        else:
            print(f"✗ Error: {result_data.get('error')} - {result_data.get('message')}")
    except Exception as e:
        print(f"✗ Exception: {e}")


def test_get_fbm_inventory_single_sku(auth_token: str, seller_id: str, test_sku: str):
    """Test get_fbm_inventory for a single SKU."""
    print_section(f"Testing Single FBM SKU Retrieval: {test_sku}")
    
    try:
        result = get_fbm_inventory(
            auth_token=auth_token,
            seller_id=seller_id,
            seller_sku=test_sku,
            marketplace_ids="A1F83G8C2ARO7P",
            include_inactive=True  # Include inactive to see more data
        )
        
        result_data = json.loads(result)
        if result_data.get('success'):
            data = result_data.get('data', {})
            
            print(f"✓ Successfully retrieved FBM listing for SKU: {test_sku}")
            print(f"  ASIN: {data.get('asin', 'N/A')}")
            print(f"  Product Name: {data.get('product_name', 'N/A')}")
            print(f"  Listing Status: {data.get('listing_status', 'N/A')}")
            
            fulfillment = data.get('fulfillment_availability', {})
            print(f"\n  Fulfillment Details:")
            print(f"  - Channel: {fulfillment.get('fulfillment_channel_code', 'N/A')}")
            print(f"  - Quantity: {fulfillment.get('quantity', 0)}")
            print(f"  - Available: {fulfillment.get('is_available', False)}")
            print(f"  - Handling Time: {fulfillment.get('handling_time', 'N/A')} days")
            
            price = data.get('price', {})
            if price.get('amount'):
                print(f"\n  Price: {price.get('currency', '')} {price.get('amount', 'N/A')}")
                
            return True
        else:
            error = result_data.get('error')
            message = result_data.get('message', '')
            
            if error == 'api_error' and 'not found' in message.lower():
                print(f"  SKU not found or not FBM: {test_sku}")
            else:
                print(f"✗ Error: {error} - {message}")
            return False
    except Exception as e:
        print(f"✗ Exception: {e}")
        return False


def test_get_fbm_inventory_report(auth_token: str):
    """Test creating an FBM inventory report."""
    print_section("Testing FBM Inventory Report Creation")
    
    try:
        # Create report for ALL merchant listings
        result = get_fbm_inventory_report(
            auth_token=auth_token,
            report_type="ALL_DATA",
            marketplace_ids="A1F83G8C2ARO7P"
        )
        
        result_data = json.loads(result)
        if result_data.get('success'):
            data = result_data.get('data', {})
            
            print(f"✓ Successfully created FBM inventory report")
            print(f"  Report ID: {data.get('reportId')}")
            print(f"  Report Type: {data.get('reportType')}")
            print(f"  Status: {data.get('status')}")
            print(f"  Created: {data.get('createdTime')}")
            
            print(f"\n  Note: Report generation is asynchronous.")
            print(f"  You would need to check the report status and download when ready.")
            print(f"  This typically takes 1-5 minutes.")
            
            return data.get('reportId')
        else:
            print(f"✗ Error: {result_data.get('error')} - {result_data.get('message')}")
            return None
    except Exception as e:
        print(f"✗ Exception: {e}")
        return None


def test_sample_skus(auth_token: str, seller_id: str):
    """Test with a few sample SKUs to find FBM items."""
    print_section("Testing Multiple SKUs to Find FBM Items")
    
    # You should replace these with your actual SKUs
    sample_skus = [
        "SAMPLE-SKU-001",
        "SAMPLE-SKU-002", 
        "TEST-PRODUCT-123",
        # Add your actual SKUs here
    ]
    
    print(f"Testing {len(sample_skus)} sample SKUs...")
    print("Note: Replace sample_skus in the script with your actual SKUs\n")
    
    fbm_found = 0
    for sku in sample_skus:
        print(f"Checking SKU: {sku}")
        if test_get_fbm_inventory_single_sku(auth_token, seller_id, sku):
            fbm_found += 1
        time.sleep(1)  # Small delay between requests
    
    print(f"\nFound {fbm_found} FBM items out of {len(sample_skus)} tested")


def main():
    """Run all read-only tests."""
    print("FBM Inventory Read-Only Tests")
    print("=" * 60)
    print("This script will test FBM endpoints without modifying any data")
    
    # Check environment
    if not test_environment_setup():
        print("\n⚠️  Missing required environment variables!")
        print("Please ensure all required variables are set in your .env file")
        return
    
    # Get auth token
    auth_token = test_auth_flow()
    if not auth_token:
        print("\n⚠️  Failed to get auth token, exiting")
        return
    
    # Get seller ID from user or use default
    seller_id = input("\nEnter your Seller ID (or press Enter to skip FBM tests): ").strip()
    
    if not seller_id:
        print("\n⚠️  No Seller ID provided, skipping FBM-specific tests")
        print("Only running tests that don't require Seller ID...")
        
        # Can still test these without seller ID
        test_get_current_inventory(auth_token)
        test_get_fbm_inventory_report(auth_token)
    else:
        # Test current inventory
        test_get_current_inventory(auth_token)
        
        # Test FBM report creation
        report_id = test_get_fbm_inventory_report(auth_token)
        
        # Test single SKU retrieval
        test_sku = input("\nEnter a specific SKU to test (or press Enter to test samples): ").strip()
        
        if test_sku:
            test_get_fbm_inventory_single_sku(auth_token, seller_id, test_sku)
        else:
            test_sample_skus(auth_token, seller_id)
    
    print_section("Test Summary")
    print("✓ All read-only tests completed")
    print("✓ No inventory data was modified")
    print("\nNext steps:")
    print("1. Check the report status using the report ID")
    print("2. Test with your actual FBM SKUs")
    print("3. Only proceed with update/bulk update tests when ready")


if __name__ == "__main__":
    main()