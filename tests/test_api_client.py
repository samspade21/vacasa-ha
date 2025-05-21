"""Test the Vacasa API client."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from homeassistant.core import HomeAssistant

from custom_components.vacasa.api_client import (
    ApiError,
    AuthenticationError,
    VacasaApiClient,
)


@pytest.fixture
def mock_session():
    """Provide a mock aiohttp ClientSession."""
    session = MagicMock()
    session.request = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def api_client(mock_session):
    """Provide a VacasaApiClient instance with a mock session."""
    with patch("aiohttp.ClientSession", return_value=mock_session):
        client = VacasaApiClient("test@example.com", "test-password")
        yield client


async def test_authentication_success(api_client, mock_session):
    """Test successful authentication."""
    # Mock the login response
    login_response = AsyncMock()
    login_response.status = 200
    login_response.text = AsyncMock(return_value="<html>Login page</html>")

    # Mock the token response
    token_response = AsyncMock()
    token_response.status = 200
    token_response.url = MagicMock()
    token_response.url.fragment = (
        "access_token=mock-token&token_type=bearer&expires_in=600"
    )

    # Set up the session to return our mock responses
    mock_session.request.side_effect = [login_response, token_response]

    # Call authenticate
    token = await api_client.authenticate()

    # Verify the result
    assert token == "mock-token"
    assert api_client._token == "mock-token"
    assert mock_session.request.call_count == 2


async def test_authentication_failure(api_client, mock_session):
    """Test authentication failure."""
    # Mock the login response
    login_response = AsyncMock()
    login_response.status = 401
    login_response.text = AsyncMock(return_value="<html>Invalid credentials</html>")

    # Set up the session to return our mock response
    mock_session.request.side_effect = [login_response]

    # Call authenticate and verify it raises an exception
    with pytest.raises(AuthenticationError):
        await api_client.authenticate()


async def test_get_owner_id_success(api_client, mock_session):
    """Test successful owner ID retrieval."""
    # Mock the API response
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(return_value={"data": {"id": "12345"}})

    # Set up the session to return our mock response
    mock_session.request.return_value = response

    # Set a token
    api_client._token = "mock-token"

    # Call get_owner_id
    owner_id = await api_client.get_owner_id()

    # Verify the result
    assert owner_id == "12345"
    assert api_client._owner_id == "12345"
    assert mock_session.request.call_count == 1


async def test_get_owner_id_failure(api_client, mock_session):
    """Test owner ID retrieval failure."""
    # Mock the API response
    response = AsyncMock()
    response.status = 404
    response.text = AsyncMock(return_value="Not found")

    # Set up the session to return our mock response
    mock_session.request.return_value = response

    # Set a token
    api_client._token = "mock-token"

    # Call get_owner_id and verify it raises an exception
    with pytest.raises(ApiError):
        await api_client.get_owner_id()


async def test_get_units_success(api_client, mock_session):
    """Test successful units retrieval."""
    # Mock the API response
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(
        return_value={
            "data": [
                {
                    "id": "67890",
                    "type": "unit",
                    "attributes": {
                        "name": "Test Property",
                        "code": "TEST123",
                    },
                }
            ]
        }
    )

    # Set up the session to return our mock response
    mock_session.request.return_value = response

    # Set token and owner ID
    api_client._token = "mock-token"
    api_client._owner_id = "12345"

    # Call get_units
    units = await api_client.get_units()

    # Verify the result
    assert len(units) == 1
    assert units[0]["id"] == "67890"
    assert units[0]["attributes"]["name"] == "Test Property"
    assert mock_session.request.call_count == 1


async def test_get_units_failure(api_client, mock_session):
    """Test units retrieval failure."""
    # Mock the API response
    response = AsyncMock()
    response.status = 500
    response.text = AsyncMock(return_value="Server error")

    # Set up the session to return our mock response
    mock_session.request.return_value = response

    # Set token and owner ID
    api_client._token = "mock-token"
    api_client._owner_id = "12345"

    # Call get_units and verify it raises an exception
    with pytest.raises(ApiError):
        await api_client.get_units()


async def test_get_reservations_success(api_client, mock_session):
    """Test successful reservations retrieval."""
    # Mock the API response
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(
        return_value={
            "data": [
                {
                    "id": "12345",
                    "type": "reservations",
                    "attributes": {
                        "startDate": "2024-08-15",
                        "endDate": "2024-08-18",
                        "firstName": "Guest",
                        "lastName": "Name",
                        "ownerHold": None,
                    },
                }
            ]
        }
    )

    # Set up the session to return our mock response
    mock_session.request.return_value = response

    # Set token and owner ID
    api_client._token = "mock-token"
    api_client._owner_id = "12345"

    # Call get_reservations
    reservations = await api_client.get_reservations(
        "67890", "2024-08-01", "2024-08-31"
    )

    # Verify the result
    assert len(reservations) == 1
    assert reservations[0]["id"] == "12345"
    assert reservations[0]["attributes"]["firstName"] == "Guest"
    assert mock_session.request.call_count == 1


async def test_get_reservations_failure(api_client, mock_session):
    """Test reservations retrieval failure."""
    # Mock the API response
    response = AsyncMock()
    response.status = 500
    response.text = AsyncMock(return_value="Server error")

    # Set up the session to return our mock response
    mock_session.request.return_value = response

    # Set token and owner ID
    api_client._token = "mock-token"
    api_client._owner_id = "12345"

    # Call get_reservations and verify it raises an exception
    with pytest.raises(ApiError):
        await api_client.get_reservations("67890", "2024-08-01", "2024-08-31")


async def test_get_categorized_reservations(api_client):
    """Test reservation categorization."""
    # Mock the get_reservations method
    api_client.get_reservations = AsyncMock(
        return_value=[
            {
                "id": "1",
                "attributes": {
                    "startDate": "2024-08-15",
                    "endDate": "2024-08-18",
                    "firstName": "Guest",
                    "lastName": "Name",
                    "ownerHold": None,
                },
            },
            {
                "id": "2",
                "attributes": {
                    "startDate": "2024-08-20",
                    "endDate": "2024-08-22",
                    "firstName": "Owner",
                    "lastName": "Name",
                    "ownerHold": {"holdType": "owner"},
                },
            },
            {
                "id": "3",
                "attributes": {
                    "startDate": "2024-08-25",
                    "endDate": "2024-08-26",
                    "firstName": "Maintenance",
                    "lastName": "Staff",
                    "ownerHold": {"holdType": "maintenance"},
                },
            },
        ]
    )

    # Call get_categorized_reservations
    categorized = await api_client.get_categorized_reservations(
        "67890", "2024-08-01", "2024-08-31"
    )

    # Verify the result
    assert "guest" in categorized
    assert "owner" in categorized
    assert "maintenance" in categorized
    assert len(categorized["guest"]) == 1
    assert len(categorized["owner"]) == 1
    assert len(categorized["maintenance"]) == 1
    assert categorized["guest"][0]["id"] == "1"
    assert categorized["owner"][0]["id"] == "2"
    assert categorized["maintenance"][0]["id"] == "3"
