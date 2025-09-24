#!/usr/bin/env python3
"""Test script for the new presence API implementation."""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add the custom_components directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'aula_easyiq'))

from client import EasyIQClient

async def test_presence_api():
    """Test the presence API functionality."""
    
    # Load credentials from environment or .env file
    username = os.getenv('AULA_USERNAME')
    password = os.getenv('AULA_PASSWORD')
    
    if not username or not password:
        print("Please set AULA_USERNAME and AULA_PASSWORD environment variables")
        return
    
    print("Testing new presence API implementation...")
    print(f"Username: {username}")
    print("-" * 50)
    
    # Create client and authenticate
    client = EasyIQClient(username, password)
    
    try:
        print("Authenticating...")
        await client.authenticate()
        
        if not client._authenticated:
            print("❌ Authentication failed")
            return
        
        print("✅ Authentication successful")
        
        # Get children
        print("\nFetching children...")
        children = await client.get_children()
        
        if not children:
            print("❌ No children found")
            return
        
        print(f"✅ Found {len(children)} children")
        
        # Test presence for each child
        for child_id, child_name in children.items():
            print(f"\n--- Testing presence for {child_name} (ID: {child_id}) ---")
            
            presence_data = await client.get_presence(child_id)
            
            if presence_data:
                print("✅ Presence data retrieved:")
                print(f"  Status: {presence_data.get('status', 'N/A')}")
                print(f"  Status Code: {presence_data.get('status_code', 'N/A')}")
                print(f"  Check In: {presence_data.get('check_in_time', 'N/A')}")
                print(f"  Check Out: {presence_data.get('check_out_time', 'N/A')}")
                print(f"  Entry Time: {presence_data.get('entry_time', 'N/A')}")
                print(f"  Exit Time: {presence_data.get('exit_time', 'N/A')}")
                print(f"  Comment: {presence_data.get('comment', 'N/A')}")
                print(f"  Exit With: {presence_data.get('exit_with', 'N/A')}")
                
                # Format like the screenshot
                print("\n📱 Display format (like screenshot):")
                status_code = presence_data.get('status_code', 0)
                if status_code == 8:  # HENTET/GÅET
                    print("Status: Gået")
                elif status_code == 3:  # KOMMET/TIL STEDE
                    print("Status: Til stede")
                else:
                    print(f"Status: {presence_data.get('status', 'N/A')}")
                
                if presence_data.get('check_in_time'):
                    print(f"Kom: kl. {presence_data.get('check_in_time')}")
                
                if presence_data.get('check_out_time'):
                    print(f"Gik: kl. {presence_data.get('check_out_time')}")
                
                if presence_data.get('exit_time'):
                    print(f"Send hjem: kl. {presence_data.get('exit_time')}")
                
                if presence_data.get('comment'):
                    print("Bemærkninger:")
                    print(presence_data.get('comment'))
                
            else:
                print("❌ No presence data retrieved")
    
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_presence_api())