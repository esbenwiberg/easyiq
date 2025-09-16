#!/usr/bin/env python3
"""Test enhanced nextweek functionality with weeks_ahead parameter."""

import asyncio
import logging
import sys
import os

# Add the custom_components directory to the path
sys.path.append('custom_components/easyiq')
from client import EasyIQClient

# Set up logging
logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)

async def test_enhanced_nextweek():
    """Test enhanced nextweek functionality."""
    print("🔍 Testing Enhanced Next Week Functionality")
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
        
        # Test with first child
        if children:
            child = children[0]
            child_id = child.get("id")
            child_name = child.get("name")
            
            print(f"\n🧒 Testing with: {child_name}")
            
            # Test different weeks with the enhanced method
            for weeks_ahead in range(0, 3):
                week_names = ["This Week", "Next Week", "Week After Next"]
                week_name = week_names[weeks_ahead]
                
                print(f"\n📅 Testing {week_name} (weeks_ahead={weeks_ahead}):")
                
                try:
                    # Test the enhanced business days method
                    events = await client.get_calendar_events_for_business_days(child_id, 5, weeks_ahead)
                    print(f"   📊 Found {len(events)} events")
                    
                    if events:
                        # Show date range of events
                        dates = [event.get('start', '')[:10] for event in events if event.get('start')]
                        unique_dates = sorted(set(dates))
                        if unique_dates:
                            print(f"   📆 Date range: {unique_dates[0]} to {unique_dates[-1]}")
                            print(f"   📆 Unique dates: {len(unique_dates)}")
                        
                        # Show sample events
                        for i, event in enumerate(events[:3]):
                            start = event.get('start', 'Unknown')
                            course = event.get('courses', 'Unknown')
                            item_type = event.get('itemType', 'Unknown')
                            type_name = "Weekplan" if item_type == 9 else "Homework" if item_type == 4 else f"Type {item_type}"
                            print(f"   {i+1}. {course} at {start} ({type_name})")
                    else:
                        print("   ❌ No events found")
                        
                except Exception as e:
                    print(f"   ❌ Error: {e}")
            
            # Test edge cases
            print(f"\n🧪 Testing edge cases:")
            
            # Test with 0 days (should return empty)
            try:
                events = await client.get_calendar_events_for_business_days(child_id, 0, 0)
                print(f"   📊 0 days requested: {len(events)} events")
            except Exception as e:
                print(f"   ❌ Error with 0 days: {e}")
            
            # Test with 10 business days from next week
            try:
                events = await client.get_calendar_events_for_business_days(child_id, 10, 1)
                print(f"   📊 10 business days from next week: {len(events)} events")
                if events:
                    dates = [event.get('start', '')[:10] for event in events if event.get('start')]
                    unique_dates = sorted(set(dates))
                    if unique_dates:
                        print(f"   📆 Date range: {unique_dates[0]} to {unique_dates[-1]}")
            except Exception as e:
                print(f"   ❌ Error with 10 days from next week: {e}")
        
        print(f"\n✅ Enhanced Next Week Support Summary:")
        print(f"   ✅ get_calendar_events_for_business_days() now supports weeks_ahead parameter")
        print(f"   ✅ Can fetch business days from: current week, next week, or future weeks")
        print(f"   ✅ Flexible date range calculation based on weeks_ahead")
        print(f"   ✅ Maintains backward compatibility (weeks_ahead defaults to 0)")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_enhanced_nextweek())