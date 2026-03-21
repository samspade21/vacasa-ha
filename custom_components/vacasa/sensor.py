"""Sensor platform for Vacasa integration."""

import asyncio
import logging
from contextlib import suppress
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import (
    VacasaConfigEntry,
    VacasaDataUpdateCoordinator,
    VacasaReservationStateMixin,
    _iter_coordinator_units,
    _make_owner_device_info,
    _make_unit_device_info,
)
from .api_client import ApiError, AuthenticationError
from .const import (
    CONF_USERNAME,
    SENSOR_ADDRESS,
    SENSOR_BATHROOMS,
    SENSOR_BEDROOMS,
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
    SIGNAL_RESERVATION_STATE,
    STAY_TYPE_TO_CATEGORY,
    STAY_TYPE_TO_NAME,
)
from .models import ReservationWindow

# Removed CoordinatorEntity import - these sensors contain static property data


_LOGGER = logging.getLogger(__name__)


class VacasaBaseSensor(SensorEntity):
    """Base class for Vacasa sensors.

    Subclasses must declare _sensor_type as a class attribute, and may override
    _attr_icon, _attr_state_class, and _attr_native_unit_of_measurement.
    """

    _sensor_type: str  # must be declared by each subclass
    _attr_icon: str = "mdi:home"

    def __init__(
        self,
        coordinator: VacasaDataUpdateCoordinator,
        unit_id: str,
        name: str,
        unit_attributes: dict[str, Any],
    ) -> None:
        """Initialize the Vacasa sensor."""
        super().__init__()
        # Store coordinator reference but don't inherit from CoordinatorEntity
        # These sensors contain static property data that rarely changes
        self._coordinator = coordinator
        self._unit_id = unit_id
        self._name = name
        self._unit_attributes = unit_attributes

        # Entity properties
        self._attr_unique_id = f"vacasa_{self._sensor_type}_{unit_id}"
        self._attr_name = self._sensor_type.replace("_", " ").title()
        self._attr_has_entity_name = True
        self._attr_device_info = _make_unit_device_info(unit_id, name)

    @staticmethod
    def _bool_to_yes_no(value: bool | None) -> str | None:
        """Convert a boolean attribute to a Yes/No string, or None if absent."""
        if value is None:
            return None
        return "Yes" if value else "No"


