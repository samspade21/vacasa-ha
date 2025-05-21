"""Data retrieval methods for the Vacasa API client."""

import logging
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
                    "Failed to get owner info from verify-token: %s", response.status
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
            end_date if end_date else "future",
        )

        reservations_url = (
            f"{API_BASE_URL}/owners/{owner_id}/units/{unit_id}/reservations"
        )
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
