#!/usr/bin/env python3
"""Debug test script to see raw listing data from Amazon SP-API."""

import json
import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from zigi_amazon_mcp.server import get_amazon_access_token, get_amazon_aws_credentials
from zigi_amazon_mcp.api.listings import ListingsAPIClient

# Configuration
SELLER_ID = os.getenv("SELLER_ID", "A2C259Q0GU1WMI")
TEST_SKU = "JL-BC002"


def test_raw_listing_data():
    """Test to see raw listing data from the API."""
    print("\n" + "="*60)
    print("Testing Raw Listing Data from SP-API")
    print("="*60)
    
    # Get credentials
    access_token = get_amazon_access_token()
    if not access_token:
        print("Failed to get Amazon access token")
        return
    
    aws_creds = get_amazon_aws_credentials()
    if not aws_creds:
        print("Failed to get AWS credentials")
        return
    
    print("✓ Credentials obtained")
    
    # Create client
    client = ListingsAPIClient(access_token, aws_creds)
    
    # Override the transform method temporarily to return raw data
    original_transform = client._transform_listings_item
    client._transform_listings_item = lambda x: x  # Return raw response
    
    print(f"\nGetting raw listing data for SKU: {TEST_SKU}")
    print("-" * 60)
    
    # Get listing with all data
    result = client.get_listings_item(
        seller_id=SELLER_ID,
        sku=TEST_SKU,
        marketplace_ids="A1F83G8C2ARO7P",
        included_data=["attributes", "issues", "offers", "fulfillmentAvailability", "summaries"]
    )
    
    if result.get('success'):
        print("✓ Successfully retrieved raw listing data\n")
        print("=== RAW API RESPONSE ===")
        print(json.dumps(result.get('data', {}), indent=2))
        print("=== END RAW RESPONSE ===\n")
        
        # Look for specific attributes
        raw_data = result.get('data', {})
        if 'attributes' in raw_data:
            print("\n=== ATTRIBUTES SECTION ===")
            print(json.dumps(raw_data['attributes'], indent=2))
            print("=== END ATTRIBUTES ===\n")
            
        if 'summaries' in raw_data:
            print("\n=== SUMMARIES SECTION ===")
            print(json.dumps(raw_data['summaries'], indent=2))
            print("=== END SUMMARIES ===\n")
            
    else:
        print(f"✗ Failed: {result.get('message', 'Unknown error')}")
        print(json.dumps(result, indent=2))
    
    # Restore original transform
    client._transform_listings_item = original_transform


def main():
    """Run the raw data test."""
    print("Raw Listing Data Test")
    print("=====================")
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
    
    test_raw_listing_data()


if __name__ == "__main__":
    main()