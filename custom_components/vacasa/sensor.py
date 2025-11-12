"""Sensor platform for Vacasa integration."""

import asyncio
import logging
from contextlib import suppress
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import VacasaConfigEntry
from .api_client import ApiError, AuthenticationError
from .const import (
    CONF_USERNAME,
    DOMAIN,
    SENSOR_ADDRESS,
    SENSOR_BATHROOMS,
    SENSOR_BEDROOMS,
    SENSOR_HOME_STATUS,
    SENSOR_HOT_TUB,
    SENSOR_LOCATION,
    SENSOR_MAINTENANCE_OPEN,
    SENSOR_MAX_ADULTS,
    SENSOR_MAX_CHILDREN,
    SENSOR_MAX_OCCUPANCY,
    SENSOR_MAX_PETS,
    SENSOR_NEXT_STAY,
    SENSOR_PARKING,
    SENSOR_PET_FRIENDLY,
    SENSOR_RATING,
    SENSOR_STATEMENTS_TOTAL,
    SENSOR_TIMEZONE,
    STAY_TYPE_GUEST,
    STAY_TYPE_TO_CATEGORY,
    STAY_TYPE_TO_NAME,
)

# Removed CoordinatorEntity import - these sensors contain static property data


_LOGGER = logging.getLogger(__name__)


class VacasaBaseSensor(SensorEntity):
    """Base class for Vacasa sensors."""

    def __init__(
        self,
        coordinator,
        unit_id: str,
        name: str,
        unit_attributes: dict[str, Any],
        sensor_type: str,
        icon: str = "mdi:home",
        device_class: str | None = None,
        state_class: str | None = None,
    ) -> None:
        """Initialize the Vacasa sensor."""
        super().__init__()
        # Store coordinator reference but don't inherit from CoordinatorEntity
        # These sensors contain static property data that rarely changes
        self._coordinator = coordinator
        self._unit_id = unit_id
        self._name = name
        self._unit_attributes = unit_attributes
        self._sensor_type = sensor_type
        self._attr_icon = icon

        if device_class:
            self._attr_device_class = device_class

        if state_class:
            self._attr_state_class = state_class

        # Entity properties
        self._attr_unique_id = f"vacasa_{sensor_type}_{unit_id}"
        self._attr_name = sensor_type.replace('_', ' ').title()
        self._attr_has_entity_name = True

        # Set device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, unit_id)},
            "name": f"Vacasa {name}",
            "manufacturer": "Vacasa",
            "model": "Vacation Rental",
            "sw_version": "1.0",
        }


