"""Unit tests for the Vacasa API client."""

import json
import urllib.parse
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, mock_open, patch

import aiohttp
import pytest

from custom_components.vacasa.api_client import ApiError, AuthenticationError, VacasaApiClient
from custom_components.vacasa.const import (
    STAY_TYPE_BLOCK,
    STAY_TYPE_GUEST,
    STAY_TYPE_MAINTENANCE,
    STAY_TYPE_OTHER,
    STAY_TYPE_OWNER,
)


class TestVacasaApiClient:
    """Test cases for VacasaApiClient."""

    def test_init_with_defaults(self):
        """Test client initialization with default parameters."""
        client = VacasaApiClient("test@example.com", "password")

        assert client._username == "test@example.com"
        assert client._password == "password"
        assert client._session is None
        assert client._token is None
        assert client._token_expiry is None
        assert client._owner_id is None
        assert client._close_session is False

    def test_init_with_custom_params(self, mock_hass, temp_token_cache):
        """Test client initialization with custom parameters."""
        mock_session = Mock()

        client = VacasaApiClient(
            username="test@example.com",
            password="password",
            session=mock_session,
            token_cache_path=temp_token_cache,
            hass=mock_hass,
        )

        assert client._username == "test@example.com"
        assert client._password == "password"
        assert client._session == mock_session
        assert client._token_cache_file == temp_token_cache
        assert client._hass == mock_hass


class TestTokenValidation:
    """Test token validation and expiry logic."""

    def test_is_token_valid_no_token(self, api_client):
        """Test token validation when no token is present."""
        assert not api_client.is_token_valid

    def test_is_token_valid_no_expiry(self, api_client):
        """Test token validation when token has no expiry."""
        api_client._token = "test_token"
        assert not api_client.is_token_valid

    def test_is_token_valid_expired_token(self, api_client):
        """Test token validation with expired token."""
        api_client._token = "test_token"
        api_client._token_expiry = datetime.now(timezone.utc) - timedelta(minutes=10)
        assert not api_client.is_token_valid

    def test_is_token_valid_token_expires_soon(self, api_client):
        """Test token validation with token expiring within refresh margin."""
        api_client._token = "test_token"
        # Token expires in 4 minutes (less than TOKEN_REFRESH_MARGIN of 5 minutes)
        api_client._token_expiry = datetime.now(timezone.utc) + timedelta(minutes=4)
        assert not api_client.is_token_valid

    def test_is_token_valid_valid_token(self, api_client):
        """Test token validation with valid token."""
        api_client._token = "test_token"
        api_client._token_expiry = datetime.now(timezone.utc) + timedelta(minutes=10)
        assert api_client.is_token_valid

    def test_token_property(self, api_client):
        """Test token property getter."""
        assert api_client.token is None

        api_client._token = "test_token"
        assert api_client.token == "test_token"


