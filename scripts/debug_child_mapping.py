#!/usr/bin/env python3
"""Debug script to check child ID mapping."""

import asyncio
import logging
import sys
import os

# Add the custom_components directory to the path
sys.path.append('custom_components/aula-easyiq')
from client import EasyIQClient

# Set up logging
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

async def debug_child_mapping():
    """Debug child ID mapping."""
    print("🔍 Debugging Child ID Mapping")
    print("=" * 50)
    
    # Load credentials
    try:
        with open('.env', 'r') as f:
            lines = f.readlines()
            username = None
            password = None
            for line in lines:
                if line.startswith('EASYIQ_USERNAME='):
                    username = line.split('=', 1)[1].strip().strip('"')
                elif line.startswith('EASYIQ_PASSWORD='):
                    password = line.split('=', 1)[1].strip().strip('"')
    except FileNotFoundError:
        print("❌ .env file not found. Please create it with EASYIQ_USERNAME and EASYIQ_PASSWORD")
        return
    
    if not username or not password:
        print("❌ Username or password not found in scripts/.env file")
        return
    
    # Initialize client
    client = EasyIQClient(username, password)
    
    try:
        # Authenticate
        print("🔐 Authenticating...")
        success = await client.authenticate()
        if not success:
            print("❌ Authentication failed")
            return
        print("✅ Authentication successful")
        
        # Get children
        children = await client.get_children()
        print(f"👥 Found {len(children)} children:")
        
        for i, child in enumerate(children):
            child_id = child.get("id")  # This is the userId
            child_name = child.get("name")
            print(f"  {i+1}. {child_name}")
            print(f"     Primary ID (userId): {child_id}")
            
            # Get the actual child data from the mapping
            child_data = client._children_data.get(child_id)
            if child_data:
                actual_id = child_data.get("id")
                user_id = child_data.get("userId")
                print(f"     Actual ID (for API): {actual_id}")
                print(f"     User ID: {user_id}")
                print(f"     Mapping: userId({child_id}) -> actual_id({actual_id})")
            else:
                print(f"     ❌ No mapping found for {child_id}")
            print()
        
        # Check for duplicate actual IDs
        actual_ids = []
        for child in children:
            child_id = child.get("id")
            child_data = client._children_data.get(child_id)
            if child_data:
                actual_id = child_data.get("id")
                actual_ids.append(actual_id)
        
        print("🔍 Checking for duplicate actual IDs...")
        unique_actual_ids = set(actual_ids)
        
        if len(actual_ids) != len(unique_actual_ids):
            print("❌ DUPLICATE ACTUAL IDs DETECTED!")
            print(f"   Total children: {len(actual_ids)}")
            print(f"   Unique actual IDs: {len(unique_actual_ids)}")
            print(f"   Actual IDs: {actual_ids}")
            print("   This explains why both children get the same calendar data!")
        else:
            print("✅ All children have unique actual IDs")
            print(f"   Actual IDs: {actual_ids}")
        
        # Show the complete children data structure
        print("\n📊 Complete children data structure:")
        print("-" * 50)
        print(f"_children_data keys: {list(client._children_data.keys())}")
        for key, data in client._children_data.items():
            print(f"  {key}: {data}")
        
    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_child_mapping())