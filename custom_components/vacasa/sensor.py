"""Sensor platform for Vacasa integration."""

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import VacasaConfigEntry
from .api_client import ApiError, AuthenticationError
from .const import (
    DOMAIN,
    SENSOR_ADDRESS,
    SENSOR_BATHROOMS,
    SENSOR_BEDROOMS,
    SENSOR_HOT_TUB,
    SENSOR_LOCATION,
    SENSOR_MAX_ADULTS,
    SENSOR_MAX_CHILDREN,
    SENSOR_MAX_OCCUPANCY,
    SENSOR_MAX_PETS,
    SENSOR_PARKING,
    SENSOR_PET_FRIENDLY,
    SENSOR_RATING,
    SENSOR_TIMEZONE,
)

# Removed CoordinatorEntity import - these sensors contain static property data


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: VacasaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Vacasa sensor platform."""
    data = config_entry.runtime_data
    client = data.client
    coordinator = data.coordinator

    # Get all units
    try:
        units = await client.get_units()
        _LOGGER.debug("Found %s Vacasa units for sensors", len(units))

        # Create sensors for each unit
        entities = []
        for unit in units:
            unit_id = unit.get("id")
            attributes = unit.get("attributes", {})
            name = attributes.get("name", f"Vacasa Unit {unit_id}")

            # Property Information Sensors
            entities.append(
                VacasaRatingSensor(
                    coordinator=coordinator,
                    unit_id=unit_id,
                    name=name,
                    unit_attributes=attributes,
                )
            )

            entities.append(
                VacasaLocationSensor(
                    coordinator=coordinator,
                    unit_id=unit_id,
                    name=name,
                    unit_attributes=attributes,
                )
            )

            entities.append(
                VacasaTimezoneSensor(
                    coordinator=coordinator,
                    unit_id=unit_id,
                    name=name,
                    unit_attributes=attributes,
                )
            )

            # Occupancy & Capacity Sensors
            entities.append(
                VacasaMaxOccupancySensor(
                    coordinator=coordinator,
                    unit_id=unit_id,
                    name=name,
                    unit_attributes=attributes,
                )
            )

            entities.append(
                VacasaMaxAdultsSensor(
                    coordinator=coordinator,
                    unit_id=unit_id,
                    name=name,
                    unit_attributes=attributes,
                )
            )

            entities.append(
                VacasaMaxChildrenSensor(
                    coordinator=coordinator,
                    unit_id=unit_id,
                    name=name,
                    unit_attributes=attributes,
                )
            )

            entities.append(
                VacasaMaxPetsSensor(
                    coordinator=coordinator,
                    unit_id=unit_id,
                    name=name,
                    unit_attributes=attributes,
                )
            )

            # Amenities Sensors
            entities.append(
                VacasaBedroomsSensor(
                    coordinator=coordinator,
                    unit_id=unit_id,
                    name=name,
                    unit_attributes=attributes,
                )
            )

            entities.append(
                VacasaBathroomsSensor(
                    coordinator=coordinator,
                    unit_id=unit_id,
                    name=name,
                    unit_attributes=attributes,
                )
            )

            entities.append(
                VacasaHotTubSensor(
                    coordinator=coordinator,
                    unit_id=unit_id,
                    name=name,
                    unit_attributes=attributes,
                )
            )

            entities.append(
                VacasaPetFriendlySensor(
                    coordinator=coordinator,
                    unit_id=unit_id,
                    name=name,
                    unit_attributes=attributes,
                )
            )

            # Property Details Sensors
            entities.append(
                VacasaParkingSensor(
                    coordinator=coordinator,
                    unit_id=unit_id,
                    name=name,
                    unit_attributes=attributes,
                )
            )

            entities.append(
                VacasaAddressSensor(
                    coordinator=coordinator,
                    unit_id=unit_id,
                    name=name,
                    unit_attributes=attributes,
                )
            )

        async_add_entities(entities, True)
    except AuthenticationError as err:
        _LOGGER.error("Authentication error setting up Vacasa sensors: %s", err)
    except ApiError as err:
        _LOGGER.error("API error setting up Vacasa sensors: %s", err)


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
        self._attr_name = f"Vacasa {name} {sensor_type.replace('_', ' ').title()}"
        self._attr_has_entity_name = True

        # Set device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, unit_id)},
            "name": f"Vacasa {name}",
            "manufacturer": "Vacasa",
            "model": "Vacation Rental",
            "sw_version": "1.0",
        }


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
