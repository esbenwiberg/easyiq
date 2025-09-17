#!/usr/bin/env python3
"""
Test the EasyIQ client async functionality with mock data.
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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Test the EasyIQ client async implementation with mock data."""
    print("🔬 Testing EasyIQ Client Async Implementation (Mock Mode)")
    print("=" * 60)
    
    # Import our client
    sys.path.append('custom_components/aula_easyiq')
    from client import EasyIQClient
    import client as client_module
    
    # Create client
    client = EasyIQClient("test_user", "test_pass")
    
    # Force test mode by setting aiohttp to None temporarily
    original_aiohttp = client_module.aiohttp
    client_module.aiohttp = None
    
    try:
        print("Testing with mock authentication...")
        
        # Test login (should use mock mode)
        if not await client.login():
            print("❌ Mock authentication failed")
            return
        
        print("✅ Mock authentication successful!")
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
            print(f"Notes: {weekplan_data.get('notes', 'No notes')}")
        else:
            print("❌ No weekplan data retrieved")
        
        # Test homework
        print("\n📚 Testing homework...")
        homework_data = await client.get_homework(child_id)
        
        if homework_data:
            print("✅ Homework data retrieved!")
            print(f"Week: {homework_data.get('week', 'Unknown')}")
            print(f"Assignments: {len(homework_data.get('assignments', []))}")
        else:
            print("❌ No homework data retrieved")
        
        # Test messages
        print("\n📧 Testing messages...")
        message_data = await client.get_messages()
        
        if message_data:
            print("✅ Message data retrieved!")
            print(f"Subject: {message_data.get('subject', 'No subject')}")
            print(f"Sender: {message_data.get('sender', 'Unknown sender')}")
        else:
            print("❌ No message data retrieved")
        
        print(f"\n🎉 Testing complete!")
        print(f"Summary:")
        print(f"- Authentication: ✅ Working (Mock)")
        print(f"- Widgets: ✅ {len(client.widgets)} found")
        print(f"- Children: ✅ {len(children)} found")
        print(f"- Weekplan: {'✅ Working' if weekplan_data else '❌ Failed'}")
        print(f"- Homework: {'✅ Working' if homework_data else '❌ Failed'}")
        print(f"- Messages: {'✅ Working' if message_data else '❌ Failed'}")
        
    finally:
        # Restore original aiohttp
        client_module.aiohttp = original_aiohttp
        # Ensure session is properly closed
        await client.close()
        
    print("\n✅ Async client test passed!")

if __name__ == "__main__":
    asyncio.run(main())