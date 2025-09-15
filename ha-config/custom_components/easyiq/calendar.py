"""Calendar platform for EasyIQ integration."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
import pytz

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EasyIQ calendar entities."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    
    entities = []
    
    # Wait for initial data
    if coordinator.data and "children" in coordinator.data:
        for child in coordinator.data["children"]:
            child_id = child.get("id")
            child_name = child.get("name", "Unknown")
            
            # Create calendar entity for each child
            entities.append(
                EasyIQCalendarEntity(
                    coordinator,
                    child_id,
                    child_name,
                )
            )
            _LOGGER.info("Created calendar entity for child: %s", child_name)
    else:
        _LOGGER.warning("No children data available for calendar setup")
    
    async_add_entities(entities)


class EasyIQCalendarEntity(CalendarEntity):
    """EasyIQ calendar entity."""

    def __init__(self, coordinator, child_id: str, child_name: str) -> None:
        """Initialize the calendar entity."""
        self._coordinator = coordinator
        self._child_id = child_id
        self._child_name = child_name
        self._attr_name = f"EasyIQ {child_name} Calendar"
        self._attr_unique_id = f"easyiq_calendar_{child_id}"

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        try:
            # Get all events (weekplan + homework) for this child
            all_events = self._get_all_events()
            
            if not all_events:
                return None
            
            # Find the next upcoming event
            now = dt_util.now()  # Use timezone-aware current time
            upcoming_events = [event for event in all_events if event.start > now]
            
            if upcoming_events:
                # Sort by start time and return the earliest
                upcoming_events.sort(key=lambda x: x.start)
                return upcoming_events[0]
            
        except Exception as err:
            _LOGGER.error("Error getting next event: %s", err)
        
        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        try:
            # Get all events (weekplan + homework) for this child
            all_events = self._get_all_events()
            
            # Filter events within the requested date range
            filtered_events = []
            for event in all_events:
                if event.end >= start_date and event.start <= end_date:
                    filtered_events.append(event)
            
            _LOGGER.debug("Found %d events for %s between %s and %s",
                         len(filtered_events), self._child_name, start_date, end_date)
            
            return filtered_events
                    
        except Exception as err:
            _LOGGER.error("Error fetching calendar events: %s", err)
            return []

    def _get_all_events(self) -> list[CalendarEvent]:
        """Get all events (weekplan + homework) for this child."""
        events = []
        
        if not self._coordinator.data:
            return events
        
        # Get weekplan events
        weekplan_data = self._coordinator.data.get("weekplan_data", {}).get(self._child_id, {})
        weekplan_events = weekplan_data.get('events', [])
        
        for event_data in weekplan_events:
            event = self._parse_weekplan_event(event_data)
            if event:
                events.append(event)
        
        # Get homework events
        homework_data = self._coordinator.data.get("homework_data", {}).get(self._child_id, {})
        homework_assignments = homework_data.get('assignments', [])
        
        for assignment_data in homework_assignments:
            event = self._parse_homework_event(assignment_data)
            if event:
                events.append(event)
        
        return events

    def _parse_weekplan_event(self, event_data: dict[str, Any]) -> CalendarEvent | None:
        """Parse a weekplan event from API data."""
        try:
            # Parse start and end times from EasyIQ format
            start_str = event_data.get('start', '')
            end_str = event_data.get('end', '')
            
            if not start_str:
                return None
            
            # Convert from "2025/09/15 08:05" format to timezone-aware datetime
            event_start = datetime.strptime(start_str, "%Y/%m/%d %H:%M")
            event_end = datetime.strptime(end_str, "%Y/%m/%d %H:%M") if end_str else event_start
            
            # Make timezone-aware (assume Europe/Copenhagen timezone for Danish schools)
            copenhagen_tz = pytz.timezone('Europe/Copenhagen')
            event_start = copenhagen_tz.localize(event_start)
            event_end = copenhagen_tz.localize(event_end)
            
            # Create CalendarEvent object for weekplan
            summary = event_data.get('courses', 'School Event')
            description_parts = []
            
            # Add activities if available
            if event_data.get('activities'):
                description_parts.append(f"📚 Activities: {event_data['activities']}")
            
            # Add original description if available
            if event_data.get('description'):
                description_parts.append(f"📝 Details: {event_data['description']}")
            
            # Add event type indicator
            description_parts.append("📅 Type: Weekplan Event")
            
            return CalendarEvent(
                start=event_start,
                end=event_end,
                summary=summary,
                description="\n".join(description_parts),
            )
            
        except Exception as err:
            _LOGGER.error("Error parsing weekplan event: %s", err)
            return None

    def _parse_homework_event(self, assignment_data: dict[str, Any]) -> CalendarEvent | None:
        """Parse a homework assignment as a calendar event."""
        try:
            # Get assignment details
            title = assignment_data.get('title', assignment_data.get('subject', 'Homework'))
            subject = assignment_data.get('subject', 'Unknown Subject')
            description = assignment_data.get('description', '')
            activities = assignment_data.get('activities', '')
            start_time_str = assignment_data.get('start_time', '')
            
            # If we have a start time, use it; otherwise create an all-day event
            copenhagen_tz = pytz.timezone('Europe/Copenhagen')
            if start_time_str:
                try:
                    event_start = datetime.strptime(start_time_str, "%Y/%m/%d %H:%M")
                    event_end = event_start.replace(hour=event_start.hour + 1)  # 1 hour duration
                    # Make timezone-aware
                    event_start = copenhagen_tz.localize(event_start)
                    event_end = copenhagen_tz.localize(event_end)
                except ValueError:
                    # If parsing fails, create all-day event for today
                    now = dt_util.now()
                    event_start = now.replace(hour=9, minute=0, second=0, microsecond=0)
                    event_end = event_start.replace(hour=10)
            else:
                # Create all-day homework event for today
                now = dt_util.now()
                event_start = now.replace(hour=9, minute=0, second=0, microsecond=0)
                event_end = event_start.replace(hour=10)
            
            # Build description
            description_parts = []
            description_parts.append(f"📚 Subject: {subject}")
            
            if activities:
                description_parts.append(f"📝 Activities: {activities}")
            
            if description:
                description_parts.append(f"📋 Description: {description}")
            
            # Add homework indicator
            description_parts.append("🏠 Type: Homework Assignment")
            
            return CalendarEvent(
                start=event_start,
                end=event_end,
                summary=f"📚 {title}",
                description="\n".join(description_parts),
            )
            
        except Exception as err:
            _LOGGER.error("Error parsing homework event: %s", err)
            return None