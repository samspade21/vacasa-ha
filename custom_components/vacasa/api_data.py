"""Data retrieval methods for the Vacasa API client."""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .api_client import ApiError
from .const import (
    API_BASE_URL,
    DEFAULT_TIMEOUT,
    STAY_TYPE_BLOCK,
    STAY_TYPE_GUEST,
    STAY_TYPE_MAINTENANCE,
    STAY_TYPE_OTHER,
    STAY_TYPE_OWNER,
)

_LOGGER = logging.getLogger(__name__)


async def get_owner_id(self) -> str:
    """Get the owner ID if not already known.

    Returns:
        The owner ID

    Raises:
        ApiError: If the owner ID cannot be determined
    """
    # If owner ID is already provided, use it
    if self._owner_id:
        _LOGGER.debug("Using provided owner ID: %s", self._owner_id)
        return self._owner_id

    # We need to make an API call to get the owner ID
    # First, ensure we have a valid token
    await self.ensure_token()

    # Make a request to an endpoint that returns owner information
    try:
        session = await self.ensure_session()
        
        # Try the verify-token endpoint first (most reliable)
        try:
            _LOGGER.debug("Attempting to get owner ID from verify-token endpoint")
            async with session.get(
                f"{API_BASE_URL}/verify-token",
                headers=self._get_headers(),
                timeout=DEFAULT_TIMEOUT,
            ) as response:
                if response.status != 200:
                    _LOGGER.warning("Failed to get owner info from verify-token: %s", response.status)
                else:
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
                            _LOGGER.debug("Retrieved owner ID from verify-token: %s", self._owner_id)
                            return self._owner_id
                        else:
                            _LOGGER.warning("No contact IDs found in verify-token response")
                    else:
                        _LOGGER.warning("Unexpected verify-token response format: %s", data)
        except Exception as e:
            _LOGGER.warning("Error getting owner ID from verify-token: %s", e)
        
        # Try the /me endpoint as a fallback
        try:
            _LOGGER.debug("Attempting to get owner ID from /me endpoint")
            async with session.get(
                f"{API_BASE_URL}/me",
                headers=self._get_headers(),
                timeout=DEFAULT_TIMEOUT,
            ) as response:
                if response.status != 200:
                    _LOGGER.warning("Failed to get owner info from /me: %s", response.status)
                    # If 404, the endpoint might not exist for this account
                    if response.status == 404:
                        _LOGGER.error("The /me endpoint returned 404 - it may not exist for this account")
                else:
                    data = await response.json()
                    _LOGGER.debug("Received response from /me endpoint: %s", data)
                    
                    # Extract owner ID from the response
                    if (
                        "data" in data
                        and "attributes" in data["data"]
                        and "legacy_contact_ids" in data["data"]["attributes"]
                    ):
                        contact_ids = data["data"]["attributes"]["legacy_contact_ids"]
                        if contact_ids and len(contact_ids) > 0:
                            self._owner_id = str(contact_ids[0])
                            _LOGGER.debug("Retrieved owner ID from /me: %s", self._owner_id)
                            return self._owner_id
                        else:
                            _LOGGER.warning("No contact IDs found in /me response")
                    else:
                        _LOGGER.warning("Unexpected /me response format: %s", data)
        except Exception as e:
            _LOGGER.warning("Error getting owner ID from /me: %s", e)
        
        # If we get here, we couldn't get the owner ID from API endpoints
        # Try to extract it from the token if possible
        try:
            _LOGGER.debug("Attempting to extract owner ID from token")
            token_parts = self._token.split(".")
            if len(token_parts) >= 2:
                padded_payload = token_parts[1] + "=" * (4 - len(token_parts[1]) % 4)
                payload = json.loads(self._base64_url_decode(padded_payload))
                
                if "sub" in payload:
                    # The subject might be the user ID, not the owner ID
                    # But we can try to use it as a fallback
                    subject_id = payload["sub"]
                    _LOGGER.debug("Extracted subject ID from token: %s", subject_id)
        except Exception as e:
            _LOGGER.warning("Error extracting owner ID from token: %s", e)
        
        # If we get here, we couldn't get the owner ID
        _LOGGER.error(
            "Could not determine owner ID from API response or token. "
            "Please provide it manually in the configuration."
        )
        raise ApiError(
            "Could not determine owner ID automatically. Please provide it manually in the configuration. "
            "You can find your Owner ID in the browser session storage under 'owners-portal:owner' "
            "or in the URL when logged into the Vacasa owner portal (e.g., https://owners.vacasa.com/owner/123456)."
        )
        
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
            _LOGGER.debug("Received units response with status: %s", response.status)

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
            end_date if end_date else "future"
        )
        
        reservations_url = f"{API_BASE_URL}/owners/{owner_id}/units/{unit_id}/reservations"
        _LOGGER.debug("Reservations URL: %s with params: %s", reservations_url, params)
        
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
            _LOGGER.debug("Received reservations response with status: %s", response.status)

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
            _LOGGER.debug("Received unit details response with status: %s", response.status)
            
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
