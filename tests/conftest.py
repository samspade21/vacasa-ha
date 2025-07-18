"""Pytest configuration and fixtures for the Vacasa integration tests."""

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
    response.url = (
        "https://owner.vacasa.io/dashboard#access_token=test_token&expires_in=3600"
    )
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
        mock_dt.fromtimestamp.return_value = datetime(
            2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc
        )
        mock_dt.fromisoformat.return_value = datetime(
            2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc
        )
        yield mock_dt
