"""Tests for the Vacasa binary sensor."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.vacasa.binary_sensor import VacasaOccupancySensor
from custom_components.vacasa.models import ReservationState, ReservationWindow


def _mock_coordinator() -> Mock:
    """Create a coordinator mock with the attributes CoordinatorEntity expects."""
    coordinator = Mock()
    coordinator.async_add_listener = Mock(return_value=lambda: None)
    coordinator.async_request_refresh = AsyncMock()
    coordinator.reservation_states = {}
    coordinator.last_update_success = True
    coordinator.data = {}
    return coordinator


def _reservation_window(
    summary: str,
    *,
    guest_name: str | None = None,
    stay_type: str = "guest",
) -> ReservationWindow:
    """Build a reservation window with deterministic times."""
    now = datetime.now(timezone.utc)
    return ReservationWindow(
        summary=summary,
        start=now,
        end=now + timedelta(days=1),
        guest_name=guest_name,
        stay_type=stay_type,
    )


def test_handle_reservation_state_updates_sensor():
    """Sensor updates state when receiving dispatcher data for its unit."""
    coordinator = _mock_coordinator()
    sensor = VacasaOccupancySensor(
        coordinator=coordinator,
        client=Mock(),
        unit_id="unit123",
        name="Test Unit",
        code="TU",
        unit_attributes={},
    )
    sensor.hass = Mock()
    sensor.async_write_ha_state = Mock()

    state = ReservationState(
        current=_reservation_window(
            "Guest Booking: Alice",
            guest_name="Alice",
            stay_type="guest",
        ),
        upcoming=_reservation_window(
            "Guest Booking: Bob",
            guest_name="Bob",
            stay_type="guest",
        ),
    )

    sensor._handle_reservation_state("unit123", state)

    assert sensor.is_on is True
    attrs = sensor.extra_state_attributes
    assert attrs["current_guest"] == "Alice"
    assert attrs["next_guest"] == "Bob"
    assert attrs["current_reservation_type"] == "Guest Booking"
    sensor.async_write_ha_state.assert_called_once()


def test_handle_reservation_state_ignores_other_units():
    """Signals for other units should be ignored."""
    coordinator = _mock_coordinator()
    sensor = VacasaOccupancySensor(
        coordinator=coordinator,
        client=Mock(),
        unit_id="unit123",
        name="Test Unit",
        code="TU",
        unit_attributes={},
    )
    sensor.hass = Mock()
    sensor.async_write_ha_state = Mock()

    state = ReservationState(
        current=_reservation_window(
            "Guest Booking: Alice",
            guest_name="Alice",
            stay_type="guest",
        )
    )

    sensor._handle_reservation_state("unit999", state)

    assert sensor.is_on is False
    sensor.async_write_ha_state.assert_not_called()


@pytest.mark.asyncio
async def test_async_update_requests_coordinator_refresh():
    """Manual updates should forward to the coordinator."""
    coordinator = _mock_coordinator()
    sensor = VacasaOccupancySensor(
        coordinator=coordinator,
        client=Mock(),
        unit_id="unit123",
        name="Test Unit",
        code="TU",
        unit_attributes={},
    )

    await sensor.async_update()

    coordinator.async_request_refresh.assert_awaited_once()


def test_refresh_from_coordinator_uses_cached_state():
    """Sensors bootstrap their state from the shared cache."""
    coordinator = _mock_coordinator()
    state = ReservationState(
        current=_reservation_window(
            "Guest Booking: Alice",
            guest_name="Alice",
            stay_type="guest",
        )
    )
    coordinator.reservation_states["unit123"] = state

    sensor = VacasaOccupancySensor(
        coordinator=coordinator,
        client=Mock(),
        unit_id="unit123",
        name="Test Unit",
        code="TU",
        unit_attributes={},
    )

    sensor._refresh_from_coordinator()

    assert sensor.is_on is True
    assert sensor.extra_state_attributes["current_guest"] == "Alice"