class TestReservationCategorization:
    """Test reservation categorization logic."""

    def test_categorize_reservation_guest(self, api_client, mock_guest_reservation):
        """Test guest booking categorization."""
        result = api_client.categorize_reservation(mock_guest_reservation)
        assert result == STAY_TYPE_GUEST

    def test_categorize_reservation_owner(self, api_client, mock_owner_reservation):
        """Test owner stay categorization."""
        result = api_client.categorize_reservation(mock_owner_reservation)
        assert result == STAY_TYPE_OWNER

    def test_categorize_reservation_maintenance(self, api_client, mock_maintenance_reservation):
        """Test maintenance categorization."""
        result = api_client.categorize_reservation(mock_maintenance_reservation)
        assert result == STAY_TYPE_MAINTENANCE

    def test_categorize_reservation_property_care(self, api_client):
        """Test property care categorization (alternative maintenance type)."""
        reservation = {"attributes": {"ownerHold": {"holdType": "Property Care"}}}
        result = api_client.categorize_reservation(reservation)
        assert result == STAY_TYPE_MAINTENANCE

    def test_categorize_reservation_block(self, api_client, mock_block_reservation):
        """Test block categorization."""
        result = api_client.categorize_reservation(mock_block_reservation)
        assert result == STAY_TYPE_BLOCK

    def test_categorize_reservation_other(self, api_client, mock_other_reservation):
        """Test fallback categorization."""
        result = api_client.categorize_reservation(mock_other_reservation)
        assert result == STAY_TYPE_OTHER

    def test_categorize_reservation_owner_hold_unknown_type(self, api_client):
        """Test categorization with unknown owner hold type."""
        reservation = {"attributes": {"ownerHold": {"holdType": "Unknown Type"}}}
        result = api_client.categorize_reservation(reservation)
        assert result == STAY_TYPE_BLOCK

    def test_categorize_reservation_case_insensitive(self, api_client):
        """Test categorization is case insensitive."""
        reservation = {"attributes": {"ownerHold": {"holdType": "OWNER"}}}
        result = api_client.categorize_reservation(reservation)
        assert result == STAY_TYPE_OWNER

    def test_categorize_reservation_partial_guest_info(self, api_client):
        """Test categorization with partial guest information."""
        reservation = {"attributes": {"firstName": "John", "lastName": None, "ownerHold": None}}
        result = api_client.categorize_reservation(reservation)
        assert result == STAY_TYPE_OTHER

    def test_categorize_reservation_empty_attributes(self, api_client):
        """Test categorization with empty attributes."""
        reservation = {"attributes": {}}
        result = api_client.categorize_reservation(reservation)
        assert result == STAY_TYPE_OTHER

    def test_categorize_reservation_no_attributes(self, api_client):
        """Test categorization with no attributes."""
        reservation = {}
        result = api_client.categorize_reservation(reservation)
        assert result == STAY_TYPE_OTHER


