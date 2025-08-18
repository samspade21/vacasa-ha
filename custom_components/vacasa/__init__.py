"""The Vacasa integration."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Any

import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api_client import ApiError, AuthenticationError, VacasaApiClient
from .const import (
    CONF_PASSWORD,
    CONF_REFRESH_INTERVAL,
    CONF_USERNAME,
    DEFAULT_REFRESH_INTERVAL,
    DOMAIN,
    PLATFORMS,
    SERVICE_CLEAR_CACHE,
    SERVICE_REFRESH_DATA,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class VacasaData:
    """Runtime data for Vacasa integration."""

    client: VacasaApiClient
    coordinator: "VacasaDataUpdateCoordinator"


if TYPE_CHECKING:
    # Type alias for config entry (compatible with older Python versions)
    VacasaConfigEntry = ConfigEntry[VacasaData]
else:
    # For runtime, use the base class
    VacasaConfigEntry = ConfigEntry


class VacasaDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching data from the Vacasa API."""

    def __init__(self, hass: HomeAssistant, client: VacasaApiClient) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Vacasa",
            update_interval=timedelta(hours=DEFAULT_REFRESH_INTERVAL),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via API."""
        try:
            # We don't actually need to fetch any data here, as the calendar
            # entities will fetch their own data when needed. This is just to
            # ensure the client is authenticated.
            async with async_timeout.timeout(30):
                await self.client.ensure_token()
            return {"last_update": self.client._token_expiry}
        except AuthenticationError as err:
            _LOGGER.error("Authentication error during update: %s", err)
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except ApiError as err:
            _LOGGER.error("API error during update: %s", err)
            raise UpdateFailed(f"API error: {err}") from err
        except asyncio.TimeoutError as err:
            _LOGGER.error("Timeout error during update")
            raise UpdateFailed("Timeout while fetching data") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error during update: %s", err)
            raise UpdateFailed(f"Unexpected error: {err}") from err


async def async_setup_entry(hass: HomeAssistant, entry: VacasaConfigEntry) -> bool:
    """Set up Vacasa from a config entry."""
    # Get configuration
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    refresh_interval = entry.options.get(
        CONF_REFRESH_INTERVAL,
        entry.data.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL),
    )

    # Create API client with modern session injection
    session = async_get_clientsession(hass)
    client = VacasaApiClient(
        username=username,
        password=password,
        session=session,
        hass_config_dir=hass.config.path(),
        hass=hass,
    )

    # Verify we can authenticate
    try:
        await client.authenticate()
    except AuthenticationError as err:
        _LOGGER.error("Authentication failed: %s", err)
        return False
    except ApiError as err:
        _LOGGER.error("API error during setup: %s", err)
        raise ConfigEntryNotReady from err

    # Create update coordinator with proper class
    coordinator = VacasaDataUpdateCoordinator(hass, client)

    # Update coordinator with options refresh interval
    coordinator.update_interval = timedelta(hours=refresh_interval)

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store runtime data using modern pattern
    entry.runtime_data = VacasaData(client=client, coordinator=coordinator)

    # Register services
    async def handle_refresh_data(call: ServiceCall) -> None:
        """Handle the refresh_data service call to refresh all Vacasa data."""
        await coordinator.async_refresh()

    async def handle_clear_cache(call: ServiceCall) -> None:
        """Handle the clear_cache service call."""
        await client.clear_cache()
        await coordinator.async_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_DATA,
        handle_refresh_data,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_CACHE,
        handle_clear_cache,
    )

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Add update listener for options
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_update_options(hass: HomeAssistant, entry: VacasaConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: VacasaConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Remove services if this is the last entry - use modern pattern
    other_loaded_entries = [
        _entry
        for _entry in hass.config_entries.async_loaded_entries(DOMAIN)
        if _entry.entry_id != entry.entry_id
    ]
    if not other_loaded_entries:
        # The last config entry is being unloaded, remove shared services
        for service in [SERVICE_REFRESH_DATA, SERVICE_CLEAR_CACHE]:
            if hass.services.has_service(DOMAIN, service):
                hass.services.async_remove(DOMAIN, service)

    # Runtime data is automatically cleaned up
    return unload_ok
