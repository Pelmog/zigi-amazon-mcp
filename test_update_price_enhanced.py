#!/usr/bin/env python3
"""Enhanced test script with multiple approaches to update price."""

import json
import os
import sys
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from zigi_amazon_mcp.api.listings import ListingsAPIClient
from zigi_amazon_mcp.api.feeds import FeedsAPIClient
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


def approach_1_listings_api(access_token: str, aws_creds: dict):
    """Approach 1: Using Listings API with purchasable_offer patch."""
    print("\n" + "=" * 60)
    print("APPROACH 1: Listings API - purchasable_offer")
    print("=" * 60)
    
    client = ListingsAPIClient(
        access_token,
        aws_creds,
        region="eu-west-1",
        endpoint="https://sellingpartnerapi-eu.amazon.com"
    )
    
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
    
    print("Ready to execute:")
    print(f"  PATCH /sellers/v1/{SELLER_ID}/{TEST_SKU}")
    print(f"  New price: £{NEW_PRICE}")
    
    return client, patches


def approach_2_feeds_api(access_token: str, aws_creds: dict):
    """Approach 2: Using Feeds API with pricing feed."""
    print("\n" + "=" * 60)
    print("APPROACH 2: Feeds API - POST_PRODUCT_PRICING_DATA")
    print("=" * 60)
    
    client = FeedsAPIClient(
        access_token,
        aws_creds,
        region="eu-west-1",
        endpoint="https://sellingpartnerapi-eu.amazon.com"
    )
    
    # Build XML feed for price update
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<AmazonEnvelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="amzn-envelope.xsd">
    <Header>
        <DocumentVersion>1.01</DocumentVersion>
        <MerchantIdentifier>{SELLER_ID}</MerchantIdentifier>
    </Header>
    <MessageType>Price</MessageType>
    <Message>
        <MessageID>1</MessageID>
        <Price>
            <SKU>{TEST_SKU}</SKU>
            <StandardPrice currency="GBP">{NEW_PRICE}</StandardPrice>
        </Price>
    </Message>
</AmazonEnvelope>"""
    
    print("Ready to execute:")
    print("  1. Create feed document")
    print("  2. Upload XML content")
    print("  3. Submit feed type: POST_PRODUCT_PRICING_DATA")
    print(f"  New price: £{NEW_PRICE}")
    
    return client, xml_content


def approach_3_listings_api_simplified(access_token: str, aws_creds: dict):
    """Approach 3: Using Listings API with simplified offer structure."""
    print("\n" + "=" * 60)
    print("APPROACH 3: Listings API - Simplified offer")
    print("=" * 60)
    
    client = ListingsAPIClient(
        access_token,
        aws_creds,
        region="eu-west-1",
        endpoint="https://sellingpartnerapi-eu.amazon.com"
    )
    
    # Simplified patch structure that some sellers use
    patches = [
        {
            "op": "replace",
            "path": "/attributes/offer",
            "value": {
                "price": {
                    "currency": "GBP",
                    "amount": NEW_PRICE
                }
            }
        }
    ]
    
    print("Ready to execute:")
    print(f"  PATCH /sellers/v1/{SELLER_ID}/{TEST_SKU}")
    print(f"  New price: £{NEW_PRICE}")
    
    return client, patches


def main():
    """Main test function."""
    print("Amazon FBM Price Update Test - Multiple Approaches")
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
    
    # Get current listing
    print("\nCurrent Listing Status:")
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
        print(f"✓ SKU: {TEST_SKU}")
        print(f"  ASIN: {data.get('asin')}")
        print(f"  Current Price: £{data.get('price', {}).get('amount', 'N/A')}")
        print(f"  Quantity: {data.get('fulfillment_availability', {}).get('quantity', 0)}")
    
    # Get Amazon credentials
    try:
        access_token = get_amazon_access_token()
        aws_creds = get_amazon_aws_credentials()
        print("\n✓ Amazon credentials obtained")
    except Exception as e:
        print(f"\n✗ Failed to get credentials: {e}")
        return
    
    # Show all approaches
    client1, patches1 = approach_1_listings_api(access_token, aws_creds)
    client2, xml_content = approach_2_feeds_api(access_token, aws_creds)
    client3, patches3 = approach_3_listings_api_simplified(access_token, aws_creds)
    
    print("\n" + "=" * 60)
    print("EXECUTION CODE")
    print("=" * 60)
    print("\nTo execute the price update, uncomment ONE of the following approaches:")
    print("\n" + "-" * 60)
    print("# APPROACH 1: Listings API - purchasable_offer")
    print("-" * 60)
    print("""
# result = client1.patch_listings_item(
#     seller_id=SELLER_ID,
#     sku=TEST_SKU,
#     marketplace_ids="A1F83G8C2ARO7P",
#     patches=patches1,
# )
# print("Result:", json.dumps(result, indent=2))
""")
    
    print("-" * 60)
    print("# APPROACH 2: Feeds API")
    print("-" * 60)
    print("""
# # Step 1: Create feed document
# doc_result = client2.create_feed_document(content_type="XML")
# if doc_result.get("success"):
#     feed_document_id = doc_result["data"]["feedDocumentId"]
#     upload_url = doc_result["data"]["url"]
#     
#     # Step 2: Upload XML
#     import requests
#     upload_response = requests.put(
#         upload_url,
#         data=xml_content.encode("utf-8"),
#         headers={"Content-Type": "text/xml; charset=UTF-8"},
#     )
#     
#     # Step 3: Create feed
#     feed_result = client2.create_feed(
#         feed_type="POST_PRODUCT_PRICING_DATA",
#         marketplace_ids="A1F83G8C2ARO7P",
#         feed_document_id=feed_document_id,
#     )
#     print("Feed Result:", json.dumps(feed_result, indent=2))
""")
    
    print("-" * 60)
    print("# APPROACH 3: Listings API - Simplified")
    print("-" * 60)
    print("""
# result = client3.patch_listings_item(
#     seller_id=SELLER_ID,
#     sku=TEST_SKU,
#     marketplace_ids="A1F83G8C2ARO7P",
#     patches=patches3,
# )
# print("Result:", json.dumps(result, indent=2))
""")
    
    print("\n" + "=" * 60)
    print("NOTES:")
    print("=" * 60)
    print("1. Different approaches work for different account types")
    print("2. Approach 1 (purchasable_offer) is the most common for FBM")
    print("3. Approach 2 (Feeds) is good for bulk updates")
    print("4. Price changes typically take 5-15 minutes to reflect")
    print("5. Monitor for errors in the response")
    print("\nPlease review and choose an approach before executing.")


if __name__ == "__main__":
    main()