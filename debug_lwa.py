#!/usr/bin/env python3
"""Debug script to test LWA token refresh directly."""

import os

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_lwa_refresh():
    """Test LWA token refresh with current credentials."""
    client_id = os.getenv("LWA_CLIENT_ID")
    client_secret = os.getenv("LWA_CLIENT_SECRET")
    refresh_token = os.getenv("LWA_REFRESH_TOKEN")

    print(f"CLIENT_ID: {client_id}")
    print(f"CLIENT_SECRET: {client_secret}")
    print(f"REFRESH_TOKEN: {refresh_token}")
    print()

    lwa_url = "https://api.amazon.com/auth/o2/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }

    print(f"Making request to: {lwa_url}")
    print(f"Request data: {data}")
    print()

    try:
        response = requests.post(lwa_url, data=data, timeout=30)
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        print(f"Response text: {response.text}")
        print()

        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            print(f"SUCCESS! Access token: {access_token[:50]}...")
            return access_token
        else:
            print("FAILED! Non-200 status code")
            try:
                error_data = response.json()
                print(f"Error details: {error_data}")
            except:
                print("Could not parse error response as JSON")
            return None

    except Exception as e:
        print(f"Exception occurred: {e}")
        return None


if __name__ == "__main__":
    test_lwa_refresh()
