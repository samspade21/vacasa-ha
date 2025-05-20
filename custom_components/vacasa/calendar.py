"""Calendar platform for Vacasa integration."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .api_client import VacasaApiClient
from .const import (
    CATEGORY_BLOCK,
    CATEGORY_GUEST,
    CATEGORY_MAINTENANCE,
    CATEGORY_OTHER,
    CATEGORY_OWNER,
    DATA_CLIENT,
    DATA_COORDINATOR,
    DOMAIN,
    STAY_TYPE_BLOCK,
    STAY_TYPE_GUEST,
    STAY_TYPE_MAINTENANCE,
    STAY_TYPE_OTHER,
    STAY_TYPE_OWNER,
)

_LOGGER = logging.getLogger(__name__)

# Mapping of stay types to calendar categories
STAY_TYPE_TO_CATEGORY = {
    STAY_TYPE_GUEST: CATEGORY_GUEST,
    STAY_TYPE_OWNER: CATEGORY_OWNER,
    STAY_TYPE_BLOCK: CATEGORY_BLOCK,
    STAY_TYPE_MAINTENANCE: CATEGORY_MAINTENANCE,
    STAY_TYPE_OTHER: CATEGORY_OTHER,
}

# Mapping of stay types to human-readable names
STAY_TYPE_TO_NAME = {
    STAY_TYPE_GUEST: "Guest Booking",
    STAY_TYPE_OWNER: "Owner Stay",
    STAY_TYPE_BLOCK: "Block",
    STAY_TYPE_MAINTENANCE: "Maintenance",
    STAY_TYPE_OTHER: "Other",
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Vacasa calendar platform."""
    client = hass.data[DOMAIN][config_entry.entry_id][DATA_CLIENT]
    coordinator = hass.data[DOMAIN][config_entry.entry_id][DATA_COORDINATOR]

    # Get all units
    try:
        units = await client.get_units()
        _LOGGER.debug("Found %s Vacasa units", len(units))

        # Create a calendar entity for each unit
        entities = []
        for unit in units:
            unit_id = unit.get("id")
            attributes = unit.get("attributes", {})
            name = attributes.get("name", f"Vacasa Unit {unit_id}")
            code = attributes.get("code", "")
            
            # Get property-specific check-in/check-out times
            checkin_time = attributes.get("checkInTime")
            checkout_time = attributes.get("checkOutTime")
            timezone = attributes.get("timezone")

            entity = VacasaCalendar(
                coordinator=coordinator,
                client=client,
                unit_id=unit_id,
                name=name,
                code=code,
                unit_attributes=attributes,
            )
            entities.append(entity)

        async_add_entities(entities, True)
    except Exception as err:
        _LOGGER.error("Error setting up Vacasa calendars: %s", err)