class TestTokenCaching:
    """Test token caching functionality."""

    @pytest.mark.asyncio
    async def test_save_token_to_cache_with_hass(self, api_client):
        """Test saving token to cache with hass instance."""
        api_client._token = "test_token"
        api_client._token_expiry = datetime.now(timezone.utc) + timedelta(minutes=10)

        # Mock the synchronous save method
        with patch.object(api_client, "_save_token_to_cache_sync") as mock_save:
            await api_client._save_token_to_cache()

            # Verify hass executor was called
            api_client._hass.async_add_executor_job.assert_called_once_with(mock_save)

    @pytest.mark.asyncio
    async def test_save_token_to_cache_without_hass(self, api_client_no_hass):
        """Test saving token to cache without hass instance."""
        api_client_no_hass._token = "test_token"
        api_client_no_hass._token_expiry = datetime.now(timezone.utc) + timedelta(minutes=10)

        # Mock the synchronous save method
        with patch.object(api_client_no_hass, "_save_token_to_cache_sync") as mock_save:
            await api_client_no_hass._save_token_to_cache()

            # Verify synchronous method was called directly
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_token_to_cache_no_token(self, api_client):
        """Test saving token to cache when no token is present."""
        with patch.object(api_client, "_save_token_to_cache_sync") as mock_save:
            await api_client._save_token_to_cache()

            # Should not call save if no token
            mock_save.assert_not_called()

    def test_save_token_to_cache_sync(self, api_client):
        """Test synchronous token cache save."""
        api_client._token = "test_token"
        api_client._token_expiry = datetime.now(timezone.utc) + timedelta(minutes=10)

        mock_file = mock_open()
        with (
            patch("builtins.open", mock_file),
            patch("json.dump") as mock_dump,
            patch("os.chmod") as mock_chmod,
        ):
            api_client._save_token_to_cache_sync()

            # Verify file operations
            mock_file.assert_called_once_with(api_client._token_cache_file, "w")
            mock_dump.assert_called_once()
            mock_chmod.assert_called_once_with(api_client._token_cache_file, 0o600)

    @pytest.mark.asyncio
    async def test_load_token_from_cache_with_hass(self, api_client):
        """Test loading token from cache with hass instance."""
        with patch.object(
            api_client, "_load_token_from_cache_sync", return_value=True
        ) as mock_load:
            # Configure hass mock to return the expected value
            api_client._hass.async_add_executor_job.return_value = True

            result = await api_client._load_token_from_cache()

            # Verify hass executor was called
            api_client._hass.async_add_executor_job.assert_called_once_with(mock_load)
            assert result is True

    @pytest.mark.asyncio
    async def test_load_token_from_cache_without_hass(self, api_client_no_hass):
        """Test loading token from cache without hass instance."""
        with patch.object(
            api_client_no_hass, "_load_token_from_cache_sync", return_value=True
        ) as mock_load:
            result = await api_client_no_hass._load_token_from_cache()

            # Verify synchronous method was called directly
            mock_load.assert_called_once()
            assert result is True

    def test_load_token_from_cache_sync_file_not_exists(self, api_client):
        """Test loading token from cache when file doesn't exist."""
        with patch("os.path.exists", return_value=False):
            result = api_client._load_token_from_cache_sync()
            assert result is False

    def test_load_token_from_cache_sync_valid_cache(self, api_client, valid_token_cache_data):
        """Test loading valid token from cache."""
        mock_file = mock_open(read_data=json.dumps(valid_token_cache_data))

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_file),
            patch("json.load", return_value=valid_token_cache_data),
        ):
            result = api_client._load_token_from_cache_sync()

            assert result is True
            assert api_client._token == valid_token_cache_data["token"]
            assert api_client._token_expiry is not None

    def test_load_token_from_cache_sync_invalid_cache(self, api_client):
        """Test loading invalid token from cache."""
        invalid_data = {"invalid": "data"}
        mock_file = mock_open(read_data=json.dumps(invalid_data))

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_file),
            patch("json.load", return_value=invalid_data),
        ):
            result = api_client._load_token_from_cache_sync()

            assert result is False

    @pytest.mark.asyncio
    async def test_load_token_from_cache_json_error(self, api_client):
        """Test loading token from cache with JSON decode error."""
        with patch.object(
            api_client,
            "_load_token_from_cache_sync",
            side_effect=json.JSONDecodeError("Invalid", "", 0),
        ):
            # Configure hass mock to raise the exception through executor
            api_client._hass.async_add_executor_job.side_effect = json.JSONDecodeError(
                "Invalid", "", 0
            )

            result = await api_client._load_token_from_cache()
            assert result is False

    @pytest.mark.asyncio
    async def test_clear_cache(self, api_client):
        """Test clearing token cache."""
        api_client._token = "test_token"
        api_client._token_expiry = datetime.now(timezone.utc)

        with (
            patch("os.path.exists", return_value=True),
            patch("os.remove") as mock_remove,
        ):
            await api_client.clear_cache()

            assert api_client._token is None
            assert api_client._token_expiry is None
            mock_remove.assert_called_once_with(api_client._token_cache_file)

    @pytest.mark.asyncio
    async def test_clear_cache_file_not_exists(self, api_client):
        """Test clearing cache when file doesn't exist."""
        with (
            patch("os.path.exists", return_value=False),
            patch("os.remove") as mock_remove,
        ):
            await api_client.clear_cache()

            assert api_client._token is None
            assert api_client._token_expiry is None
            mock_remove.assert_not_called()


