#!/usr/bin/env python3
"""Debug script to test calendar child separation issue."""

import asyncio
import logging
import sys
import os

# Add the custom_components directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components'))

from easyiq.client import EasyIQClient

# Set up logging
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

async def debug_calendar_separation():
    """Debug calendar child separation."""
    print("🔍 Debugging Calendar Child Separation")
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
        print("❌ Username or password not found in .env file")
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
            print(f"  {i+1}. {child.get('name')} (ID: {child.get('id')})")
        
        if len(children) < 2:
            print("⚠️  Need at least 2 children to test separation")
            return
        
        print("\n🔍 Testing child-specific data separation...")
        print("-" * 50)
        
        # Test each child individually
        for i, child in enumerate(children):
            child_id = child.get("id")
            child_name = child.get("name")
            
            print(f"\n📚 Testing Child {i+1}: {child_name} (ID: {child_id})")
            
            # Get events for this specific child
            events = await client.get_calendar_events_for_business_days(child_id, 5)
            
            print(f"  📅 Total events: {len(events)}")
            
            # Separate by type
            weekplan_events = [event for event in events if event.get("itemType") == 9]
            homework_events = [event for event in events if event.get("itemType") == 4]
            
            print(f"  📋 Weekplan events: {len(weekplan_events)}")
            print(f"  🏠 Homework events: {len(homework_events)}")
            
            # Show sample events with unique identifiers
            if weekplan_events:
                print("  📋 Sample weekplan events:")
                for j, event in enumerate(weekplan_events[:3]):
                    event_id = f"{event.get('start', '')}-{event.get('courses', '')}"
                    print(f"    {j+1}. {event.get('courses', 'Unknown')} at {event.get('start', 'Unknown')} (ID: {event_id})")
            
            if homework_events:
                print("  🏠 Sample homework events:")
                for j, event in enumerate(homework_events[:3]):
                    event_id = f"{event.get('start', '')}-{event.get('courses', '')}"
                    print(f"    {j+1}. {event.get('courses', 'Unknown')} at {event.get('start', 'Unknown')} (ID: {event_id})")
        
        # Now test the coordinator data structure
        print("\n🔄 Testing coordinator data structure...")
        print("-" * 50)
        
        # Simulate the update_data method
        await client.update_data()
        
        print(f"📊 Weekplan data keys: {list(client.weekplan_data.keys())}")
        print(f"📊 Homework data keys: {list(client.homework_data.keys())}")
        
        # Check if data is properly separated
        for child in children:
            child_id = child.get("id")
            child_name = child.get("name")
            
            weekplan_data = client.weekplan_data.get(child_id, {})
            homework_data = client.homework_data.get(child_id, {})
            
            weekplan_events = weekplan_data.get('events', [])
            homework_assignments = homework_data.get('assignments', [])
            
            print(f"\n👤 {child_name} (ID: {child_id}):")
            print(f"  📋 Weekplan events in coordinator: {len(weekplan_events)}")
            print(f"  🏠 Homework assignments in coordinator: {len(homework_assignments)}")
            
            # Show unique event signatures to detect duplicates
            if weekplan_events:
                signatures = set()
                for event in weekplan_events:
                    signature = f"{event.get('start', '')}-{event.get('courses', '')}"
                    signatures.add(signature)
                print(f"  📋 Unique weekplan signatures: {len(signatures)}")
                
                # Show first few signatures
                for j, sig in enumerate(list(signatures)[:3]):
                    print(f"    {j+1}. {sig}")
            
            if homework_assignments:
                signatures = set()
                for assignment in homework_assignments:
                    signature = f"{assignment.get('start_time', '')}-{assignment.get('title', '')}"
                    signatures.add(signature)
                print(f"  🏠 Unique homework signatures: {len(signatures)}")
                
                # Show first few signatures
                for j, sig in enumerate(list(signatures)[:3]):
                    print(f"    {j+1}. {sig}")
        
        # Final comparison
        print("\n🔍 Cross-child comparison...")
        print("-" * 50)
        
        if len(children) >= 2:
            child1_id = children[0].get("id")
            child2_id = children[1].get("id")
            
            child1_weekplan = client.weekplan_data.get(child1_id, {}).get('events', [])
            child2_weekplan = client.weekplan_data.get(child2_id, {}).get('events', [])
            
            child1_homework = client.homework_data.get(child1_id, {}).get('assignments', [])
            child2_homework = client.homework_data.get(child2_id, {}).get('assignments', [])
            
            # Create signatures for comparison
            child1_weekplan_sigs = {f"{e.get('start', '')}-{e.get('courses', '')}" for e in child1_weekplan}
            child2_weekplan_sigs = {f"{e.get('start', '')}-{e.get('courses', '')}" for e in child2_weekplan}
            
            child1_homework_sigs = {f"{a.get('start_time', '')}-{a.get('title', '')}" for a in child1_homework}
            child2_homework_sigs = {f"{a.get('start_time', '')}-{a.get('title', '')}" for a in child2_homework}
            
            weekplan_overlap = child1_weekplan_sigs & child2_weekplan_sigs
            homework_overlap = child1_homework_sigs & child2_homework_sigs
            
            print(f"📋 Weekplan events overlap: {len(weekplan_overlap)} out of {len(child1_weekplan_sigs)} vs {len(child2_weekplan_sigs)}")
            print(f"🏠 Homework events overlap: {len(homework_overlap)} out of {len(child1_homework_sigs)} vs {len(child2_homework_sigs)}")
            
            if weekplan_overlap:
                print("⚠️  WEEKPLAN OVERLAP DETECTED:")
                for sig in list(weekplan_overlap)[:5]:
                    print(f"    - {sig}")
            
            if homework_overlap:
                print("⚠️  HOMEWORK OVERLAP DETECTED:")
                for sig in list(homework_overlap)[:5]:
                    print(f"    - {sig}")
            
            if not weekplan_overlap and not homework_overlap:
                print("✅ NO OVERLAP - Data is properly separated!")
            else:
                print("❌ OVERLAP DETECTED - This is the bug!")
        
    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_calendar_separation())