class VacasaApiUpdateMixin:
    """Mixin to throttle API-backed sensors to the coordinator refresh."""

    _refresh_task: asyncio.Task[None] | None

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002,ANN003
        """Initialize API update mixin."""
        self._update_lock = asyncio.Lock()
        self._refresh_task = None
        super().__init__(*args, **kwargs)
        self._attr_should_poll = False

    async def async_added_to_hass(self) -> None:
        """Register coordinator listener when added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._coordinator.async_add_listener(self._handle_coordinator_refresh)
        )
        await self.async_update()

    async def async_update(self) -> None:
        """Update entity state from API."""
        task = self._ensure_refresh_task()
        if task is not None:
            await task

    async def async_will_remove_from_hass(self) -> None:
        """Clean up refresh task when removed from hass."""
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._refresh_task
        await super().async_will_remove_from_hass()

    def _ensure_refresh_task(self) -> asyncio.Task[None] | None:
        if self.hass is None:
            return None
        if self._refresh_task is None or self._refresh_task.done():
            self._refresh_task = self.hass.async_create_task(
                self._async_refresh_from_api()
            )
        return self._refresh_task

    async def _async_refresh_from_api(self) -> None:
        current_task = asyncio.current_task()
        try:
            async with self._update_lock:
                await self._async_update_from_api()
        finally:
            if self._refresh_task is current_task:
                self._refresh_task = None
            # Only write state if entity is registered (has entity_id)
            if self.hass is not None and self.entity_id is not None:
                self.async_write_ha_state()

    @callback
    def _handle_coordinator_refresh(self) -> None:
        self._ensure_refresh_task()

    async def _async_update_from_api(self) -> None:
        """Fetch data from the Vacasa API."""
        raise NotImplementedError


class VacasaRatingSensor(VacasaBaseSensor):
    """Sensor for Vacasa property rating."""

    def __init__(
        self,
        coordinator,
        unit_id: str,
        name: str,
        unit_attributes: dict[str, Any],
    ) -> None:
        """Initialize the rating sensor."""
        super().__init__(
            coordinator=coordinator,
            unit_id=unit_id,
            name=name,
            unit_attributes=unit_attributes,
            sensor_type=SENSOR_RATING,
            icon="mdi:star",
            state_class=SensorStateClass.MEASUREMENT,
        )
        self._attr_native_unit_of_measurement = "★"

    @property
    def native_value(self) -> float | None:
        """Return the rating value."""
        return self._unit_attributes.get("rating")


class VacasaLocationSensor(VacasaBaseSensor):
    """Sensor for Vacasa property location."""

    def __init__(
        self,
        coordinator,
        unit_id: str,
        name: str,
        unit_attributes: dict[str, Any],
    ) -> None:
        """Initialize the location sensor."""
        super().__init__(
            coordinator=coordinator,
            unit_id=unit_id,
            name=name,
            unit_attributes=unit_attributes,
            sensor_type=SENSOR_LOCATION,
            icon="mdi:map-marker",
        )

    @property
    def native_value(self) -> str | None:
        """Return the location value."""
        location = self._unit_attributes.get("location", {})
        if location and "lat" in location and "lng" in location:
            return f"{location['lat']},{location['lng']}"
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        location = self._unit_attributes.get("location", {})
        if location and "lat" in location and "lng" in location:
            return {
                "latitude": location["lat"],
                "longitude": location["lng"],
            }
        return {}


class VacasaTimezoneSensor(VacasaBaseSensor):
    """Sensor for Vacasa property timezone."""

    def __init__(
        self,
        coordinator,
        unit_id: str,
        name: str,
        unit_attributes: dict[str, Any],
    ) -> None:
        """Initialize the timezone sensor."""
        super().__init__(
            coordinator=coordinator,
            unit_id=unit_id,
            name=name,
            unit_attributes=unit_attributes,
            sensor_type=SENSOR_TIMEZONE,
            icon="mdi:clock-time-eight-outline",
        )

    @property
    def native_value(self) -> str | None:
        """Return the timezone value."""
        return self._unit_attributes.get("timezone")


class VacasaMaxOccupancySensor(VacasaBaseSensor):
    """Sensor for Vacasa property max occupancy."""

    def __init__(
        self,
        coordinator,
        unit_id: str,
        name: str,
        unit_attributes: dict[str, Any],
    ) -> None:
        """Initialize the max occupancy sensor."""
        super().__init__(
            coordinator=coordinator,
            unit_id=unit_id,
            name=name,
            unit_attributes=unit_attributes,
            sensor_type=SENSOR_MAX_OCCUPANCY,
            icon="mdi:account-group",
            state_class=SensorStateClass.MEASUREMENT,
        )
        self._attr_native_unit_of_measurement = "people"

    @property
    def native_value(self) -> int | None:
        """Return the max occupancy value."""
        return self._unit_attributes.get("maxOccupancyTotal")


class VacasaMaxAdultsSensor(VacasaBaseSensor):
    """Sensor for Vacasa property max adults."""

    def __init__(
        self,
        coordinator,
        unit_id: str,
        name: str,
        unit_attributes: dict[str, Any],
    ) -> None:
        """Initialize the max adults sensor."""
        super().__init__(
            coordinator=coordinator,
            unit_id=unit_id,
            name=name,
            unit_attributes=unit_attributes,
            sensor_type=SENSOR_MAX_ADULTS,
            icon="mdi:account",
            state_class=SensorStateClass.MEASUREMENT,
        )
        self._attr_native_unit_of_measurement = "people"

    @property
    def native_value(self) -> int | None:
        """Return the max adults value."""
        return self._unit_attributes.get("maxAdults")


class VacasaMaxChildrenSensor(VacasaBaseSensor):
    """Sensor for Vacasa property max children."""

    def __init__(
        self,
        coordinator,
        unit_id: str,
        name: str,
        unit_attributes: dict[str, Any],
    ) -> None:
        """Initialize the max children sensor."""
        super().__init__(
            coordinator=coordinator,
            unit_id=unit_id,
            name=name,
            unit_attributes=unit_attributes,
            sensor_type=SENSOR_MAX_CHILDREN,
            icon="mdi:account-child",
            state_class=SensorStateClass.MEASUREMENT,
        )
        self._attr_native_unit_of_measurement = "people"

    @property
    def native_value(self) -> int | None:
        """Return the max children value."""
        return self._unit_attributes.get("maxChildren")


class VacasaMaxPetsSensor(VacasaBaseSensor):
    """Sensor for Vacasa property max pets."""

    def __init__(
        self,
        coordinator,
        unit_id: str,
        name: str,
        unit_attributes: dict[str, Any],
    ) -> None:
        """Initialize the max pets sensor."""
        super().__init__(
            coordinator=coordinator,
            unit_id=unit_id,
            name=name,
            unit_attributes=unit_attributes,
            sensor_type=SENSOR_MAX_PETS,
            icon="mdi:paw",
            state_class=SensorStateClass.MEASUREMENT,
        )
        self._attr_native_unit_of_measurement = "pets"

    @property
    def native_value(self) -> int | None:
        """Return the max pets value."""
        return self._unit_attributes.get("maxPets")


class VacasaBedroomsSensor(VacasaBaseSensor):
    """Sensor for Vacasa property bedrooms."""

    def __init__(
        self,
        coordinator,
        unit_id: str,
        name: str,
        unit_attributes: dict[str, Any],
    ) -> None:
        """Initialize the bedrooms sensor."""
        super().__init__(
            coordinator=coordinator,
            unit_id=unit_id,
            name=name,
            unit_attributes=unit_attributes,
            sensor_type=SENSOR_BEDROOMS,
            icon="mdi:bed",
            state_class=SensorStateClass.MEASUREMENT,
        )
        self._attr_native_unit_of_measurement = "rooms"

    @property
    def native_value(self) -> int | None:
        """Return the bedrooms value."""
        amenities = self._unit_attributes.get("amenities", {})
        rooms = amenities.get("rooms", {})
        return rooms.get("bedrooms") if rooms else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        amenities = self._unit_attributes.get("amenities", {})
        beds = amenities.get("beds", {})

        attributes = {}
        if beds:
            for bed_type, count in beds.items():
                if count and bed_type != "child":  # Skip child beds as they're not real beds
                    attributes[f"{bed_type}_beds"] = count

        return attributes


class VacasaBathroomsSensor(VacasaBaseSensor):
    """Sensor for Vacasa property bathrooms."""

    def __init__(
        self,
        coordinator,
        unit_id: str,
        name: str,
        unit_attributes: dict[str, Any],
    ) -> None:
        """Initialize the bathrooms sensor."""
        super().__init__(
            coordinator=coordinator,
            unit_id=unit_id,
            name=name,
            unit_attributes=unit_attributes,
            sensor_type=SENSOR_BATHROOMS,
            icon="mdi:shower",
            state_class=SensorStateClass.MEASUREMENT,
        )
        self._attr_native_unit_of_measurement = "rooms"

    @property
    def native_value(self) -> float | None:
        """Return the bathrooms value."""
        amenities = self._unit_attributes.get("amenities", {})
        rooms = amenities.get("rooms", {})
        bathrooms = rooms.get("bathrooms", {}) if rooms else {}

        if bathrooms:
            full = bathrooms.get("full", 0)
            half = bathrooms.get("half", 0)
            return full + (half * 0.5)

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        amenities = self._unit_attributes.get("amenities", {})
        rooms = amenities.get("rooms", {})
        bathrooms = rooms.get("bathrooms", {}) if rooms else {}

        attributes = {}
        if bathrooms:
            attributes["full_bathrooms"] = bathrooms.get("full", 0)
            attributes["half_bathrooms"] = bathrooms.get("half", 0)

        return attributes


class VacasaHotTubSensor(VacasaBaseSensor):
    """Sensor for Vacasa property hot tub."""

    def __init__(
        self,
        coordinator,
        unit_id: str,
        name: str,
        unit_attributes: dict[str, Any],
    ) -> None:
        """Initialize the hot tub sensor."""
        super().__init__(
            coordinator=coordinator,
            unit_id=unit_id,
            name=name,
            unit_attributes=unit_attributes,
            sensor_type=SENSOR_HOT_TUB,
            icon="mdi:hot-tub",
        )

    @property
    def native_value(self) -> str | None:
        """Return the hot tub value."""
        amenities = self._unit_attributes.get("amenities", {})
        hot_tub = amenities.get("hotTub")

        if hot_tub is not None:
            return "Yes" if hot_tub else "No"

        return None


class VacasaPetFriendlySensor(VacasaBaseSensor):
    """Sensor for Vacasa property pet friendly status."""

    def __init__(
        self,
        coordinator,
        unit_id: str,
        name: str,
        unit_attributes: dict[str, Any],
    ) -> None:
        """Initialize the pet friendly sensor."""
        super().__init__(
            coordinator=coordinator,
            unit_id=unit_id,
            name=name,
            unit_attributes=unit_attributes,
            sensor_type=SENSOR_PET_FRIENDLY,
            icon="mdi:paw",
        )

    @property
    def native_value(self) -> str | None:
        """Return the pet friendly value."""
        amenities = self._unit_attributes.get("amenities", {})
        pet_friendly = amenities.get("petsFriendly")

        if pet_friendly is not None:
            return "Yes" if pet_friendly else "No"

        return None


class VacasaParkingSensor(VacasaBaseSensor):
    """Sensor for Vacasa property parking."""

    def __init__(
        self,
        coordinator,
        unit_id: str,
        name: str,
        unit_attributes: dict[str, Any],
    ) -> None:
        """Initialize the parking sensor."""
        super().__init__(
            coordinator=coordinator,
            unit_id=unit_id,
            name=name,
            unit_attributes=unit_attributes,
            sensor_type=SENSOR_PARKING,
            icon="mdi:car",
            state_class=SensorStateClass.MEASUREMENT,
        )
        self._attr_native_unit_of_measurement = "spaces"

    @property
    def native_value(self) -> int | None:
        """Return the parking value."""
        parking = self._unit_attributes.get("parking", {})
        return parking.get("total") if parking else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        parking = self._unit_attributes.get("parking", {})

        attributes = {}
        if parking:
            if "notes" in parking and parking["notes"]:
                attributes["notes"] = parking["notes"]

            for key in [
                "accessible",
                "fourWheelDriveRequired",
                "paid",
                "street",
                "valet",
            ]:
                if key in parking:
                    # Convert -1 to None for better display
                    value = parking[key]
                    if value == -1:
                        value = None
                    attributes[key] = value

        return attributes


class VacasaAddressSensor(VacasaBaseSensor):
    """Sensor for Vacasa property address."""

    def __init__(
        self,
        coordinator,
        unit_id: str,
        name: str,
        unit_attributes: dict[str, Any],
    ) -> None:
        """Initialize the address sensor."""
        super().__init__(
            coordinator=coordinator,
            unit_id=unit_id,
            name=name,
            unit_attributes=unit_attributes,
            sensor_type=SENSOR_ADDRESS,
            icon="mdi:map-marker",
        )

    @property
    def native_value(self) -> str | None:
        """Return the address value."""
        address = self._unit_attributes.get("address", {})
        if not address:
            return None

        parts = []
        if address.get("address_1"):
            parts.append(address["address_1"])

        if address.get("address_2"):
            parts.append(address["address_2"])

        city_state_zip = []
        if address.get("city"):
            city_state_zip.append(address["city"])

        if address.get("state"):
            city_state_zip.append(address["state"])

        if address.get("zip"):
            city_state_zip.append(address["zip"])

        if city_state_zip:
            parts.append(", ".join(city_state_zip))

        country = address.get("country", {})
        if country and country.get("name"):
            parts.append(country["name"])

        return ", ".join(parts) if parts else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        address = self._unit_attributes.get("address", {})

        attributes = {}
        if address:
            for key in ["address_1", "address_2", "city", "state", "zip"]:
                if key in address and address[key]:
                    attributes[key] = address[key]

            country = address.get("country", {})
            if country:
                if country.get("name"):
                    attributes["country"] = country["name"]
                if country.get("code"):
                    attributes["country_code"] = country["code"]

        return attributes


class VacasaHomeInfoSensor(VacasaApiUpdateMixin, VacasaBaseSensor):
    """Sensor exposing home inspection and cleanliness information."""

    def __init__(
        self,
        coordinator,
        unit_id: str,
        name: str,
        unit_attributes: dict[str, Any],
    ) -> None:
        """Initialize home info sensor."""
        super().__init__(
            coordinator=coordinator,
            unit_id=unit_id,
            name=name,
            unit_attributes=unit_attributes,
            sensor_type=SENSOR_HOME_STATUS,
            icon="mdi:home-analytics",
        )
        self._home_info: dict[str, Any] = {}

    async def _async_update_from_api(self) -> None:
        """Refresh the home info payload."""
        try:
            self._home_info = await self._coordinator.client.get_home_info(self._unit_id)
        except (AuthenticationError, ApiError) as err:
            _LOGGER.warning("Unable to update home info for %s: %s", self._name, err)
            self._home_info = {}

    def _home_attributes(self) -> dict[str, Any]:
        if isinstance(self._home_info, dict):
            if "attributes" in self._home_info and isinstance(
                self._home_info["attributes"], dict
            ):
                return self._home_info["attributes"]
            return self._home_info
        return {}

    @property
    def native_value(self) -> str | None:
        """Return the current home status if available."""
        attributes = self._home_attributes()
        for key in ("homeStatus", "cleanStatus", "propertyStatus", "status"):
            value = attributes.get(key)
            if isinstance(value, str):
                return value
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose additional inspection metadata."""
        attributes = self._home_attributes()
        return {
            "last_inspection_date": attributes.get("lastInspectionDate")
            or attributes.get("inspectionDate"),
            "last_clean_date": attributes.get("lastCleanDate"),
            "next_clean_date": attributes.get("nextCleanDate"),
            "clean_score": attributes.get("cleanScore") or attributes.get("score"),
            "inspection_score": attributes.get("inspectionScore"),
            "upcoming_tasks": attributes.get("upcomingTasks"),
        }


