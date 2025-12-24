"""Tests for the Vacasa configuration flow."""

from types import SimpleNamespace

from custom_components.vacasa.config_flow import VacasaOptionsFlowHandler


def test_options_flow_initializes_base_class():
    """Ensure the options flow handler initializes correctly."""
    entry = SimpleNamespace(hass="hass")
    handler = VacasaOptionsFlowHandler(entry)
    assert handler.config_entry is entry
    # Note: hass attribute is set by the flow manager, not in __init__
