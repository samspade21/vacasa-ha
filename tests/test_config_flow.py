"""Test the Vacasa config flow."""
from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.vacasa.api_client import ApiError, AuthenticationError
from custom_components.vacasa.const import CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL, DOMAIN


async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] is None

    with patch(
        "custom_components.vacasa.config_flow.validate_input",
        return_value={"title": "Vacasa (test@example.com)", "units": 1},
    ), patch(
        "custom_components.vacasa.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "test@example.com",
                CONF_PASSWORD: "test-password",
                CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL,
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Vacasa (test@example.com)"
    assert result2["data"] == {
        CONF_USERNAME: "test@example.com",
        CONF_PASSWORD: "test-password",
        CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(hass: HomeAssistant) -> None:
    """Test we handle invalid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.vacasa.config_flow.validate_input",
        side_effect=AuthenticationError("Invalid authentication"),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "test@example.com",
                CONF_PASSWORD: "test-password",
                CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL,
            },
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_cannot_connect(hass: HomeAssistant) -> None:
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.vacasa.config_flow.validate_input",
        side_effect=ApiError("Cannot connect"),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "test@example.com",
                CONF_PASSWORD: "test-password",
                CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL,
            },
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_unknown_error(hass: HomeAssistant) -> None:
    """Test we handle unknown error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.vacasa.config_flow.validate_input",
        side_effect=Exception("Unknown error"),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "test@example.com",
                CONF_PASSWORD: "test-password",
                CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL,
            },
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_options_flow(hass: HomeAssistant) -> None:
    """Test options flow."""
    # Create a config entry
    entry = config_entries.ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Vacasa (test@example.com)",
        data={
            CONF_USERNAME: "test@example.com",
            CONF_PASSWORD: "test-password",
            CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL,
        },
        source=config_entries.SOURCE_USER,
        options={},
        entry_id="test",
    )

    # Initialize options flow
    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    # Set new options
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_REFRESH_INTERVAL: 4},
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_REFRESH_INTERVAL: 4}
