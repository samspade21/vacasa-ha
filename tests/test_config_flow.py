"""Tests for the Vacasa configuration flow."""

from homeassistant.config_entries import ConfigEntry
from custom_components.vacasa.config_flow import VacasaOptionsFlowHandler


def test_options_flow_initializes_base_class():
    """Ensure the options flow handler initializes its base class."""

    entry = ConfigEntry(hass="hass")
    handler = VacasaOptionsFlowHandler(entry)
    assert handler.config_entry is entry
    assert handler.hass == "hass"