class VacasaApiUpdateMixin:
    """Mixin to throttle API-backed sensors to the coordinator refresh."""

    _refresh_task: asyncio.Task[None] | None

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002,ANN003
        """Initialize API update mixin."""
        self._refresh_task = None
        super().__init__(*args, **kwargs)
        self._attr_should_poll = False

    async def async_added_to_hass(self) -> None:
        """Register coordinator listener when added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(self._coordinator.async_add_listener(self._handle_coordinator_refresh))
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
            self._refresh_task = self.hass.async_create_task(self._async_refresh_from_api())
        return self._refresh_task

    async def _async_refresh_from_api(self) -> None:
        current_task = asyncio.current_task()
        try:
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

    _sensor_type = SENSOR_RATING
    _attr_icon = "mdi:star"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "★"

    @property
    def native_value(self) -> float | None:
        """Return the rating value."""
        return self._unit_attributes.get("rating")


class VacasaLocationSensor(VacasaBaseSensor):
    """Sensor for Vacasa property location."""

    _sensor_type = SENSOR_LOCATION
    _attr_icon = "mdi:map-marker"

    def __init__(self, **kwargs: Any) -> None:
        """Pre-compute location value and attributes from immutable unit_attributes."""
        super().__init__(**kwargs)
        location = self._unit_attributes.get("location", {})
        if location and "lat" in location and "lng" in location:
            self._location_value: str | None = f"{location['lat']},{location['lng']}"
            self._location_attrs: dict[str, Any] = {
                "latitude": location["lat"],
                "longitude": location["lng"],
            }
        else:
            self._location_value = None
            self._location_attrs = {}

    @property
    def native_value(self) -> str | None:
        """Return the location value."""
        return self._location_value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return self._location_attrs


class VacasaTimezoneSensor(VacasaBaseSensor):
    """Sensor for Vacasa property timezone."""

    _sensor_type = SENSOR_TIMEZONE
    _attr_icon = "mdi:clock-time-eight-outline"

    @property
    def native_value(self) -> str | None:
        """Return the timezone value."""
        return self._unit_attributes.get("timezone")


class VacasaMaxOccupancySensor(VacasaBaseSensor):
    """Sensor for Vacasa property max occupancy."""

    _sensor_type = SENSOR_MAX_OCCUPANCY
    _attr_icon = "mdi:account-group"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "people"

    @property
    def native_value(self) -> int | None:
        """Return the max occupancy value."""
        return self._unit_attributes.get("maxOccupancyTotal")


class VacasaMaxAdultsSensor(VacasaBaseSensor):
    """Sensor for Vacasa property max adults."""

    _sensor_type = SENSOR_MAX_ADULTS
    _attr_icon = "mdi:account"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "people"

    @property
    def native_value(self) -> int | None:
        """Return the max adults value."""
        return self._unit_attributes.get("maxAdults")


class VacasaMaxChildrenSensor(VacasaBaseSensor):
    """Sensor for Vacasa property max children."""

    _sensor_type = SENSOR_MAX_CHILDREN
    _attr_icon = "mdi:account-child"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "people"

    @property
    def native_value(self) -> int | None:
        """Return the max children value."""
        return self._unit_attributes.get("maxChildren")


class VacasaMaxPetsSensor(VacasaBaseSensor):
    """Sensor for Vacasa property max pets."""

    _sensor_type = SENSOR_MAX_PETS
    _attr_icon = "mdi:paw"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "pets"

    @property
    def native_value(self) -> int | None:
        """Return the max pets value."""
        return self._unit_attributes.get("maxPets")


class VacasaBedroomsSensor(VacasaBaseSensor):
    """Sensor for Vacasa property bedrooms."""

    _sensor_type = SENSOR_BEDROOMS
    _attr_icon = "mdi:bed"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "rooms"

    def __init__(self, **kwargs: Any) -> None:
        """Pre-compute bedroom count and bed-type attributes from immutable unit_attributes."""
        super().__init__(**kwargs)
        amenities = self._unit_attributes.get("amenities", {})
        rooms = amenities.get("rooms", {})
        self._bedrooms: int | None = rooms.get("bedrooms") if rooms else None
        self._bed_attrs: dict[str, Any] = {
            f"{bed_type}_beds": count
            for bed_type, count in amenities.get("beds", {}).items()
            if count and bed_type != "child"  # Skip child beds as they're not real beds
        }

    @property
    def native_value(self) -> int | None:
        """Return the bedrooms value."""
        return self._bedrooms

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return self._bed_attrs


class VacasaBathroomsSensor(VacasaBaseSensor):
    """Sensor for Vacasa property bathrooms."""

    _sensor_type = SENSOR_BATHROOMS
    _attr_icon = "mdi:shower"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "rooms"

    def __init__(self, **kwargs: Any) -> None:
        """Pre-compute bathroom value and attributes from immutable unit_attributes."""
        super().__init__(**kwargs)
        bathrooms = self._unit_attributes.get("amenities", {}).get("rooms", {}).get("bathrooms", {})
        if bathrooms:
            self._bathrooms_value: float | None = (
                bathrooms.get("full", 0) + bathrooms.get("half", 0) * 0.5
            )
            self._bathrooms_attrs: dict[str, Any] = {
                "full_bathrooms": bathrooms.get("full", 0),
                "half_bathrooms": bathrooms.get("half", 0),
            }
        else:
            self._bathrooms_value = None
            self._bathrooms_attrs = {}

    @property
    def native_value(self) -> float | None:
        """Return the bathrooms value."""
        return self._bathrooms_value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return self._bathrooms_attrs


class VacasaHotTubSensor(VacasaBaseSensor):
    """Sensor for Vacasa property hot tub."""

    _sensor_type = SENSOR_HOT_TUB
    _attr_icon = "mdi:hot-tub"

    def __init__(self, **kwargs: Any) -> None:
        """Pre-compute hot tub value from immutable unit_attributes."""
        super().__init__(**kwargs)
        amenities = self._unit_attributes.get("amenities", {})
        self._hot_tub_value = self._bool_to_yes_no(amenities.get("hotTub") if amenities else None)

    @property
    def native_value(self) -> str | None:
        """Return the hot tub value."""
        return self._hot_tub_value


class VacasaPetFriendlySensor(VacasaBaseSensor):
    """Sensor for Vacasa property pet friendly status."""

    _sensor_type = SENSOR_PET_FRIENDLY
    _attr_icon = "mdi:paw"

    def __init__(self, **kwargs: Any) -> None:
        """Pre-compute pet friendly value from immutable unit_attributes."""
        super().__init__(**kwargs)
        amenities = self._unit_attributes.get("amenities", {})
        self._pet_friendly_value = self._bool_to_yes_no(
            amenities.get("petsFriendly") if amenities else None
        )

    @property
    def native_value(self) -> str | None:
        """Return the pet friendly value."""
        return self._pet_friendly_value


class VacasaParkingSensor(VacasaBaseSensor):
    """Sensor for Vacasa property parking."""

    _sensor_type = SENSOR_PARKING
    _attr_icon = "mdi:car"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "spaces"

    def __init__(self, **kwargs: Any) -> None:
        """Pre-compute parking value and attributes from immutable unit_attributes."""
        super().__init__(**kwargs)
        parking = self._unit_attributes.get("parking", {})
        self._parking_total: int | None = parking.get("total") if parking else None
        attrs: dict[str, Any] = {}
        if parking:
            if parking.get("notes"):
                attrs["notes"] = parking["notes"]
            for key in ["accessible", "fourWheelDriveRequired", "paid", "street", "valet"]:
                if key in parking:
                    value = parking[key]
                    attrs[key] = None if value == -1 else value  # Convert -1 to None for display
        self._parking_attrs = attrs

    @property
    def native_value(self) -> int | None:
        """Return the parking value."""
        return self._parking_total

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return self._parking_attrs


class VacasaAddressSensor(VacasaBaseSensor):
    """Sensor for Vacasa property address."""

    _sensor_type = SENSOR_ADDRESS
    _attr_icon = "mdi:map-marker"

    def __init__(self, **kwargs: Any) -> None:
        """Pre-compute address string and attributes once from immutable unit_attributes."""
        super().__init__(**kwargs)
        self._address_value, self._address_attrs = self._parse_address(
            self._unit_attributes.get("address", {})
        )

    @staticmethod
    def _parse_address(address: dict[str, Any]) -> tuple[str | None, dict[str, Any]]:
        """Parse address dict into a display string and attribute dict."""
        if not address:
            return None, {}

        parts = []
        attrs: dict[str, Any] = {}

        for key in ["address_1", "address_2"]:
            if address.get(key):
                parts.append(address[key])
                attrs[key] = address[key]

        city_state_zip = []
        for key in ["city", "state", "zip"]:
            if address.get(key):
                city_state_zip.append(address[key])
                attrs[key] = address[key]
        if city_state_zip:
            parts.append(", ".join(city_state_zip))

        country = address.get("country", {})
        if country:
            if country.get("name"):
                parts.append(country["name"])
                attrs["country"] = country["name"]
            if country.get("code"):
                attrs["country_code"] = country["code"]

        return ", ".join(parts) if parts else None, attrs

    @property
    def native_value(self) -> str | None:
        """Return the address value."""
        return self._address_value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return self._address_attrs


class VacasaMaintenanceSensor(VacasaApiUpdateMixin, VacasaBaseSensor):
    """Sensor representing open maintenance tickets for a unit."""

    _sensor_type = SENSOR_MAINTENANCE_OPEN
    _attr_icon = "mdi:tools"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "tickets"

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
        )
        self._status = status
        self._tickets: list[dict[str, Any]] = []

    async def _async_update_from_api(self) -> None:
        """Refresh the maintenance ticket list."""
        try:
            self._tickets = await self._coordinator.client.get_maintenance(
                self._unit_id, status=self._status
            )
        except (AuthenticationError, ApiError) as err:
            _LOGGER.warning("Unable to update maintenance tickets for %s: %s", self._name, err)
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
            attributes = ticket.get("attributes", {})
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
        self._latest: dict[str, Any] | None = None
        self._attr_name = "Vacasa Statements"
        self._attr_has_entity_name = True
        self._attr_unique_id = f"vacasa_{SENSOR_STATEMENTS_TOTAL}_{config_entry.entry_id}"
        self._attr_icon = "mdi:cash-check"
        self._attr_native_unit_of_measurement = "$"

        username = config_entry.data.get(CONF_USERNAME, "Vacasa Account")
        self._attr_device_info = _make_owner_device_info(config_entry.entry_id, username)

    async def _async_update_from_api(self) -> None:
        """Refresh statement totals."""
        try:
            self._statements = await self._coordinator.client.get_statements()
        except (AuthenticationError, ApiError) as err:
            _LOGGER.warning("Unable to update statements: %s", err)
            self._statements = []
        self._latest = self._latest_statement()

    def _latest_statement(self) -> dict[str, Any] | None:
        if not self._statements:
            return None

        def _sort_key(statement: dict[str, Any]) -> str:
            attributes = statement.get("attributes", {})
            return attributes.get("updatedAt") or attributes.get("periodEndDate") or ""

        return max(self._statements, key=_sort_key)

    @classmethod
    def _coerce_amount(cls, value: Any) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = value.replace("$", "").replace(",", "").strip()
            try:
                return float(cleaned)
            except ValueError:
                _LOGGER.warning("Could not parse statement amount %r as a number", value)
                return None
        return None

    def _latest_attributes(self) -> dict[str, Any]:
        """Return the attributes dict from the latest statement, or {} if unavailable."""
        if self._latest is None:
            return {}
        return self._latest.get("attributes", {}) or {}

    @property
    def native_value(self) -> float | int:
        """Return the latest statement total."""
        if not self._latest:
            return 0

        attributes = self._latest_attributes()
        for field in ("totalAmount", "netAmount", "balance", "amountDue"):
            amount = self._coerce_amount(attributes.get(field))
            if amount is not None:
                return amount

        return len(self._statements)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose detailed statement attributes."""
        attributes = self._latest_attributes()

        return {
            "statement_count": len(self._statements),
            "latest_statement_id": self._latest.get("id") if self._latest is not None else None,
            "period_start": attributes.get("periodStartDate"),
            "period_end": attributes.get("periodEndDate"),
            "status": attributes.get("status"),
            "total_amount": attributes.get("totalAmount"),
            "net_amount": attributes.get("netAmount"),
            "amount_due": attributes.get("amountDue"),
        }


