"""EasyIQ sensor platform."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .client import EasyIQClient
from .const import (
    CONF_WEEKPLAN,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EasyIQ sensor based on a config entry."""
    username = config_entry.data[CONF_USERNAME]
    password = config_entry.data[CONF_PASSWORD]
    
    # Create the EasyIQ client
    client = EasyIQClient(username, password)
    
    # Create coordinator for data updates
    coordinator = EasyIQDataUpdateCoordinator(hass, client)
    
    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()
    
    # Store client and coordinator in hass data
    hass.data[DOMAIN][config_entry.entry_id]["client"] = client
    hass.data[DOMAIN][config_entry.entry_id]["coordinator"] = coordinator
    
    # Create sensor entities
    entities = []
    
    # Check if we have data and children
    if coordinator.data and "children" in coordinator.data and coordinator.data["children"]:
        _LOGGER.info("Found %d children in coordinator data", len(coordinator.data["children"]))
        for child in coordinator.data["children"]:
            child_id = child.get("id")
            child_name = child.get("name", "Unknown")
            
            _LOGGER.info("Creating sensors for child: %s (ID: %s)", child_name, child_id)
            
            # Create main sensor for each child
            entities.append(EasyIQChildSensor(coordinator, child_id, child_name))
            
            # Add weekplan sensor if enabled (check both options and data for backward compatibility)
            weekplan_enabled = config_entry.options.get(CONF_WEEKPLAN, config_entry.data.get(CONF_WEEKPLAN, True))
            if weekplan_enabled:
                entities.append(EasyIQWeekplanSensor(coordinator, child_id, child_name))
                _LOGGER.info("Added weekplan sensor for child: %s", child_name)
    else:
        _LOGGER.warning("No children data found in coordinator. Data: %s", coordinator.data)
        # Create a placeholder sensor to show the integration is loaded but has issues
        entities.append(EasyIQStatusSensor(coordinator, "No children found"))
    
    _LOGGER.info("Adding %d entities to Home Assistant", len(entities))
    async_add_entities(entities)


class EasyIQDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the EasyIQ API."""

    def __init__(self, hass: HomeAssistant, client: EasyIQClient) -> None:
        """Initialize."""
        self.client = client
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            await self.client.update_data()
            return {
                "children": self.client.children,
                "unread_messages": self.client.unread_messages,
                "message": self.client.message,
                "weekplan_data": self.client.weekplan_data,
                "homework_data": getattr(self.client, 'homework_data', {}),
            }
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err


class EasyIQChildSensor(CoordinatorEntity, SensorEntity):
    """Representation of an EasyIQ child sensor."""

    def __init__(self, coordinator: EasyIQDataUpdateCoordinator, child_id: str, child_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._child_id = child_id
        self._child_name = child_name
        self._attr_name = f"EasyIQ {child_name}"
        self._attr_unique_id = f"easyiq_{child_id}"

    @property
    def state(self) -> str | None:
        """Return the state of the sensor."""
        # Return the current week as the state
        weekplan_data = self.coordinator.data.get("weekplan_data", {}).get(self._child_id, {})
        if weekplan_data and weekplan_data.get('week'):
            return weekplan_data['week']
        return "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        weekplan_data = self.coordinator.data.get("weekplan_data", {}).get(self._child_id, {})
        
        attributes = {
            "child_id": self._child_id,
            "child_name": self._child_name,
        }
        
        if weekplan_data:
            attributes.update({
                "week": weekplan_data.get('week', 'Unknown'),
                "events_count": len(weekplan_data.get('events', [])),
                "html_content": weekplan_data.get('html_content', ''),
                "last_updated": weekplan_data.get('last_updated', 'Unknown')
            })
            
            # Add first few events as attributes for easy access
            events = weekplan_data.get('events', [])
            for i, event in enumerate(events[:5]):  # Limit to first 5 events
                attributes[f"event_{i+1}_subject"] = event.get('courses', 'Unknown')
                attributes[f"event_{i+1}_time"] = event.get('start', 'Unknown')
                attributes[f"event_{i+1}_activities"] = event.get('activities', 'Unknown')
        
        return attributes


class EasyIQWeekplanSensor(CoordinatorEntity, SensorEntity):
    """Representation of an EasyIQ weekplan sensor."""

    def __init__(self, coordinator: EasyIQDataUpdateCoordinator, child_id: str, child_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._child_id = child_id
        self._child_name = child_name
        self._attr_name = f"EasyIQ {child_name} Weekplan"
        self._attr_unique_id = f"easyiq_{child_id}_weekplan"

    @property
    def state(self) -> str | None:
        """Return the state of the sensor."""
        weekplan_data = self.coordinator.data.get("weekplan_data", {}).get(self._child_id)
        if weekplan_data:
            return "available"
        return "unavailable"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        weekplan_data = self.coordinator.data.get("weekplan_data", {}).get(self._child_id, {})
        return {
            "child_id": self._child_id,
            "child_name": self._child_name,
            "weekplan": weekplan_data,
        }


class EasyIQStatusSensor(CoordinatorEntity, SensorEntity):
    """Representation of an EasyIQ status sensor for debugging."""

    def __init__(self, coordinator: EasyIQDataUpdateCoordinator, status_message: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._status_message = status_message
        self._attr_name = "EasyIQ Status"
        self._attr_unique_id = "easyiq_status"

    @property
    def state(self) -> str | None:
        """Return the state of the sensor."""
        return self._status_message

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            "coordinator_data": str(self.coordinator.data),
            "last_update_success": self.coordinator.last_update_success,
            "last_exception": str(self.coordinator.last_exception) if self.coordinator.last_exception else None,
        }



