"""Config flow for Vacasa integration."""

import json
import logging
import re
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api_client import ApiError, AuthenticationError, VacasaApiClient
from .const import (
    CONF_API_VERSION,
    CONF_PASSWORD,
    CONF_REFRESH_INTERVAL,
    CONF_STAY_TYPE_MAPPING,
    CONF_USERNAME,
    DEFAULT_API_VERSION,
    DEFAULT_REFRESH_INTERVAL,
    DOMAIN,
    SUPPORTED_API_VERSIONS,
    STAY_TYPE_TO_CATEGORY,
)

_LOGGER = logging.getLogger(__name__)

# Email validation regex pattern
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def validate_email(value: str) -> str:
    """Validate email format."""
    if not value:
        raise vol.Invalid("Email cannot be empty")

    value = value.strip()
    if not EMAIL_REGEX.match(value):
        raise vol.Invalid("Please enter a valid email address")

    return value


def validate_password(value: str) -> str:
    """Validate password requirements."""
    if not value:
        raise vol.Invalid("Password cannot be empty")

    # Check if password is only whitespace
    if not value.strip():
        raise vol.Invalid("Password cannot be empty or contain only spaces")

    # Check minimum length
    if len(value) < 8:
        raise vol.Invalid("Password must be at least 8 characters long")

    return value


