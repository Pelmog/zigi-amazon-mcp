#!/usr/bin/env python3
"""Test script to explore Inventory API v0 for FBM inventory."""

import json
import os
from urllib.parse import urlencode
import requests
from dotenv import load_dotenv
from requests_aws4auth import AWS4Auth
import boto3

load_dotenv()

def get_amazon_access_token():
    """Exchange refresh token for access token from Amazon LWA."""
    client_id = os.getenv("LWA_CLIENT_ID")
    client_secret = os.getenv("LWA_CLIENT_SECRET")
    refresh_token = os.getenv("LWA_REFRESH_TOKEN")
    
    if not all([client_id, client_secret, refresh_token]):
        raise ValueError("Missing required LWA credentials")
    
    lwa_url = "https://api.amazon.com/auth/o2/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }
    
    response = requests.post(lwa_url, data=data, timeout=30)
    if response.status_code == 200:
        token_data = response.json()
        return str(token_data["access_token"])
    else:
        print(f"LWA Error: {response.status_code} - {response.text}")
        return None

def get_amazon_aws_credentials():
    """Get AWS temporary credentials by assuming role for Amazon SP-API."""
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    if not all([aws_access_key_id, aws_secret_access_key]):
        raise ValueError("Missing required AWS credentials")
    
    role_arn = os.getenv(
        "AWS_ROLE_ARN",
        "arn:aws:iam::295290492609:role/SPapi-Role-2025",
    )
    
    sts_client = boto3.client(
        "sts",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )
    
    try:
        assume_response = sts_client.assume_role(
            RoleArn=role_arn, 
            RoleSessionName="SPapi-Role-2025"
        )
        
        credentials = assume_response["Credentials"]
        return {
            "AccessKeyId": credentials["AccessKeyId"],
            "SecretAccessKey": credentials["SecretAccessKey"],
            "SessionToken": credentials["SessionToken"],
        }
    except Exception as e:
        print(f"STS Error: {e}")
        return None

def test_inventory_api_v0():
    """Test the Inventory API v0 endpoint."""
    print("Testing Inventory API v0 for FBM inventory...")
    
    # Get access token
    access_token = get_amazon_access_token()
    if not access_token:
        print("Failed to get access token")
        return
    
    # Get AWS credentials
    creds = get_amazon_aws_credentials()
    if not creds:
        print("Failed to get AWS credentials")
        return
    
    # Set up AWS4Auth
    region = "eu-west-1"
    aws_auth = AWS4Auth(
        creds["AccessKeyId"],
        creds["SecretAccessKey"],
        region,
        "execute-api",
        session_token=creds["SessionToken"],
    )
    
    # Headers
    headers = {
        "x-amz-access-token": access_token,
        "user-agent": "ZigiAmazonMCP/1.0 (Language=Python)",
        "content-type": "application/json",
    }
    
    # Prepare request for Inventory API v0
    endpoint = "https://sellingpartnerapi-eu.amazon.com"
    api_path = "/inventory/v1/summaries"
    
    # Parameters for inventory summaries
    params = {
        "details": "true",
        "marketplaceIds": "A1F83G8C2ARO7P",  # UK marketplace
        "granularityType": "Marketplace",
        "granularityId": "A1F83G8C2ARO7P",
    }
    
    url = f"{endpoint}{api_path}?{urlencode(params, doseq=True)}"
    
    print(f"\nMaking request to: {api_path}")
    print(f"Parameters: {params}")
    
    try:
        response = requests.get(url, headers=headers, auth=aws_auth, timeout=30)
        
        print(f"\nResponse status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print("\nSuccessful response:")
            print(json.dumps(data, indent=2))
            
            # Process inventory items
            if "inventorySummaries" in data:
                summaries = data["inventorySummaries"]
                print(f"\nFound {len(summaries)} inventory items")
                
                # Filter for FBM items
                fbm_items = []
                for item in summaries:
                    # Check if this is FBM inventory
                    total_quantity = item.get("totalQuantity", 0)
                    if total_quantity > 0:
                        print(f"\nItem: {item.get('sellerSku', 'Unknown SKU')}")
                        print(f"  ASIN: {item.get('asin')}")
                        print(f"  Total Quantity: {total_quantity}")
                        print(f"  Condition: {item.get('condition')}")
                        print(f"  Product Name: {item.get('productName')}")
                        
                        # Check inventory details
                        inventory_details = item.get("inventoryDetails", {})
                        print(f"  Inventory Details: {inventory_details}")
                        
                        fbm_items.append(item)
                
                print(f"\nTotal FBM items in stock: {len(fbm_items)}")
            else:
                print("\nNo inventory summaries found in response")
                
        else:
            print(f"\nError response: {response.text}")
            
    except Exception as e:
        print(f"\nException occurred: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_inventory_api_v0()