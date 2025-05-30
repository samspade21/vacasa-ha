"""API client for the Vacasa integration."""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp

from .const import (
    API_BASE_URL,
    DEFAULT_TIMEOUT,
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

        _LOGGER.debug("Initialized Vacasa API client")

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
                _LOGGER.debug("Using valid authentication token from cache")
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

    async def get_units(self) -> List[Dict[str, Any]]:
        """Get all units for the owner.

        Returns:
            List of unit dictionaries

        Raises:
            ApiError: If the API request fails
        """
        # Ensure we have a valid token and owner ID
        await self.ensure_token()
        owner_id = await self.get_owner_id()

        try:
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
        except Exception as e:
            _LOGGER.error("Error getting units: %s", e)
            raise ApiError(f"Error getting units: {e}")

    async def get_reservations(
        self,
        unit_id: str,
        start_date: str,
        end_date: Optional[str] = None,
        limit: int = 100,
        page: int = 1,
        filter_cancelled: bool = False,
    ) -> List[Dict[str, Any]]:
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

    async def get_unit_details(self, unit_id: str) -> Dict[str, Any]:
        """Get details for a specific unit.

        Args:
            unit_id: The unit ID

        Returns:
            Unit details dictionary

        Raises:
            ApiError: If the API request fails
        """
        # Ensure we have a valid token and owner ID
        await self.ensure_token()
        owner_id = await self.get_owner_id()

        try:
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
        except Exception as e:
            _LOGGER.error("Error getting unit details: %s", e)
            raise ApiError(f"Error getting unit details: {e}")

    async def get_categorized_reservations(
        self, unit_id: str, start_date: str, end_date: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
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
