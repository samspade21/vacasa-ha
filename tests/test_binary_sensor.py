"""Tests for Vacasa binary sensor retry logic."""

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
