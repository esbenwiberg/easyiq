#!/usr/bin/env python3
"""Test script to verify homework data is included in coordinator data."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'easyiq'))

from client import EasyIQClient
from sensor import EasyIQDataUpdateCoordinator
import asyncio
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

async def test_homework_fix():
    """Test that homework data is included in coordinator data."""
    print("🔬 Testing Homework Fix")
    print("=" * 60)
    
    # Create a mock client
    client = EasyIQClient("test_user", "test_pass")
    
    # Check that homework_data is initialized
    print(f"✅ Client has homework_data attribute: {hasattr(client, 'homework_data')}")
    print(f"✅ homework_data initialized as: {client.homework_data}")
    
    # Mock some data
    client.children = [{"id": "test_child", "name": "Test Child"}]
    client.weekplan_data = {"test_child": {"week": "Week 1", "events": []}}
    client.homework_data = {"test_child": {"assignments": [{"title": "Math homework"}]}}
    client.unread_messages = 0
    client.message = {}
    
    # Create coordinator (without Home Assistant)
    class MockHass:
        pass
    
    coordinator = EasyIQDataUpdateCoordinator(MockHass(), client)
    
    # Test the _async_update_data method directly
    try:
        # Mock the update_data method to avoid authentication
        async def mock_update_data():
            pass
        
        client.update_data = mock_update_data
        
        # Call the coordinator's update method
        data = await coordinator._async_update_data()
        
        print(f"✅ Coordinator data keys: {list(data.keys())}")
        print(f"✅ Has weekplan_data: {'weekplan_data' in data}")
        print(f"✅ Has homework_data: {'homework_data' in data}")
        
        if 'homework_data' in data:
            print(f"✅ Homework data content: {data['homework_data']}")
            print("🎉 SUCCESS: Homework data is now included in coordinator!")
        else:
            print("❌ FAILED: Homework data is missing from coordinator")
            
    except Exception as e:
        print(f"❌ Error testing coordinator: {e}")

if __name__ == "__main__":
    asyncio.run(test_homework_fix())