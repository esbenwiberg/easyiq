#!/usr/bin/env python3
"""Test both children to see if they get different calendar data."""

import asyncio
import logging
import sys
import os

# Add the custom_components directory to the path
sys.path.append('custom_components/aula-easyiq')
from client import EasyIQClient

# Set up logging
logging.basicConfig(level=logging.INFO)  # Use INFO to reduce noise
_LOGGER = logging.getLogger(__name__)

async def test_both_children():
    """Test both children to see if they get different calendar data."""
    print("🔍 Testing Both Children for Calendar Data Separation")
    print("=" * 60)
    
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
        print(f"👥 Found {len(children)} children")
        
        # Test each child individually
        for i, child in enumerate(children):
            child_id = child.get("id")
            child_name = child.get("name")
            
            print(f"\n{'='*60}")
            print(f"🧒 Testing Child {i+1}: {child_name}")
            print(f"   Primary ID: {child_id}")
            
            # Get the actual ID for API calls
            child_data = client._children_data.get(child_id)
            if child_data:
                actual_id = child_data.get("id")
                print(f"   Actual ID: {actual_id}")
            
            print(f"{'='*60}")
            
            # Get calendar events for this specific child
            print(f"📅 Getting calendar events for {child_name}...")
            events = await client.get_calendar_events_for_business_days(child_id, 5)
            
            print(f"📊 Total events: {len(events)}")
            
            # Separate by type
            weekplan_events = [event for event in events if event.get("itemType") == 9]
            homework_events = [event for event in events if event.get("itemType") == 4]
            
            print(f"📋 Weekplan events: {len(weekplan_events)}")
            print(f"🏠 Homework events: {len(homework_events)}")
            
            # Create unique signatures for comparison
            weekplan_signatures = set()
            homework_signatures = set()
            
            for event in weekplan_events:
                signature = f"{event.get('start', '')}-{event.get('courses', '')}-{event.get('activities', '')}"
                weekplan_signatures.add(signature)
            
            for event in homework_events:
                signature = f"{event.get('start', '')}-{event.get('courses', '')}-{event.get('activities', '')}"
                homework_signatures.add(signature)
            
            print(f"📋 Unique weekplan signatures: {len(weekplan_signatures)}")
            print(f"🏠 Unique homework signatures: {len(homework_signatures)}")
            
            # Show sample events
            if weekplan_events:
                print(f"\n📋 Sample weekplan events for {child_name}:")
                for j, event in enumerate(weekplan_events[:3]):
                    print(f"   {j+1}. {event.get('courses', 'Unknown')} at {event.get('start', 'Unknown')}")
                    print(f"      Activities: {event.get('activities', 'None')}")
            
            if homework_events:
                print(f"\n🏠 Sample homework events for {child_name}:")
                for j, event in enumerate(homework_events[:3]):
                    print(f"   {j+1}. {event.get('courses', 'Unknown')} at {event.get('start', 'Unknown')}")
                    print(f"      Activities: {event.get('activities', 'None')}")
            
            # Store data for comparison
            if i == 0:
                child1_weekplan_sigs = weekplan_signatures.copy()
                child1_homework_sigs = homework_signatures.copy()
                child1_name = child_name
            elif i == 1:
                child2_weekplan_sigs = weekplan_signatures.copy()
                child2_homework_sigs = homework_signatures.copy()
                child2_name = child_name
        
        # Compare data between children
        if len(children) >= 2:
            print(f"\n{'='*60}")
            print("🔍 COMPARISON BETWEEN CHILDREN")
            print(f"{'='*60}")
            
            weekplan_overlap = child1_weekplan_sigs & child2_weekplan_sigs
            homework_overlap = child1_homework_sigs & child2_homework_sigs
            
            print(f"📋 {child1_name} weekplan events: {len(child1_weekplan_sigs)}")
            print(f"📋 {child2_name} weekplan events: {len(child2_weekplan_sigs)}")
            print(f"📋 Weekplan overlap: {len(weekplan_overlap)} events")
            
            print(f"\n🏠 {child1_name} homework events: {len(child1_homework_sigs)}")
            print(f"🏠 {child2_name} homework events: {len(child2_homework_sigs)}")
            print(f"🏠 Homework overlap: {len(homework_overlap)} events")
            
            if weekplan_overlap:
                print(f"\n⚠️  WEEKPLAN OVERLAP DETECTED:")
                for sig in list(weekplan_overlap)[:5]:
                    print(f"   - {sig}")
            
            if homework_overlap:
                print(f"\n⚠️  HOMEWORK OVERLAP DETECTED:")
                for sig in list(homework_overlap)[:5]:
                    print(f"   - {sig}")
            
            # Final verdict
            print(f"\n{'='*60}")
            if weekplan_overlap or homework_overlap:
                print("❌ PROBLEM CONFIRMED: Children are getting overlapping calendar data!")
                print("   This explains why both children show the same events in Home Assistant.")
            else:
                print("✅ SUCCESS: Children have completely separate calendar data!")
                print("   The issue might be elsewhere in the Home Assistant integration.")
            print(f"{'='*60}")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_both_children())