class VacasaMaintenanceSensor(VacasaApiUpdateMixin, VacasaBaseSensor):
    """Sensor representing open maintenance tickets for a unit."""

    def __init__(
        self,
        coordinator,
        unit_id: str,
        name: str,
        unit_attributes: dict[str, Any],
        status: str = "open",
    ) -> None:
        """Initialize maintenance sensor."""
        super().__init__(
            coordinator=coordinator,
            unit_id=unit_id,
            name=name,
            unit_attributes=unit_attributes,
            sensor_type=SENSOR_MAINTENANCE_OPEN,
            icon="mdi:tools",
            state_class=SensorStateClass.MEASUREMENT,
        )
        self._status = status
        self._tickets: list[dict[str, Any]] = []
        self._attr_native_unit_of_measurement = "tickets"

    async def _async_update_from_api(self) -> None:
        """Refresh the maintenance ticket list."""
        try:
            self._tickets = await self._coordinator.client.get_maintenance(
                self._unit_id, status=self._status
            )
        except (AuthenticationError, ApiError) as err:
            _LOGGER.warning(
                "Unable to update maintenance tickets for %s: %s", self._name, err
            )
            self._tickets = []

    @property
    def native_value(self) -> int:
        """Return the number of tickets."""
        return len(self._tickets)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return metadata about open tickets."""
        summaries = []
        ticket_ids = []
        for ticket in self._tickets:
            if not isinstance(ticket, dict):
                continue
            ticket_ids.append(ticket.get("id"))
            attributes = ticket.get("attributes", {}) if isinstance(ticket, dict) else {}
            summaries.append(
                {
                    "id": ticket.get("id"),
                    "status": attributes.get("status"),
                    "title": attributes.get("title") or attributes.get("summary"),
                    "updated_at": attributes.get("updatedAt"),
                }
            )

        return {
            "status_filter": self._status,
            "open_ticket_ids": ticket_ids,
            "tickets": summaries,
        }


class VacasaStatementSensor(VacasaApiUpdateMixin, SensorEntity):
    """Sensor exposing the latest owner statement totals."""

    def __init__(self, coordinator, config_entry: VacasaConfigEntry) -> None:
        """Initialize statement sensor."""
        super().__init__()
        self._coordinator = coordinator
        self._config_entry = config_entry
        self._statements: list[dict[str, Any]] = []
        self._attr_name = "Vacasa Statements"
        self._attr_has_entity_name = True
        self._attr_unique_id = f"vacasa_{SENSOR_STATEMENTS_TOTAL}_{config_entry.entry_id}"
        self._attr_icon = "mdi:cash-check"
        self._attr_native_unit_of_measurement = "$"

        username = config_entry.data.get(CONF_USERNAME, "Vacasa Account")
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"owner_{config_entry.entry_id}")},
            "name": f"Vacasa {username}",
            "manufacturer": "Vacasa",
        }

    async def _async_update_from_api(self) -> None:
        """Refresh statement totals."""
        try:
            self._statements = await self._coordinator.client.get_statements()
        except (AuthenticationError, ApiError) as err:
            _LOGGER.warning("Unable to update statements: %s", err)
            self._statements = []

    def _latest_statement(self) -> dict[str, Any] | None:
        if not self._statements:
            return None

        def _sort_key(statement: dict[str, Any]) -> str:
            if not isinstance(statement, dict):
                return ""
            attributes = statement.get("attributes", {})
            if isinstance(attributes, dict):
                return attributes.get("updatedAt") or attributes.get("periodEndDate") or ""
            return ""

        return max(self._statements, key=_sort_key)

    @staticmethod
    def _coerce_amount(value: Any) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = value.replace("$", "").replace(",", "").strip()
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None

    @property
    def native_value(self) -> float | int:
        """Return the latest statement total."""
        latest = self._latest_statement()
        if not latest:
            return 0

        attributes = latest.get("attributes", {}) if isinstance(latest, dict) else {}
        if not isinstance(attributes, dict):
            attributes = {}

        for field in ("totalAmount", "netAmount", "balance", "amountDue"):
            amount = self._coerce_amount(attributes.get(field))
            if amount is not None:
                return amount

        return len(self._statements)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose detailed statement attributes."""
        latest = self._latest_statement()
        attributes = latest.get("attributes", {}) if isinstance(latest, dict) else {}
        if not isinstance(attributes, dict):
            attributes = {}

        return {
            "statement_count": len(self._statements),
            "latest_statement_id": latest.get("id") if isinstance(latest, dict) else None,
            "period_start": attributes.get("periodStartDate"),
            "period_end": attributes.get("periodEndDate"),
            "status": attributes.get("status"),
            "total_amount": attributes.get("totalAmount"),
            "net_amount": attributes.get("netAmount"),
            "amount_due": attributes.get("amountDue"),
        }


