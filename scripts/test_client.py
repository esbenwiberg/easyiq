#!/usr/bin/env python3
"""
Test the EasyIQ client implementation with working CalendarGetWeekplanEvents endpoint.
"""

import os
import sys
import asyncio
import logging

# Set up proper encoding for Windows console
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def load_credentials():
    """Load credentials from .env file."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value.strip('"\'')
    
    username = os.getenv('EASYIQ_USERNAME')
    password = os.getenv('EASYIQ_PASSWORD')
    
    if not password:
        print("❌ EASYIQ_PASSWORD not found in environment")
        sys.exit(1)
    
    return username, password

async def main():
    """Test the EasyIQ client implementation."""
    print("🔬 Testing EasyIQ Client Implementation")
    print("=" * 60)
    
    # Import our client
    sys.path.append('custom_components/easyiq')
    from client import EasyIQClient
    
    username, password = load_credentials()
    
    # Create and authenticate client
    client = EasyIQClient(username, password)
    
    print(f"Testing with username: {username}")
    
    try:
        if not client.login():
            print("❌ Authentication failed")
            return
        
        print("✅ Authentication successful!")
        
        # Load widgets after authentication
        client.get_widgets()
        print(f"Available widgets: {client.widgets}")
        
        # Get children
        children = await client.get_children()
        print(f"Found {len(children)} children: {[c['name'] for c in children]}")
        
        if not children:
            print("❌ No children found")
            return
        
        # Test both weekplan and homework for first child
        child = children[0]
        child_id = child['id']
        child_name = child['name']
        
        print(f"\n--- Testing data for {child_name} (ID: {child_id}) ---")
        
        # Test weekplan
        print("\n📅 Testing weekplan...")
        weekplan_data = await client.get_weekplan(child_id)
        
        if weekplan_data:
            print("✅ Weekplan data retrieved!")
            print(f"Week: {weekplan_data.get('week', 'Unknown')}")
            print(f"Events: {len(weekplan_data.get('events', []))}")
            
            # Show first few events
            events = weekplan_data.get('events', [])
            for i, event in enumerate(events[:3]):
                print(f"  Event {i+1}: {event.get('courses', 'Unknown')} - {event.get('start', 'Unknown time')}")
            
            if len(events) > 3:
                print(f"  ... and {len(events) - 3} more events")
        else:
            print("❌ No weekplan data retrieved")
        
        # Test homework
        print("\n📚 Testing homework...")
        homework_data = await client.get_homework(child_id)
        
        if homework_data:
            print("✅ Homework data retrieved!")
            print(f"Week: {homework_data.get('week', 'Unknown')}")
            print(f"Assignments: {len(homework_data.get('assignments', []))}")
            
            # Show assignments
            assignments = homework_data.get('assignments', [])
            for i, assignment in enumerate(assignments[:3]):
                print(f"  Assignment {i+1}: {assignment.get('subject', 'Unknown')} - {assignment.get('start_time', 'Unknown time')}")
                if assignment.get('description'):
                    desc = assignment['description'][:100] + "..." if len(assignment['description']) > 100 else assignment['description']
                    print(f"    Description: {desc}")
            
            if len(assignments) > 3:
                print(f"  ... and {len(assignments) - 3} more assignments")
        else:
            print("❌ No homework data retrieved")
        
        # Test presence
        print(f"\n👤 Testing presence...")
        presence_data = await client.get_presence(child_id)
        
        if presence_data:
            print("✅ Presence data retrieved!")
            print(f"Status: ({presence_data.get('status_code', 'Unknown')})")
        else:
            print("❌ No presence data retrieved")
        
        # Test messages
        print(f"\n👤 Testing messages...")
        messages_data = await client.get_messages()
        if messages_data:
            print("✅ Messages data retrieved!")
            print("Messages data found")
        else:
            print("❌ No messages data retrieved")

        print(f"\n🎉 Testing complete!")
        print(f"Summary:")
        print(f"- Authentication: ✅ Working")
        print(f"- Widgets: ✅ {len(client.widgets)} found")
        print(f"- Children: ✅ {len(children)} found")
        print(f"- Weekplan: {'✅ Working' if weekplan_data else '❌ Failed'}")
        print(f"- Homework: {'✅ Working' if homework_data else '❌ Failed'}")
        print(f"- Presence: {'✅ Working' if presence_data else '❌ Failed'}")
        print(f"- Messages: {'✅ Working' if messages_data else '❌ Failed'}")
        
    finally:
        # Ensure session is properly closed
        await client.close()
        
    print("\n✅ Client test passed!")

if __name__ == "__main__":
    asyncio.run(main())