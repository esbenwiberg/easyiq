"""EasyIQ binary sensor platform."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EasyIQ binary sensor based on a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    
    # Create binary sensor entities
    entities = []
    
    # Add message binary sensor
    entities.append(EasyIQMessageBinarySensor(coordinator))
    
    async_add_entities(entities)


class EasyIQMessageBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of an EasyIQ message binary sensor."""

    def __init__(self, coordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_name = "EasyIQ Messages"
        self._attr_unique_id = "easyiq_messages"
        self._attr_device_class = "connectivity"

    @property
    def is_on(self) -> bool:
        """Return true if there are unread messages."""
        unread_messages = self.coordinator.data.get("unread_messages", 0)
        return unread_messages > 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        message_data = self.coordinator.data.get("message", {})
        unread_count = self.coordinator.data.get("unread_messages", 0)
        
        attributes = {
            "unread_count": unread_count,
        }
        
        # Add message details if available
        if message_data:
            attributes.update({
                "subject": message_data.get("subject", ""),
                "text": message_data.get("text", ""),
                "sender": message_data.get("sender", ""),
            })
        
        return attributes

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        if self.is_on:
            return "mdi:message-alert"
        return "mdi:message-outline"