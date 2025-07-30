"""Binary sensor platform for Vacasa integration."""

import asyncio
import logging
import re
from datetime import datetime
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import VacasaConfigEntry
from .const import DOMAIN, SENSOR_OCCUPANCY

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: VacasaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Vacasa binary sensor platform."""
    # Use modern runtime data pattern
    data = config_entry.runtime_data
    client = data.client
    coordinator = data.coordinator

    # Get all units
    try:
        units = await client.get_units()
        _LOGGER.debug("Found %s Vacasa units for binary sensors", len(units))

        # Create an occupancy sensor for each unit
        entities = []
        for unit in units:
            unit_id = unit.get("id")
            attributes = unit.get("attributes", {})
            name = attributes.get("name", f"Vacasa Unit {unit_id}")
            code = attributes.get("code", "")

            entity = VacasaOccupancySensor(
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
        _LOGGER.error("Error setting up Vacasa binary sensors: %s", err)


class VacasaOccupancySensor(BinarySensorEntity):
    """Representation of a Vacasa occupancy sensor."""

    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY

    def __init__(
        self,
        coordinator,
        client,
        unit_id,
        name,
        code,
        unit_attributes,
    ) -> None:
        """Initialize the Vacasa occupancy sensor."""
        super().__init__()
        self._client = client
        self._unit_id = unit_id
        self._name = name
        self._code = code
        self._unit_attributes = unit_attributes
        self._coordinator = coordinator
        self._unsub_coordinator = None
        self._calendar_entity = None
        self._current_event = None
        self._next_event = None

        # Entity properties
        self._attr_unique_id = f"vacasa_occupancy_{unit_id}"
        self._attr_name = f"Vacasa {name} Occupancy"
        self._attr_translation_key = SENSOR_OCCUPANCY
        self._attr_available = True

        # Set device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, unit_id)},
            "name": f"Vacasa {name}",
            "manufacturer": "Vacasa",
            "model": "Vacation Rental",
            "sw_version": "1.0",
        }

    @property
    def is_on(self) -> bool:
        """Return true if the property is currently occupied."""
        return self._current_event is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attrs = {}

        # Add next check-in information
        if self._next_event:
            attrs["next_checkin"] = self._format_datetime(self._next_event.start)
            attrs["next_checkout"] = self._format_datetime(self._next_event.end)

            # Extract guest name from event
            guest_name = self._extract_guest_name_from_event(self._next_event)
            if guest_name:
                attrs["next_guest"] = guest_name

            # Extract reservation type from event
            reservation_type = self._extract_reservation_type_from_event(
                self._next_event
            )
            if reservation_type:
                attrs["next_reservation_type"] = reservation_type

            # Log the next reservation details for debugging
            _LOGGER.debug(
                "Next reservation for %s: check-in=%s, check-out=%s, guest=%s, type=%s",
                self._name,
                attrs.get("next_checkin"),
                attrs.get("next_checkout"),
                attrs.get("next_guest", "Unknown"),
                attrs.get("next_reservation_type", "Unknown"),
            )

        # Add current reservation information if occupied
        if self._current_event:
            attrs["current_checkout"] = self._format_datetime(self._current_event.end)

            # Extract guest name from event
            guest_name = self._extract_guest_name_from_event(self._current_event)
            if guest_name:
                attrs["current_guest"] = guest_name

            # Extract reservation type from event
            reservation_type = self._extract_reservation_type_from_event(
                self._current_event
            )
            if reservation_type:
                attrs["current_reservation_type"] = reservation_type

            # Log the current reservation details for debugging
            _LOGGER.debug(
                "Current reservation for %s: check-out=%s, guest=%s, type=%s",
                self._name,
                attrs.get("current_checkout"),
                attrs.get("current_guest", "Unknown"),
                attrs.get("current_reservation_type", "Unknown"),
            )

        return attrs

    async def async_update(self) -> None:
        """Update the entity.

        This is only used by the generic entity update service.
        """
        await self._update_from_calendar()

    async def _update_from_calendar(self) -> None:
        """Update occupancy based on calendar events."""
        try:
            # Find the calendar entity for this unit with retry mechanism
            if not self._calendar_entity:
                self._calendar_entity = await self._find_calendar_entity_with_retry()
                if not self._calendar_entity:
                    _LOGGER.warning(
                        "Calendar entity not found for %s after retries, occupancy will be unavailable",
                        self._name,
                    )
                    self._attr_available = False
                    return

            # Get current events from the calendar
            await self._update_current_and_next_events()

        except Exception as err:
            _LOGGER.error(
                "Error updating occupancy from calendar for %s: %s", self._name, err
            )
            # Don't mark as unavailable for temporary issues
            # Keep last known state

    async def _find_calendar_entity_with_retry(
        self, max_retries: int = 3
    ) -> str | None:
        """Find calendar entity with retry mechanism for timing issues."""
        for attempt in range(max_retries):
            entity_id = await self._find_calendar_entity()
            if entity_id:
                return entity_id

            if attempt < max_retries - 1:
                # Exponential backoff: wait 2s, 4s, 8s between retries
                wait_time = 2 ** (attempt + 1)
                _LOGGER.debug(
                    "Calendar entity not found for unit %s, retrying in %ss (attempt %d/%d)",
                    self._unit_id,
                    wait_time,
                    attempt + 1,
                    max_retries,
                )
                await asyncio.sleep(wait_time)

        _LOGGER.warning(
            "Calendar entity not found for unit %s after %d attempts",
            self._unit_id,
            max_retries,
        )
        return None

    async def _find_calendar_entity(self) -> str | None:
        """Find the corresponding calendar entity ID for this unit."""
        # Generate possible entity IDs to try
        sanitized_name = self._sanitize_entity_name(self._name)
        possible_entity_ids = [
            f"calendar.vacasa_{sanitized_name}",
            f"calendar.vacasa_calendar_{self._unit_id}",
            f"calendar.vacasa_{self._unit_id}",
        ]

        _LOGGER.debug(
            "Searching for calendar entity for unit %s, trying: %s",
            self._unit_id,
            possible_entity_ids,
        )

        # First try: Check state registry (faster)
        for entity_id in possible_entity_ids:
            if self.hass.states.get(entity_id):
                _LOGGER.debug(
                    "Found calendar entity %s for unit %s (state check)",
                    entity_id,
                    self._unit_id,
                )
                return entity_id

        # Second try: Check entity registry (more reliable for newly created entities)
        try:
            registry = er.async_get(self.hass)
            calendar_unique_id = f"vacasa_calendar_{self._unit_id}"

            for entity_id, entity_entry in registry.entities.items():
                if (
                    entity_entry.unique_id == calendar_unique_id
                    and entity_entry.domain == "calendar"
                ):
                    _LOGGER.debug(
                        "Found calendar entity %s for unit %s (registry check)",
                        entity_id,
                        self._unit_id,
                    )
                    return entity_id

        except Exception as e:
            _LOGGER.debug(
                "Error checking entity registry for unit %s: %s", self._unit_id, e
            )

        _LOGGER.debug(
            "Calendar entity not found for unit %s (tried %s)",
            self._unit_id,
            possible_entity_ids,
        )
        return None

    def _sanitize_entity_name(self, name: str) -> str:
        """Sanitize property name for entity ID."""
        # Convert to lowercase and replace problematic characters
        sanitized = name.lower()
        sanitized = sanitized.replace(" ", "_")
        sanitized = sanitized.replace("-", "_")
        sanitized = sanitized.replace("'", "")
        sanitized = sanitized.replace('"', "")
        sanitized = sanitized.replace("(", "")
        sanitized = sanitized.replace(")", "")
        sanitized = sanitized.replace("&", "and")
        # Remove any other special characters and replace with underscore
        sanitized = re.sub(r"[^a-z0-9_]", "_", sanitized)
        # Remove multiple consecutive underscores
        sanitized = re.sub(r"_+", "_", sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip("_")
        return sanitized

    async def _update_current_and_next_events(self) -> None:
        """Update current and next events from the calendar."""
        if not self._calendar_entity:
            _LOGGER.debug("No calendar entity set for unit %s", self._unit_id)
            return

        # Reset current and next events
        self._current_event = None
        self._next_event = None

        try:
            # Get the calendar state
            calendar_state = self.hass.states.get(self._calendar_entity)
            if not calendar_state:
                _LOGGER.debug(
                    "Calendar entity %s found but state not yet available (unit %s) - this is normal during startup, will resolve automatically on next update",
                    self._calendar_entity,
                    self._unit_id,
                )

                # Add additional debugging info only if needed
                from homeassistant.helpers import entity_registry as er

                try:
                    registry = er.async_get(self.hass)
                    entity_entry = registry.async_get(self._calendar_entity)
                    if entity_entry:
                        _LOGGER.debug(
                            "Calendar entity %s registry details - unique_id: %s, platform: %s",
                            self._calendar_entity,
                            entity_entry.unique_id,
                            entity_entry.platform,
                        )
                    else:
                        _LOGGER.debug(
                            "Calendar entity %s not found in entity registry",
                            self._calendar_entity,
                        )
                except Exception as e:
                    _LOGGER.debug(
                        "Error checking entity registry for %s: %s",
                        self._calendar_entity,
                        e,
                    )

                return

            # Log calendar state info for debugging
            _LOGGER.debug(
                "Calendar entity %s state: %s, attributes: %s",
                self._calendar_entity,
                calendar_state.state,
                (
                    list(calendar_state.attributes.keys())
                    if calendar_state.attributes
                    else "None"
                ),
            )

            # Check if there's a current event
            if calendar_state.state == "on":
                # There's an active event, get it from attributes
                current_event_summary = calendar_state.attributes.get("message", "")
                current_event_start = calendar_state.attributes.get("start_time")
                current_event_end = calendar_state.attributes.get("end_time")

                if current_event_summary and current_event_start and current_event_end:
                    # Create a simple event object
                    self._current_event = type(
                        "Event",
                        (),
                        {
                            "summary": current_event_summary,
                            "start": dt_util.parse_datetime(current_event_start),
                            "end": dt_util.parse_datetime(current_event_end),
                        },
                    )()

                    _LOGGER.debug(
                        "Found current event for %s: %s (%s to %s)",
                        self._name,
                        self._current_event.summary,
                        self._current_event.start,
                        self._current_event.end,
                    )

            # For finding next event, we'll need to call the calendar platform directly
            # This is a simplified approach - we'll just use the current event for now
            # and implement next event detection in a future update if needed

            # Log results
            if self._current_event:
                _LOGGER.debug(
                    "Current event for %s: %s",
                    self._name,
                    self._current_event.summary,
                )
            else:
                _LOGGER.debug("No current event for %s", self._name)

        except Exception as err:
            _LOGGER.error("Error getting calendar events for %s: %s", self._name, err)

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()

        # Listen to coordinator updates first
        self._unsub_coordinator = self._coordinator.async_add_listener(
            self._handle_coordinator_update
        )

        # Schedule initial calendar update with slight delay to allow calendar entities to load
        self.hass.async_create_task(self._delayed_initial_update())

    async def _delayed_initial_update(self) -> None:
        """Perform initial update with a small delay to allow calendar entities to be ready."""
        # Wait a bit for calendar entities to be fully loaded
        await asyncio.sleep(1)
        await self._update_from_calendar()
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from hass."""
        if self._unsub_coordinator:
            self._unsub_coordinator()
            self._unsub_coordinator = None
        await super().async_will_remove_from_hass()

    def _handle_coordinator_update(self) -> None:
        """Handle coordinator update."""
        # Update from calendar when coordinator updates
        self.hass.async_create_task(self._async_coordinator_update())

    async def _async_coordinator_update(self) -> None:
        """Handle coordinator update asynchronously."""
        try:
            self._attr_available = True
            await self._update_from_calendar()
            self.async_write_ha_state()
            _LOGGER.debug("Successfully updated occupancy for unit %s", self._unit_id)
        except Exception as err:
            _LOGGER.warning(
                "Error during coordinator update for unit %s: %s", self._unit_id, err
            )
            # Don't mark as unavailable for temporary API issues
            # Keep last known state

    def _extract_guest_name_from_event(self, event) -> str | None:
        """Extract guest name from calendar event summary."""
        if not event or not event.summary:
            return None

        # Calendar event summaries are formatted like:
        # "Guest Booking: John Doe"
        # "Owner Stay: Jane Smith"
        # "Block: Maintenance"
        # etc.

        summary = event.summary
        if ":" in summary:
            # Split on the first colon and get the part after it
            parts = summary.split(":", 1)
            if len(parts) > 1:
                guest_part = parts[1].strip()
                # Only return if it looks like a name (not empty, not just a type)
                if guest_part and guest_part not in ["Maintenance", "Block", "Other"]:
                    return guest_part

        return None

    def _extract_reservation_type_from_event(self, event) -> str | None:
        """Extract reservation type from calendar event summary."""
        if not event or not event.summary:
            return None

        # Calendar event summaries are formatted like:
        # "Guest Booking: John Doe"
        # "Owner Stay: Jane Smith"
        # "Block: Maintenance"
        # etc.

        summary = event.summary
        if ":" in summary:
            # Split on the first colon and get the part before it
            parts = summary.split(":", 1)
            if len(parts) > 0:
                type_part = parts[0].strip()
                # Return the reservation type
                return type_part

        # Fallback - return the whole summary if no colon
        return summary

    def _format_datetime(self, dt: datetime | None) -> str | None:
        """Format a datetime for display."""
        if not dt:
            return None

        return dt.strftime("%Y-%m-%d %H:%M:%S")
