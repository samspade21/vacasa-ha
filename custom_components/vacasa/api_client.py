"""API client for the Vacasa integration."""

import asyncio
import base64
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, TypeVar
from urllib.parse import urlencode

import aiohttp

from .cached_data import CachedData, RetryWithBackoff, run_blocking_io
from .const import (
    API_BASE_TEMPLATE,
    AUTH_URL,
    CLIENT_ID_CACHE_TTL,
    DEFAULT_API_VERSION,
    DEFAULT_CACHE_TTL,
    DEFAULT_CLIENT_ID,
    DEFAULT_CONN_TIMEOUT,
    DEFAULT_JITTER_MAX,
    DEFAULT_KEEPALIVE_TIMEOUT,
    DEFAULT_MAX_CONCURRENT_REQUESTS,
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
    STAY_TYPE_TO_CATEGORY,
    SUPPORTED_API_VERSIONS,
    TOKEN_CACHE_FILE,
    TOKEN_REFRESH_MARGIN,
)

T = TypeVar("T")

_LOGGER = logging.getLogger(__name__)
_DEFAULT_CLIENT_TIMEOUT = aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)


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
        *,
        client_id: str | None = None,
        api_version: str | None = DEFAULT_API_VERSION,
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
        self._client_id = client_id or DEFAULT_CLIENT_ID
        self._client_id_last_fetch: float | None = None
        self._api_version = api_version or DEFAULT_API_VERSION
        self._api_base_url = API_BASE_TEMPLATE.format(version=self._api_version)
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

        # Semaphore to cap concurrent API requests and avoid rate-limit errors
        self._request_semaphore = asyncio.Semaphore(DEFAULT_MAX_CONCURRENT_REQUESTS)
        # Lock to prevent concurrent owner_id fetches from making duplicate API calls
        self._owner_id_lock = asyncio.Lock()

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
    def token_expiry(self) -> datetime | None:
        """Return the current token expiry."""
        return self._token_expiry

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

    async def _retrieve_client_id(self) -> str | None:
        """Fetch the login page and extract the OAuth client ID."""
        session = await self.ensure_session()

        try:
            async with session.get(AUTH_URL, timeout=_DEFAULT_CLIENT_TIMEOUT) as response:
                if response.status != 200:
                    _LOGGER.warning("Failed to fetch login page for client ID: %s", response.status)
                    return None

                html = await response.text()
        except aiohttp.ClientError as err:
            _LOGGER.warning("Error retrieving client ID: %s", err)
            return None

        patterns = [
            r'data-client-id="([A-Za-z0-9_-]+)"',
            r"client_id=([A-Za-z0-9_-]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1)

        _LOGGER.debug("Unable to parse client ID from login page")
        return None

    async def _ensure_client_id(self) -> str:
        """Ensure the OAuth client ID is up to date."""
        now = time.time()
        cache_valid = (
            self._client_id_last_fetch is not None
            and now - self._client_id_last_fetch < CLIENT_ID_CACHE_TTL
        )

        if cache_valid and self._client_id:
            return self._client_id

        client_id = await self._retrieve_client_id()
        if client_id:
            self._client_id = client_id
            self._client_id_last_fetch = now
            _LOGGER.debug("Retrieved dynamic client ID")
        else:
            if not self._client_id:
                self._client_id = DEFAULT_CLIENT_ID
            _LOGGER.debug("Using cached or default client ID")

        return self._client_id

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

    async def _run_blocking_io(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute a blocking IO function safely in the event loop."""
        return await run_blocking_io(self._hass, func, *args, **kwargs)

    def _set_api_version(self, version: str) -> None:
        """Persist the API version that successfully responded."""
        if version != self._api_version:
            _LOGGER.debug("Switching API version from %s to %s", self._api_version, version)
        self._api_version = version
        self._api_base_url = API_BASE_TEMPLATE.format(version=version)

    def _build_api_url(self, path: str, version: str) -> str:
        """Construct the full API URL for a given version and path."""
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{API_BASE_TEMPLATE.format(version=version)}{path}"

    def _version_candidates(self, override: str | None = None) -> list[str]:
        """Return API versions to try in priority order."""
        if override:
            return [override]

        candidates: list[str] = []
        if self._api_version:
            candidates.append(self._api_version)

        for version in SUPPORTED_API_VERSIONS:
            if version not in candidates:
                candidates.append(version)

        return candidates

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: Any | None = None,
        acceptable_status: tuple[int, ...] = (200,),
        version_override: str | None = None,
        return_json: bool = True,
        retry_on_unauthorized: bool = True,
    ) -> Any:
        """Perform an HTTP request with API version fallback and error handling."""
        session = await self.ensure_session()
        last_error: Exception | None = None

        for version in self._version_candidates(version_override):
            url = self._build_api_url(path, version)
            try:
                async with self._request_semaphore:
                    async with session.request(
                        method,
                        url,
                        params=params,
                        json=json_data,
                        headers=self._get_headers(),
                        timeout=_DEFAULT_CLIENT_TIMEOUT,
                    ) as response:
                        if response.status in acceptable_status:
                            self._set_api_version(version)
                            if not return_json:
                                return await response.text()
                            # Always attempt JSON parsing when return_json=True
                            # API may include charset in content-type
                            # (e.g., "application/json; charset=utf-8")
                            try:
                                return await response.json()
                            except (aiohttp.ContentTypeError, json.JSONDecodeError) as e:
                                # Log diagnostic info for troubleshooting
                                response_text = await response.text()
                                _LOGGER.warning(
                                    "Failed to parse JSON from %s (content-type: %s): %s. "
                                    "Response: %s",
                                    url,
                                    response.content_type,
                                    e,
                                    response_text[:200],
                                )
                                raise ApiError(
                                    f"Non-JSON response from {url}: {response_text[:200]}"
                                ) from e

                        if response.status == 401:
                            # Attempt token refresh once when unauthorized
                            _LOGGER.warning(
                                "API request unauthorized for %s, refreshing token", url
                            )
                            if retry_on_unauthorized:
                                await self.authenticate()
                                await self._save_token_to_cache()
                                return await self._request(
                                    method,
                                    path,
                                    params=params,
                                    json_data=json_data,
                                    acceptable_status=acceptable_status,
                                    version_override=version,
                                    return_json=return_json,
                                    retry_on_unauthorized=False,
                                )
                            last_error = AuthenticationError("Unauthorized")
                            continue

                        if response.status == 403:
                            last_error = AuthenticationError(
                                f"Forbidden request to {path}: {response.status}"
                            )
                            break

                        # Try next version on not found errors when fallbacks are allowed
                        if response.status in (404, 400) and version_override is None:
                            _LOGGER.debug(
                                "API version %s returned %s for %s, trying fallback",
                                version,
                                response.status,
                                path,
                            )
                            last_error = ApiError(f"Endpoint {path} unavailable")
                            continue

                        response_text = await response.text()
                        last_error = ApiError(
                            f"Unexpected status {response.status} for {path}: {response_text[:200]}"
                        )
            except AuthenticationError:
                raise
            except aiohttp.ClientError as err:
                _LOGGER.warning("HTTP error calling %s: %s", url, err)
                last_error = ApiError(f"HTTP error contacting Vacasa API: {err}")
                continue

        if last_error:
            raise last_error

        raise ApiError(f"No API versions available for path {path}")

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
            await self._run_blocking_io(self._save_token_to_cache_sync)
        except (OSError, IOError) as e:
            _LOGGER.warning("Failed to save token to cache file: %s", e)
        except Exception as e:
            _LOGGER.error("Unexpected error saving token to cache: %s", e)
            raise

    def _load_token_from_cache_sync(self) -> bool:
        """Load the token from the cache file (synchronous helper).

        Returns:
            True if the token was loaded successfully, False otherwise
        """
        try:
            with open(self._token_cache_file, "r") as f:
                cache_data = json.load(f)
        except FileNotFoundError:
            _LOGGER.debug("Token cache file does not exist: %s", self._token_cache_file)
            return False

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
            return await self._run_blocking_io(self._load_token_from_cache_sync)
        except Exception as e:
            _LOGGER.warning("Failed to load token from cache file: %s", e)
            return False

    async def clear_cache(self) -> None:
        """Clear the token cache."""
        self._token = None
        self._token_expiry = None

        try:
            await self._run_blocking_io(os.remove, self._token_cache_file)
            _LOGGER.debug("Token cache file removed: %s", self._token_cache_file)
        except FileNotFoundError:
            pass  # File already absent — nothing to remove
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

    def _base64_url_decode(self, encoded: str) -> str:
        """Decode base64url-encoded string."""
        # Add padding if needed
        padding = len(encoded) % 4
        if padding:
            encoded += "=" * (4 - padding)
        return base64.urlsafe_b64decode(encoded).decode("utf-8")

    def _sanitize_url_for_log(self, url: str) -> str:
        """Remove sensitive tokens from URLs before logging."""
        if "#access_token=" in url:
            return url.split("#access_token=")[0] + "#<token_redacted>"
        if "access_token=" in url:
            return re.sub(r"access_token=[^&\s]+", "access_token=<redacted>", url)
        return url

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

        # Check for owner hold first
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

    async def _authenticate_once(self) -> str:
        """Perform a single authentication attempt.

        Returns:
            The authentication token

        Raises:
            AuthenticationError: If the attempt fails for any reason
        """
        session = await self.ensure_session()

        # Step 1: Get the login page to obtain CSRF token
        _LOGGER.debug("Fetching login page")

        client_id = await self._ensure_client_id()

        auth_params = {
            "next": "/authorize",
            "directory_hint": "email",
            "owner_migration_needed": "true",
            "client_id": client_id,
            "response_type": "token",
            "redirect_uri": "https://owners.vacasa.com",
            "scope": "owners:read employees:read",
            "audience": "owner.vacasa.io",
            "state": f"{int(time.time())}",
            "nonce": f"{int(time.time())}-nonce",
            "mode": "owner",
        }

        _LOGGER.debug("Auth URL with params: %s?%s", AUTH_URL, urlencode(auth_params))

        async with session.get(
            AUTH_URL, params=auth_params, timeout=_DEFAULT_CLIENT_TIMEOUT
        ) as response:
            if response.status != 200:
                response_text = await response.text()
                _LOGGER.error(
                    "Failed to load login page: %s - Response: %s...",
                    response.status,
                    response_text[:200],
                )
                raise AuthenticationError(f"Failed to load login page: {response.status}")

            login_page = await response.text()

            csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', login_page)
            if not csrf_match:
                _LOGGER.error(
                    "Could not find CSRF token on login page. Page snippet: %s...",
                    login_page[:200],
                )
                raise AuthenticationError("Could not find CSRF token on login page")

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
                f"&client_id={client_id}&response_type=token"
                f"&redirect_uri=https://owners.vacasa.com"
                f"&scope=owners:read%20employees:read&audience=owner.vacasa.io"
                f"&state={auth_params['state']}&nonce={auth_params['nonce']}&mode=owner"
            ),
        }

        headers = {
            "Referer": f"{AUTH_URL}?{urlencode(auth_params)}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        async with session.post(
            AUTH_URL,
            data=login_data,
            headers=headers,
            allow_redirects=False,
            timeout=_DEFAULT_CLIENT_TIMEOUT,
        ) as response:
            if response.status not in (302, 303):
                _LOGGER.error(
                    "Login failed with status %s. Expected redirect (302/303).",
                    response.status,
                )
                raise AuthenticationError(f"Login failed with status {response.status}")

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
            raise AuthenticationError("Failed to obtain token after authentication")

        self._token = token
        _LOGGER.debug("Successfully obtained authentication token")

        # Extract token expiry from JWT
        try:
            token_parts = token.split(".")
            if len(token_parts) >= 2:
                padded_payload = token_parts[1] + "=" * (4 - len(token_parts[1]) % 4)
                payload = json.loads(self._base64_url_decode(padded_payload))

                if "exp" in payload:
                    self._token_expiry = self._timestamp_to_datetime(payload["exp"])
                    _LOGGER.debug("Token expires at %s", self._token_expiry)
                else:
                    _LOGGER.warning("No expiry found in token payload")
        except Exception as e:
            _LOGGER.warning("Failed to parse JWT token: %s", e)

        return self._token

    async def authenticate(self) -> str:
        """Authenticate with Vacasa and get a token.

        Returns:
            The authentication token

        Raises:
            AuthenticationError: If authentication fails after all retries
        """
        try:
            return await self._retry_handler.retry(self._authenticate_once)
        except AuthenticationError:
            raise
        except Exception as e:
            raise AuthenticationError(f"Authentication failed: {e}") from e

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
                    current_url, allow_redirects=False, timeout=_DEFAULT_CLIENT_TIMEOUT
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
                                _LOGGER.debug("Extracted token from response URL fragment")
                                return token

                        # If we've reached owners.vacasa.com without a token, try one more request
                        # Use domain-parts check: ensure last 3 labels are owners.vacasa.com
                        # This prevents false matches like fake-owners.vacasa.com
                        response_host = str(response.url.host).lower() if response.url.host else ""
                        host_parts = response_host.split(".")
                        is_owners_host = (
                            len(host_parts) >= 3
                            and ".".join(host_parts[-3:]) == "owners.vacasa.com"
                        )
                        if is_owners_host:
                            page_content = await response.text()
                            token_match = re.search(r'access_token=([^&"\']+)', page_content)
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
        # Fast path: return cached value without acquiring lock
        if self._owner_id:
            _LOGGER.debug("Using cached owner ID: %s", self._owner_id)
            return self._owner_id

        # Serialize concurrent fetches so only one API call is made
        async with self._owner_id_lock:
            # Re-check after acquiring lock (another task may have populated it)
            if self._owner_id:
                return self._owner_id

            # Ensure we have a valid token
            await self.ensure_token()

            try:
                _LOGGER.debug("Getting owner ID from verify-token endpoint")
                data = await self._request("POST", "/verify-token")
                _LOGGER.debug("Received response from verify-token endpoint: %s", data)

                # Extract owner ID from the response
                if "data" in data and "contactIds" in data["data"] and data["data"]["contactIds"]:
                    self._owner_id = str(data["data"]["contactIds"][0])
                    _LOGGER.debug("Retrieved owner ID from verify-token: %s", self._owner_id)
                    return self._owner_id

                _LOGGER.error("Unexpected verify-token response format: %s", data)
                raise ApiError(f"Unexpected verify-token response format: {data}")

            except AuthenticationError:
                raise
            except Exception as e:
                _LOGGER.error("Error getting owner ID: %s", e)
                raise ApiError(f"Error getting owner ID: {e}")

    async def _cached_api_get(self, cache_key: str, fetch_func, log_name: str) -> Any:
        """Fetch a value from the property cache, or call fetch_func and cache the result.

        Args:
            cache_key: Key for the property cache lookup
            fetch_func: Async callable that fetches fresh data when the cache misses
            log_name: Human-readable label used in log messages

        Returns:
            Cached or freshly fetched data

        Raises:
            ApiError: If fetch_func raises or returns no data after all retries
        """
        cached = await self._property_cache.get(cache_key)
        if cached is not None:
            _LOGGER.debug("Using cached %s", log_name)
            return cached

        try:
            result = await self._retry_handler.retry(fetch_func)
            if result:
                await self._property_cache.set(cache_key, result)
                _LOGGER.debug("Cached %s", log_name)
            return result
        except Exception as e:
            _LOGGER.error("Error getting %s: %s", log_name, e)
            raise ApiError(f"Error getting {log_name}: {e}")

    async def get_units(self) -> list[dict[str, Any]]:
        """Get all units for the owner.

        Returns:
            List of unit dictionaries

        Raises:
            ApiError: If the API request fails
        """

        async def _fetch():
            owner_id = await self.get_owner_id()
            _LOGGER.debug("Getting units for owner ID: %s", owner_id)
            data = await self._request("GET", f"/owners/{owner_id}/units")
            _LOGGER.debug("Received units response: %s", data)

            if "data" not in data:
                _LOGGER.warning("No data field in units response: %s", data)
                return []

            units = data["data"]
            _LOGGER.debug("Retrieved %s units", len(units))
            if units:
                _LOGGER.debug("Unit IDs: %s", [unit.get("id") for unit in units])
            return units

        try:
            return await self._retry_handler.retry(_fetch)
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

        async def _fetch():
            _LOGGER.debug(
                "Getting reservations for unit %s from %s to %s",
                unit_id,
                start_date,
                end_date if end_date else "future",
            )

            data = await self._request(
                "GET",
                f"/owners/{owner_id}/units/{unit_id}/reservations",
                params=params,
            )

            if "data" not in data:
                _LOGGER.warning("No data field in reservations response: %s", data)
                return []

            reservations = data["data"]
            _LOGGER.debug("Retrieved %s reservations", len(reservations))

            if reservations and _LOGGER.isEnabledFor(logging.DEBUG):
                dates = [
                    (
                        res.get("attributes", {}).get("startDate"),
                        res.get("attributes", {}).get("endDate"),
                    )
                    for res in reservations
                ]
                _LOGGER.debug("Reservation dates: %s", dates)

            return reservations

        try:
            return await self._retry_handler.retry(_fetch)
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

        async def _fetch():
            owner_id = await self.get_owner_id()
            _LOGGER.debug("Getting details for unit %s", unit_id)
            data = await self._request("GET", f"/owners/{owner_id}/units/{unit_id}")
            _LOGGER.debug("Received unit details response: %s", data)
            if "data" in data and "attributes" in data["data"]:
                _LOGGER.debug("Unit name: %s", data["data"]["attributes"].get("name"))
            return data

        return await self._cached_api_get(
            f"unit_details_{unit_id}", _fetch, f"unit details for {unit_id}"
        )

    async def get_statements(
        self, year: int | None = None, month: int | None = None
    ) -> list[dict[str, Any]]:
        """Fetch owner statements, optionally scoped to a specific month."""
        owner_id = await self.get_owner_id()

        path = f"/owners/{owner_id}/statements"
        if year is not None and month is not None:
            path = f"{path}/{year}/{month:02d}"

        data = await self._request("GET", path)

        if isinstance(data, dict):
            if "data" in data and isinstance(data["data"], list):
                return data["data"]
        elif isinstance(data, list):
            return data

        return []

    async def get_maintenance(
        self, unit_id: str, status: str | None = "open"
    ) -> list[dict[str, Any]]:
        """Fetch maintenance tickets for a unit."""
        owner_id = await self.get_owner_id()

        params = {"status": status} if status else None
        data = await self._request(
            "GET",
            f"/owners/{owner_id}/units/{unit_id}/maintenance",
            params=params,
        )

        if isinstance(data, dict):
            return data.get("data", [])

        return []

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
        categorized: dict[str, list[dict[str, Any]]] = {
            stay_type: [] for stay_type in STAY_TYPE_TO_CATEGORY
        }

        # Categorize each reservation
        for reservation in reservations:
            stay_type = self.categorize_reservation(reservation)
            categorized[stay_type].append(reservation)

        # Log counts for debugging
        _LOGGER.debug(
            "Categorized reservations: Guest: %s, Owner: %s, Maintenance: %s, Block: %s, Other: %s",
            len(categorized.get(STAY_TYPE_GUEST, [])),
            len(categorized.get(STAY_TYPE_OWNER, [])),
            len(categorized.get(STAY_TYPE_MAINTENANCE, [])),
            len(categorized.get(STAY_TYPE_BLOCK, [])),
            len(categorized.get(STAY_TYPE_OTHER, [])),
        )

        return categorized
