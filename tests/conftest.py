"""Pytest configuration and fixtures for the Vacasa integration tests."""

# flake8: noqa

# Provide minimal stubs for the Home Assistant modules used during import.
import sys
import types

ha = types.ModuleType("homeassistant")
config_entries = types.ModuleType("homeassistant.config_entries")


class ConfigEntry:
    """Simplified ConfigEntry stub matching Home Assistant."""

    def __init__(self, data=None, options=None):
        self.data = data or {}
        self.options = options or {}
        self.hass = None


class OptionsFlow:
    """Simplified OptionsFlow stub."""

    def __init__(self, config_entry):
        self.hass = config_entry.hass
        self.config_entry = config_entry


config_entries.ConfigEntry = ConfigEntry
config_entries.OptionsFlow = OptionsFlow


class ConfigFlow:
    def __init__(self, hass=None):
        self.hass = hass

    def __init_subclass__(cls, **kwargs):  # pragma: no cover - only for import
        pass


config_entries.ConfigFlow = ConfigFlow

core = types.ModuleType("homeassistant.core")


class HomeAssistant:
    pass


class ServiceCall:
    pass


class Event:
    def __init__(self, data=None):
        self.data = data or {}


core.HomeAssistant = HomeAssistant
core.ServiceCall = ServiceCall
core.Event = Event

exceptions = types.ModuleType("homeassistant.exceptions")


class HomeAssistantError(Exception):
    pass


class ConfigEntryNotReady(Exception):
    pass


exceptions.HomeAssistantError = HomeAssistantError
exceptions.ConfigEntryNotReady = ConfigEntryNotReady

helpers = types.ModuleType("homeassistant.helpers")
aiohttp_client = types.ModuleType("homeassistant.helpers.aiohttp_client")
update_coordinator = types.ModuleType("homeassistant.helpers.update_coordinator")
entity_platform = types.ModuleType("homeassistant.helpers.entity_platform")
entity_registry = types.ModuleType("homeassistant.helpers.entity_registry")
event_helper = types.ModuleType("homeassistant.helpers.event")
util = types.ModuleType("homeassistant.util")
dt_util = types.ModuleType("homeassistant.util.dt")
components = types.ModuleType("homeassistant.components")
components_binary_sensor = types.ModuleType("homeassistant.components.binary_sensor")
components_calendar = types.ModuleType("homeassistant.components.calendar")


def _async_track_point_in_time(hass, action, point_in_time):
    return None


event_helper.async_track_point_in_time = _async_track_point_in_time


class BinarySensorEntity:
    async def async_added_to_hass(self):
        return None

    async def async_will_remove_from_hass(self):
        return None

    def async_write_ha_state(self):
        return None


class BinarySensorDeviceClass:
    OCCUPANCY = "occupancy"


components_binary_sensor.BinarySensorEntity = BinarySensorEntity
components_binary_sensor.BinarySensorDeviceClass = BinarySensorDeviceClass
components_calendar.CalendarEntity = type("CalendarEntity", (), {})


class CalendarEvent:
    def __init__(self, **data):
        for key, value in data.items():
            setattr(self, key, value)


components_calendar.CalendarEvent = CalendarEvent

entity_platform.AddEntitiesCallback = None
entity_registry.async_get = lambda hass: types.SimpleNamespace(entities={})
dt_util.parse_datetime = lambda s: datetime.fromisoformat(s)
dt_util.utcnow = lambda: datetime.now(timezone.utc)
dt_util.as_utc = (
    lambda dt: dt.astimezone(timezone.utc)
    if dt.tzinfo
    else dt.replace(tzinfo=timezone.utc)
)
util.dt = dt_util


async def async_get_clientsession(hass):
    return None


class DataUpdateCoordinator:
    def __init__(self, hass, logger, name, update_interval):
        self.hass = hass

    # Support subscription like DataUpdateCoordinator[dict]
    def __class_getitem__(cls, item):  # pragma: no cover - typing only
        return cls


class UpdateFailed(Exception):
    pass


class CoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.hass = coordinator.hass

    async def async_added_to_hass(self):  # pragma: no cover - stub
        return None

    async def async_will_remove_from_hass(self):  # pragma: no cover - stub
        return None

    def __class_getitem__(cls, item):  # pragma: no cover - typing only
        return cls


aiohttp_client.async_get_clientsession = async_get_clientsession
update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
update_coordinator.UpdateFailed = UpdateFailed
update_coordinator.CoordinatorEntity = CoordinatorEntity

helpers.aiohttp_client = aiohttp_client
helpers.update_coordinator = update_coordinator
helpers.event = event_helper

data_entry_flow = types.ModuleType("homeassistant.data_entry_flow")


class FlowResult(dict):
    pass


data_entry_flow.FlowResult = FlowResult

modules = {
    "homeassistant": ha,
    "homeassistant.config_entries": config_entries,
    "homeassistant.core": core,
    "homeassistant.exceptions": exceptions,
    "homeassistant.helpers": helpers,
    "homeassistant.helpers.aiohttp_client": aiohttp_client,
    "homeassistant.helpers.update_coordinator": update_coordinator,
    "homeassistant.helpers.entity_platform": entity_platform,
    "homeassistant.helpers.entity_registry": entity_registry,
    "homeassistant.helpers.event": event_helper,
    "homeassistant.util": util,
    "homeassistant.util.dt": dt_util,
    "homeassistant.components": components,
    "homeassistant.components.binary_sensor": components_binary_sensor,
    "homeassistant.components.calendar": components_calendar,
    "homeassistant.data_entry_flow": data_entry_flow,
}

for name, module in modules.items():
    sys.modules.setdefault(name, module)

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest
from aiohttp import ClientSession

from custom_components.vacasa.api_client import VacasaApiClient


@pytest.fixture
def mock_hass():
    """Mock Home Assistant instance."""
    hass = Mock()
    hass.async_add_executor_job = AsyncMock()
    return hass


@pytest.fixture
def mock_session():
    """Mock aiohttp ClientSession."""
    session = Mock(spec=ClientSession)
    session.close = AsyncMock()
    return session


@pytest.fixture
def temp_token_cache():
    """Create a temporary token cache file."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        temp_file = f.name

    yield temp_file

    # Clean up
    if os.path.exists(temp_file):
        os.unlink(temp_file)


@pytest.fixture
def api_client(mock_hass, temp_token_cache):
    """Create a VacasaApiClient instance for testing."""
    return VacasaApiClient(
        username="test@example.com",
        password="test_password",
        token_cache_path=temp_token_cache,
        hass=mock_hass,
    )


@pytest.fixture
def api_client_no_hass(temp_token_cache):
    """Create a VacasaApiClient instance without hass for testing."""
    return VacasaApiClient(
        username="test@example.com",
        password="test_password",
        token_cache_path=temp_token_cache,
    )


@pytest.fixture
def valid_token():
    """Return valid JWT token for testing."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"


@pytest.fixture
def valid_token_cache_data():
    """Return valid token cache data."""
    expiry_time = datetime.now(timezone.utc) + timedelta(minutes=30)
    return {"token": "valid_test_token", "expiry": expiry_time.isoformat()}


@pytest.fixture
def expired_token_cache_data():
    """Expired token cache data."""
    expiry_time = datetime.now(timezone.utc) - timedelta(minutes=30)
    return {"token": "expired_test_token", "expiry": expiry_time.isoformat()}


@pytest.fixture
def mock_guest_reservation():
    """Mock guest reservation data."""
    return {
        "id": "12345",
        "type": "reservations",
        "attributes": {
            "startDate": "2024-01-15",
            "endDate": "2024-01-18",
            "firstName": "John",
            "lastName": "Doe",
            "ownerHold": None,
        },
    }


@pytest.fixture
def mock_owner_reservation():
    """Mock owner reservation data."""
    return {
        "id": "67890",
        "type": "reservations",
        "attributes": {
            "startDate": "2024-02-01",
            "endDate": "2024-02-05",
            "firstName": None,
            "lastName": None,
            "ownerHold": {"holdType": "Owner"},
        },
    }


