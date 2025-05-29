#!/usr/bin/env python3
"""Test script to explore Reports API for inventory reports."""

import json
import os
from urllib.parse import urlencode
import requests
from dotenv import load_dotenv
from requests_aws4auth import AWS4Auth
import boto3
from datetime import datetime, timedelta

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

def test_reports_api():
    """Test the Reports API to get available reports."""
    print("Testing Reports API for inventory reports...")
    
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
    
    # First, let's list available report types
    endpoint = "https://sellingpartnerapi-eu.amazon.com"
    
    # Get reports created in the last 7 days
    created_since = (datetime.utcnow() - timedelta(days=7)).isoformat() + "Z"
    
    # List existing reports
    api_path = "/reports/2021-06-30/reports"
    params = {
        "marketplaceIds": "A1F83G8C2ARO7P",  # UK marketplace
        "createdSince": created_since,
        "reportTypes": "GET_MERCHANT_LISTINGS_ALL_DATA,GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA,GET_FLAT_FILE_OPEN_LISTINGS_DATA"
    }
    
    url = f"{endpoint}{api_path}?{urlencode(params, doseq=True)}"
    
    print(f"\nListing existing reports...")
    print(f"Parameters: {params}")
    
    try:
        response = requests.get(url, headers=headers, auth=aws_auth, timeout=30)
        
        print(f"\nResponse status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            reports = data.get("reports", [])
            
            print(f"\nFound {len(reports)} reports")
            
            for report in reports[:5]:  # Show first 5 reports
                print(f"\nReport ID: {report.get('reportId')}")
                print(f"  Type: {report.get('reportType')}")
                print(f"  Status: {report.get('processingStatus')}")
                print(f"  Created: {report.get('createdTime')}")
                
        else:
            print(f"\nError response: {response.text}")
            
        # Now try to create a merchant listings report
        print("\n\n--- Creating a merchant listings report ---")
        
        api_path = "/reports/2021-06-30/reports"
        
        report_request = {
            "reportType": "GET_MERCHANT_LISTINGS_ALL_DATA",
            "marketplaceIds": ["A1F83G8C2ARO7P"],
        }
        
        print(f"\nCreating report with type: {report_request['reportType']}")
        
        response = requests.post(
            f"{endpoint}{api_path}",
            headers=headers,
            auth=aws_auth,
            json=report_request,
            timeout=30
        )
        
        print(f"\nResponse status: {response.status_code}")
        
        if response.status_code in [200, 202]:
            data = response.json()
            print("\nReport creation response:")
            print(json.dumps(data, indent=2))
        else:
            print(f"\nError response: {response.text}")
            
    except Exception as e:
        print(f"\nException occurred: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_reports_api()