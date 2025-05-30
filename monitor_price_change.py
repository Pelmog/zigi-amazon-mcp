#!/usr/bin/env python3
"""Monitor price change every 30 seconds for 10 minutes."""

import json
import os
import sys
import time
from datetime import datetime, timedelta

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from zigi_amazon_mcp.server import (
    get_auth_token,
    get_fbm_inventory,
)

# Configuration
SELLER_ID = "A2C259Q0GU1WMI"
TEST_SKU = "JL-BC002"
OLD_PRICE = "69.98"
NEW_PRICE = "69.96"
CHECK_INTERVAL = 30  # seconds
TOTAL_DURATION = 900  # 10 minutes in seconds


def check_price(auth_token: str, check_number: int):
    """Check current price and return status."""
    try:
        result = get_fbm_inventory(
            auth_token=auth_token,
            seller_id=SELLER_ID,
            seller_sku=TEST_SKU,
            marketplace_ids="A1F83G8C2ARO7P"
        )
        
        result_data = json.loads(result)
        if result_data.get('success'):
            data = result_data.get('data', {})
            current_price = data.get('price', {}).get('amount', 'N/A')
            quantity = data.get('fulfillment_availability', {}).get('quantity', 0)
            
            return {
                'success': True,
                'price': current_price,
                'quantity': quantity,
                'changed': current_price == NEW_PRICE
            }
        else:
            return {
                'success': False,
                'error': result_data.get('message', 'Unknown error')
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def main():
    """Monitor price changes."""
    print("\n" + "=" * 80)
    print("PRICE CHANGE MONITORING")
    print("=" * 80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Monitoring: {TEST_SKU}")
    print(f"Expected Change: £{OLD_PRICE} → £{NEW_PRICE}")
    print(f"Check Interval: Every {CHECK_INTERVAL} seconds")
    print(f"Total Duration: {TOTAL_DURATION // 60} minutes")
    print("=" * 80)
    
    # Get auth token
    auth_result = get_auth_token()
    if "Your auth token is:" not in auth_result:
        print("Failed to get auth token")
        return
        
    auth_token = auth_result.split("Your auth token is: ")[1].strip()
    print("✓ Authentication successful\n")
    
    # Initial check
    print("Starting monitoring...")
    print("-" * 80)
    print("Time".ljust(20) + "Check #".ljust(10) + "Price".ljust(10) + "Status")
    print("-" * 80)
    
    start_time = datetime.now()
    end_time = start_time + timedelta(seconds=TOTAL_DURATION)
    check_count = 0
    price_changed = False
    change_detected_at = None
    
    while datetime.now() < end_time:
        check_count += 1
        current_time = datetime.now()
        elapsed = (current_time - start_time).total_seconds()
        
        # Check price
        result = check_price(auth_token, check_count)
        
        # Format output
        time_str = current_time.strftime('%H:%M:%S')
        check_str = f"#{check_count}"
        
        if result['success']:
            price_str = f"£{result['price']}"
            
            if result['changed'] and not price_changed:
                # First time detecting change
                price_changed = True
                change_detected_at = current_time
                status_str = "🎉 CHANGED!"
                print(f"{time_str.ljust(20)}{check_str.ljust(10)}{price_str.ljust(10)}{status_str}")
                print("\n" + "!" * 80)
                print(f"PRICE CHANGE DETECTED at {time_str}!")
                print(f"Time since update: {elapsed:.0f} seconds ({elapsed/60:.1f} minutes)")
                print("!" * 80 + "\n")
            elif result['changed']:
                status_str = "✓ New price"
                print(f"{time_str.ljust(20)}{check_str.ljust(10)}{price_str.ljust(10)}{status_str}")
            else:
                status_str = "No change"
                print(f"{time_str.ljust(20)}{check_str.ljust(10)}{price_str.ljust(10)}{status_str}")
        else:
            print(f"{time_str.ljust(20)}{check_str.ljust(10)}ERROR".ljust(10) + result['error'])
        
        # Wait for next check (unless it's the last check)
        if datetime.now() < end_time:
            time.sleep(CHECK_INTERVAL)
    
    # Final summary
    print("-" * 80)
    print("\nMONITORING COMPLETE")
    print("=" * 80)
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Checks: {check_count}")
    print(f"Total Duration: {(datetime.now() - start_time).total_seconds():.0f} seconds")
    
    if price_changed:
        time_to_change = (change_detected_at - start_time).total_seconds()
        print(f"\n✅ PRICE CHANGE SUCCESSFUL")
        print(f"   Changed at: {change_detected_at.strftime('%H:%M:%S')}")
        print(f"   Time to change: {time_to_change:.0f} seconds ({time_to_change/60:.1f} minutes)")
    else:
        print(f"\n⏳ Price has not changed yet (still £{OLD_PRICE})")
        print("   Note: Price changes can sometimes take up to 15-30 minutes")
    
    print("=" * 80)


if __name__ == "__main__":
    main()
