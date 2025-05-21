"""Test the Vacasa binary sensor platform."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

from custom_components.vacasa.const import (
    CONF_REFRESH_INTERVAL,
    DEFAULT_REFRESH_INTERVAL,
    DOMAIN,
)


@pytest.fixture
def mock_occupied_property():
    """Provide mock reservation data for an occupied property."""
    now = dt_util.now()
    yesterday = now - timedelta(days=1)
    tomorrow = now + timedelta(days=1)

    return {
        "guest": [
            {
                "id": "12345",
                "attributes": {
                    "startDate": yesterday.strftime("%Y-%m-%d"),
                    "endDate": tomorrow.strftime("%Y-%m-%d"),
                    "firstName": "Test",
                    "lastName": "Guest",
                    "ownerHold": None,
                },
            }
        ],
        "owner": [],
        "maintenance": [],
    }


@pytest.fixture
def mock_vacant_property():
    """Provide mock reservation data for a vacant property."""
    now = dt_util.now()
    tomorrow = now + timedelta(days=1)
    day_after = now + timedelta(days=2)

    return {
        "guest": [
            {
                "id": "12345",
                "attributes": {
                    "startDate": tomorrow.strftime("%Y-%m-%d"),
                    "endDate": day_after.strftime("%Y-%m-%d"),
                    "firstName": "Test",
                    "lastName": "Guest",
                    "ownerHold": None,
                },
            }
        ],
        "owner": [],
        "maintenance": [],
    }


async def test_binary_sensor_creation(
    hass: HomeAssistant, mock_successful_auth, mock_successful_api
):
    """Test binary sensor entity creation."""
    # Set up the integration
    assert await async_setup_component(
        hass,
        DOMAIN,
        {
            DOMAIN: {
                CONF_USERNAME: "test@example.com",
                CONF_PASSWORD: "test-password",
                CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL,
            }
        },
    )
    await hass.async_block_till_done()

    # Verify binary sensor entity was created
    binary_sensors = [
        entity_id
        for entity_id in hass.states.async_entity_ids(BINARY_SENSOR_DOMAIN)
        if entity_id.startswith(f"{BINARY_SENSOR_DOMAIN}.vacasa_")
    ]
    assert len(binary_sensors) >= 1

    # Verify the occupancy sensor exists
    occupancy_sensor = next(
        (entity_id for entity_id in binary_sensors if "occupied" in entity_id), None
    )
    assert occupancy_sensor is not None


async def test_occupied_property(
    hass: HomeAssistant, mock_successful_auth, mock_occupied_property
):
    """Test binary sensor state for an occupied property."""
    # Mock the API client to return our test reservations
    with (
        patch(
            "custom_components.vacasa.api_client.VacasaApiClient.get_owner_id",
            return_value="12345",
        ),
        patch(
            "custom_components.vacasa.api_client.VacasaApiClient.get_units",
            return_value=[
                {
                    "id": "67890",
                    "attributes": {
                        "name": "Test Property",
                        "code": "TEST123",
                    },
                }
            ],
        ),
        patch(
            "custom_components.vacasa.api_client.VacasaApiClient.get_categorized_reservations",
            return_value=mock_occupied_property,
        ),
    ):
        # Set up the integration
        assert await async_setup_component(
            hass,
            DOMAIN,
            {
                DOMAIN: {
                    CONF_USERNAME: "test@example.com",
                    CONF_PASSWORD: "test-password",
                    CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL,
                }
            },
        )
        await hass.async_block_till_done()

    # Find the occupancy sensor
    binary_sensors = [
        entity_id
        for entity_id in hass.states.async_entity_ids(BINARY_SENSOR_DOMAIN)
        if entity_id.startswith(f"{BINARY_SENSOR_DOMAIN}.vacasa_")
        and "occupied" in entity_id
    ]
    occupancy_sensor = binary_sensors[0]

    # Verify the sensor state is ON (occupied)
    assert hass.states.get(occupancy_sensor).state == STATE_ON

    # Verify attributes
    attributes = hass.states.get(occupancy_sensor).attributes
    assert "next_check_out" in attributes
    assert "current_reservation" in attributes


async def test_vacant_property(
    hass: HomeAssistant, mock_successful_auth, mock_vacant_property
):
    """Test binary sensor state for a vacant property."""
    # Mock the API client to return our test reservations
    with (
        patch(
            "custom_components.vacasa.api_client.VacasaApiClient.get_owner_id",
            return_value="12345",
        ),
        patch(
            "custom_components.vacasa.api_client.VacasaApiClient.get_units",
            return_value=[
                {
                    "id": "67890",
                    "attributes": {
                        "name": "Test Property",
                        "code": "TEST123",
                    },
                }
            ],
        ),
        patch(
            "custom_components.vacasa.api_client.VacasaApiClient.get_categorized_reservations",
            return_value=mock_vacant_property,
        ),
    ):
        # Set up the integration
        assert await async_setup_component(
            hass,
            DOMAIN,
            {
                DOMAIN: {
                    CONF_USERNAME: "test@example.com",
                    CONF_PASSWORD: "test-password",
                    CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL,
                }
            },
        )
        await hass.async_block_till_done()

    # Find the occupancy sensor
    binary_sensors = [
        entity_id
        for entity_id in hass.states.async_entity_ids(BINARY_SENSOR_DOMAIN)
        if entity_id.startswith(f"{BINARY_SENSOR_DOMAIN}.vacasa_")
        and "occupied" in entity_id
    ]
    occupancy_sensor = binary_sensors[0]

    # Verify the sensor state is OFF (vacant)
    assert hass.states.get(occupancy_sensor).state == STATE_OFF

    # Verify attributes
    attributes = hass.states.get(occupancy_sensor).attributes
    assert "next_check_in" in attributes