class TestAuthenticationTokenHandling:
    """Test authentication token handling."""

    @pytest.mark.asyncio
    async def test_ensure_token_valid_cached_token(self, api_client):
        """Test ensure_token with valid cached token."""
        api_client._token = "cached_token"
        api_client._token_expiry = datetime.now(timezone.utc) + timedelta(minutes=10)

        result = await api_client.ensure_token()

        assert result == "cached_token"

    @pytest.mark.asyncio
    async def test_ensure_token_load_from_cache(self, api_client):
        """Test ensure_token loading valid token from cache."""
        with (
            patch.object(api_client, "_load_token_from_cache", return_value=True),
            patch.object(
                type(api_client),
                "is_token_valid",
                new_callable=lambda: property(lambda self: True),
            ),
        ):
            api_client._token = "cached_token"
            result = await api_client.ensure_token()

            assert result == "cached_token"

    @pytest.mark.asyncio
    async def test_ensure_token_authenticate_and_save(self, api_client):
        """Test ensure_token authenticating and saving new token."""
        with (
            patch.object(api_client, "_load_token_from_cache", return_value=False),
            patch.object(api_client, "authenticate") as mock_auth,
            patch.object(api_client, "_save_token_to_cache") as mock_save,
        ):
            api_client._token = "new_token"
            result = await api_client.ensure_token()

            mock_auth.assert_called_once()
            mock_save.assert_called_once()
            assert result == "new_token"

    @pytest.mark.asyncio
    async def test_ensure_session_creates_new_session(self, api_client):
        """Test ensure_session creates new session when none exists."""
        # Mock the internal session creation method to avoid real connectors
        mock_session = Mock()
        with patch.object(
            api_client, "_create_optimized_session", return_value=mock_session
        ) as mock_create:
            session = await api_client.ensure_session()

            mock_create.assert_called_once()
            assert session == mock_session
            assert api_client._session == mock_session
            assert api_client._close_session is True

    @pytest.mark.asyncio
    async def test_ensure_session_returns_existing_session(self, api_client, mock_session):
        """Test ensure_session returns existing session."""
        api_client._session = mock_session

        session = await api_client.ensure_session()

        assert session == mock_session

    @pytest.mark.asyncio
    async def test_context_manager_creates_session(self):
        """Test context manager creates and closes session."""
        client = VacasaApiClient("test@example.com", "password")

        # Mock the internal session creation method to avoid real connectors
        mock_session = Mock()
        mock_session.close = AsyncMock()

        with patch.object(
            client, "_create_optimized_session", return_value=mock_session
        ) as mock_create:
            async with client as ctx_client:
                assert ctx_client == client
                assert client._session == mock_session
                assert client._close_session is True

            mock_create.assert_called_once()
            mock_session.close.assert_called_once()
            assert client._session is None
            assert client._close_session is False

    @pytest.mark.asyncio
    async def test_context_manager_with_existing_session(self, mock_session):
        """Test context manager with existing session."""
        client = VacasaApiClient("test@example.com", "password", session=mock_session)

        async with client as ctx_client:
            assert ctx_client == client
            assert client._session == mock_session
            assert client._close_session is False

        mock_session.close.assert_not_called()


