"""Tests for Vacasa calendar platform."""

from datetime import timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.vacasa.calendar import VacasaCalendar
from custom_components.vacasa.const import (
    SIGNAL_RESERVATION_BOUNDARY,
    SIGNAL_RESERVATION_STATE,
    STAY_TYPE_GUEST,
)
from homeassistant.util import dt as dt_util


@pytest.mark.asyncio
async def test_async_get_current_event():
    """Calendar returns current event when reservation spans now."""
    now = dt_util.now()
    start = now - timedelta(days=1)
    end = now + timedelta(days=1)

    client = Mock()
    client.get_categorized_reservations = AsyncMock(
        return_value={
            STAY_TYPE_GUEST: [
                {
                    "attributes": {
                        "startDate": start.strftime("%Y-%m-%d"),
                        "endDate": end.strftime("%Y-%m-%d"),
                        "checkinTime": "14:00:00",
                        "checkoutTime": "10:00:00",
                        "firstName": "Alice",
                        "lastName": "Current",
                    }
                }
            ]
        }
    )

    coordinator = Mock()
    coordinator.reservation_states = {}

    calendar = VacasaCalendar(
        coordinator=coordinator,
        client=client,
        unit_id="1",
        name="Unit 1",
        code="U1",
        unit_attributes={"timezone": "UTC"},
    )
    calendar.hass = None

    with patch("custom_components.vacasa.calendar.async_track_point_in_time", return_value=None):
        event = await calendar.async_get_current_event()
    assert event is not None
    assert event.summary == "Guest Booking: Alice Current"


def _build_calendar(
    start_delta: timedelta,
    end_delta: timedelta,
    next_start_delta: timedelta,
    next_end_delta: timedelta,
):
    """Create a VacasaCalendar with deterministic events."""
    now = dt_util.utcnow()
    client = Mock()
    client.get_categorized_reservations = AsyncMock(
        return_value={
            STAY_TYPE_GUEST: [
                {
                    "attributes": {
                        "startDate": (now + start_delta).strftime("%Y-%m-%d"),
                        "endDate": (now + end_delta).strftime("%Y-%m-%d"),
                        "checkinTime": "12:00:00",
                        "checkoutTime": "12:00:00",
                        "firstName": "Alice",
                        "lastName": "Current",
                    }
                },
                {
                    "attributes": {
                        "startDate": (now + next_start_delta).strftime("%Y-%m-%d"),
                        "endDate": (now + next_end_delta).strftime("%Y-%m-%d"),
                        "checkinTime": "12:00:00",
                        "checkoutTime": "12:00:00",
                        "firstName": "Bob",
                        "lastName": "Future",
                    }
                },
            ]
        }
    )

    hass = Mock()
    hass.loop = Mock()
    hass.loop.call_at = Mock(return_value=None)
    hass.loop.time = Mock(return_value=0)
    hass.async_create_task = Mock()
    hass._dispatcher_listeners = {}
    hass.data = {}

    coordinator = Mock()
    coordinator.hass = hass
    coordinator.async_request_refresh = AsyncMock()
    coordinator.reservation_states = {}

    calendar = VacasaCalendar(
        coordinator=coordinator,
        client=client,
        unit_id="unit123",
        name="Test Unit",
        code="TU",
        unit_attributes={"timezone": "UTC"},
    )
    calendar.hass = hass
    return calendar, coordinator


@pytest.mark.asyncio
async def test_schedule_boundary_timers_sets_checkin_and_checkout():
    """Calendar schedules timers for both checkout and next check-in."""
    calendar, _ = _build_calendar(
        start_delta=timedelta(days=-1),
        end_delta=timedelta(days=1),
        next_start_delta=timedelta(days=2),
        next_end_delta=timedelta(days=3),
    )

    with patch("custom_components.vacasa.calendar.async_track_point_in_time") as mock_track:
        await calendar._update_current_event()
        calendar._schedule_boundary_timers()

    checkout_call = next(
        call
        for call in mock_track.call_args_list
        if call.args[1].keywords["boundary"] == "checkout"
    )
    checkin_call = next(
        call for call in mock_track.call_args_list if call.args[1].keywords["boundary"] == "checkin"
    )

    assert checkout_call.args[0] is calendar.hass
    assert checkout_call.args[2].tzinfo == timezone.utc

    assert checkin_call.args[0] is calendar.hass
    assert checkin_call.args[2].tzinfo == timezone.utc


def test_boundary_timer_dispatches_signal():
    """Boundary timer sends dispatcher signal and schedules refresh."""
    calendar, coordinator = _build_calendar(
        start_delta=timedelta(days=-1),
        end_delta=timedelta(days=1),
        next_start_delta=timedelta(days=2),
        next_end_delta=timedelta(days=3),
    )

    # Mock the event loop's call_soon_threadsafe
    mock_call_soon = Mock()
    calendar.hass.loop.call_soon_threadsafe = mock_call_soon
    calendar.hass.async_create_task = Mock()

    with patch("custom_components.vacasa.calendar.async_dispatcher_send") as mock_send:
        calendar._handle_boundary_timer(
            dt_util.utcnow(),
            boundary="checkin",
        )

    # Verify call_soon_threadsafe was called twice (once for dispatcher, once for refresh)
    assert mock_call_soon.call_count == 2

    # Verify the first call was for async_dispatcher_send
    first_call_args = mock_call_soon.call_args_list[0][0]
    assert first_call_args[0] == mock_send
    assert first_call_args[1] == calendar.hass
    assert first_call_args[2] == SIGNAL_RESERVATION_BOUNDARY
    assert first_call_args[3] == "unit123"
    assert first_call_args[4] == "checkin"

    # Verify the second call was for refresh (wrapped in a lambda)
    second_call_args = mock_call_soon.call_args_list[1][0]
    assert callable(second_call_args[0])  # Should be a lambda or callable


def test_midnight_times_use_default_checkin_and_checkout():
    """Midnight check-in/out values should fall back to default times."""
    coordinator = Mock()
    coordinator.reservation_states = {}

    calendar = VacasaCalendar(
        coordinator=coordinator,
        client=Mock(),
        unit_id="unit123",
        name="Test Unit",
        code="TU",
        unit_attributes={},
    )

    event = calendar._reservation_to_event(
        {
            "id": "res123",
            "attributes": {
                "startDate": "2024-05-01",
                "endDate": "2024-05-02",
                "checkinTime": "00:00:00.000Z",
                "checkoutTime": "00:00:00.000Z",
            },
        },
        STAY_TYPE_GUEST,
    )

    assert event is not None
    assert event.start.hour == 16
    assert event.start.minute == 0
    assert event.end.hour == 10
    assert event.end.minute == 0


@pytest.mark.asyncio
async def test_update_current_event_broadcasts_reservation_state():
    """Calendar publishes reservation data for other entities to consume."""
    calendar, coordinator = _build_calendar(
        start_delta=timedelta(days=-1),
        end_delta=timedelta(days=1),
        next_start_delta=timedelta(days=2),
        next_end_delta=timedelta(days=3),
    )

    with patch("custom_components.vacasa.calendar.async_dispatcher_send") as mock_send:
        await calendar._update_current_event()

    assert "unit123" in coordinator.reservation_states
    state = coordinator.reservation_states["unit123"]
    assert state.current is not None
    assert state.upcoming is not None
    assert state.current.guest_name == "Alice Current"
    assert state.current.stay_type == STAY_TYPE_GUEST
    assert state.upcoming.guest_name == "Bob Future"

    mock_send.assert_called_with(
        calendar.hass,
        SIGNAL_RESERVATION_STATE,
        "unit123",
        state,
    )
