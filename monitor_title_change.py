#!/usr/bin/env python3
"""Monitor title change every 30 seconds for 15 minutes."""

import json
import os
import sys
import time
from datetime import datetime, timedelta

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from zigi_amazon_mcp.server import (
    get_auth_token,
    get_listing,
)

# Configuration
SELLER_ID = "A2C259Q0GU1WMI"
TEST_SKU = "JL-BC002"
TARGET_WORD = "Trolly"  # Looking for this word (note the spelling)
CHECK_INTERVAL = 30  # seconds
TOTAL_DURATION = 900  # 15 minutes in seconds


def check_title(auth_token: str, check_number: int):
    """Check current title and return status."""
    try:
        result = get_listing(
            auth_token=auth_token,
            seller_id=SELLER_ID,
            seller_sku=TEST_SKU,
            marketplace_ids="A1F83G8C2ARO7P"
        )
        
        result_data = json.loads(result)
        if result_data.get('success'):
            data = result_data.get('data', {})
            current_title = data.get('title', '')
            
            # Check if the word "Trolly" appears in the title
            has_trolly = TARGET_WORD in current_title
            
            # Also check for "Trolley" to see if it's been changed
            has_trolley = "Trolley" in current_title and "Trolley on Wheels" not in current_title
            
            return {
                'success': True,
                'title': current_title,
                'has_trolly': has_trolly,
                'has_middle_trolley': has_trolley,
                'changed': has_trolly
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


def truncate_title(title: str, max_length: int = 80) -> str:
    """Truncate title for display if too long."""
    if len(title) <= max_length:
        return title
    return title[:max_length-3] + "..."


def main():
    """Monitor title changes."""
    print("\n" + "=" * 100)
    print("TITLE CHANGE MONITORING")
    print("=" * 100)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Monitoring: {TEST_SKU}")
    print(f"Looking for: The word '{TARGET_WORD}' in the title")
    print(f"Check Interval: Every {CHECK_INTERVAL} seconds")
    print(f"Total Duration: {TOTAL_DURATION // 60} minutes")
    print("=" * 100)
    
    # Get auth token
    auth_result = get_auth_token()
    if "Your auth token is:" not in auth_result:
        print("Failed to get auth token")
        return
        
    auth_token = auth_result.split("Your auth token is: ")[1].strip()
    print("✓ Authentication successful\n")
    
    # Initial check to show current title
    print("Checking initial title...")
    initial_result = check_title(auth_token, 0)
    if initial_result['success']:
        print(f"\nCurrent Title:")
        print(f"  {initial_result['title']}")
        print(f"\nContains '{TARGET_WORD}': {'Yes ✓' if initial_result['has_trolly'] else 'No ✗'}")
    print("\n" + "-" * 100)
    
    # Start monitoring
    print("Starting monitoring...")
    print("-" * 100)
    print("Time".ljust(20) + "Check #".ljust(10) + "Status".ljust(20) + "Title Preview")
    print("-" * 100)
    
    start_time = datetime.now()
    end_time = start_time + timedelta(seconds=TOTAL_DURATION)
    check_count = 0
    title_changed = False
    change_detected_at = None
    
    while datetime.now() < end_time:
        check_count += 1
        current_time = datetime.now()
        elapsed = (current_time - start_time).total_seconds()
        
        # Check title
        result = check_title(auth_token, check_count)
        
        # Format output
        time_str = current_time.strftime('%H:%M:%S')
        check_str = f"#{check_count}"
        
        if result['success']:
            title_preview = truncate_title(result['title'], 50)
            
            if result['changed'] and not title_changed:
                # First time detecting change
                title_changed = True
                change_detected_at = current_time
                status_str = "🎉 CHANGED!"
                print(f"{time_str.ljust(20)}{check_str.ljust(10)}{status_str.ljust(20)}{title_preview}")
                print("\n" + "!" * 100)
                print(f"TITLE CHANGE DETECTED at {time_str}!")
                print(f"The word '{TARGET_WORD}' is now present in the title!")
                print(f"Time since update: {elapsed:.0f} seconds ({elapsed/60:.1f} minutes)")
                print("!" * 100 + "\n")
            elif result['changed']:
                status_str = f"✓ Has '{TARGET_WORD}'"
                print(f"{time_str.ljust(20)}{check_str.ljust(10)}{status_str.ljust(20)}{title_preview}")
            else:
                status_str = f"No '{TARGET_WORD}' yet"
                print(f"{time_str.ljust(20)}{check_str.ljust(10)}{status_str.ljust(20)}{title_preview}")
        else:
            error_msg = f"ERROR: {result['error'][:40]}..."
            print(f"{time_str.ljust(20)}{check_str.ljust(10)}{error_msg}")
        
        # Wait for next check (unless it's the last check)
        if datetime.now() < end_time:
            time.sleep(CHECK_INTERVAL)
    
    # Final check
    print("-" * 100)
    final_result = check_title(auth_token, check_count + 1)
    
    # Final summary
    print("\nMONITORING COMPLETE")
    print("=" * 100)
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Checks: {check_count}")
    print(f"Total Duration: {(datetime.now() - start_time).total_seconds():.0f} seconds")
    
    if final_result['success']:
        print(f"\nFinal Title:")
        print(f"  {final_result['title']}")
        print(f"\nContains '{TARGET_WORD}': {'Yes ✓' if final_result['has_trolly'] else 'No ✗'}")
    
    if title_changed:
        time_to_change = (change_detected_at - start_time).total_seconds()
        print(f"\n✅ TITLE CHANGE SUCCESSFUL")
        print(f"   Changed at: {change_detected_at.strftime('%H:%M:%S')}")
        print(f"   Time to change: {time_to_change:.0f} seconds ({time_to_change/60:.1f} minutes)")
    else:
        print(f"\n⏳ Title has not changed yet")
        print(f"   The word '{TARGET_WORD}' was not detected in the title")
        print("   Note: Title changes can sometimes take up to 15-30 minutes")
    
    print("=" * 100)


if __name__ == "__main__":
    main()