#!/usr/bin/env python3
"""Execute price update with verbose logging - Approach 1: Listings API."""

import json
import os
import sys
from datetime import datetime
import logging

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Enable detailed logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from zigi_amazon_mcp.api.listings import ListingsAPIClient
from zigi_amazon_mcp.server import (
    get_amazon_access_token,
    get_amazon_aws_credentials,
    get_auth_token,
    get_fbm_inventory,
)

# Your seller information
SELLER_ID = "A2C259Q0GU1WMI"
TEST_SKU = "JL-BC002"
TEST_ASIN = "B0CY5RJ3CL"
CURRENT_PRICE = "69.99"
NEW_PRICE = "69.98"


def main():
    """Execute the price update with detailed logging."""
    print("\n" + "=" * 80)
    print("AMAZON FBM PRICE UPDATE EXECUTION - APPROACH 1")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Target SKU: {TEST_SKU}")
    print(f"Price Change: £{CURRENT_PRICE} → £{NEW_PRICE} (1 penny reduction)")
    print("=" * 80)
    
    # Step 1: Authentication
    print("\n📋 STEP 1: AUTHENTICATION")
    print("-" * 80)
    
    print("1.1 Getting MCP auth token...")
    auth_result = get_auth_token()
    if "Your auth token is:" not in auth_result:
        logger.error("Failed to get auth token")
        return
        
    auth_token = auth_result.split("Your auth token is: ")[1].strip()
    print(f"✅ MCP auth token obtained: {auth_token[:20]}...")
    
    # Step 2: Verify Current State
    print("\n📋 STEP 2: VERIFY CURRENT LISTING STATE")
    print("-" * 80)
    
    print("2.1 Fetching current listing details...")
    result = get_fbm_inventory(
        auth_token=auth_token,
        seller_id=SELLER_ID,
        seller_sku=TEST_SKU,
        marketplace_ids="A1F83G8C2ARO7P"
    )
    
    result_data = json.loads(result)
    if result_data.get('success'):
        data = result_data.get('data', {})
        current_price_actual = data.get('price', {}).get('amount', 'N/A')
        print(f"✅ Current listing verified:")
        print(f"   - SKU: {TEST_SKU}")
        print(f"   - ASIN: {data.get('asin')}")
        print(f"   - Product: {data.get('product_name', 'N/A')[:60]}...")
        print(f"   - Current Price: £{current_price_actual}")
        print(f"   - Quantity: {data.get('fulfillment_availability', {}).get('quantity', 0)} units")
        print(f"   - Status: {data.get('listing_status')}")
        
        if current_price_actual != CURRENT_PRICE:
            print(f"\n⚠️  WARNING: Current price (£{current_price_actual}) doesn't match expected (£{CURRENT_PRICE})")
            confirm = input("Continue anyway? (yes/no): ")
            if confirm.lower() != 'yes':
                print("Aborted by user")
                return
    else:
        logger.error(f"Failed to get listing: {result_data.get('message')}")
        return
    
    # Step 3: Get Amazon Credentials
    print("\n📋 STEP 3: OBTAIN AMAZON SP-API CREDENTIALS")
    print("-" * 80)
    
    try:
        print("3.1 Getting Amazon LWA access token...")
        access_token = get_amazon_access_token()
        print(f"✅ LWA access token obtained: {access_token[:20]}...")
        
        print("\n3.2 Getting AWS credentials for request signing...")
        aws_creds = get_amazon_aws_credentials()
        print(f"✅ AWS credentials obtained:")
        print(f"   - Access Key ID: {aws_creds['AccessKeyId'][:10]}...")
        print(f"   - Has Session Token: {'Yes' if aws_creds.get('SessionToken') else 'No'}")
    except Exception as e:
        logger.error(f"Failed to get credentials: {e}")
        return
    
    # Step 4: Prepare API Client and Request
    print("\n📋 STEP 4: PREPARE PRICE UPDATE REQUEST")
    print("-" * 80)
    
    print("4.1 Initializing Listings API client...")
    client = ListingsAPIClient(
        access_token,
        aws_creds,
        region="eu-west-1",
        endpoint="https://sellingpartnerapi-eu.amazon.com"
    )
    print("✅ API client initialized")
    
    print("\n4.2 Constructing patch operation...")
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
    
    print("✅ Patch operation constructed:")
    print(json.dumps(patches, indent=2))
    
    # Step 5: Execute the Update
    print("\n📋 STEP 5: EXECUTE PRICE UPDATE")
    print("-" * 80)
    
    print(f"5.1 Sending PATCH request to SP-API...")
    print(f"    Endpoint: PATCH /sellers/v1/{SELLER_ID}/{TEST_SKU}")
    print(f"    Marketplace: A1F83G8C2ARO7P (UK)")
    print(f"    Product Type: PRODUCT")
    
    try:
        logger.info("Making API request...")
        result = client.patch_listings_item(
            seller_id=SELLER_ID,
            sku=TEST_SKU,
            marketplace_ids="A1F83G8C2ARO7P",
            patches=patches,
        )
        
        print("\n5.2 Response received:")
        print("-" * 40)
        print(json.dumps(result, indent=2))
        print("-" * 40)
        
        # Step 6: Analyze Results
        print("\n📋 STEP 6: ANALYZE UPDATE RESULTS")
        print("-" * 80)
        
        if result.get('success'):
            print("✅ PRICE UPDATE SUCCESSFUL!")
            print(f"   - SKU: {result.get('sku', TEST_SKU)}")
            print(f"   - Status: {result.get('status', 'SUBMITTED')}")
            print(f"   - Submission ID: {result.get('submissionId', 'N/A')}")
            print(f"   - Request ID: {result.get('metadata', {}).get('request_id', 'N/A')}")
            
            # Check for any warnings
            if result.get('issues'):
                print("\n⚠️  Issues/Warnings reported:")
                for issue in result.get('issues', []):
                    print(f"   - {issue.get('code', 'N/A')}: {issue.get('message', 'N/A')}")
            
            print("\n📝 NEXT STEPS:")
            print("   1. Price change typically takes 5-15 minutes to reflect on Amazon")
            print("   2. Check your Seller Central to verify the update")
            print("   3. Re-run get_fbm_inventory to confirm the new price")
            
        else:
            print("❌ PRICE UPDATE FAILED!")
            print(f"   - Error Code: {result.get('error', 'Unknown')}")
            print(f"   - Message: {result.get('message', 'No message')}")
            
            if result.get('details'):
                print("\n   Error Details:")
                for detail in result.get('details', []):
                    print(f"   - {detail}")
                    
    except Exception as e:
        logger.error(f"Exception during API call: {e}")
        import traceback
        traceback.print_exc()
        
    print("\n" + "=" * 80)
    print(f"EXECUTION COMPLETE - {datetime.now().isoformat()}")
    print("=" * 80)


if __name__ == "__main__":
    main()