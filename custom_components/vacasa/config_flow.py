"""Config flow for Vacasa integration."""
import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api_client import ApiError, AuthenticationError, VacasaApiClient
from .const import (
    CONF_CHECKIN_TIME,
    CONF_CHECKOUT_TIME,
    CONF_OWNER_ID,
    CONF_PASSWORD,
    CONF_REFRESH_INTERVAL,
    CONF_USERNAME,
    DEFAULT_CHECKIN_TIME,
    DEFAULT_CHECKOUT_TIME,
    DEFAULT_REFRESH_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    session = async_get_clientsession(hass)

    client = VacasaApiClient(
        username=data[CONF_USERNAME],
        password=data[CONF_PASSWORD],
        session=session,
        hass_config_dir=hass.config.path(),
        owner_id=data.get(CONF_OWNER_ID),  # Pass the optional owner ID
    )

    try:
        # Test authentication
        await client.authenticate()

        # If owner ID is provided, use it directly
        if data.get(CONF_OWNER_ID):
            owner_id = data[CONF_OWNER_ID]
            _LOGGER.debug("Using provided owner ID: %s", owner_id)
        else:
            # Try to get owner ID from API
            try:
                owner_id = await client.get_owner_id()
                _LOGGER.debug("Retrieved owner ID from API: %s", owner_id)
            except ApiError as err:
                _LOGGER.error("Failed to get owner ID from API: %s", err)
                raise OwnerIdError from err

        # Test API access by getting units
        try:
            units = await client.get_units()
            _LOGGER.debug("Retrieved %s units", len(units))
        except ApiError as err:
            _LOGGER.error("Failed to get units: %s", err)
            if "owner_id" in str(err).lower():
                raise OwnerIdError from err
            raise CannotConnect from err

        # Return info that you want to store in the config entry.
        return {
            "title": f"Vacasa ({data[CONF_USERNAME]})",
            "units": len(units),
            "owner_id": owner_id,
        }
    except AuthenticationError as err:
        _LOGGER.error("Authentication error: %s", err)
        raise InvalidAuth from err
    except ApiError as err:
        _LOGGER.error("API error: %s", err)
        raise CannotConnect from err
    except Exception as err:
        _LOGGER.exception("Unexpected error: %s", err)
        raise UnknownError from err


class VacasaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Vacasa."""

    VERSION = 1

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)

                # Check if this account is already configured
                await self.async_set_unique_id(user_input[CONF_USERNAME])
                self._abort_if_unique_id_configured()

                # Store the owner ID in the data
                user_input[CONF_OWNER_ID] = info.get("owner_id")

                return self.async_create_entry(title=info["title"], data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except OwnerIdError:
                errors["base"] = "owner_id_error"
            except UnknownError:
                errors["base"] = "unknown"
        else:
            user_input = {
                CONF_USERNAME: "",
                CONF_PASSWORD: "",
                CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL,
                CONF_OWNER_ID: "",
                CONF_CHECKIN_TIME: DEFAULT_CHECKIN_TIME,
                CONF_CHECKOUT_TIME: DEFAULT_CHECKOUT_TIME,
            }

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME, default=user_input[CONF_USERNAME]): str,
                vol.Required(CONF_PASSWORD, default=user_input[CONF_PASSWORD]): str,
                vol.Required(
                    CONF_REFRESH_INTERVAL,
                    default=user_input[CONF_REFRESH_INTERVAL],
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=24)),
                vol.Optional(CONF_OWNER_ID, default=user_input.get(CONF_OWNER_ID, "")): str,
                vol.Optional(
                    CONF_CHECKIN_TIME,
                    default=user_input.get(CONF_CHECKIN_TIME, DEFAULT_CHECKIN_TIME),
                ): str,
                vol.Optional(
                    CONF_CHECKOUT_TIME,
                    default=user_input.get(CONF_CHECKOUT_TIME, DEFAULT_CHECKOUT_TIME),
                ): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return VacasaOptionsFlowHandler(config_entry)


class VacasaOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Vacasa options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        default_refresh = self.config_entry.options.get(
            CONF_REFRESH_INTERVAL,
            self.config_entry.data.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL),
        )

        default_checkin = self.config_entry.options.get(
            CONF_CHECKIN_TIME,
            self.config_entry.data.get(CONF_CHECKIN_TIME, DEFAULT_CHECKIN_TIME),
        )

        default_checkout = self.config_entry.options.get(
            CONF_CHECKOUT_TIME,
            self.config_entry.data.get(CONF_CHECKOUT_TIME, DEFAULT_CHECKOUT_TIME),
        )

        schema = vol.Schema(
            {
                vol.Required(CONF_REFRESH_INTERVAL, default=default_refresh): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=24)
                ),
                vol.Optional(CONF_CHECKIN_TIME, default=default_checkin): str,
                vol.Optional(CONF_CHECKOUT_TIME, default=default_checkout): str,
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class OwnerIdError(HomeAssistantError):
    """Error to indicate there is an issue with the owner ID."""


class UnknownError(HomeAssistantError):
    """Error to indicate there is an unknown error."""