@pytest.fixture
def mock_maintenance_reservation():
    """Mock maintenance reservation data."""
    return {
        "id": "11111",
        "type": "reservations",
        "attributes": {
            "startDate": "2024-03-01",
            "endDate": "2024-03-02",
            "firstName": None,
            "lastName": None,
            "ownerHold": {"holdType": "Maintenance"},
        },
    }


@pytest.fixture
def mock_block_reservation():
    """Mock block reservation data."""
    return {
        "id": "22222",
        "type": "reservations",
        "attributes": {
            "startDate": "2024-04-01",
            "endDate": "2024-04-03",
            "firstName": None,
            "lastName": None,
            "ownerHold": {"holdType": "Block"},
        },
    }


@pytest.fixture
def mock_other_reservation():
    """Mock other/unknown reservation data."""
    return {
        "id": "33333",
        "type": "reservations",
        "attributes": {
            "startDate": "2024-05-01",
            "endDate": "2024-05-02",
            "firstName": None,
            "lastName": None,
            "ownerHold": None,
        },
    }


@pytest.fixture
def mock_units_response():
    """Mock units API response."""
    return {
        "data": [
            {
                "id": "unit123",
                "type": "unit",
                "attributes": {
                    "name": "Beach House",
                    "code": "BH001",
                    "address": {"city": "Ocean City", "state": "CA"},
                },
            }
        ]
    }


@pytest.fixture
def mock_verify_token_response():
    """Mock verify-token API response."""
    return {"data": {"contactIds": ["owner123"], "valid": True}}


@pytest.fixture
def mock_reservations_response(mock_guest_reservation, mock_owner_reservation):
    """Mock reservations API response."""
    return {"data": [mock_guest_reservation, mock_owner_reservation]}


@pytest.fixture
def mock_auth_response():
    """Mock authentication response."""
    response = Mock()
    response.status = 200
    response.url = "https://owner.vacasa.io/dashboard#access_token=test_token&expires_in=3600"
    response.text = AsyncMock(return_value="Authentication successful")
    return response


@pytest.fixture
def mock_api_error_response():
    """Mock API error response."""
    response = Mock()
    response.status = 401
    response.text = AsyncMock(return_value="Unauthorized")
    return response


@pytest.fixture
def mock_network_error():
    """Mock network error."""
    return aiohttp.ClientError("Network connection failed")


@pytest.fixture
def mock_json_decode_error():
    """Mock JSON decode error."""
    return json.JSONDecodeError("Invalid JSON", "", 0)


@pytest.fixture
def mock_timeout_error():
    """Mock timeout error."""
    return aiohttp.ServerTimeoutError("Request timed out")


@pytest.fixture
def setup_mock_responses(mock_session):
    """Set up mock HTTP responses."""

    def _setup_responses(responses):
        """Configure mock responses for the session."""
        mock_session.get.side_effect = responses.get("get", [])
        mock_session.post.side_effect = responses.get("post", [])

    return _setup_responses


@pytest.fixture
def mock_successful_auth_flow(mock_session, mock_auth_response):
    """Mock successful authentication flow."""
    # Mock the authentication redirect sequence
    mock_session.post.return_value.__aenter__.return_value = mock_auth_response
    return mock_session


@pytest.fixture
def mock_failed_auth_flow(mock_session, mock_api_error_response):
    """Mock failed authentication flow."""
    mock_session.post.return_value.__aenter__.return_value = mock_api_error_response
    return mock_session


@pytest.fixture
def mock_file_operations():
    """Mock file operations for token caching."""
    with (
        patch("builtins.open"),
        patch("os.path.exists"),
        patch("os.chmod"),
        patch("os.remove"),
        patch("json.dump"),
        patch("json.load") as mock_load,
    ):
        yield mock_load


@pytest.fixture
def mock_datetime():
    """Mock datetime for consistent testing."""
    with patch("custom_components.vacasa.api_client.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt.fromtimestamp.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt.fromisoformat.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        yield mock_dt
