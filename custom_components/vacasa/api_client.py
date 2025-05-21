"""API client for the Vacasa integration."""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import aiohttp

from .const import (
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
        session: Optional[aiohttp.ClientSession] = None,
        token_cache_path: Optional[str] = None,
        hass_config_dir: Optional[str] = None,
    ):
        """Initialize the Vacasa API client.

        Args:
            username: Vacasa account username/email
            password: Vacasa account password
            session: Optional aiohttp ClientSession
            token_cache_path: Optional path to token cache file
            hass_config_dir: Optional Home Assistant config directory
        """
        self._username = username
        self._password = password
        self._session = session
        self._owner_id = None
        self._token = None
        self._token_expiry = None
        self._client_id = (
            "KOIkAJP9XW7ZpTXwRa0B7O4qMuXSQ3p4BKFfTPhr"  # From the auth URL
        )
        self._close_session = False

        # Set up token cache file path
        if token_cache_path:
            self._token_cache_file = token_cache_path
        elif hass_config_dir:
            self._token_cache_file = os.path.join(hass_config_dir, TOKEN_CACHE_FILE)
        else:
            self._token_cache_file = TOKEN_CACHE_FILE

        _LOGGER.debug(
            "Initialized Vacasa API client for user %s",
            username,
        )

    async def __aenter__(self):
        """Async enter context manager."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
            self._close_session = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async exit context manager."""
        if self._close_session and self._session:
            await self._session.close()
            self._session = None
            self._close_session = False

    @property
    def token(self) -> Optional[str]:
        """Get the current token."""
        return self._token

    @property
    def is_token_valid(self) -> bool:
        """Check if the current token is valid."""
        if not self._token or not self._token_expiry:
            return False
        # Consider token invalid if it expires within TOKEN_REFRESH_MARGIN
        return (
            datetime.now() + timedelta(seconds=TOKEN_REFRESH_MARGIN)
            < self._token_expiry
        )

    async def ensure_session(self) -> aiohttp.ClientSession:
        """Ensure we have an aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
            self._close_session = True
        return self._session

    def _save_token_to_cache(self) -> None:
        """Save the token to the cache file."""
        if not self._token or not self._token_expiry:
            return

        try:
            cache_data = {
                "token": self._token,
                "expiry": self._token_expiry.isoformat(),
            }

            with open(self._token_cache_file, "w") as f:
                json.dump(cache_data, f)

            # Set file permissions to be readable only by the owner
            os.chmod(self._token_cache_file, 0o600)

            _LOGGER.debug("Token saved to cache file")
        except Exception as e:
            _LOGGER.warning("Failed to save token to cache file: %s", e)

    def _load_token_from_cache(self) -> bool:
        """Load the token from the cache file.

        Returns:
            True if the token was loaded successfully, False otherwise
        """
        if not os.path.exists(self._token_cache_file):
            _LOGGER.debug("Token cache file does not exist: %s", self._token_cache_file)
            return False

        try:
            with open(self._token_cache_file, "r") as f:
                cache_data = json.load(f)

            if (
                not cache_data
                or "token" not in cache_data
                or "expiry" not in cache_data
            ):
                _LOGGER.warning("Invalid token cache data format")
                return False

            self._token = cache_data["token"]
            self._token_expiry = datetime.fromisoformat(cache_data["expiry"])

            _LOGGER.debug("Token loaded from cache file")
            _LOGGER.debug("Token expires at: %s", self._token_expiry)

            return True
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
            if self._load_token_from_cache() and self.is_token_valid:
                _LOGGER.debug("Using valid token from cache")
                return self._token

            # If token is still not valid, authenticate
            _LOGGER.debug("Authenticating to get a new token")
            await self.authenticate()

            # Save the new token to cache
            self._save_token_to_cache()

        return self._token

    def _get_headers(self) -> Dict[str, str]:
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
        import base64

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
            Datetime object
        """
        return datetime.fromtimestamp(timestamp)

    def categorize_reservation(self, reservation: Dict[str, Any]) -> str:
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

    # Import methods from other files
    from .api_auth import _follow_auth_redirects, authenticate
    from .api_data import (
        get_categorized_reservations,
        get_owner_id,
        get_reservations,
        get_unit_details,
        get_units,
    )
