"""API client for the Vacasa integration."""

import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp
import base64

from .cached_data import CachedData, RetryWithBackoff
from .const import (
    API_BASE_URL,
    AUTH_URL,
    DEFAULT_CACHE_TTL,
    DEFAULT_CONN_TIMEOUT,
    DEFAULT_JITTER_MAX,
    DEFAULT_KEEPALIVE_TIMEOUT,
    DEFAULT_MAX_CONNECTIONS,
    DEFAULT_READ_TIMEOUT,
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
    PROPERTY_CACHE_FILE,
    RETRY_BACKOFF_MULTIPLIER,
    RETRY_DELAY,
    STAY_TYPE_BLOCK,
    STAY_TYPE_GUEST,
    STAY_TYPE_MAINTENANCE,
    STAY_TYPE_OTHER,
    STAY_TYPE_OWNER,
    TOKEN_CACHE_FILE,
    TOKEN_REFRESH_MARGIN,
)

_LOGGER = logging.getLogger(__name__)


class VacasaApiError(Exception):
    """Base exception for Vacasa API errors."""

    pass


class AuthenticationError(VacasaApiError):
    """Exception raised for authentication failures."""

    pass


class ApiError(VacasaApiError):
    """Exception raised for API errors."""

    pass


class VacasaApiClient:
    """API client for the Vacasa API."""

    def __init__(
        self,
        username: str,
        password: str,
        session: aiohttp.ClientSession | None = None,
        token_cache_path: str | None = None,
        hass_config_dir: str | None = None,
        hass=None,
        cache_ttl: int = DEFAULT_CACHE_TTL,
        max_connections: int = DEFAULT_MAX_CONNECTIONS,
        keepalive_timeout: int = DEFAULT_KEEPALIVE_TIMEOUT,
        conn_timeout: int = DEFAULT_CONN_TIMEOUT,
        read_timeout: int = DEFAULT_READ_TIMEOUT,
        max_retries: int = MAX_RETRIES,
        retry_delay: float = RETRY_DELAY,
        jitter_max: float = DEFAULT_JITTER_MAX,
    ) -> None:
        """Initialize the Vacasa API client.

        Args:
            username: Vacasa account username/email
            password: Vacasa account password
            session: Optional aiohttp ClientSession
            token_cache_path: Optional path to token cache file
            hass_config_dir: Optional Home Assistant config directory
            hass: Optional Home Assistant instance for async file operations
            cache_ttl: Cache TTL in seconds for property data
            max_connections: Maximum number of connections in connection pool
            keepalive_timeout: Keep-alive timeout for connections
            conn_timeout: Connection timeout in seconds
            read_timeout: Read timeout in seconds
            max_retries: Maximum number of retries for requests
            retry_delay: Base retry delay in seconds
            jitter_max: Maximum jitter to add to retry delays
        """
        self._username = username
        self._password = password
        self._session = session
        self._hass = hass
        self._owner_id = None
        self._token = None
        self._token_expiry = None
        self._client_id = (
            "KOIkAJP9XW7ZpTXwRa0B7O4qMuXSQ3p4BKFfTPhr"  # From the auth URL
        )
        self._close_session = False

        # Performance optimization settings
        self._max_connections = max_connections
        self._keepalive_timeout = keepalive_timeout
        self._conn_timeout = conn_timeout
        self._read_timeout = read_timeout

        # Set up token cache file path
        if token_cache_path:
            self._token_cache_file = token_cache_path
        elif hass_config_dir:
            self._token_cache_file = os.path.join(hass_config_dir, TOKEN_CACHE_FILE)
        else:
            self._token_cache_file = TOKEN_CACHE_FILE

        # Set up property cache
        property_cache_path = None
        if hass_config_dir:
            property_cache_path = os.path.join(hass_config_dir, PROPERTY_CACHE_FILE)

        self._property_cache = CachedData(
            cache_file_path=property_cache_path,
            default_ttl=cache_ttl,
            hass=hass,
        )

        # Set up retry handler
        self._retry_handler = RetryWithBackoff(
            max_retries=max_retries,
            base_delay=retry_delay,
            backoff_multiplier=RETRY_BACKOFF_MULTIPLIER,
            max_jitter=jitter_max,
        )


        _LOGGER.debug(
            "Initialized Vacasa API client with cache TTL: %s, max connections: %s",
            cache_ttl,
            max_connections,
        )

    async def __aenter__(self):
        """Async enter context manager."""
        if self._session is None:
            self._session = await self._create_optimized_session()
            self._close_session = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async exit context manager."""
        if self._close_session and self._session:
            await self._session.close()
            self._session = None
            self._close_session = False

    @property
    def token(self) -> str | None:
        """Get the current token."""
        return self._token

    @property
    def is_token_valid(self) -> bool:
        """Check if the current token is valid."""
        if not self._token or not self._token_expiry:
            return False
        # Consider token invalid if it expires within TOKEN_REFRESH_MARGIN
        return (
            datetime.now(timezone.utc) + timedelta(seconds=TOKEN_REFRESH_MARGIN)
            < self._token_expiry
        )

    async def _create_optimized_session(self) -> aiohttp.ClientSession:
        """Create an optimized aiohttp session with connection pooling."""
        # Configure connection pool with optimized settings
        connector = aiohttp.TCPConnector(
            limit=self._max_connections,
            limit_per_host=self._max_connections // 2,
            keepalive_timeout=self._keepalive_timeout,
            enable_cleanup_closed=True,
            ttl_dns_cache=300,  # 5 minutes DNS cache
            use_dns_cache=True,
        )

        # Configure timeouts
        timeout = aiohttp.ClientTimeout(
            total=self._conn_timeout + self._read_timeout,
            connect=self._conn_timeout,
            sock_read=self._read_timeout,
        )

        session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            raise_for_status=False,  # We handle status codes manually
        )

        _LOGGER.debug(
            "Created optimized session with %s max connections, %ss keepalive",
            self._max_connections,
            self._keepalive_timeout,
        )

        return session

    async def ensure_session(self) -> aiohttp.ClientSession:
        """Ensure we have an aiohttp session."""
        if self._session is None:
            self._session = await self._create_optimized_session()
            self._close_session = True
        return self._session

    def _save_token_to_cache_sync(self) -> None:
        """Save the token to the cache file (synchronous helper)."""
        if not self._token or not self._token_expiry:
            return

        cache_data = {
            "token": self._token,
            "expiry": self._token_expiry.isoformat(),
        }

        with open(self._token_cache_file, "w") as f:
            json.dump(cache_data, f)

        # Set file permissions to be readable only by the owner
        os.chmod(self._token_cache_file, 0o600)

        _LOGGER.debug("Token saved to cache file")

    async def _save_token_to_cache(self) -> None:
        """Save the token to the cache file."""
        if not self._token or not self._token_expiry:
            return

        try:
            if self._hass:
                # Use Home Assistant's executor for async file operations
                await self._hass.async_add_executor_job(self._save_token_to_cache_sync)
            else:
                # Fallback to synchronous operation if no hass instance
                self._save_token_to_cache_sync()
        except Exception as e:
            _LOGGER.warning("Failed to save token to cache file: %s", e)

    def _load_token_from_cache_sync(self) -> bool:
        """Load the token from the cache file (synchronous helper).

        Returns:
            True if the token was loaded successfully, False otherwise
        """
        if not os.path.exists(self._token_cache_file):
            _LOGGER.debug("Token cache file does not exist: %s", self._token_cache_file)
            return False

        with open(self._token_cache_file, "r") as f:
            cache_data = json.load(f)

        if not cache_data or "token" not in cache_data or "expiry" not in cache_data:
            _LOGGER.warning("Invalid token cache data format")
            return False

        self._token = cache_data["token"]
        # Ensure token expiry is timezone-aware in UTC
        token_expiry = datetime.fromisoformat(cache_data["expiry"])
        if token_expiry.tzinfo is None:
            # If no timezone info, assume UTC
            self._token_expiry = token_expiry.replace(tzinfo=timezone.utc)
        else:
            # Convert to UTC if it has timezone info
            self._token_expiry = token_expiry.astimezone(timezone.utc)

        _LOGGER.debug("Token loaded from cache file")
        _LOGGER.debug("Token expires at: %s", self._token_expiry)

        return True

    async def _load_token_from_cache(self) -> bool:
        """Load the token from the cache file.

        Returns:
            True if the token was loaded successfully, False otherwise
        """
        try:
            if self._hass:
                # Use Home Assistant's executor for async file operations
                return await self._hass.async_add_executor_job(
                    self._load_token_from_cache_sync
                )
            else:
                # Fallback to synchronous operation if no hass instance
                return self._load_token_from_cache_sync()
        except json.JSONDecodeError:
            _LOGGER.warning("Failed to parse token cache file (invalid JSON)")
            return False
        except Exception as e:
            _LOGGER.warning("Failed to load token from cache file: %s", e)
            return False

    async def clear_cache(self) -> None:
        """Clear the token cache."""
        self._token = None
        self._token_expiry = None

        if os.path.exists(self._token_cache_file):
            try:
                os.remove(self._token_cache_file)
                _LOGGER.debug("Token cache file removed: %s", self._token_cache_file)
            except Exception as e:
                _LOGGER.warning("Failed to remove token cache file: %s", e)

    async def ensure_token(self) -> str:
        """Ensure we have a valid token, refreshing if necessary."""
        if not self.is_token_valid:
            _LOGGER.debug("Token is invalid or missing, attempting to refresh")

            # Try to load token from cache first
            if await self._load_token_from_cache() and self.is_token_valid:
                _LOGGER.debug("Using valid authentication token from cache")
                return self._token

            # If token is still not valid, authenticate
            _LOGGER.debug("Authenticating to get a new token")
            await self.authenticate()

            # Save the new token to cache
            await self._save_token_to_cache()

        return self._token

    def _get_headers(self) -> dict[str, str]:
        """Get headers for API requests.

        Returns:
            Headers dictionary
        """
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Authorization": f"Bearer {self._token}",
            "Sec-Fetch-Site": "cross-site",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Fetch-Mode": "cors",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": "https://owners.vacasa.com",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1.1 Safari/605.1.15"
            ),
            "Referer": "https://owners.vacasa.com/",
            "Sec-Fetch-Dest": "empty",
            "Priority": "u=3, i",
        }

        # Add owner ID header if available
        if self._owner_id:
            headers["X-Authorization-Contact"] = self._owner_id

        return headers

    def _format_params(self, params: dict) -> str:
        """Format parameters for URL.

        Args:
            params: Dictionary of parameters

        Returns:
            Formatted parameters string
        """
        return "&".join([f"{k}={v}" for k, v in params.items()])

    def _base64_url_decode(self, input: str) -> str:
        """Decode base64url-encoded string.

        Args:
            input: The base64url-encoded string

        Returns:
            The decoded string
        """
        # Use the standard library's base64 module with proper URL-safe decoding
        # Add padding if needed
        padding = len(input) % 4
        if padding:
            input += "=" * (4 - padding)

        return base64.urlsafe_b64decode(input).decode("utf-8")

    def _timestamp_to_datetime(self, timestamp: int) -> datetime:
        """Convert timestamp to datetime.

        Args:
            timestamp: Unix timestamp

        Returns:
            Timezone-aware datetime object in UTC
        """
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)

    def categorize_reservation(self, reservation: dict[str, Any]) -> str:
        """Categorize a reservation by stay type.

        Args:
            reservation: The reservation dictionary

        Returns:
            The stay type (guest, owner, block, maintenance, other)
        """
        attributes = reservation.get("attributes", {})

        # Check for owner hold
        owner_hold = attributes.get("ownerHold")
        if owner_hold:
            hold_type = owner_hold.get("holdType", "").lower()
            _LOGGER.debug("Found owner hold with type: %s", hold_type)

            if "owner" in hold_type:
                return STAY_TYPE_OWNER
            elif "maintenance" in hold_type or "property care" in hold_type:
                return STAY_TYPE_MAINTENANCE
            else:
                return STAY_TYPE_BLOCK

        # If it has a first name and last name, it's likely a guest booking
        if attributes.get("firstName") and attributes.get("lastName"):
            return STAY_TYPE_GUEST

        # Default to other
        _LOGGER.debug(
            "Could not categorize reservation, defaulting to 'other': %s",
            attributes.get("id", "unknown"),
        )
        return STAY_TYPE_OTHER

    async def authenticate(self) -> str:
        """Authenticate with Vacasa and get a token.

        This method implements the authentication flow without using Selenium,
        by making direct HTTP requests to simulate the browser-based auth flow.

        Returns:
            The authentication token

        Raises:
            AuthenticationError: If authentication fails
        """
        session = await self.ensure_session()

        # Implement retry logic
        retry_count = 0
        last_error = None

        while retry_count < MAX_RETRIES:
            try:
                if retry_count > 0:
                    # Wait before retrying
                    wait_time = RETRY_DELAY * (
                        2 ** (retry_count - 1)
                    )  # Exponential backoff
                    _LOGGER.debug(
                        "Retrying authentication (attempt %s/%s) after %ss",
                        retry_count + 1,
                        MAX_RETRIES,
                        wait_time,
                    )
                    await asyncio.sleep(wait_time)

                # Step 1: Get the login page to obtain CSRF token
                _LOGGER.debug(
                    "Fetching login page (attempt %s/%s)", retry_count + 1, MAX_RETRIES
                )

                # Try with response_type=token to avoid unsupported_response_type error
                auth_params = {
                    "next": "/authorize",
                    "directory_hint": "email",
                    "owner_migration_needed": "true",
                    "client_id": self._client_id,
                    "response_type": "token",  # Use token instead of token,id_token
                    "redirect_uri": "https://owners.vacasa.com",
                    "scope": "owners:read employees:read",
                    "audience": "owner.vacasa.io",
                    "state": f"{int(time.time())}",  # Use timestamp as state
                    "nonce": f"{int(time.time())}-nonce",  # Use timestamp as nonce
                    "mode": "owner",
                }

                _LOGGER.debug(
                    "Auth URL with params: %s?%s",
                    AUTH_URL,
                    "&".join([f"{k}={v}" for k, v in auth_params.items()]),
                )

                async with session.get(
                    AUTH_URL, params=auth_params, timeout=DEFAULT_TIMEOUT
                ) as response:
                    if response.status != 200:
                        response_text = await response.text()
                        _LOGGER.error(
                            "Failed to load login page: %s - Response: %s...",
                            response.status,
                            response_text[:200],
                        )
                        raise AuthenticationError(
                            f"Failed to load login page: {response.status}"
                        )

                    login_page = await response.text()

                    # Extract CSRF token from the login page
                    csrf_match = re.search(
                        r'name="csrfmiddlewaretoken" value="([^"]+)"', login_page
                    )
                    if not csrf_match:
                        _LOGGER.error(
                            "Could not find CSRF token on login page. Page snippet: %s...",
                            login_page[:200],
                        )
                        raise AuthenticationError(
                            "Could not find CSRF token on login page"
                        )

                    csrf_token = csrf_match.group(1)
                    _LOGGER.debug("Found CSRF token: %s...", csrf_token[:10])

                # Step 2: Submit login credentials
                _LOGGER.debug("Submitting login credentials")
                login_data = {
                    "csrfmiddlewaretoken": csrf_token,
                    "username": self._username,
                    "password": self._password,
                    "next": (
                        f"/authorize?directory_hint=email&owner_migration_needed=true"
                        f"&client_id={self._client_id}&response_type=token"
                        f"&redirect_uri=https://owners.vacasa.com"
                        f"&scope=owners:read%20employees:read&audience=owner.vacasa.io"
                        f"&state={auth_params['state']}&nonce={auth_params['nonce']}&mode=owner"
                    ),
                }

                headers = {
                    "Referer": f"{AUTH_URL}?{self._format_params(auth_params)}",
                    "Content-Type": "application/x-www-form-urlencoded",
                }

                async with session.post(
                    AUTH_URL,
                    data=login_data,
                    headers=headers,
                    allow_redirects=False,
                    timeout=DEFAULT_TIMEOUT,
                ) as response:
                    # Check for redirect (successful login)
                    if response.status not in (302, 303):
                        _LOGGER.error(
                            "Login failed with status %s. Expected redirect (302/303).",
                            response.status,
                        )
                        raise AuthenticationError(
                            f"Login failed with status {response.status}"
                        )

                    # Get redirect location
                    redirect_url = response.headers.get("Location")
                    if not redirect_url:
                        _LOGGER.error("No redirect URL after login")
                        raise AuthenticationError("No redirect URL after login")

                    _LOGGER.debug("Login successful, redirecting to: %s", redirect_url)

                # Step 3: Follow redirects until we get the token
                _LOGGER.debug("Following auth redirects")
                token = await self._follow_auth_redirects(redirect_url)

                if not token:
                    _LOGGER.error("Failed to obtain token after authentication")
                    raise AuthenticationError(
                        "Failed to obtain token after authentication"
                    )

                self._token = token
                _LOGGER.debug("Successfully obtained authentication token")

                # Extract token expiry from JWT
                try:
                    # JWT tokens have 3 parts separated by dots
                    token_parts = token.split(".")
                    if len(token_parts) >= 2:
                        # Decode the payload (middle part)
                        padded_payload = token_parts[1] + "=" * (
                            4 - len(token_parts[1]) % 4
                        )
                        payload = json.loads(self._base64_url_decode(padded_payload))

                        # Extract expiry timestamp
                        if "exp" in payload:
                            self._token_expiry = self._timestamp_to_datetime(
                                payload["exp"]
                            )
                            _LOGGER.debug("Token expires at %s", self._token_expiry)
                        else:
                            _LOGGER.warning("No expiry found in token payload")
                except Exception as e:
                    _LOGGER.warning("Failed to parse JWT token: %s", e)

                return self._token

            except Exception as e:
                last_error = e
                _LOGGER.warning(
                    "Authentication attempt %s/%s failed: %s",
                    retry_count + 1,
                    MAX_RETRIES,
                    e,
                )
                retry_count += 1

        # If we've exhausted all retries, raise the last error
        _LOGGER.error(
            "Authentication failed after %s attempts: %s", MAX_RETRIES, last_error
        )
        raise AuthenticationError(
            f"Authentication failed after {MAX_RETRIES} attempts: {last_error}"
        )

    async def _follow_auth_redirects(self, initial_url: str) -> str | None:
        """Follow authentication redirects to extract the token.

        Args:
            initial_url: The initial redirect URL

        Returns:
            The authentication token if found, None otherwise
        """
        session = await self.ensure_session()
        current_url = initial_url
        max_redirects = 10
        redirect_count = 0

        _LOGGER.debug("Following auth redirects starting with: %s", current_url)

        while redirect_count < max_redirects:
            redirect_count += 1

            # Check if the URL already contains the token
            if "#access_token=" in current_url:
                match = re.search(r"access_token=([^&]+)", current_url)
                if match:
                    token = match.group(1)
                    _LOGGER.debug("Extracted token from URL fragment")
                    return token

            # If URL is relative, make it absolute
            if current_url.startswith("/"):
                current_url = f"https://accounts.vacasa.io{current_url}"

            # Follow the redirect
            try:
                async with session.get(
                    current_url, allow_redirects=False, timeout=DEFAULT_TIMEOUT
                ) as response:
                    if response.status in (301, 302, 303, 307, 308):
                        # Handle redirect
                        current_url = response.headers.get("Location", "")
                        if not current_url:
                            _LOGGER.warning("No Location header in redirect response")
                            return None
                    else:
                        # Check for token in URL
                        if "#" in str(response.url):
                            fragment = str(response.url).split("#")[1]
                            match = re.search(r"access_token=([^&]+)", fragment)
                            if match:
                                token = match.group(1)
                                _LOGGER.debug(
                                    "Extracted token from response URL fragment"
                                )
                                return token

                        # If we've reached owners.vacasa.com without a token, try one more request
                        if "owners.vacasa.com" in str(response.url.host):
                            page_content = await response.text()
                            token_match = re.search(
                                r'access_token=([^&"\']+)', page_content
                            )
                            if token_match:
                                token = token_match.group(1)
                                _LOGGER.debug("Found token in page content")
                                return token

                        _LOGGER.warning("No token found in redirect chain")
                        return None
            except Exception as e:
                _LOGGER.error("Error following redirect: %s", e)
                return None

        _LOGGER.warning("Exceeded maximum redirects without finding token")
        return None

    async def get_owner_id(self) -> str:
        """Get the owner ID using the verify-token endpoint.

        Returns:
            The owner ID

        Raises:
            ApiError: If the owner ID cannot be determined
        """
        # If we already have the owner ID cached, return it
        if self._owner_id:
            _LOGGER.debug("Using cached owner ID: %s", self._owner_id)
            return self._owner_id

        # Ensure we have a valid token
        await self.ensure_token()

        try:
            session = await self.ensure_session()

            # Use POST request to verify-token endpoint
            _LOGGER.debug("Getting owner ID from verify-token endpoint")
            async with session.post(
                f"{API_BASE_URL}/verify-token",
                headers=self._get_headers(),
                timeout=DEFAULT_TIMEOUT,
            ) as response:
                if response.status != 200:
                    _LOGGER.error(
                        "Failed to get owner info from verify-token: %s",
                        response.status,
                    )
                    raise ApiError(
                        f"Failed to get owner info from verify-token: {response.status}"
                    )

                data = await response.json()
                _LOGGER.debug("Received response from verify-token endpoint: %s", data)

                # Extract owner ID from the response
                if (
                    "data" in data
                    and "contactIds" in data["data"]
                    and data["data"]["contactIds"]
                ):
                    contact_ids = data["data"]["contactIds"]
                    if contact_ids and len(contact_ids) > 0:
                        self._owner_id = str(contact_ids[0])
                        _LOGGER.debug(
                            "Retrieved owner ID from verify-token: %s", self._owner_id
                        )
                        return self._owner_id
                    else:
                        _LOGGER.error("No contact IDs found in verify-token response")
                        raise ApiError("No contact IDs found in verify-token response")
                else:
                    _LOGGER.error("Unexpected verify-token response format: %s", data)
                    raise ApiError(f"Unexpected verify-token response format: {data}")

        except Exception as e:
            _LOGGER.error("Error getting owner ID: %s", e)
            raise ApiError(f"Error getting owner ID: {e}")

    async def get_units(self) -> list[dict[str, Any]]:
        """Get all units for the owner with caching support.

        Returns:
            List of unit dictionaries

        Raises:
            ApiError: If the API request fails
        """
        # Try to get from cache first
        cache_key = "units"
        cached_units = await self._property_cache.get(cache_key)

        if cached_units is not None:
            _LOGGER.debug("Using cached units data (%s units)", len(cached_units))
            return cached_units

        # If not cached, fetch from API with retry logic
        async def _fetch_units():
            # Ensure we have a valid token and owner ID
            await self.ensure_token()
            owner_id = await self.get_owner_id()

            session = await self.ensure_session()

            _LOGGER.debug("Getting units for owner ID: %s", owner_id)
            units_url = f"{API_BASE_URL}/owners/{owner_id}/units"
            _LOGGER.debug("Units URL: %s", units_url)

            async with session.get(
                units_url,
                headers=self._get_headers(),
                timeout=DEFAULT_TIMEOUT,
            ) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to get units: %s", response.status)
                    response_text = await response.text()
                    _LOGGER.debug("Response: %s", response_text[:200])
                    raise ApiError(f"Failed to get units: {response.status}")

                data = await response.json()
                _LOGGER.debug(
                    "Received units response with status: %s", response.status
                )

                if "data" not in data:
                    _LOGGER.warning("No data field in units response: %s", data)
                    return []

                units = data["data"]
                _LOGGER.debug("Retrieved %s units", len(units))

                # Log unit IDs for debugging
                if units:
                    unit_ids = [unit.get("id") for unit in units]
                    _LOGGER.debug("Unit IDs: %s", unit_ids)

                return units

        try:
            # Use retry wrapper for the API call
            units = await self._retry_handler.retry(_fetch_units)

            # Cache the result
            if units:
                await self._property_cache.set(cache_key, units)
                _LOGGER.debug("Cached %s units", len(units))

            return units

        except Exception as e:
            _LOGGER.error("Error getting units: %s", e)
            raise ApiError(f"Error getting units: {e}")

    async def get_reservations(
        self,
        unit_id: str,
        start_date: str,
        end_date: str | None = None,
        limit: int = 100,
        page: int = 1,
        filter_cancelled: bool = False,
    ) -> list[dict[str, Any]]:
        """Get reservations for a specific unit.

        Args:
            unit_id: The unit ID
            start_date: Start date in YYYY-MM-DD format
            end_date: Optional end date in YYYY-MM-DD format
            limit: Number of results per page
            page: Page number
            filter_cancelled: Whether to filter out cancelled reservations

        Returns:
            List of reservation dictionaries

        Raises:
            ApiError: If the API request fails
        """
        # Ensure we have a valid token and owner ID
        await self.ensure_token()
        owner_id = await self.get_owner_id()

        params = {
            "startDate": start_date,
            "page[limit]": limit,
            "page[number]": page,
            "filterCancelledReservations": 1 if filter_cancelled else 0,
            "unitRelationshipId": "",
            "sort": "asc",
            "acceptVersion": "v2",
        }

        if end_date:
            params["endDate"] = end_date

        try:
            session = await self.ensure_session()

            _LOGGER.debug(
                "Getting reservations for unit %s from %s to %s",
                unit_id,
                start_date,
                end_date if end_date else "future",
            )

            reservations_url = (
                f"{API_BASE_URL}/owners/{owner_id}/units/{unit_id}/reservations"
            )
            _LOGGER.debug(
                "Reservations URL: %s with params: %s", reservations_url, params
            )

            async with session.get(
                reservations_url,
                params=params,
                headers=self._get_headers(),
                timeout=DEFAULT_TIMEOUT,
            ) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to get reservations: %s", response.status)
                    response_text = await response.text()
                    _LOGGER.debug("Response: %s", response_text[:200])
                    raise ApiError(f"Failed to get reservations: {response.status}")

                data = await response.json()
                _LOGGER.debug(
                    "Received reservations response with status: %s", response.status
                )

                if "data" not in data:
                    _LOGGER.warning("No data field in reservations response: %s", data)
                    return []

                reservations = data["data"]
                _LOGGER.debug("Retrieved %s reservations", len(reservations))

                # Log reservation dates for debugging
                if reservations:
                    dates = [
                        (
                            res.get("attributes", {}).get("startDate"),
                            res.get("attributes", {}).get("endDate"),
                        )
                        for res in reservations
                    ]
                    _LOGGER.debug("Reservation dates: %s", dates)

                return reservations
        except Exception as e:
            _LOGGER.error("Error getting reservations: %s", e)
            raise ApiError(f"Error getting reservations: {e}")

    async def get_unit_details(self, unit_id: str) -> dict[str, Any]:
        """Get details for a specific unit with caching support.

        Args:
            unit_id: The unit ID

        Returns:
            Unit details dictionary

        Raises:
            ApiError: If the API request fails
        """
        # Try to get from cache first
        cache_key = f"unit_details_{unit_id}"
        cached_details = await self._property_cache.get(cache_key)

        if cached_details is not None:
            _LOGGER.debug("Using cached unit details for unit %s", unit_id)
            return cached_details

        # If not cached, fetch from API with retry logic
        async def _fetch_unit_details():
            # Ensure we have a valid token and owner ID
            await self.ensure_token()
            owner_id = await self.get_owner_id()

            session = await self.ensure_session()

            _LOGGER.debug("Getting details for unit %s", unit_id)
            unit_details_url = f"{API_BASE_URL}/owners/{owner_id}/units/{unit_id}"
            _LOGGER.debug("Unit details URL: %s", unit_details_url)

            async with session.get(
                unit_details_url,
                headers=self._get_headers(),
                timeout=DEFAULT_TIMEOUT,
            ) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to get unit details: %s", response.status)
                    response_text = await response.text()
                    _LOGGER.debug("Response: %s", response_text[:200])
                    raise ApiError(f"Failed to get unit details: {response.status}")

                data = await response.json()
                _LOGGER.debug(
                    "Received unit details response with status: %s", response.status
                )

                # Log unit name for debugging
                if "data" in data and "attributes" in data["data"]:
                    unit_name = data["data"]["attributes"].get("name")
                    _LOGGER.debug("Unit name: %s", unit_name)

                return data

        try:
            # Use retry wrapper for the API call
            unit_details = await self._retry_handler.retry(_fetch_unit_details)

            # Cache the result
            if unit_details:
                await self._property_cache.set(cache_key, unit_details)
                _LOGGER.debug("Cached unit details for unit %s", unit_id)

            return unit_details

        except Exception as e:
            _LOGGER.error("Error getting unit details: %s", e)
            raise ApiError(f"Error getting unit details: {e}")

    async def clear_property_cache(self) -> None:
        """Clear all cached property data."""
        await self._property_cache.clear()
        _LOGGER.debug("Cleared all property cache data")

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        return self._property_cache.get_stats()

    async def cleanup_expired_cache(self) -> int:
        """Clean up expired cache entries.

        Returns:
            Number of entries removed
        """
        return await self._property_cache.cleanup_expired()

    async def invalidate_cache_for_unit(self, unit_id: str) -> None:
        """Invalidate cache entries for a specific unit.

        Args:
            unit_id: The unit ID to invalidate cache for
        """
        await self._property_cache.delete(f"unit_details_{unit_id}")
        _LOGGER.debug("Invalidated cache for unit %s", unit_id)

    async def get_categorized_reservations(
        self, unit_id: str, start_date: str, end_date: str | None = None
    ) -> dict[str, list[dict[str, Any]]]:
        """Get reservations for a unit, categorized by stay type.

        Args:
            unit_id: The unit ID
            start_date: Start date in YYYY-MM-DD format
            end_date: Optional end date in YYYY-MM-DD format

        Returns:
            Dictionary mapping stay types to lists of reservations

        Raises:
            ApiError: If the API request fails
        """
        reservations = await self.get_reservations(unit_id, start_date, end_date)

        # Initialize categories
        categorized = {
            STAY_TYPE_GUEST: [],
            STAY_TYPE_OWNER: [],
            STAY_TYPE_MAINTENANCE: [],
            STAY_TYPE_BLOCK: [],
            STAY_TYPE_OTHER: [],
        }

        # Categorize each reservation
        for reservation in reservations:
            stay_type = self.categorize_reservation(reservation)
            categorized[stay_type].append(reservation)

        # Log counts for debugging
        _LOGGER.debug(
            "Categorized reservations: Guest: %s, Owner: %s, Maintenance: %s, Block: %s, Other: %s",
            len(categorized[STAY_TYPE_GUEST]),
            len(categorized[STAY_TYPE_OWNER]),
            len(categorized[STAY_TYPE_MAINTENANCE]),
            len(categorized[STAY_TYPE_BLOCK]),
            len(categorized[STAY_TYPE_OTHER]),
        )

        return categorized
