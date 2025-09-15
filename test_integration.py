#!/usr/bin/env python3
"""Test script to verify EasyIQ integration functionality."""

import asyncio
import logging
import sys
import os

# Add the custom_components path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components'))

from custom_components.easyiq.client import EasyIQClient

# Set up logging
logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)

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
        
        # Test message data
        _LOGGER.info(f"✅ Messages: {client.message}")
        _LOGGER.info(f"✅ Unread messages: {client.unread_messages}")
        
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