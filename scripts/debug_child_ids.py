#!/usr/bin/env python3
"""Debug script to test child ID mapping in EasyIQ integration."""

import asyncio
import logging
import sys
import os

# Add the custom_components path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components'))

from custom_components.easyiq.client import EasyIQClient

# Set up comprehensive debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
_LOGGER = logging.getLogger(__name__)

# Enable debug logging for all EasyIQ components
logging.getLogger('custom_components.easyiq').setLevel(logging.DEBUG)
logging.getLogger('custom_components.easyiq.client').setLevel(logging.DEBUG)

async def debug_child_ids():
    """Debug child ID mapping."""
    # You'll need to provide your credentials
    username = input("Enter username: ")
    password = input("Enter password: ")
    
    client = EasyIQClient(username, password)
    
    try:
        # Authenticate
        _LOGGER.info("Authenticating...")
        if not await client.authenticate():
            _LOGGER.error("Authentication failed")
            return
        
        _LOGGER.info("Authentication successful!")
        
        # Get children
        children = await client.get_children()
        _LOGGER.info(f"Found {len(children)} children: {children}")
        
        # Debug child data mapping
        _LOGGER.info("Child data mapping:")
        for key, value in client._children_data.items():
            _LOGGER.info(f"  {key}: {value}")
        
        # Test calendar events for each child
        for child in children:
            child_id = child.get("id")
            child_name = child.get("name")
            _LOGGER.info(f"\n--- Testing child: {child_name} (ID: {child_id}) ---")
            
            # Test current week events
            events = await client._get_calendar_events(child_id, 0)
            _LOGGER.info(f"Found {len(events)} events for {child_name}")
            
            if events:
                # Show first few events
                for i, event in enumerate(events[:3]):
                    _LOGGER.info(f"  Event {i+1}: {event.get('courses', 'Unknown')} at {event.get('start', 'Unknown time')}")
            
            # Test business days events
            business_events = await client.get_calendar_events_for_business_days(child_id, 5)
            _LOGGER.info(f"Found {len(business_events)} business day events for {child_name}")
        
    except Exception as e:
        _LOGGER.error(f"Error during debugging: {e}", exc_info=True)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(debug_child_ids())