class VacasaNextStaySensor(VacasaApiUpdateMixin, VacasaBaseSensor):
    """Sensor representing the next upcoming stay/reservation."""

    def __init__(
        self,
        coordinator,
        unit_id: str,
        name: str,
        unit_attributes: dict[str, Any],
    ) -> None:
        """Initialize the next stay sensor."""
        _LOGGER.debug("Initializing VacasaNextStaySensor for unit %s (%s)", unit_id, name)
        super().__init__(
            coordinator=coordinator,
            unit_id=unit_id,
            name=name,
            unit_attributes=unit_attributes,
            sensor_type=SENSOR_NEXT_STAY,
            icon="mdi:calendar-clock",
        )
        self._reservation: dict[str, Any] | None = None
        _LOGGER.debug("VacasaNextStaySensor initialized successfully for unit %s", unit_id)

    async def _async_update_from_api(self) -> None:
        """Fetch next reservation from API."""
        _LOGGER.debug("VacasaNextStaySensor._async_update_from_api called for %s", self._name)
        try:
            # Get reservations starting from today
            today = datetime.now().strftime("%Y-%m-%d")
            future_date = (datetime.now() + timedelta(days=365)).strftime(
                "%Y-%m-%d"
            )

            _LOGGER.debug("Fetching reservations for %s from %s to %s", self._unit_id, today, future_date)
            reservations = await self._coordinator.client.get_reservations(
                self._unit_id,
                start_date=today,
                end_date=future_date,
                limit=10,
            )
            _LOGGER.debug("Retrieved %s reservations for %s", len(reservations), self._unit_id)

            # Find next upcoming or current reservation
            self._reservation = self._find_next_stay(reservations)
            _LOGGER.debug("Next stay for %s: %s", self._unit_id, "found" if self._reservation else "none")

        except (AuthenticationError, ApiError) as err:
            _LOGGER.warning(
                "Unable to update next stay for %s: %s", self._name, err
            )
            self._reservation = None
        except Exception as err:
            _LOGGER.error(
                "Unexpected error updating next stay for %s: %s",
                self._name,
                err,
                exc_info=True,
            )
            self._reservation = None

    def _find_next_stay(self, reservations: list[dict]) -> dict | None:
        """Find the next relevant reservation (current or upcoming)."""
        now = dt_util.now()

        for reservation in sorted(
            reservations,
            key=lambda r: r.get("attributes", {}).get("startDate", ""),
        ):
            attrs = reservation.get("attributes", {})
            end_date = self._parse_date(attrs.get("endDate"))

            # Include if checkout is in the future (current or upcoming)
            if end_date and end_date > now:
                return reservation

        return None

    def _parse_date(self, date_str: str | None) -> datetime | None:
        """Parse date string to datetime object."""
        if not date_str:
            return None

        try:
            # Try parsing as date only first
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")

            # Get timezone from property or use local
            if self._unit_attributes.get("timezone"):
                try:
                    from zoneinfo import ZoneInfo

                    tz = ZoneInfo(self._unit_attributes["timezone"])
                    return date_obj.replace(tzinfo=tz)
                except Exception:
                    pass

            # Fall back to local timezone
            return dt_util.as_local(date_obj)

        except ValueError:
            # Try parsing as full datetime
            try:
                return dt_util.parse_datetime(date_str)
            except Exception:
                _LOGGER.warning("Could not parse date: %s", date_str)
                return None

    @property
    def native_value(self) -> str:
        """Return human-readable state."""
        if not self._reservation:
            return "No upcoming reservations"

        attrs = self._reservation.get("attributes", {})
        start_date = self._parse_date(attrs.get("startDate"))
        end_date = self._parse_date(attrs.get("endDate"))
        now = dt_util.now()

        # Determine if current or upcoming
        is_current = start_date and end_date and start_date <= now < end_date

        # Get stay type
        stay_type = self._coordinator.client.categorize_reservation(self._reservation)
        stay_name = STAY_TYPE_TO_NAME.get(stay_type, "Reservation")

        if is_current:
            return f"{stay_name} (currently occupied)"
        else:
            days_until = (start_date - now).days if start_date else None
            if days_until is not None:
                if days_until == 0:
                    return f"{stay_name} (today)"
                elif days_until == 1:
                    return f"{stay_name} (tomorrow)"
                else:
                    return f"{stay_name} in {days_until} days"

        return stay_name

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return detailed reservation attributes."""
        if not self._reservation:
            return {
                "is_current": False,
                "is_upcoming": False,
            }

        attrs = self._reservation.get("attributes", {})
        start_date = self._parse_date(attrs.get("startDate"))
        end_date = self._parse_date(attrs.get("endDate"))
        now = dt_util.now()

        # Compute time values
        is_current = start_date and end_date and start_date <= now < end_date
        days_until_checkin = (
            (start_date - now).days if start_date and start_date > now else None
        )
        days_until_checkout = (end_date - now).days if end_date else None
        stay_duration = (end_date - start_date).days if start_date and end_date else None

        # Get stay classification
        stay_type = self._coordinator.client.categorize_reservation(self._reservation)

        # Extract guest info
        guest_name = None
        if stay_type == STAY_TYPE_GUEST:
            first = attrs.get("firstName", "")
            last = attrs.get("lastName", "")
            if first and last:
                guest_name = f"{first} {last}"

        return {
            # Core data
            "reservation_id": self._reservation.get("id"),
            "status": "confirmed",  # MVP: Assume confirmed
            # Dates
            "checkin_date": start_date.isoformat() if start_date else None,
            "checkout_date": end_date.isoformat() if end_date else None,
            "checkin_time": attrs.get(
                "checkinTime", self._unit_attributes.get("checkInTime")
            ),
            "checkout_time": attrs.get(
                "checkoutTime", self._unit_attributes.get("checkOutTime")
            ),
            # Classification
            "stay_type": stay_type,
            "stay_category": STAY_TYPE_TO_CATEGORY.get(stay_type),
            # Guest info
            "guest_count": attrs.get("guestCount"),
            "guest_name": guest_name,
            # Booking (MVP: limited data)
            "booking_source": "vacasa_direct",
            "special_notes": None,
            # Computed values
            "days_until_checkin": days_until_checkin,
            "days_until_checkout": days_until_checkout,
            "stay_duration_nights": stay_duration,
            # Flags
            "is_current": is_current,
            "is_upcoming": not is_current and days_until_checkin is not None,
        }


# List of sensor classes instantiated per Vacasa unit. Keeping the mapping in one
# place makes it easier to understand which entities are created and allows
# async_setup_entry to remain concise.
UNIT_SENSOR_CLASSES: tuple[type[VacasaBaseSensor], ...] = (
    VacasaRatingSensor,
    VacasaLocationSensor,
    VacasaTimezoneSensor,
    VacasaMaxOccupancySensor,
    VacasaMaxAdultsSensor,
    VacasaMaxChildrenSensor,
    VacasaMaxPetsSensor,
    VacasaBedroomsSensor,
    VacasaBathroomsSensor,
    VacasaHotTubSensor,
    VacasaPetFriendlySensor,
    VacasaParkingSensor,
    VacasaAddressSensor,
    VacasaHomeInfoSensor,
    VacasaMaintenanceSensor,
    VacasaNextStaySensor,
)


def _create_unit_sensors(
    coordinator,
    unit_id: str,
    name: str,
    attributes: dict[str, Any],
) -> list[VacasaBaseSensor]:
    """Build the entity list for a single Vacasa unit."""
    _LOGGER.debug("Creating sensors for unit %s (%s) - %s sensor classes", unit_id, name, len(UNIT_SENSOR_CLASSES))
    sensors = []
    for sensor_class in UNIT_SENSOR_CLASSES:
        try:
            _LOGGER.debug("Creating %s for unit %s", sensor_class.__name__, unit_id)
            sensor = sensor_class(
                coordinator=coordinator,
                unit_id=unit_id,
                name=name,
                unit_attributes=attributes,
            )
            sensors.append(sensor)
            _LOGGER.debug("Successfully created %s for unit %s", sensor_class.__name__, unit_id)
        except Exception as err:
            _LOGGER.error("Failed to create %s for unit %s: %s", sensor_class.__name__, unit_id, err, exc_info=True)
    return sensors


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: VacasaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Vacasa sensor platform."""
    data = config_entry.runtime_data
    client = data.client
    coordinator = data.coordinator

    try:
        units = await client.get_units()
        _LOGGER.debug("Found %s Vacasa units for sensors", len(units))
    except AuthenticationError as err:
        _LOGGER.error("Authentication error setting up Vacasa sensors: %s", err)
        return
    except ApiError as err:
        _LOGGER.error("API error setting up Vacasa sensors: %s", err)
        return

    entities: list[SensorEntity] = []
    for unit in units:
        unit_id = unit.get("id")
        if not unit_id:
            _LOGGER.debug("Skipping Vacasa unit without an id: %s", unit)
            continue

        attributes = unit.get("attributes", {})
        name = attributes.get("name", f"Vacasa Unit {unit_id}")
        entities.extend(_create_unit_sensors(coordinator, unit_id, name, attributes))

    # Add owner-level statements sensor once per config entry
    entities.append(VacasaStatementSensor(coordinator=coordinator, config_entry=config_entry))

    async_add_entities(entities, True)
