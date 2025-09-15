#!/usr/bin/env python3
"""Comprehensive diagnostic script for EasyIQ integration issues."""

import asyncio
import logging
import sys
import os
import json

# Add the custom_components path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components'))

from custom_components.easyiq.client import EasyIQClient

# Set up comprehensive debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
_LOGGER = logging.getLogger(__name__)

# Enable debug logging for all EasyIQ components
logging.getLogger('custom_components.easyiq').setLevel(logging.DEBUG)
logging.getLogger('custom_components.easyiq.client').setLevel(logging.DEBUG)
logging.getLogger('custom_components.easyiq.sensor').setLevel(logging.DEBUG)
logging.getLogger('custom_components.easyiq.binary_sensor').setLevel(logging.DEBUG)

async def diagnose_integration():
    """Comprehensive diagnosis of integration issues."""
    print("🔍 EasyIQ Integration Diagnostic Tool")
    print("=" * 50)
    
    # Get credentials
    username = input("Enter username: ")
    password = input("Enter password: ")
    
    client = EasyIQClient(username, password)
    
    try:
        print("\n1️⃣ Testing Authentication...")
        if not await client.authenticate():
            print("❌ Authentication failed - check credentials")
            return
        print("✅ Authentication successful")
        
        print("\n2️⃣ Analyzing Children Data...")
        children = client.children
        print(f"Found {len(children)} children:")
        for i, child in enumerate(children, 1):
            print(f"  {i}. {child.get('name')} (ID: {child.get('id')})")
        
        print("\n3️⃣ Checking Child Data Mapping...")
        print("Children data structure:")
        for key, value in client._children_data.items():
            print(f"  Key: {key} -> {value}")
        
        print("\n4️⃣ Testing Calendar Events for Each Child...")
        for child in children:
            child_id = child.get("id")
            child_name = child.get("name")
            print(f"\n--- Testing {child_name} (ID: {child_id}) ---")
            
            # Test direct calendar events
            try:
                events = await client._get_calendar_events(child_id, 0)
                print(f"  Direct events: {len(events)}")
                if events:
                    # Show unique courses to check for duplication
                    courses = set(event.get('courses', 'Unknown') for event in events)
                    print(f"  Unique courses: {list(courses)[:5]}...")  # Show first 5
            except Exception as e:
                print(f"  ❌ Direct events failed: {e}")
            
            # Test business day events
            try:
                business_events = await client.get_calendar_events_for_business_days(child_id, 5)
                print(f"  Business day events: {len(business_events)}")
            except Exception as e:
                print(f"  ❌ Business day events failed: {e}")
        
        print("\n5️⃣ Testing Full Data Update...")
        try:
            await client.update_data()
            print("✅ Data update successful")
            
            print("\n6️⃣ Analyzing Final Data Structure...")
            print(f"Weekplan data keys: {list(client.weekplan_data.keys())}")
            print(f"Homework data keys: {list(client.homework_data.keys())}")
            print(f"Presence data keys: {list(client.presence_data.keys())}")
            
            # Check for data duplication
            print("\n7️⃣ Checking for Data Duplication...")
            for child in children:
                child_id = child.get("id")
                child_name = child.get("name")
                
                weekplan = client.weekplan_data.get(child_id, {})
                events = weekplan.get('events', [])
                
                if events:
                    # Get unique event signatures
                    event_signatures = set()
                    for event in events:
                        signature = f"{event.get('start', '')}-{event.get('courses', '')}"
                        event_signatures.add(signature)
                    
                    print(f"  {child_name}: {len(events)} events, {len(event_signatures)} unique")
                    
                    # Show sample events
                    for i, event in enumerate(events[:3]):
                        print(f"    Event {i+1}: {event.get('courses', 'Unknown')} at {event.get('start', 'Unknown')}")
                else:
                    print(f"  {child_name}: No events found")
            
            print("\n8️⃣ Testing Presence Data...")
            for child in children:
                child_id = child.get("id")
                child_name = child.get("name")
                
                presence = client.presence_data.get(child_id, {})
                print(f"  {child_name}: {presence.get('status', 'No status')}")
            
            print("\n9️⃣ Testing Messages...")
            print(f"Messages: {client.message}")
            print(f"Unread count: {client.unread_messages}")
            
        except Exception as e:
            print(f"❌ Data update failed: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n🎯 Diagnosis Summary:")
        print("=" * 30)
        
        # Check for common issues
        if len(children) == 0:
            print("❌ No children found - check authentication or account setup")
        elif len(set(child.get('id') for child in children)) != len(children):
            print("❌ Duplicate child IDs detected")
        else:
            print("✅ Children data looks good")
        
        # Check data mapping
        if len(client._children_data) != len(children):
            print("❌ Child data mapping mismatch")
        else:
            print("✅ Child data mapping looks good")
        
        # Check for data
        if not client.weekplan_data:
            print("❌ No weekplan data - check API calls")
        else:
            print("✅ Weekplan data present")
        
        if not client.presence_data:
            print("❌ No presence data - check presence logic")
        else:
            print("✅ Presence data present")
        
        print("\n✅ Diagnosis complete! Check the output above for issues.")
        
    except Exception as e:
        print(f"❌ Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(diagnose_integration())