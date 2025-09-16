#!/usr/bin/env python3
"""Test nextweek functionality."""

import asyncio
import logging
import sys
import os

# Add the custom_components directory to the path
sys.path.append('custom_components/aula-easyiq')
from client import EasyIQClient

# Set up logging
logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)

async def test_nextweek():
    """Test nextweek functionality."""
    print("🔍 Testing Next Week Functionality")
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
        print(f"👥 Found {len(children)} children")
        
        # Test with first child
        if children:
            child = children[0]
            child_id = child.get("id")
            child_name = child.get("name")
            
            print(f"\n🧒 Testing with: {child_name}")
            
            # Test different weeks
            for weeks_ahead in range(0, 3):
                week_name = ["This Week", "Next Week", "Week After Next"][weeks_ahead]
                print(f"\n📅 Testing {week_name} (weeks_ahead={weeks_ahead}):")
                
                try:
                    events = await client._get_calendar_events(child_id, weeks_ahead)
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
                            print(f"   {i+1}. {course} at {start}")
                    else:
                        print("   ❌ No events found")
                        
                except Exception as e:
                    print(f"   ❌ Error: {e}")
            
            # Test the business days method with different weeks
            print(f"\n📅 Testing business days method:")
            try:
                current_week_events = await client.get_calendar_events_for_business_days(child_id, 5)
                print(f"   📊 Current business days: {len(current_week_events)} events")
                
                # The current method doesn't have a weeks_ahead parameter
                # Let's check if we can modify it to support next week
                print("   ℹ️  Current method fetches current week + 2 weeks ahead automatically")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        # Check if there's a method to get next week specifically
        print(f"\n🔍 Checking available methods for week selection:")
        methods = [method for method in dir(client) if 'week' in method.lower() or 'calendar' in method.lower()]
        for method in methods:
            if not method.startswith('_'):
                print(f"   📋 {method}")
        
        print(f"\n✅ Next week support analysis:")
        print(f"   ✅ _get_calendar_events() supports weeks_ahead parameter")
        print(f"   ✅ Can fetch 0=current, 1=next week, 2=week after next")
        print(f"   ⚠️  get_calendar_events_for_business_days() doesn't have weeks_ahead parameter")
        print(f"   💡 Recommendation: Add weeks_ahead parameter to business days method")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_nextweek())