class VacasaCalendar(CoordinatorEntity, CalendarEntity):
    """Representation of a Vacasa calendar."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        client: VacasaApiClient,
        unit_id: str,
        name: str,
        code: str,
        unit_attributes: Dict[str, Any],
    ) -> None:
        """Initialize the Vacasa calendar."""
        super().__init__(coordinator)
        self._client = client
        self._unit_id = unit_id
        self._name = name
        self._code = code
        self._unit_attributes = unit_attributes
        self._checkin_time = unit_attributes.get("checkInTime")
        self._checkout_time = unit_attributes.get("checkOutTime")
        self._timezone = unit_attributes.get("timezone")
        self._event_cache: Dict[str, List[CalendarEvent]] = {}
        self._current_event: Optional[CalendarEvent] = None

        # Entity properties
        self._attr_unique_id = f"vacasa_calendar_{unit_id}"
        self._attr_name = f"Vacasa {name}"

        # Set device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, unit_id)},
            "name": f"Vacasa {name}",
            "manufacturer": "Vacasa",
            "model": "Vacation Rental",
            "sw_version": "1.0",
        }

    @property
    def event(self) -> Optional[CalendarEvent]:
        """Return the next upcoming event."""
        return self._current_event

    @property
    def event_types(self) -> list[str]:
        """Return a list of supported event types."""
        return list(STAY_TYPE_TO_CATEGORY.values())

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> List[CalendarEvent]:
        """Get all events in a specific time frame."""
        # Convert to YYYY-MM-DD format for API
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        # Check if we have cached events for this date range
        cache_key = f"{start_str}_{end_str}"
        if cache_key in self._event_cache:
            return self._event_cache[cache_key]

        try:
            # Get categorized reservations
            categorized = await self._client.get_categorized_reservations(
                self._unit_id, start_str, end_str
            )

            events = []
            for stay_type, reservations in categorized.items():
                for reservation in reservations:
                    event = self._reservation_to_event(reservation, stay_type)
                    if event:
                        events.append(event)

            # Cache the events
            self._event_cache[cache_key] = events

            return events
        except Exception as err:
            _LOGGER.error("Error getting events for %s: %s", self._name, err)
            return []

    async def async_update(self) -> None:
        """Update the entity.

        This is only used by the generic entity update service.
        """
        await self.coordinator.async_request_refresh()
        await self._update_current_event()

    async def _update_current_event(self) -> None:
        """Update the current event."""
        self._current_event = await self.async_get_next_event()

    async def async_get_next_event(self) -> Optional[CalendarEvent]:
        """Get the next event."""
        now = dt_util.now()
        events = await self.async_get_events(self.hass, now, now + timedelta(days=365))

        # Find the next event
        next_event = None
        for event in events:
            event_start = event.start
            if event_start and event_start >= now:
                if next_event is None:
                    next_event = event
                else:
                    if event_start < next_event.start:
                        next_event = event

        return next_event

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        # Update current event when entity is added to hass
        await self._update_current_event()

    def _reservation_to_event(
        self, reservation: Dict[str, Any], stay_type: str
    ) -> Optional[CalendarEvent]:
        """Convert a reservation to a calendar event."""
        try:
            attributes = reservation.get("attributes", {})

            # Get start and end dates
            start_date = attributes.get("startDate")
            end_date = attributes.get("endDate")

            if not start_date or not end_date:
                return None

            # Get check-in and check-out times from the reservation or property
            checkin_time = attributes.get("checkinTime")
            checkout_time = attributes.get("checkoutTime")

            # Create datetime objects based on available information
            if checkin_time and checkin_time not in ["00:00:00", "12:00:00"]:
                # Use time from reservation
                start_dt_str = f"{start_date}T{checkin_time}"
            elif self._checkin_time:
                # Use property-specific time
                start_dt_str = f"{start_date}T{self._checkin_time}"
            else:
                # No time available, use date only
                start_dt_str = f"{start_date}T00:00:00"

            if checkout_time and checkout_time not in ["00:00:00", "12:00:00"]:
                # Use time from reservation
                end_dt_str = f"{end_date}T{checkout_time}"
            elif self._checkout_time:
                # Use property-specific time
                end_dt_str = f"{end_date}T{self._checkout_time}"
            else:
                # No time available, use date only
                end_dt_str = f"{end_date}T00:00:00"

            # Parse datetime strings
            start_dt = dt_util.parse_datetime(start_dt_str)
            end_dt = dt_util.parse_datetime(end_dt_str)

            if not start_dt or not end_dt:
                return None

            # Handle timezone properly
            # For all-day events (no specific time), don't apply timezone
            is_all_day_start = "T00:00:00" in start_dt_str
            is_all_day_end = "T00:00:00" in end_dt_str
            
            if is_all_day_start and is_all_day_end:
                # This is an all-day event
                _LOGGER.debug("Creating all-day event for %s from %s to %s", 
                             self._name, start_date, end_date)
                # No timezone needed for all-day events
            else:
                # This is a timed event, apply timezone
                if self._timezone:
                    import pytz
                    try:
                        tz = pytz.timezone(self._timezone)
                        _LOGGER.debug("Using property timezone: %s", self._timezone)
                        
                        # Create timezone-aware datetime objects
                        if not is_all_day_start:
                            # Use localize instead of replace to handle DST correctly
                            naive_start = start_dt.replace(tzinfo=None)
                            start_dt = tz.localize(naive_start)
                            _LOGGER.debug("Start time with TZ: %s", start_dt)
                        
                        if not is_all_day_end:
                            # Use localize instead of replace to handle DST correctly
                            naive_end = end_dt.replace(tzinfo=None)
                            end_dt = tz.localize(naive_end)
                            _LOGGER.debug("End time with TZ: %s", end_dt)
                    except Exception as e:
                        _LOGGER.warning("Error applying timezone %s: %s", self._timezone, e)
                        # Fall back to local timezone
                        if not is_all_day_start:
                            start_dt = dt_util.as_local(start_dt)
                        if not is_all_day_end:
                            end_dt = dt_util.as_local(end_dt)
                else:
                    # No property timezone, use local timezone
                    _LOGGER.debug("No property timezone, using local timezone")
                    if not is_all_day_start:
                        start_dt = dt_util.as_local(start_dt)
                    if not is_all_day_end:
                        end_dt = dt_util.as_local(end_dt)

            # Get guest/owner information
            first_name = attributes.get("firstName", "")
            last_name = attributes.get("lastName", "")

            # Get owner hold information
            owner_hold = attributes.get("ownerHold")
            hold_type = ""
            hold_who_booked = ""
            hold_note = ""

            if owner_hold:
                hold_type = owner_hold.get("holdType", "")
                hold_who_booked = owner_hold.get("holdWhoBooked", "")
                hold_note = owner_hold.get("holdExternalNote", "")

            # Create summary based on stay type
            summary_prefix = STAY_TYPE_TO_NAME[stay_type]

            if stay_type == STAY_TYPE_GUEST and first_name and last_name:
                summary = f"{summary_prefix}: {first_name} {last_name}"
            elif stay_type == STAY_TYPE_OWNER and hold_who_booked:
                summary = f"{summary_prefix}: {hold_who_booked}"
            elif hold_type:
                summary = f"{summary_prefix}: {hold_type}"
            else:
                summary = summary_prefix

            # Create description
            description_parts = []

            # Add check-in and check-out information
            if checkin_time and checkin_time not in ["00:00:00", "12:00:00"]:
                description_parts.append(f"Check-in: {start_date} {checkin_time[:5]}")
            elif self._checkin_time:
                description_parts.append(f"Check-in: {start_date} {self._checkin_time[:5]}")
            else:
                description_parts.append(f"Check-in: {start_date}")
                
            if checkout_time and checkout_time not in ["00:00:00", "12:00:00"]:
                description_parts.append(f"Check-out: {end_date} {checkout_time[:5]}")
            elif self._checkout_time:
                description_parts.append(f"Check-out: {end_date} {self._checkout_time[:5]}")
            else:
                description_parts.append(f"Check-out: {end_date}")
                
            description_parts.append("")

            if stay_type == STAY_TYPE_GUEST:
                description_parts.append("Type: Guest booking")
            elif stay_type == STAY_TYPE_OWNER:
                description_parts.append("Type: Owner stay")
            elif stay_type == STAY_TYPE_MAINTENANCE:
                description_parts.append("Type: Maintenance")
            elif stay_type == STAY_TYPE_BLOCK:
                description_parts.append("Type: Block")
                if hold_type:
                    description_parts.append(f"Block type: {hold_type}")

            if hold_who_booked and stay_type != STAY_TYPE_OWNER:
                description_parts.append(f"Booked by: {hold_who_booked}")

            if hold_note:
                description_parts.append(f"Note: {hold_note}")

            description = "\n".join(description_parts)

            # Create the event with datetime objects for start and end
            return CalendarEvent(
                uid=f"reservation_{reservation.get('id', '')}",
                summary=summary,
                start=start_dt,
                end=end_dt,
                location=self._name,
                description=description,
            )
        except Exception as err:
            _LOGGER.error("Error converting reservation to event: %s", err)
            return None
