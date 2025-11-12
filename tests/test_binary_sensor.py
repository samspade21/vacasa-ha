"""Tests for Vacasa binary sensor behavior."""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, call, patch

import pytest

from custom_components.vacasa.binary_sensor import VacasaOccupancySensor


class TestBinarySensorRetry:
    """Test retry behavior when locating calendar entity."""

    @pytest.mark.asyncio
    async def test_find_calendar_entity_with_retry_success(self):
        """Calendar entity found after retries with expected backoff."""
        sensor = VacasaOccupancySensor(
            coordinator=Mock(),
            client=Mock(),
            unit_id="unit123",
            name="Test Unit",
            code="TU",
            unit_attributes={},
        )

        with (
            patch.object(
                sensor,
                "_find_calendar_entity",
                side_effect=[None, None, "calendar.test"],
            ),
            patch(
                "custom_components.vacasa.binary_sensor.asyncio.sleep",
                new=AsyncMock(),
            ) as mock_sleep,
        ):
            result = await sensor._find_calendar_entity_with_retry(max_retries=3)

            assert result == "calendar.test"
            mock_sleep.assert_has_awaits([call(2), call(4)])


class TestBinarySensorScheduling:
    """Test scheduling logic for occupancy updates."""

    @patch("custom_components.vacasa.binary_sensor.async_track_point_in_time")
    def test_schedule_event_timers_for_current_and_next(self, mock_track):
        """Timers are scheduled for current event end and next event start."""
        sensor = VacasaOccupancySensor(
            coordinator=Mock(),
            client=Mock(),
            unit_id="unit123",
            name="Test Unit",
            code="TU",
            unit_attributes={},
        )
        sensor.hass = Mock()

        current_start = datetime.now(timezone.utc) - timedelta(days=1)
        current_end = datetime.now(timezone.utc) + timedelta(hours=2)
        next_start = current_end + timedelta(hours=3)
        next_end = next_start + timedelta(days=2)

        mock_track.side_effect = ["end_unsub", "start_unsub"]

        sensor._current_event = type(
            "Event",
            (),
            {"summary": "Current", "start": current_start, "end": current_end},
        )()
        sensor._next_event = type(
            "Event",
            (),
            {"summary": "Next", "start": next_start, "end": next_end},
        )()

        sensor._schedule_event_timers()

        assert mock_track.call_count == 2
        end_call = mock_track.call_args_list[0]
        start_call = mock_track.call_args_list[1]

        assert end_call.args[0] is sensor.hass
        assert end_call.args[1] == sensor._handle_scheduled_refresh
        assert end_call.args[2] == current_end

        assert start_call.args[0] is sensor.hass
        assert start_call.args[1] == sensor._handle_scheduled_refresh
        assert start_call.args[2] == next_start

        assert sensor._unsubscribe_end_timer == "end_unsub"
        assert sensor._unsubscribe_start_timer == "start_unsub"

    @patch("custom_components.vacasa.binary_sensor.async_track_point_in_time")
    def test_schedule_event_timer_for_next_only(self, mock_track):
        """When only a next event exists, schedule a start timer."""
        sensor = VacasaOccupancySensor(
            coordinator=Mock(),
            client=Mock(),
            unit_id="unit123",
            name="Test Unit",
            code="TU",
            unit_attributes={},
        )
        sensor.hass = Mock()

        next_start = datetime.now(timezone.utc) + timedelta(hours=4)
        next_end = next_start + timedelta(days=1)
        mock_track.side_effect = ["start_unsub"]

        sensor._next_event = type(
            "Event",
            (),
            {"summary": "Next", "start": next_start, "end": next_end},
        )()

        sensor._schedule_event_timers()

        mock_track.assert_called_once()
        call_args = mock_track.call_args
        assert call_args.args[0] is sensor.hass
        assert call_args.args[1] == sensor._handle_scheduled_refresh
        assert call_args.args[2] == next_start

        assert sensor._unsubscribe_start_timer == "start_unsub"
        assert sensor._unsubscribe_end_timer is None

    def test_handle_scheduled_refresh_creates_task(self):
        """Scheduled refresh triggers a hass task."""
        sensor = VacasaOccupancySensor(
            coordinator=Mock(),
            client=Mock(),
            unit_id="unit123",
            name="Test Unit",
            code="TU",
            unit_attributes={},
        )
        sensor.hass = Mock()

        sensor._handle_scheduled_refresh(datetime.now(timezone.utc))

        sensor.hass.async_create_task.assert_called_once()
        task_arg = sensor.hass.async_create_task.call_args.args[0]
        assert asyncio.iscoroutine(task_arg)
        task_arg.close()

    @pytest.mark.asyncio
    async def test_scheduled_refresh_requests_update(self):
        """Scheduled refresh awaits coordinator and updates calendar."""
        coordinator = AsyncMock()
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

        with patch.object(sensor, "_update_from_calendar", new=AsyncMock()) as mock_update:
            await sensor._scheduled_refresh()

        coordinator.async_request_refresh.assert_awaited_once()
        mock_update.assert_awaited_once()
        sensor.async_write_ha_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_calendar_entity_with_retry_failure(self):
        """Calendar entity not found after max retries."""
        sensor = VacasaOccupancySensor(
            coordinator=Mock(),
            client=Mock(),
            unit_id="unit123",
            name="Test Unit",
            code="TU",
            unit_attributes={},
        )

        with (
            patch.object(sensor, "_find_calendar_entity", return_value=None),
            patch(
                "custom_components.vacasa.binary_sensor.asyncio.sleep",
                new=AsyncMock(),
            ) as mock_sleep,
        ):
            result = await sensor._find_calendar_entity_with_retry(max_retries=3)

            assert result is None
            mock_sleep.assert_has_awaits([call(2), call(4)])