class TestErrorHandling:
    """Test error handling and retry logic."""

    @pytest.mark.asyncio
    async def test_get_units_api_error(self, api_client):
        """Test get_units with API error response."""
        with (
            patch.object(api_client, "ensure_token"),
            patch.object(api_client, "get_owner_id", return_value="owner123"),
            patch.object(api_client, "ensure_session") as mock_session_method,
            patch.object(
                api_client,
                "authenticate",
                new=AsyncMock(side_effect=AuthenticationError("Unauthorized")),
            ),
        ):
            mock_response = Mock()
            mock_response.status = 401
            mock_response.text = AsyncMock(return_value="Unauthorized")

            mock_session = Mock()
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_response
            mock_context_manager.__aexit__.return_value = None
            mock_session.request.return_value = mock_context_manager
            mock_session_method.return_value = mock_session

            with pytest.raises(ApiError, match="Error getting units: Unauthorized"):
                await api_client.get_units()

    @pytest.mark.asyncio
    async def test_get_units_network_error(self, api_client):
        """Test get_units with network error."""
        with (
            patch.object(api_client, "ensure_token"),
            patch.object(api_client, "get_owner_id", return_value="owner123"),
            patch.object(api_client, "ensure_session") as mock_session_method,
        ):
            mock_session = Mock()
            mock_session.request.side_effect = aiohttp.ClientError("Network error")
            mock_session_method.return_value = mock_session

            with pytest.raises(
                ApiError,
                match="Error getting units: HTTP error contacting Vacasa API: Network error",
            ):
                await api_client.get_units()

    @pytest.mark.asyncio
    async def test_get_reservations_api_error(self, api_client):
        """Test get_reservations with API error response."""
        with (
            patch.object(api_client, "ensure_token"),
            patch.object(api_client, "get_owner_id", return_value="owner123"),
            patch.object(api_client, "ensure_session") as mock_session_method,
        ):
            mock_response = Mock()
            mock_response.status = 404
            mock_response.text = AsyncMock(return_value="Not Found")

            mock_session = Mock()
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_response
            mock_context_manager.__aexit__.return_value = None
            mock_session.request.return_value = mock_context_manager
            mock_session_method.return_value = mock_session

            with pytest.raises(
                ApiError,
                match=(
                    "Error getting reservations: Endpoint "
                    "/owners/owner123/units/unit123/reservations unavailable"
                ),
            ):
                await api_client.get_reservations("unit123", "2024-01-01")

    @pytest.mark.asyncio
    async def test_get_owner_id_api_error(self, api_client):
        """Test get_owner_id with API error response."""
        with (
            patch.object(api_client, "ensure_token"),
            patch.object(api_client, "ensure_session") as mock_session_method,
        ):
            mock_response = Mock()
            mock_response.status = 403
            mock_response.text = AsyncMock(return_value="Forbidden")

            mock_session = Mock()
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_response
            mock_context_manager.__aexit__.return_value = None
            mock_session.request.return_value = mock_context_manager
            mock_session_method.return_value = mock_session

            with pytest.raises(
                AuthenticationError,
                match="Forbidden request to /verify-token: 403",
            ):
                await api_client.get_owner_id()

    @pytest.mark.asyncio
    async def test_get_owner_id_unexpected_response(self, api_client):
        """Test get_owner_id with unexpected response format."""
        with (
            patch.object(api_client, "ensure_token"),
            patch.object(api_client, "ensure_session") as mock_session_method,
        ):
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"unexpected": "format"})

            mock_session = Mock()
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_response
            mock_context_manager.__aexit__.return_value = None
            mock_session.request.return_value = mock_context_manager
            mock_session_method.return_value = mock_session

            with pytest.raises(ApiError, match="Unexpected verify-token response format"):
                await api_client.get_owner_id()