class VacasaNextStaySensor(VacasaReservationStateMixin, VacasaBaseSensor):
    """Sensor representing the next upcoming stay/reservation."""

    _sensor_type = SENSOR_NEXT_STAY
    _attr_icon = "mdi:calendar-clock"

    def __init__(
        self,
        coordinator,
        unit_id: str,
        name: str,
        unit_attributes: dict[str, Any],
    ) -> None:
        """Initialize the next stay sensor."""
        super().__init__(
            coordinator=coordinator,
            unit_id=unit_id,
            name=name,
            unit_attributes=unit_attributes,
        )
        self._attr_should_poll = False
        self._attr_available = False

    async def async_added_to_hass(self) -> None:
        """Register listeners when added to Home Assistant."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_RESERVATION_STATE,
                self._handle_reservation_state,
            )
        )
        self.async_on_remove(self._coordinator.async_add_listener(self._handle_coordinator_update))

        self._refresh_from_coordinator()
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update reservation data when the coordinator refreshes."""
        prev_current = self._current_reservation
        prev_next = self._next_reservation
        self._refresh_from_coordinator()
        if self._current_reservation != prev_current or self._next_reservation != prev_next:
            self.async_write_ha_state()

    @staticmethod
    def _as_local(value: datetime | None) -> datetime | None:
        """Convert a datetime to local timezone, or return None."""
        return dt_util.as_local(value) if value is not None else None

    def _days_until(self, target: datetime | None, now: datetime) -> int | None:
        """Calculate whole days between now and a target datetime."""
        if target is None:
            return None

        target_local = self._as_local(target)
        now_local = (
            now.astimezone(target_local.tzinfo) if target_local and target_local.tzinfo else now
        )

        return (target_local.date() - now_local.date()).days

    def _active_reservation(self) -> ReservationWindow | None:
        """Return the current reservation if present, otherwise the next."""
        return self._current_reservation or self._next_reservation

    @property
    def native_value(self) -> str:
        """Return human-readable state based on reservation windows."""
        reservation = self._active_reservation()
        if reservation is None:
            return "No upcoming reservations"

        start_date = self._as_local(reservation.start)
        end_date = self._as_local(reservation.end)
        now = dt_util.now()

        is_current = start_date and end_date and start_date <= now < end_date
        stay_name = STAY_TYPE_TO_NAME.get(reservation.stay_type, "Reservation")

        if is_current:
            return f"{stay_name} (currently occupied)"

        days_until = self._days_until(start_date, now)
        if days_until is not None:
            if days_until == 0:
                return f"{stay_name} (today)"
            if days_until == 1:
                return f"{stay_name} (tomorrow)"
            return f"{stay_name} in {days_until} days"

        return stay_name

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return detailed reservation attributes from shared state."""
        reservation = self._active_reservation()
        if reservation is None:
            return {
                "is_current": False,
                "is_upcoming": False,
            }

        start_date = self._as_local(reservation.start)
        end_date = self._as_local(reservation.end)
        now = dt_util.now()

        is_current = start_date and end_date and start_date <= now < end_date
        is_upcoming = start_date and start_date > now

        days_until_checkin = self._days_until(start_date, now) if is_upcoming else None
        days_until_checkout = self._days_until(end_date, now)
        stay_duration = (
            (end_date.date() - start_date.date()).days if start_date and end_date else None
        )

        return {
            "summary": reservation.summary,
            "reservation_id": reservation.reservation_id,
            "checkin_date": start_date.isoformat() if start_date else None,
            "checkout_date": end_date.isoformat() if end_date else None,
            "checkin_time": start_date.time().isoformat() if start_date else None,
            "checkout_time": end_date.time().isoformat() if end_date else None,
            "stay_type": reservation.stay_type,
            "stay_category": STAY_TYPE_TO_CATEGORY.get(reservation.stay_type),
            "guest_name": reservation.guest_name,
            "guest_count": reservation.guest_count,
            "days_until_checkin": days_until_checkin,
            "days_until_checkout": days_until_checkout,
            "stay_duration_nights": stay_duration,
            "is_current": bool(is_current),
            "is_upcoming": bool(is_upcoming),
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
    VacasaMaintenanceSensor,
    VacasaNextStaySensor,
)


def _create_unit_sensors(
    coordinator: VacasaDataUpdateCoordinator,
    unit_id: str,
    name: str,
    attributes: dict[str, Any],
) -> list[VacasaBaseSensor]:
    """Build the entity list for a single Vacasa unit."""
    sensors = []
    for sensor_class in UNIT_SENSOR_CLASSES:
        try:
            sensor = sensor_class(
                coordinator=coordinator,
                unit_id=unit_id,
                name=name,
                unit_attributes=attributes,
            )
            sensors.append(sensor)
        except (ValueError, KeyError, TypeError) as err:
            _LOGGER.error(
                "Failed to create %s for unit %s: %s",
                sensor_class.__name__,
                unit_id,
                err,
            )
        except Exception as err:
            _LOGGER.error(
                "Unexpected error creating %s for unit %s: %s",
                sensor_class.__name__,
                unit_id,
                err,
                exc_info=True,
            )
    return sensors


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: VacasaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Vacasa sensor platform."""
    coordinator = config_entry.runtime_data.coordinator

    entities: list[SensorEntity] = []
    for unit_id, attributes, name in _iter_coordinator_units(coordinator, "sensors"):
        entities.extend(_create_unit_sensors(coordinator, unit_id, name, attributes))

    # Add owner-level statements sensor once per config entry
    entities.append(VacasaStatementSensor(coordinator=coordinator, config_entry=config_entry))

    async_add_entities(entities, True)
