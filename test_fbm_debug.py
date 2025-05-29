#!/usr/bin/env python3
"""Debug test to see raw API response."""

import json
import os
import sys
from datetime import datetime, timedelta

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

from zigi_amazon_mcp.api.listings import ListingsAPIClient
from zigi_amazon_mcp.server import get_amazon_access_token, get_amazon_aws_credentials, get_auth_token

# Your seller information
SELLER_ID = "A2C259Q0GU1WMI"
TEST_SKU = "JL-BC002"
TEST_ASIN = "B0CY5RJ3CL"


def main():
    """Run debug test."""
    print("Debug FBM API Test")
    print("=" * 60)
    
    # Get auth token
    auth_result = get_auth_token()
    if "Your auth token is:" not in auth_result:
        print("Failed to get auth token")
        return
        
    print("✓ Got MCP auth token")
    
    # Get Amazon credentials
    try:
        access_token = get_amazon_access_token()
        print("✓ Got Amazon access token")
        
        aws_creds = get_amazon_aws_credentials()
        print("✓ Got AWS credentials")
        
        # Create API client
        client = ListingsAPIClient(
            access_token, 
            aws_creds,
            region="eu-west-1",
            endpoint="https://sellingpartnerapi-eu.amazon.com"
        )
        
        print(f"\nCalling Listings API for SKU: {TEST_SKU}")
        print("-" * 60)
        
        # Make direct API call
        result = client.get_listings_item(
            seller_id=SELLER_ID,
            sku=TEST_SKU,
            marketplace_ids="A1F83G8C2ARO7P",
            included_data=["summaries", "attributes", "offers", "fulfillmentAvailability"],
        )
        
        print("\nAPI Response:")
        print(json.dumps(result, indent=2))
        
        # Check the raw response structure
        if result.get('success'):
            print("\n" + "=" * 60)
            print("Response Analysis:")
            print("=" * 60)
            
            data = result.get('data', {})
            
            # Check what fields are actually populated
            for key, value in data.items():
                if value:
                    print(f"✓ {key}: {type(value).__name__} - populated")
                else:
                    print(f"  {key}: {type(value).__name__} - empty/null")
                    
    except Exception as e:
        print(f"\n✗ Exception: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()