def validate_password_optional(value: str) -> str:
    """Validate password requirements for optional fields (options flow)."""
    if not value:
        # Empty password is allowed in options flow (keeps current password)
        return value

    # If password is provided, apply the same validation as required password
    return validate_password(value)


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
        hass=hass,
        api_version=data.get(CONF_API_VERSION),
        stay_type_mapping=data.get(CONF_STAY_TYPE_MAPPING),
    )

    try:
        # Test authentication
        await client.authenticate()

        # Get owner ID from API
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
            raise CannotConnect from err

        # Return info that you want to store in the config entry.
        return {
            "title": f"Vacasa ({data[CONF_USERNAME]})",
            "units": len(units),
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
                # Manual validation since we can't use custom validators in schema
                try:
                    validate_email(user_input[CONF_USERNAME])
                    validate_password(user_input[CONF_PASSWORD])
                except vol.Invalid as err:
                    if "email" in str(err).lower():
                        errors[CONF_USERNAME] = "invalid_email"
                    elif "password" in str(err).lower():
                        errors[CONF_PASSWORD] = "invalid_password"
                    else:
                        errors["base"] = "invalid_input"
                    raise

                info = await validate_input(self.hass, user_input)

                # Check if this account is already configured
                await self.async_set_unique_id(user_input[CONF_USERNAME])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(title=info["title"], data=user_input)
            except vol.Invalid:
                # Handle validation errors already set above
                pass
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
            }

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME, default=user_input[CONF_USERNAME]): str,
                vol.Required(CONF_PASSWORD, default=user_input[CONF_PASSWORD]): str,
                vol.Required(
                    CONF_REFRESH_INTERVAL,
                    default=user_input[CONF_REFRESH_INTERVAL],
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=24)),
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
        super().__init__()
        self.config_entry = config_entry
        # For test compatibility - in real HA, hass is set by framework
        if hasattr(config_entry, "hass"):
            self.hass = config_entry.hass

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Manage the options."""
        errors: Dict[str, str] = {}
        current_api_version = self.config_entry.options.get(
            CONF_API_VERSION, DEFAULT_API_VERSION
        )
        existing_mapping: dict[str, str] = self.config_entry.options.get(
            CONF_STAY_TYPE_MAPPING, {}
        )

        if user_input is not None:
            api_version = user_input.get(CONF_API_VERSION) or DEFAULT_API_VERSION
            mapping_value: dict[str, str] = {}

            mapping_text = user_input.get(CONF_STAY_TYPE_MAPPING, "")
            if mapping_text and mapping_text.strip():
                try:
                    raw_mapping = json.loads(mapping_text)
                except json.JSONDecodeError as err:
                    _LOGGER.debug("Invalid stay type mapping JSON: %s", err)
                    errors[CONF_STAY_TYPE_MAPPING] = "invalid_stay_type_mapping"
                    raw_mapping = None

                if isinstance(raw_mapping, dict):
                    try:
                        for key, value in raw_mapping.items():
                            if not isinstance(key, str) or not isinstance(value, str):
                                raise ValueError("Stay type mapping keys and values must be strings")
                            normalized_value = value.lower()
                            if normalized_value not in STAY_TYPE_TO_CATEGORY:
                                raise ValueError(
                                    f"Unknown stay type category '{value}'"
                                )
                            mapping_value[key.lower()] = normalized_value
                    except ValueError as err:
                        _LOGGER.debug("Invalid stay type mapping value: %s", err)
                        errors[CONF_STAY_TYPE_MAPPING] = "invalid_stay_type_mapping"
                elif raw_mapping is not None:
                    errors[CONF_STAY_TYPE_MAPPING] = "invalid_stay_type_mapping"

            if api_version not in SUPPORTED_API_VERSIONS:
                errors[CONF_API_VERSION] = "invalid_api_version"

            # Check if credentials were updated
            current_username = self.config_entry.data.get(CONF_USERNAME)
            current_password = self.config_entry.data.get(CONF_PASSWORD)

            new_username = user_input.get(CONF_USERNAME)
            new_password = user_input.get(CONF_PASSWORD)

            credentials_changed = new_username != current_username or (
                new_password and new_password != current_password
            )

            if credentials_changed:
                # Validate new credentials if they changed
                try:
                    # Manual validation since we can't use custom validators in schema
                    try:
                        validate_email(new_username)
                        if new_password:  # Only validate password if provided
                            validate_password(new_password)
                    except vol.Invalid as err:
                        if "email" in str(err).lower():
                            errors[CONF_USERNAME] = "invalid_email"
                        elif "password" in str(err).lower():
                            errors[CONF_PASSWORD] = "invalid_password"
                        else:
                            errors["base"] = "invalid_input"
                        raise

                    # Create a validation dict with the new credentials
                    validation_data = {
                        CONF_USERNAME: new_username,
                        CONF_PASSWORD: (new_password if new_password else current_password),
                        CONF_REFRESH_INTERVAL: user_input[CONF_REFRESH_INTERVAL],
                        CONF_API_VERSION: api_version,
                        CONF_STAY_TYPE_MAPPING: mapping_value,
                    }
                    await validate_input(self.hass, validation_data)

                    # Update the config entry data with new credentials
                    new_data = dict(self.config_entry.data)
                    new_data[CONF_USERNAME] = new_username
                    if new_password:  # Only update password if provided
                        new_data[CONF_PASSWORD] = new_password

                    self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)

                except vol.Invalid:
                    # Handle validation errors already set above
                    pass
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except InvalidAuth:
                    errors["base"] = "invalid_auth"
                except OwnerIdError:
                    errors["base"] = "owner_id_error"
                except UnknownError:
                    errors["base"] = "unknown"

            if not errors:
                # Validate API connectivity when auth not changed but API settings did
                if not credentials_changed and (
                    api_version != current_api_version
                    or mapping_value != existing_mapping
                ):
                    try:
                        validation_data = {
                            CONF_USERNAME: current_username,
                            CONF_PASSWORD: current_password,
                            CONF_REFRESH_INTERVAL: user_input[CONF_REFRESH_INTERVAL],
                            CONF_API_VERSION: api_version,
                            CONF_STAY_TYPE_MAPPING: mapping_value,
                        }
                        await validate_input(self.hass, validation_data)
                    except CannotConnect:
                        errors["base"] = "cannot_connect"
                    except InvalidAuth:
                        errors["base"] = "invalid_auth"
                    except OwnerIdError:
                        errors["base"] = "owner_id_error"
                    except UnknownError:
                        errors["base"] = "unknown"

            if not errors:
                # Success - create options entry with all options
                # This will trigger async_update_options which does a full reload
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_REFRESH_INTERVAL: user_input[CONF_REFRESH_INTERVAL],
                        CONF_API_VERSION: api_version,
                        CONF_STAY_TYPE_MAPPING: mapping_value,
                    },
                )

        # Get current values for defaults
        current_username = self.config_entry.data.get(CONF_USERNAME, "")
        default_refresh = self.config_entry.options.get(
            CONF_REFRESH_INTERVAL,
            self.config_entry.data.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL),
        )
        default_api_version = current_api_version
        default_mapping_text = json.dumps(existing_mapping, indent=2) if existing_mapping else ""

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME, default=current_username): str,
                vol.Optional(CONF_PASSWORD): str,
                vol.Required(CONF_REFRESH_INTERVAL, default=default_refresh): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=24)
                ),
                vol.Optional(
                    CONF_API_VERSION, default=default_api_version
                ): vol.In(SUPPORTED_API_VERSIONS),
                vol.Optional(
                    CONF_STAY_TYPE_MAPPING, default=default_mapping_text
                ): str,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "current_username": current_username,
            },
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class OwnerIdError(HomeAssistantError):
    """Error to indicate there is an issue with the owner ID."""


class UnknownError(HomeAssistantError):
    """Error to indicate there is an unknown error."""
