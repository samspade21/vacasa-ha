"""Fixtures for Vacasa integration tests."""

from unittest.mock import patch

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


# This fixture enables loading custom integrations in all tests.
@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations in all tests."""
    yield


# This fixture is used to prevent HomeAssistant from attempting to create and dismiss persistent
# notifications. These calls would fail without this patch because the persistent_notification
# integration is never loaded during a test.
@pytest.fixture(name="skip_notifications", autouse=True)
def skip_notifications_fixture():
    """Skip notification calls."""
    with (
        patch("homeassistant.components.persistent_notification.async_create"),
        patch("homeassistant.components.persistent_notification.async_dismiss"),
    ):
        yield


# This fixture can be used in tests that need to simulate a successful authentication
@pytest.fixture
def mock_successful_auth():
    """Mock a successful authentication."""
    with patch(
        "custom_components.vacasa.api_client.VacasaApiClient.authenticate",
        return_value="mock-token",
    ):
        yield


# This fixture can be used in tests that need to simulate successful API calls
@pytest.fixture
def mock_successful_api():
    """Mock successful API calls."""
    with (
        patch(
            "custom_components.vacasa.api_client.VacasaApiClient.get_owner_id",
            return_value="12345",
        ),
        patch(
            "custom_components.vacasa.api_client.VacasaApiClient.get_units",
            return_value=[
                {
                    "id": "67890",
                    "attributes": {
                        "name": "Test Property",
                        "code": "TEST123",
                    },
                }
            ],
        ),
        patch(
            "custom_components.vacasa.api_client.VacasaApiClient.get_categorized_reservations",
            return_value={},
        ),
    ):
        yield
