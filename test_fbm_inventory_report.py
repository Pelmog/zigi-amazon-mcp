#!/usr/bin/env python3
"""Test script to get FBM inventory through Reports API."""

import json
import os
import time
import csv
import io
from urllib.parse import urlencode
import requests
from dotenv import load_dotenv
from requests_aws4auth import AWS4Auth
import boto3
from datetime import datetime, timedelta, timezone

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
    except Exception:
        return None

def test_fbm_inventory():
    """Test getting FBM inventory through the Reports API."""
    print("Testing FBM inventory retrieval through Reports API...")
    
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
    
    endpoint = "https://sellingpartnerapi-eu.amazon.com"
    
    # Step 1: Check for recent merchant listings report
    print("\n1. Checking for recent merchant listings reports...")
    
    created_since = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    
    api_path = "/reports/2021-06-30/reports"
    params = {
        "marketplaceIds": "A1F83G8C2ARO7P",
        "createdSince": created_since,
        "reportTypes": "GET_MERCHANT_LISTINGS_ALL_DATA",
        "processingStatuses": "DONE"
    }
    
    url = f"{endpoint}{api_path}?{urlencode(params, doseq=True)}"
    response = requests.get(url, headers=headers, auth=aws_auth, timeout=30)
    
    report_id = None
    if response.status_code == 200:
        data = response.json()
        reports = data.get("reports", [])
        
        if reports:
            report_id = reports[0]["reportId"]
            print(f"Found recent report: {report_id}")
        else:
            print("No recent reports found")
    
    # Step 2: Create a new report if needed
    if not report_id:
        print("\n2. Creating new merchant listings report...")
        
        report_request = {
            "reportType": "GET_MERCHANT_LISTINGS_ALL_DATA",
            "marketplaceIds": ["A1F83G8C2ARO7P"],
        }
        
        response = requests.post(
            f"{endpoint}{api_path}",
            headers=headers,
            auth=aws_auth,
            json=report_request,
            timeout=30
        )
        
        if response.status_code in [200, 202]:
            data = response.json()
            report_id = data["reportId"]
            print(f"Created report: {report_id}")
            
            # Wait for report to complete
            print("\n3. Waiting for report to complete...")
            
            for i in range(30):  # Wait up to 5 minutes
                time.sleep(10)
                
                # Check report status
                url = f"{endpoint}{api_path}/{report_id}"
                response = requests.get(url, headers=headers, auth=aws_auth, timeout=30)
                
                if response.status_code == 200:
                    report_data = response.json()
                    status = report_data.get("processingStatus")
                    print(f"  Status: {status}")
                    
                    if status == "DONE":
                        print("Report completed!")
                        break
                    elif status in ["CANCELLED", "FATAL"]:
                        print(f"Report failed with status: {status}")
                        return
            else:
                print("Report timed out")
                return
    
    # Step 3: Get report document
    print("\n4. Getting report document...")
    
    url = f"{endpoint}{api_path}/{report_id}"
    response = requests.get(url, headers=headers, auth=aws_auth, timeout=30)
    
    if response.status_code == 200:
        report_data = response.json()
        document_id = report_data.get("reportDocumentId")
        
        if document_id:
            print(f"Document ID: {document_id}")
            
            # Get document download URL
            url = f"{endpoint}/reports/2021-06-30/documents/{document_id}"
            response = requests.get(url, headers=headers, auth=aws_auth, timeout=30)
            
            if response.status_code == 200:
                document_data = response.json()
                download_url = document_data.get("url")
                compression = document_data.get("compressionAlgorithm")
                
                print(f"Download URL obtained")
                print(f"Compression: {compression}")
                
                # Download the report
                print("\n5. Downloading report...")
                response = requests.get(download_url, timeout=30)
                
                if response.status_code == 200:
                    # Parse the report (assuming it's a TSV file)
                    content = response.text
                    
                    # Parse TSV data
                    reader = csv.DictReader(io.StringIO(content), delimiter='\t')
                    
                    fbm_items = []
                    all_items = []
                    
                    for row in reader:
                        all_items.append(row)
                        
                        # Check if this is FBM inventory
                        fulfillment_channel = row.get('fulfillment-channel', '')
                        quantity = row.get('quantity', '0')
                        
                        try:
                            quantity_int = int(quantity) if quantity else 0
                        except ValueError:
                            quantity_int = 0
                        
                        if fulfillment_channel == 'DEFAULT' and quantity_int > 0:
                            fbm_items.append({
                                'sku': row.get('seller-sku', ''),
                                'asin': row.get('asin1', ''),
                                'product_name': row.get('item-name', ''),
                                'quantity': quantity_int,
                                'price': row.get('price', ''),
                                'condition': row.get('item-condition', ''),
                                'status': row.get('status', '')
                            })
                    
                    print(f"\n6. Report Analysis:")
                    print(f"Total items: {len(all_items)}")
                    print(f"FBM items in stock: {len(fbm_items)}")
                    
                    if fbm_items:
                        print("\nFBM Inventory:")
                        for item in fbm_items[:10]:  # Show first 10
                            print(f"\nSKU: {item['sku']}")
                            print(f"  ASIN: {item['asin']}")
                            print(f"  Name: {item['product_name'][:50]}...")
                            print(f"  Quantity: {item['quantity']}")
                            print(f"  Price: {item['price']}")
                            print(f"  Condition: {item['condition']}")
                            print(f"  Status: {item['status']}")
                    
                    # Show column headers to understand the data
                    if all_items:
                        print("\n\nAvailable columns in the report:")
                        print(list(all_items[0].keys()))

if __name__ == "__main__":
    test_fbm_inventory()