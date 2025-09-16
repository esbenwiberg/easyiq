#!/usr/bin/env python3
"""Simple test to verify homework data structure."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'aula-easyiq'))

# Mock the homeassistant imports
class MockSensorEntity:
    pass

class MockCoordinatorEntity:
    pass

class MockUpdateFailed(Exception):
    pass

class MockDataUpdateCoordinator:
    def __init__(self, hass, logger, name, update_interval):
        pass

# Mock homeassistant modules
sys.modules['homeassistant'] = type(sys)('homeassistant')
sys.modules['homeassistant.components'] = type(sys)('homeassistant.components')
sys.modules['homeassistant.components.sensor'] = type(sys)('homeassistant.components.sensor')
sys.modules['homeassistant.helpers'] = type(sys)('homeassistant.helpers')
sys.modules['homeassistant.helpers.update_coordinator'] = type(sys)('homeassistant.helpers.update_coordinator')
sys.modules['homeassistant.helpers.entity_platform'] = type(sys)('homeassistant.helpers.entity_platform')
sys.modules['homeassistant.config_entries'] = type(sys)('homeassistant.config_entries')
sys.modules['homeassistant.core'] = type(sys)('homeassistant.core')
sys.modules['homeassistant.const'] = type(sys)('homeassistant.const')

# Add mock classes to modules
sys.modules['homeassistant.components.sensor'].SensorEntity = MockSensorEntity
sys.modules['homeassistant.helpers.update_coordinator'].CoordinatorEntity = MockCoordinatorEntity
sys.modules['homeassistant.helpers.update_coordinator'].DataUpdateCoordinator = MockDataUpdateCoordinator
sys.modules['homeassistant.helpers.update_coordinator'].UpdateFailed = MockUpdateFailed
sys.modules['homeassistant.helpers.entity_platform'].AddEntitiesCallback = object
sys.modules['homeassistant.config_entries'].ConfigEntry = object
sys.modules['homeassistant.core'].HomeAssistant = object
sys.modules['homeassistant.const'].CONF_PASSWORD = 'password'
sys.modules['homeassistant.const'].CONF_USERNAME = 'username'

from client import EasyIQClient
import asyncio
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)

async def test_client_structure():
    """Test that client has homework functionality."""
    print("🔬 Testing Client Structure for Homework Fix")
    print("=" * 60)
    
    # Create a client
    client = EasyIQClient("test_user", "test_pass")
    
    # Check initialization
    print(f"✅ Client has homework_data attribute: {hasattr(client, 'homework_data')}")
    print(f"✅ homework_data initialized as: {client.homework_data}")
    
    # Check methods
    print(f"✅ Client has get_homework method: {hasattr(client, 'get_homework')}")
    print(f"✅ Client has update_data method: {hasattr(client, 'update_data')}")
    
    # Mock some data to test update_data structure
    client.children = [{"id": "test_child", "name": "Test Child"}]
    client._authenticated = True
    
    # Mock the individual methods to avoid network calls
    async def mock_get_children():
        return client.children
    
    async def mock_get_weekplan(child_id):
        return {"week": "Week 1", "events": []}
    
    async def mock_get_homework(child_id):
        return {"assignments": [{"title": "Math homework"}]}
    
    async def mock_get_messages():
        return {}
    
    async def mock_authenticate():
        return True
    
    # Replace methods with mocks
    client.get_children = mock_get_children
    client.get_weekplan = mock_get_weekplan
    client.get_homework = mock_get_homework
    client.get_messages = mock_get_messages
    client.authenticate = mock_authenticate
    
    # Test update_data
    try:
        await client.update_data()
        
        print(f"✅ After update_data:")
        print(f"   - weekplan_data: {client.weekplan_data}")
        print(f"   - homework_data: {client.homework_data}")
        
        if client.homework_data:
            print("🎉 SUCCESS: Client now fetches and stores homework data!")
        else:
            print("❌ FAILED: homework_data is still empty")
            
    except Exception as e:
        print(f"❌ Error testing update_data: {e}")

if __name__ == "__main__":
    asyncio.run(test_client_structure())