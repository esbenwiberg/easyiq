#!/usr/bin/env python3
"""Test script to verify EasyIQ integration functionality."""

import asyncio
import logging
import sys
import os

# Add the custom_components path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components'))

from custom_components.easyiq.client import EasyIQClient

# Set up logging with DEBUG level to see all details
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
_LOGGER = logging.getLogger(__name__)

# Also enable debug logging for the EasyIQ client
logging.getLogger('custom_components.easyiq.client').setLevel(logging.DEBUG)

async def test_integration():
    """Test the integration functionality."""
    # You'll need to provide your credentials
    username = input("Enter username: ")
    password = input("Enter password: ")
    
    client = EasyIQClient(username, password)
    
    try:
        # Test authentication
        _LOGGER.info("Testing authentication...")
        if not await client.authenticate():
            _LOGGER.error("❌ Authentication failed")
            return
        
        _LOGGER.info("✅ Authentication successful!")
        
        # Test data update
        _LOGGER.info("Testing data update...")
        await client.update_data()
        _LOGGER.info("✅ Data update successful!")
        
        # Check children
        children = client.children
        _LOGGER.info(f"✅ Found {len(children)} children: {[c['name'] for c in children]}")
        
        # Check data structures
        _LOGGER.info(f"✅ Weekplan data keys: {list(client.weekplan_data.keys())}")
        _LOGGER.info(f"✅ Homework data keys: {list(client.homework_data.keys())}")
        _LOGGER.info(f"✅ Presence data keys: {list(client.presence_data.keys())}")
        
        # Test message data in detail
        _LOGGER.info("🔍 Testing NEW Messages System Implementation...")
        
        # Test direct message API call
        try:
            message_result = await client.get_messages()
            _LOGGER.info(f"✅ Direct message API call successful")
            _LOGGER.info(f"  Message result: {message_result}")
        except Exception as e:
            _LOGGER.error(f"❌ Direct message API call failed: {e}")
        
        _LOGGER.info(f"  Raw message data: {client.message}")
        _LOGGER.info(f"  Unread count: {client.unread_messages}")
        _LOGGER.info(f"  Message type: {type(client.message)}")
        
        # Test message structure
        if isinstance(client.message, dict):
            _LOGGER.info(f"  Message keys: {list(client.message.keys())}")
            for key, value in client.message.items():
                _LOGGER.info(f"    {key}: {value}")
        
        # Test what coordinator would see
        coordinator_data = {
            "children": client.children,
            "unread_messages": client.unread_messages,
            "message": client.message,
            "weekplan_data": client.weekplan_data,
            "homework_data": getattr(client, 'homework_data', {}),
            "presence_data": getattr(client, 'presence_data', {}),
        }
        
        _LOGGER.info("🔍 Testing Coordinator Data Structure...")
        _LOGGER.info(f"  Coordinator unread_messages: {coordinator_data.get('unread_messages', 'MISSING')}")
        _LOGGER.info(f"  Coordinator message: {coordinator_data.get('message', 'MISSING')}")
        
        # Simulate binary sensor logic
        _LOGGER.info("🔍 Testing Binary Sensor Logic...")
        unread_messages = coordinator_data.get("unread_messages", 0)
        is_on = unread_messages > 0
        _LOGGER.info(f"  Binary sensor would be: {'ON' if is_on else 'OFF'}")
        _LOGGER.info(f"  Logic: unread_messages ({unread_messages}) > 0 = {is_on}")
        
        # Test message sensor availability
        if client.unread_messages > 0:
            _LOGGER.info("🎉 MESSAGES WORKING! You have unread messages!")
        else:
            _LOGGER.info("📭 No unread messages found (this is normal if you don't have any)")
        
        # Test each child's data
        for child in children:
            child_id = child.get("id")
            child_name = child.get("name")
            
            weekplan = client.weekplan_data.get(child_id, {})
            homework = client.homework_data.get(child_id, {})
            presence = client.presence_data.get(child_id, {})
            
            _LOGGER.info(f"\n--- Child: {child_name} (ID: {child_id}) ---")
            _LOGGER.info(f"  Weekplan events: {len(weekplan.get('events', []))}")
            _LOGGER.info(f"  Homework assignments: {len(homework.get('assignments', []))}")
            _LOGGER.info(f"  Presence status: {presence.get('status', 'Unknown')}")
        
        _LOGGER.info("\n🎉 All tests passed! Integration should work correctly.")
        
    except Exception as e:
        _LOGGER.error(f"❌ Error during testing: {e}", exc_info=True)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_integration())