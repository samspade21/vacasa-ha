"""Tests for the Vacasa configuration flow."""

from custom_components.vacasa.config_flow import VacasaOptionsFlowHandler


def test_options_flow_initializes_base_class():
    """Ensure the options flow handler initializes correctly."""
    handler = VacasaOptionsFlowHandler()
    # config_entry is injected by the framework, not passed to __init__
    assert hasattr(handler, "async_step_init")
