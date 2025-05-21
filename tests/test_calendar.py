"""Test the Vacasa calendar platform."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from homeassistant.components.calendar import DOMAIN as CALENDAR_DOMAIN
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

from custom_components.vacasa.const import (
    CONF_REFRESH_INTERVAL,
    DEFAULT_REFRESH_INTERVAL,
    DOMAIN,
)


@pytest.fixture
def mock_reservations():
    """Provide mock reservation data."""
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


async def test_calendar_creation(
    hass: HomeAssistant, mock_successful_auth, mock_successful_api
):
    """Test calendar entity creation."""
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

    # Verify calendar entity was created
    assert len(hass.states.async_entity_ids(CALENDAR_DOMAIN)) == 1
    calendar_entity = hass.states.async_entity_ids(CALENDAR_DOMAIN)[0]
    assert hass.states.get(calendar_entity).name == "Test Property"


async def test_calendar_events(
    hass: HomeAssistant, mock_successful_auth, mock_reservations
):
    """Test calendar events retrieval."""
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
            return_value=mock_reservations,
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

    # Get the calendar entity
    calendar_entity = hass.states.async_entity_ids(CALENDAR_DOMAIN)[0]

    # Get calendar events
    now = dt_util.now()
    start = now - timedelta(days=1)
    end = now + timedelta(days=3)

    events = await hass.services.async_call(
        CALENDAR_DOMAIN,
        "get_events",
        {
            "entity_id": calendar_entity,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        },
        blocking=True,
        return_response=True,
    )

    # Verify events
    assert len(events) == 1
    event = events[0]
    assert "Test Guest" in event["summary"]
    assert event["start"] is not None
    assert event["end"] is not None


async def test_calendar_refresh(
    hass: HomeAssistant, mock_successful_auth, mock_successful_api
):
    """Test calendar data refresh."""
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

    # Verify the refresh service is registered
    services = hass.services.async_services().get(DOMAIN, {})
    assert "refresh_data" in services or "refresh_calendars" in services

    # Call the refresh service
    refresh_service = (
        "refresh_data" if "refresh_data" in services else "refresh_calendars"
    )
    with patch(
        "custom_components.vacasa.api_client.VacasaApiClient.get_categorized_reservations"
    ) as mock_get:
        await hass.services.async_call(
            DOMAIN,
            refresh_service,
            {},
            blocking=True,
        )
        assert mock_get.called
