"""Binary sensor platform for Vacasa integration."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

# DataUpdateCoordinator import removed - using coordinator listening pattern instead
from homeassistant.util import dt as dt_util

from .const import (
    DATA_CLIENT,
    DATA_COORDINATOR,
    DOMAIN,
    SENSOR_OCCUPANCY,
    STAY_TYPE_BLOCK,
    STAY_TYPE_GUEST,
    STAY_TYPE_MAINTENANCE,
    STAY_TYPE_OTHER,
    STAY_TYPE_OWNER,
)

_LOGGER = logging.getLogger(__name__)

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
    """Set up the Vacasa binary sensor platform."""
    client = hass.data[DOMAIN][config_entry.entry_id][DATA_CLIENT]
    coordinator = hass.data[DOMAIN][config_entry.entry_id][DATA_COORDINATOR]

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
        self._checkin_time = unit_attributes.get("checkInTime")
        self._checkout_time = unit_attributes.get("checkOutTime")
        self._timezone = unit_attributes.get("timezone")
        self._categorized_reservations = {}
        self._current_reservation = None
        self._current_stay_type = None
        self._next_reservation = None
        self._next_stay_type = None
        self._coordinator = coordinator
        self._unsub_coordinator = None

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
        return self._current_reservation is not None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return the state attributes."""
        attrs = {}

        # Add next check-in information
        if self._next_reservation:
            checkin_dt = self._get_checkin_datetime(self._next_reservation)
            checkout_dt = self._get_checkout_datetime(self._next_reservation)

            attrs["next_checkin"] = self._format_datetime(checkin_dt)
            attrs["next_checkout"] = self._format_datetime(checkout_dt)

            # Add guest information if available
            guest_name = self._get_guest_name(self._next_reservation)
            if guest_name:
                attrs["next_guest"] = guest_name

            # Add reservation type
            if self._next_stay_type:
                attrs["next_reservation_type"] = STAY_TYPE_TO_NAME.get(
                    self._next_stay_type, "Unknown"
                )

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
        if self._current_reservation:
            checkout_dt = self._get_checkout_datetime(self._current_reservation)

            attrs["current_checkout"] = self._format_datetime(checkout_dt)

            # Add guest information if available
            guest_name = self._get_guest_name(self._current_reservation)
            if guest_name:
                attrs["current_guest"] = guest_name

            # Add reservation type
            if self._current_stay_type:
                attrs["current_reservation_type"] = STAY_TYPE_TO_NAME.get(
                    self._current_stay_type, "Unknown"
                )

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
        await self._update_reservations()

    async def _update_reservations(self) -> None:
        """Update the reservations data."""
        try:
            # Get current date in YYYY-MM-DD format
            now = dt_util.now()
            start_date = now.strftime("%Y-%m-%d")

            # Get reservations for the next 365 days
            end_date = (now + timedelta(days=365)).strftime("%Y-%m-%d")

            # Use the get_categorized_reservations method to get properly categorized reservations
            self._categorized_reservations = (
                await self._client.get_categorized_reservations(
                    self._unit_id, start_date, end_date
                )
            )

            _LOGGER.debug(
                "Retrieved categorized reservations for %s: %s",
                self._name,
                {k: len(v) for k, v in self._categorized_reservations.items()},
            )

            # Update current and next reservations
            self._update_current_and_next_reservations()

        except Exception as err:
            _LOGGER.error("Error updating reservations for %s: %s", self._name, err)

    def _update_current_and_next_reservations(self) -> None:
        """Update the current and next reservation information."""
        now = dt_util.now()

        # Reset current and next reservation info
        self._current_reservation = None
        self._current_stay_type = None
        self._next_reservation = None
        self._next_stay_type = None

        # Find the current reservation (if any)
        for stay_type, reservations in self._categorized_reservations.items():
            for reservation in reservations:
                checkin = self._get_checkin_datetime(reservation)
                checkout = self._get_checkout_datetime(reservation)

                if checkin and checkout and checkin <= now <= checkout:
                    self._current_reservation = reservation
                    self._current_stay_type = stay_type
                    _LOGGER.debug(
                        "Found current %s reservation for %s: %s to %s",
                        stay_type,
                        self._name,
                        checkin,
                        checkout,
                    )
                    break

            # If we found a current reservation, no need to check other stay types
            if self._current_reservation:
                break

        # Find the next reservation
        next_checkin = None

        for stay_type, reservations in self._categorized_reservations.items():
            for reservation in reservations:
                checkin = self._get_checkin_datetime(reservation)

                # Skip if this is the current reservation or if check-in is in the past
                if (
                    reservation == self._current_reservation
                    or not checkin
                    or checkin <= now
                ):
                    continue

                # If this is the first future reservation we've found, or it's earlier than the current next
                if next_checkin is None or checkin < next_checkin:
                    self._next_reservation = reservation
                    self._next_stay_type = stay_type
                    next_checkin = checkin
                    _LOGGER.debug(
                        "Found next %s reservation for %s: check-in at %s",
                        stay_type,
                        self._name,
                        checkin,
                    )

        # Log the results
        if self._current_reservation:
            _LOGGER.debug(
                "Current reservation for %s: %s (%s)",
                self._name,
                self._get_guest_name(self._current_reservation) or "Unknown",
                self._current_stay_type,
            )
        else:
            _LOGGER.debug("No current reservation for %s", self._name)

        if self._next_reservation:
            _LOGGER.debug(
                "Next reservation for %s: %s (%s) at %s",
                self._name,
                self._get_guest_name(self._next_reservation) or "Unknown",
                self._next_stay_type,
                next_checkin,
            )
        else:
            _LOGGER.debug("No upcoming reservations for %s", self._name)

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        # Update reservations when entity is added to hass
        await self._update_reservations()

        # Listen to coordinator updates without inheriting from CoordinatorEntity
        self._unsub_coordinator = self._coordinator.async_add_listener(
            self._handle_coordinator_update
        )

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from hass."""
        if self._unsub_coordinator:
            self._unsub_coordinator()
            self._unsub_coordinator = None
        await super().async_will_remove_from_hass()

    def _handle_coordinator_update(self) -> None:
        """Handle coordinator update."""
        # Update reservations when coordinator updates
        self.hass.async_create_task(self._async_coordinator_update())

    async def _async_coordinator_update(self) -> None:
        """Handle coordinator update asynchronously."""
        try:
            self._attr_available = True
            await self._update_reservations()
            self.async_write_ha_state()
        except Exception as err:
            _LOGGER.warning(
                "Error during coordinator update for %s: %s", self._name, err
            )
            # Don't mark as unavailable for temporary API issues
            # Keep last known state

    def _get_checkin_datetime(self, reservation: Dict[str, Any]) -> Optional[datetime]:
        """Get the check-in datetime for a reservation."""
        attributes = reservation.get("attributes", {})
        start_date = attributes.get("startDate")

        if not start_date:
            return None

        # Create datetime string based on available information
        if "checkinTime" in attributes and attributes["checkinTime"] not in [
            "00:00:00",
            "12:00:00",
        ]:
            # Use time from reservation
            checkin_time = attributes["checkinTime"]
            start_dt_str = f"{start_date}T{checkin_time}"
        elif self._checkin_time:
            # Use property-specific time
            start_dt_str = f"{start_date}T{self._checkin_time}"
        else:
            # No time available, use date only
            start_dt_str = f"{start_date}T00:00:00"

        # Parse the datetime
        checkin_dt = dt_util.parse_datetime(start_dt_str)

        if not checkin_dt:
            return None

        # Apply property timezone if available
        if self._timezone and "T00:00:00" not in start_dt_str:
            try:
                # Use zoneinfo instead of pytz to avoid blocking calls
                tz = ZoneInfo(self._timezone)
                # Create naive datetime first, then localize it
                naive_dt = checkin_dt.replace(tzinfo=None)
                localized_dt = naive_dt.replace(tzinfo=tz)
                _LOGGER.debug(
                    "Applied timezone %s to check-in: %s -> %s",
                    self._timezone,
                    naive_dt,
                    localized_dt,
                )
                return localized_dt
            except Exception as e:
                _LOGGER.warning("Error applying timezone %s: %s", self._timezone, e)
                # Fall back to local timezone
                return dt_util.as_local(checkin_dt)
        else:
            # Use default check-in time (4 PM) if no specific time available
            if "T00:00:00" in start_dt_str:
                # Replace midnight with 4 PM for check-in
                start_dt_str = start_dt_str.replace("T00:00:00", "T16:00:00")
                checkin_dt = dt_util.parse_datetime(start_dt_str)
                if not checkin_dt:
                    return None
                _LOGGER.debug(
                    "Using default check-in time (4 PM) for %s: %s",
                    self._name,
                    checkin_dt,
                )
            # Fall back to local timezone
            return dt_util.as_local(checkin_dt)

    def _get_checkout_datetime(self, reservation: Dict[str, Any]) -> Optional[datetime]:
        """Get the check-out datetime for a reservation."""
        attributes = reservation.get("attributes", {})
        end_date = attributes.get("endDate")

        if not end_date:
            return None

        # Create datetime string based on available information
        if "checkoutTime" in attributes and attributes["checkoutTime"] not in [
            "00:00:00",
            "12:00:00",
        ]:
            # Use time from reservation
            checkout_time = attributes["checkoutTime"]
            end_dt_str = f"{end_date}T{checkout_time}"
        elif self._checkout_time:
            # Use property-specific time
            end_dt_str = f"{end_date}T{self._checkout_time}"
        else:
            # No time available, use date only
            end_dt_str = f"{end_date}T00:00:00"

        # Parse the datetime
        checkout_dt = dt_util.parse_datetime(end_dt_str)

        if not checkout_dt:
            return None

        # Apply property timezone if available
        if self._timezone and "T00:00:00" not in end_dt_str:
            try:
                # Use zoneinfo instead of pytz to avoid blocking calls
                tz = ZoneInfo(self._timezone)
                # Create naive datetime first, then localize it
                naive_dt = checkout_dt.replace(tzinfo=None)
                localized_dt = naive_dt.replace(tzinfo=tz)
                _LOGGER.debug(
                    "Applied timezone %s to check-out: %s -> %s",
                    self._timezone,
                    naive_dt,
                    localized_dt,
                )
                return localized_dt
            except Exception as e:
                _LOGGER.warning("Error applying timezone %s: %s", self._timezone, e)
                # Fall back to local timezone
                return dt_util.as_local(checkout_dt)
        else:
            # Use default check-out time (10 AM) if no specific time available
            if "T00:00:00" in end_dt_str:
                # Replace midnight with 10 AM for check-out
                end_dt_str = end_dt_str.replace("T00:00:00", "T10:00:00")
                checkout_dt = dt_util.parse_datetime(end_dt_str)
                if not checkout_dt:
                    return None
                _LOGGER.debug(
                    "Using default check-out time (10 AM) for %s: %s",
                    self._name,
                    checkout_dt,
                )
            # Fall back to local timezone
            return dt_util.as_local(checkout_dt)

    def _get_guest_name(self, reservation: Dict[str, Any]) -> Optional[str]:
        """Get the guest name for a reservation."""
        attributes = reservation.get("attributes", {})
        first_name = attributes.get("firstName", "")
        last_name = attributes.get("lastName", "")

        if first_name and last_name:
            return f"{first_name} {last_name}"
        elif first_name:
            return first_name
        elif last_name:
            return last_name

        # Check for owner hold information
        owner_hold = attributes.get("ownerHold")
        if owner_hold:
            hold_who_booked = owner_hold.get("holdWhoBooked", "")
            if hold_who_booked:
                return hold_who_booked

        return None

    def _format_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Format a datetime for display."""
        if not dt:
            return None

        return dt.strftime("%Y-%m-%d %H:%M:%S")
