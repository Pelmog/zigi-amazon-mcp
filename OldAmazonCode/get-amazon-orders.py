#!/usr/bin/env python3
"""Standalone Amazon SP-API orders retrieval example."""

import json
import os
from urllib.parse import urlencode

import boto3
import requests
from requests_aws4auth import AWS4Auth


def get_amazon_access_token():
    """Exchange refresh token for access token from Amazon LWA."""
    client_id = os.getenv("LWA_CLIENT_ID")
    client_secret = os.getenv("LWA_CLIENT_SECRET")
    refresh_token = os.getenv("LWA_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        print("Missing required LWA credentials.")
        print("Please set LWA_CLIENT_ID, LWA_CLIENT_SECRET, and LWA_REFRESH_TOKEN environment variables.")
        return None

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
        return token_data["access_token"]
    else:
        print(f"Error getting access token: {response.status_code}, {response.text}")
        return None


def get_aws_credentials():
    """Get AWS temporary credentials by assuming role for Amazon SP-API."""
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")

    if not all([aws_access_key_id, aws_secret_access_key]):
        print("Missing required AWS credentials.")
        print("Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.")
        return None

    # The role ARN to assume
    role_arn = os.getenv("AWS_ROLE_ARN", "arn:aws:iam::295290492609:role/SPapi-Role-2025")

    sts_client = boto3.client(
        "sts",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )

    try:
        assume_response = sts_client.assume_role(RoleArn=role_arn, RoleSessionName="SPapi-Role-2025")

        credentials = assume_response["Credentials"]
        return {
            "AccessKeyId": credentials["AccessKeyId"],
            "SecretAccessKey": credentials["SecretAccessKey"],
            "SessionToken": credentials["SessionToken"],
        }
    except Exception as e:
        print(f"Error assuming role: {e}")
        return None


def get_orders(marketplace_ids="A1F83G8C2ARO7P", created_after="2025-01-01T00:00:00Z"):
    """Retrieve orders from Amazon SP-API."""
    # Get access token
    access_token = get_amazon_access_token()
    if not access_token:
        return

    # Get AWS credentials
    creds = get_aws_credentials()
    if not creds:
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

    # Prepare request parameters
    params = {
        "MarketplaceIds": marketplace_ids.split(","),
        "CreatedAfter": created_after,
    }

    # Headers
    headers = {
        "x-amz-access-token": access_token,
        "user-agent": "ZigiAmazonMCP/1.0 (Language=Python)",
        "content-type": "application/json",
    }

    # Make request
    endpoint = "https://sellingpartnerapi-eu.amazon.com"
    api_path = "/orders/v0/orders"
    url = f"{endpoint}{api_path}?{urlencode(params, doseq=True)}"

    try:
        response = requests.get(url, headers=headers, auth=aws_auth, timeout=30)
        response.raise_for_status()

        result = response.json()
        orders = result.get("payload", {}).get("Orders", [])

        print(f"Retrieved {len(orders)} orders:")
        for order in orders:
            print(f"Order ID: {order.get('AmazonOrderId')}")
            print(
                f"Order Total: {order.get('OrderTotal', {}).get('Amount')} {order.get('OrderTotal', {}).get('CurrencyCode')}"
            )
            print(f"Buyer Name: {order.get('BuyerInfo', {}).get('BuyerName', 'N/A')}")
            print("---")

    except Exception as e:
        print(f"Error retrieving orders: {e}")
        return None
    else:
        return orders


if __name__ == "__main__":
    orders = get_orders()
    if orders:
        print(json.dumps(orders, indent=2))
