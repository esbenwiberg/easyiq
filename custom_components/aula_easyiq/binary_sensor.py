"""EasyIQ binary sensor platform."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PRESENCE_STATUS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EasyIQ binary sensor based on a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    client = hass.data[DOMAIN][config_entry.entry_id]["client"]
    
    # Create binary sensor entities
    entities = []
    
    # Always add message binary sensor
    entities.append(EasyIQMessageBinarySensor(coordinator))
    _LOGGER.info("Created message binary sensor")
    
    # Add presence sensors - use client.children if coordinator data not ready
    children_data = None
    if coordinator.data and "children" in coordinator.data and coordinator.data["children"]:
        children_data = coordinator.data["children"]
        _LOGGER.info("Using children data from coordinator: %d children", len(children_data))
    elif hasattr(client, 'children') and client.children:
        children_data = client.children
        _LOGGER.info("Using children data from client: %d children", len(children_data))
    else:
        _LOGGER.warning("No children data available in coordinator or client")
        _LOGGER.debug("Coordinator data: %s", coordinator.data)
        _LOGGER.debug("Client children: %s", getattr(client, 'children', 'Not available'))
    
    if children_data:
        for child in children_data:
            child_id = child.get("id")
            child_name = child.get("name", "Unknown")
            entities.append(EasyIQPresenceBinarySensor(coordinator, child_id, child_name))
            _LOGGER.info("Created presence sensor for child: %s (ID: %s)", child_name, child_id)
    
    _LOGGER.info("Adding %d binary sensor entities to Home Assistant", len(entities))
    async_add_entities(entities)


class EasyIQMessageBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of an EasyIQ message binary sensor."""

    def __init__(self, coordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_name = "EasyIQ Messages"
        self._attr_unique_id = "easyiq_messages"
        # Remove device_class to avoid "Disconnected" status
        # self._attr_device_class = "connectivity"

    @property
    def is_on(self) -> bool:
        """Return true if there are unread messages."""
        if not self.coordinator.data:
            return False
        unread_messages = self.coordinator.data.get("unread_messages", 0)
        return unread_messages > 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.coordinator.data:
            return {
                "error": "No coordinator data available",
                "unread_count": 0,
            }
            
        message_data = self.coordinator.data.get("message", {})
        unread_count = self.coordinator.data.get("unread_messages", 0)
        
        attributes = {
            "unread_count": unread_count,
            "coordinator_available": True,
            "last_update_success": self.coordinator.last_update_success,
        }
        
        # Add message details if available
        if message_data:
            attributes.update({
                "subject": message_data.get("subject", ""),
                "text": message_data.get("text", ""),
                "sender": message_data.get("sender", ""),
            })
        else:
            attributes["message_data_available"] = False
        
        return attributes


class EasyIQPresenceBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of an EasyIQ presence binary sensor."""

    def __init__(self, coordinator, child_id: str, child_name: str) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._child_id = child_id
        self._child_name = child_name
        self._attr_name = f"EasyIQ {child_name} Present"
        self._attr_unique_id = f"easyiq_{child_id}_presence"
        # Use occupancy instead of presence to avoid connectivity issues
        self._attr_device_class = "occupancy"

    @property
    def is_on(self) -> bool:
        """Return true if child is present at school."""
        if not self.coordinator.data:
            return False
        presence_data = self.coordinator.data.get("presence_data", {}).get(self._child_id, {})
        status_code = presence_data.get("status_code", 0)
        # Status codes indicating presence at school:
        # 3 = KOMMET/TIL STEDE (Arrived/Present)
        # 4 = PÅ TUR (On trip)
        # 5 = SOVER (Sleeping)
        # Status codes indicating NOT present:
        # 0 = IKKE KOMMET (Not arrived)
        # 1 = SYG (Sick)
        # 2 = FERIE/FRI (Holiday/Free)
        # 8 = HENTET/GÅET (Picked up/Gone)
        return status_code in [3, 4, 5]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        presence_data = self.coordinator.data.get("presence_data", {}).get(self._child_id, {})
        
        attributes = {
            "child_id": self._child_id,
            "child_name": self._child_name,
        }
        
        if presence_data:
            status_code = presence_data.get("status_code", 0)
            status_text = PRESENCE_STATUS.get(status_code, f"Unknown Status ({status_code})")
            
            attributes.update({
                "status": presence_data.get("status", status_text),
                "status_code": status_code,
                "status_description": status_text,
                "last_updated": presence_data.get("last_updated", "Unknown"),
            })
            
            # Add presence times and details
            check_in_time = presence_data.get("check_in_time", "")
            check_out_time = presence_data.get("check_out_time", "")
            entry_time = presence_data.get("entry_time", "")
            exit_time = presence_data.get("exit_time", "")
            comment = presence_data.get("comment", "")
            exit_with = presence_data.get("exit_with", "")
            
            if check_in_time:
                attributes["check_in_time"] = check_in_time
            
            if check_out_time:
                attributes["check_out_time"] = check_out_time
            
            if entry_time:
                attributes["entry_time"] = entry_time
            
            if exit_time:
                attributes["exit_time"] = exit_time
            
            if comment:
                attributes["comment"] = comment
            
            if exit_with:
                attributes["exit_with"] = exit_with
        
        return attributes

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        if self.is_on:
            return "mdi:account-check"
        return "mdi:account-off"
        
        return attributes

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        if self.is_on:
            return "mdi:message-alert"
        return "mdi:message-outline"