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
    CONF_WEEKPLAN_INTERVAL,
    CONF_HOMEWORK_INTERVAL,
    CONF_PRESENCE_INTERVAL,
    CONF_MESSAGES_INTERVAL,
    CONF_WEEKPLAN_DAYS,
    CONF_HOMEWORK_DAYS,
    DEFAULT_WEEKPLAN_INTERVAL,
    DEFAULT_HOMEWORK_INTERVAL,
    DEFAULT_PRESENCE_INTERVAL,
    DEFAULT_MESSAGES_INTERVAL,
    DEFAULT_WEEKPLAN_DAYS,
    DEFAULT_HOMEWORK_DAYS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EasyIQ sensor based on a config entry."""
    # Use the coordinator created in __init__.py instead of creating a new one
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    
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
    """Class to manage fetching data from the EasyIQ API with configurable intervals."""

    def __init__(self, hass: HomeAssistant, client: EasyIQClient, config_entry) -> None:
        """Initialize."""
        self.client = client
        self.config_entry = config_entry
        
        # Get update intervals from config
        options = config_entry.options
        self.update_intervals = {
            "weekplan": options.get(CONF_WEEKPLAN_INTERVAL, DEFAULT_WEEKPLAN_INTERVAL),
            "homework": options.get(CONF_HOMEWORK_INTERVAL, DEFAULT_HOMEWORK_INTERVAL),
            "presence": options.get(CONF_PRESENCE_INTERVAL, DEFAULT_PRESENCE_INTERVAL),
            "messages": options.get(CONF_MESSAGES_INTERVAL, DEFAULT_MESSAGES_INTERVAL),
        }
        
        # Get days configuration from config
        self.days_config = {
            "weekplan": options.get(CONF_WEEKPLAN_DAYS, DEFAULT_WEEKPLAN_DAYS),
            "homework": options.get(CONF_HOMEWORK_DAYS, DEFAULT_HOMEWORK_DAYS),
        }
        
        # Track last update times for each data type
        self.last_updates = {
            "weekplan": None,
            "homework": None,
            "presence": None,
            "messages": None,
        }
        
        # Use the shortest interval as the coordinator's base interval
        min_interval = min(self.update_intervals.values())
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=min_interval),
        )
        
        _LOGGER.info(f"EasyIQ coordinator initialized with intervals: {self.update_intervals}")

    def _should_update_data_type(self, data_type: str) -> bool:
        """Check if a specific data type should be updated based on its interval."""
        if data_type not in self.update_intervals:
            return True
            
        last_update = self.last_updates.get(data_type)
        if last_update is None:
            return True
            
        interval = self.update_intervals[data_type]
        time_since_update = (datetime.now() - last_update).total_seconds()
        
        should_update = time_since_update >= interval
        if should_update:
            _LOGGER.debug(f"Should update {data_type}: {time_since_update}s >= {interval}s")
        
        return should_update

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library with selective updates based on intervals."""
        from datetime import datetime
        
        try:
            # Determine which data types need updating
            update_weekplan = self._should_update_data_type("weekplan")
            update_homework = self._should_update_data_type("homework")
            update_presence = self._should_update_data_type("presence")
            update_messages = self._should_update_data_type("messages")
            
            _LOGGER.debug(f"Update flags - weekplan: {update_weekplan}, homework: {update_homework}, "
                         f"presence: {update_presence}, messages: {update_messages}")
            
            # Update only the data types that need updating
            await self.client.update_data_selective(
                update_weekplan=update_weekplan,
                update_homework=update_homework,
                update_presence=update_presence,
                update_messages=update_messages,
                weekplan_days=self.days_config["weekplan"],
                homework_days=self.days_config["homework"]
            )
            
            # Update last update times for updated data types
            current_time = datetime.now()
            if update_weekplan:
                self.last_updates["weekplan"] = current_time
            if update_homework:
                self.last_updates["homework"] = current_time
            if update_presence:
                self.last_updates["presence"] = current_time
            if update_messages:
                self.last_updates["messages"] = current_time
            
            data = {
                "children": self.client.children,
                "unread_messages": self.client.unread_messages,
                "message": self.client.message,
                "weekplan_data": self.client.weekplan_data,
                "homework_data": getattr(self.client, 'homework_data', {}),
                "presence_data": getattr(self.client, 'presence_data', {}),
                "last_updates": self.last_updates.copy(),
                "update_intervals": self.update_intervals.copy(),
            }
            _LOGGER.debug(f"Coordinator updated data successfully: {len(data['children'])} children")
            return data
        except Exception as err:
            _LOGGER.error(f"Error updating coordinator data: {err}", exc_info=True)
            # Return partial data to keep integration running instead of failing completely
            return {
                "children": getattr(self.client, 'children', []),
                "unread_messages": getattr(self.client, 'unread_messages', 0),
                "message": getattr(self.client, 'message', {"subject": "Error", "text": "Update failed", "sender": "System"}),
                "weekplan_data": getattr(self.client, 'weekplan_data', {}),
                "homework_data": getattr(self.client, 'homework_data', {}),
                "presence_data": getattr(self.client, 'presence_data', {}),
                "last_updates": self.last_updates.copy(),
                "update_intervals": self.update_intervals.copy(),
            }


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
        
        # Limit the size of weekplan data to avoid database issues
        # Only include essential information
        limited_weekplan = {}
        if isinstance(weekplan_data, dict):
            # Include only the most recent events (limit to 10)
            events = weekplan_data.get("events", [])
            if isinstance(events, list):
                limited_weekplan["events"] = events[:10]
                limited_weekplan["total_events"] = len(events)
            
            # Include summary information
            limited_weekplan["last_updated"] = weekplan_data.get("last_updated")
        
        return {
            "child_id": self._child_id,
            "child_name": self._child_name,
            "weekplan_summary": limited_weekplan,
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



