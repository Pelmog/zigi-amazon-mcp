#!/usr/bin/env python3
"""Legacy Amazon SP-API integration example."""

import os
import sys

import boto3
import requests

# Load LWA credentials from environment variables
CLIENT_ID = os.getenv("LWA_CLIENT_ID")
CLIENT_SECRET = os.getenv("LWA_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("LWA_REFRESH_TOKEN")

# Check if all required credentials are available
if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
    print("Missing required LWA credentials.")
    print("Please set LWA_CLIENT_ID, LWA_CLIENT_SECRET, and LWA_REFRESH_TOKEN environment variables.")
    sys.exit(1)

# Amazon LWA token endpoint
LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"  # noqa: S105

# Prepare the request data
data = {
    "grant_type": "refresh_token",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "refresh_token": REFRESH_TOKEN,
}

# Request a new access token
response = requests.post(LWA_TOKEN_URL, data=data, timeout=30)
if response.status_code == 200:
    token_json = response.json()
    access_token = token_json["access_token"]
    print(f"Access token: {access_token}")
else:
    print(f"Error: {response.status_code}, {response.text}")
    sys.exit(1)

# AWS credentials for the IAM user (with AssumeRole permissions)
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# Check if all required AWS credentials are available
if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY]):
    print("Missing required AWS credentials.")
    print("Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.")
    sys.exit(1)

# Assume the role
role_arn = "arn:aws:iam::295290492609:role/SPapi-Role-2025"
session_name = "SPapi-Role-2025"

# Create an STS client
sts_client = boto3.client(
    "sts",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

# Assume the role
assume_response = sts_client.assume_role(RoleArn=role_arn, RoleSessionName=session_name)

# Extract the credentials
credentials = assume_response["Credentials"]
aws_access_key = credentials["AccessKeyId"]
aws_secret_key = credentials["SecretAccessKey"]
session_token = credentials["SessionToken"]

print(f"AWS Access Key: {aws_access_key}")
print(f"AWS Secret Key: {aws_secret_key}")
print(f"Session Token: {session_token}")
