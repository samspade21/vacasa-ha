"""Binary sensor platform for Vacasa integration."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import VacasaConfigEntry, VacasaDataUpdateCoordinator
from .const import DOMAIN, SENSOR_OCCUPANCY, SIGNAL_RESERVATION_STATE
from .models import ReservationState, ReservationWindow

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: VacasaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Vacasa binary sensor platform."""
    _LOGGER.debug("Setting up Vacasa binary sensor platform")

    data = config_entry.runtime_data
    client = data.client
    coordinator = data.coordinator

    try:
        units = await client.get_units()
        _LOGGER.info("Found %d Vacasa units for binary sensors", len(units))

        entities: list[VacasaOccupancySensor] = []
        for unit in units:
            unit_id = unit.get("id")
            attributes = unit.get("attributes", {})
            name = attributes.get("name", f"Vacasa Unit {unit_id}")
            code = attributes.get("code", "")

            entities.append(
                VacasaOccupancySensor(
                    coordinator=coordinator,
                    client=client,
                    unit_id=unit_id,
                    name=name,
                    code=code,
                    unit_attributes=attributes,
                )
            )

        async_add_entities(entities, True)
    except Exception as err:  # pragma: no cover - defensive logging
        _LOGGER.error("Error setting up Vacasa binary sensors: %s", err)
        import traceback

        _LOGGER.debug("Full traceback: %s", traceback.format_exc())


class VacasaOccupancySensor(CoordinatorEntity[VacasaDataUpdateCoordinator], BinarySensorEntity):
    """Representation of a Vacasa occupancy sensor."""

    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY

    def __init__(
        self,
        coordinator: VacasaDataUpdateCoordinator,
        client,
        unit_id,
        name,
        code,
        unit_attributes,
    ) -> None:
        """Initialize the Vacasa occupancy sensor."""
        super().__init__(coordinator)
        self._client = client
        self._unit_id = unit_id
        self._name = name
        self._code = code
        self._unit_attributes = unit_attributes
        self._current_reservation: ReservationWindow | None = None
        self._next_reservation: ReservationWindow | None = None

        self._attr_unique_id = f"vacasa_occupancy_{unit_id}"
        self._attr_name = f"Vacasa {name} Occupancy"
        self._attr_translation_key = SENSOR_OCCUPANCY
        self._attr_available = False

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
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional reservation metadata."""
        attrs: dict[str, Any] = {}

        if self._next_reservation:
            attrs["next_checkin"] = self._format_datetime(self._next_reservation.start)
            attrs["next_checkout"] = self._format_datetime(self._next_reservation.end)

            guest_name = self._extract_guest_name_from_window(self._next_reservation)
            if guest_name:
                attrs["next_guest"] = guest_name

            reservation_type = self._extract_reservation_type_from_window(self._next_reservation)
            if reservation_type:
                attrs["next_reservation_type"] = reservation_type

        if self._current_reservation:
            attrs["current_checkout"] = self._format_datetime(self._current_reservation.end)

            guest_name = self._extract_guest_name_from_window(self._current_reservation)
            if guest_name:
                attrs["current_guest"] = guest_name

            reservation_type = self._extract_reservation_type_from_window(self._current_reservation)
            if reservation_type:
                attrs["current_reservation_type"] = reservation_type

        return attrs

    async def async_added_to_hass(self) -> None:
        """Register listeners once added to hass."""
        await super().async_added_to_hass()

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_RESERVATION_STATE,
                self._handle_reservation_state,
            )
        )

        self._refresh_from_coordinator()

    async def async_update(self) -> None:
        """Request a refresh from the coordinator."""
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update reservation data from the coordinator."""
        self._refresh_from_coordinator()
        super()._handle_coordinator_update()

    def _refresh_from_coordinator(self) -> None:
        """Load reservation state from the shared coordinator cache."""
        state = self.coordinator.reservation_states.get(self._unit_id)
        if state is None:
            return
        self._update_from_state(state)

    def _handle_reservation_state(self, unit_id: str, state: ReservationState) -> None:
        """Handle reservation updates sent by the calendar entities."""
        if unit_id != self._unit_id:
            return

        self._update_from_state(state)
        self.async_write_ha_state()

    def _update_from_state(self, state: ReservationState) -> None:
        """Store reservation state and mark availability."""
        self._current_reservation = state.current
        self._next_reservation = state.upcoming
        self._attr_available = True

    def _extract_guest_name_from_window(self, window: ReservationWindow) -> str | None:
        """Extract guest name from reservation summary."""
        if not window or not window.summary:
            return None

        summary = window.summary
        if ":" in summary:
            parts = summary.split(":", 1)
            if len(parts) > 1:
                guest_part = parts[1].strip()
                if guest_part and guest_part not in ["Maintenance", "Block", "Other"]:
                    return guest_part
        return None

    def _extract_reservation_type_from_window(self, window: ReservationWindow) -> str | None:
        """Extract reservation type from reservation summary."""
        if not window or not window.summary:
            return None

        summary = window.summary
        if ":" in summary:
            parts = summary.split(":", 1)
            if parts:
                return parts[0].strip()
        return summary

    def _format_datetime(self, dt: datetime | None) -> str | None:
        """Format a datetime for display."""
        if not dt:
            return None
        return dt_util.as_local(dt).strftime("%Y-%m-%d %H:%M:%S")