class TestApiResponseParsing:
    """Test API response parsing."""

    @pytest.mark.asyncio
    async def test_get_units_success(self, api_client, mock_units_response):
        """Test successful get_units response parsing."""
        with (
            patch.object(api_client, "ensure_token"),
            patch.object(api_client, "get_owner_id", return_value="owner123"),
            patch.object(api_client, "ensure_session") as mock_session_method,
        ):
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_units_response)

            mock_session = Mock()
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_response
            mock_context_manager.__aexit__.return_value = None
            mock_session.request.return_value = mock_context_manager
            mock_session_method.return_value = mock_session

            result = await api_client.get_units()

            assert len(result) == 1
            assert result[0]["id"] == "unit123"
            assert result[0]["attributes"]["name"] == "Beach House"

    @pytest.mark.asyncio
    async def test_get_units_empty_response(self, api_client):
        """Test get_units with empty response."""
        with (
            patch.object(api_client, "ensure_token"),
            patch.object(api_client, "get_owner_id", return_value="owner123"),
            patch.object(api_client, "ensure_session") as mock_session_method,
        ):
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"data": []})

            mock_session = Mock()
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_response
            mock_context_manager.__aexit__.return_value = None
            mock_session.request.return_value = mock_context_manager
            mock_session_method.return_value = mock_session

            result = await api_client.get_units()

            assert result == []

    @pytest.mark.asyncio
    async def test_get_units_no_data_field(self, api_client):
        """Test get_units with response missing data field."""
        with (
            patch.object(api_client, "ensure_token"),
            patch.object(api_client, "get_owner_id", return_value="owner123"),
            patch.object(api_client, "ensure_session") as mock_session_method,
        ):
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"error": "No data"})

            mock_session = Mock()
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_response
            mock_context_manager.__aexit__.return_value = None
            mock_session.request.return_value = mock_context_manager
            mock_session_method.return_value = mock_session

            result = await api_client.get_units()

            assert result == []

    @pytest.mark.asyncio
    async def test_get_reservations_success(self, api_client, mock_reservations_response):
        """Test successful get_reservations response parsing."""
        with (
            patch.object(api_client, "ensure_token"),
            patch.object(api_client, "get_owner_id", return_value="owner123"),
            patch.object(api_client, "ensure_session") as mock_session_method,
        ):
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_reservations_response)

            mock_session = Mock()
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_response
            mock_context_manager.__aexit__.return_value = None
            mock_session.request.return_value = mock_context_manager
            mock_session_method.return_value = mock_session

            result = await api_client.get_reservations("unit123", "2024-01-01")

            assert len(result) == 2
            assert result[0]["id"] == "12345"
            assert result[1]["id"] == "67890"

    @pytest.mark.asyncio
    async def test_get_owner_id_success(self, api_client, mock_verify_token_response):
        """Test successful get_owner_id response parsing."""
        with (
            patch.object(api_client, "ensure_token"),
            patch.object(api_client, "ensure_session") as mock_session_method,
        ):
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_verify_token_response)

            mock_session = Mock()
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_response
            mock_context_manager.__aexit__.return_value = None
            mock_session.request.return_value = mock_context_manager
            mock_session_method.return_value = mock_session

            result = await api_client.get_owner_id()

            assert result == "owner123"
            assert api_client._owner_id == "owner123"

    @pytest.mark.asyncio
    async def test_get_owner_id_cached(self, api_client):
        """Test get_owner_id returns cached value."""
        api_client._owner_id = "cached_owner"

        result = await api_client.get_owner_id()

        assert result == "cached_owner"

    @pytest.mark.asyncio
    async def test_get_categorized_reservations(self, api_client, mock_reservations_response):
        """Test get_categorized_reservations."""
        with patch.object(
            api_client,
            "get_reservations",
            return_value=mock_reservations_response["data"],
        ):
            result = await api_client.get_categorized_reservations("unit123", "2024-01-01")

            assert len(result[STAY_TYPE_GUEST]) == 1
            assert len(result[STAY_TYPE_OWNER]) == 1
            assert len(result[STAY_TYPE_MAINTENANCE]) == 0
            assert len(result[STAY_TYPE_BLOCK]) == 0
            assert len(result[STAY_TYPE_OTHER]) == 0

    def test_get_headers_without_owner_id(self, api_client):
        """Test _get_headers without owner ID."""
        api_client._token = "test_token"

        headers = api_client._get_headers()

        assert headers["Authorization"] == "Bearer test_token"
        assert headers["Accept"] == "application/json, text/plain, */*"
        assert "X-Authorization-Contact" not in headers

    def test_get_headers_with_owner_id(self, api_client):
        """Test _get_headers with owner ID."""
        api_client._token = "test_token"
        api_client._owner_id = "owner123"

        headers = api_client._get_headers()

        assert headers["Authorization"] == "Bearer test_token"
        assert headers["X-Authorization-Contact"] == "owner123"

    def test_format_params(self, api_client):
        """Test _format_params utility method."""
        params = {"key1": "value1", "key2": "value2"}
        result = api_client._format_params(params)

        parsed = dict(urllib.parse.parse_qsl(result))
        assert parsed == params

    def test_format_params_special_characters(self, api_client):
        """Test parameter formatting with special characters."""
        params = {
            "spaced key": "value with spaces",
            "amp": "a&b",
            "equals": "x=y",
        }

        result = api_client._format_params(params)
        parsed = dict(urllib.parse.parse_qsl(result))

        assert parsed == params

    def test_base64_url_decode(self, api_client):
        """Test _base64_url_decode utility method."""
        # Test with properly padded base64url string
        encoded = "SGVsbG8gV29ybGQ"  # "Hello World" in base64url
        result = api_client._base64_url_decode(encoded)

        assert result == "Hello World"

    def test_timestamp_to_datetime(self, api_client):
        """Test _timestamp_to_datetime utility method."""
        timestamp = 1640995200  # 2022-01-01 00:00:00 UTC
        result = api_client._timestamp_to_datetime(timestamp)

        assert result.year == 2022
        assert result.month == 1
        assert result.day == 1
        assert result.tzinfo == timezone.utc
