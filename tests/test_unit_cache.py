"""Regression tests for shared Vacasa unit caching."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.vacasa import VacasaData
from custom_components.vacasa import binary_sensor as binary_sensor_platform
from custom_components.vacasa import calendar as calendar_platform
from custom_components.vacasa import sensor as sensor_platform


@pytest.mark.asyncio
async def test_platforms_use_cached_units() -> None:
    """Platform setup reuses coordinator data without extra API calls."""
    units = [
        {"id": "1", "attributes": {"name": "Unit 1", "code": "U1"}},
        {"id": "2", "attributes": {"name": "Unit 2", "code": "U2"}},
    ]

    client = Mock()
    client.get_units = AsyncMock(return_value=units)

    # Simulate the single coordinator refresh that populates the cache.
    await client.get_units()
    assert client.get_units.await_count == 1

    coordinator = Mock()
    coordinator.data = {"last_update": datetime.now(timezone.utc), "units": units}
    coordinator.reservation_states = {}

    hass = Mock()
    config_entry = SimpleNamespace(runtime_data=VacasaData(client=client, coordinator=coordinator))

    async_add_entities = Mock()

    with (
        patch("custom_components.vacasa.calendar.VacasaCalendar"),
        patch("custom_components.vacasa.binary_sensor.VacasaOccupancySensor"),
        patch("custom_components.vacasa.sensor._create_unit_sensors", return_value=[]),
        patch(
            "custom_components.vacasa.sensor.VacasaStatementSensor",
            return_value=Mock(),
        ),
    ):
        await calendar_platform.async_setup_entry(hass, config_entry, async_add_entities)
        await binary_sensor_platform.async_setup_entry(hass, config_entry, async_add_entities)
        await sensor_platform.async_setup_entry(hass, config_entry, async_add_entities)

    assert client.get_units.await_count == 1


@pytest.mark.asyncio
async def test_coordinator_enforces_30s_timeout() -> None:
    """_async_update_data raises UpdateFailed when the API times out."""
    from custom_components.vacasa import VacasaDataUpdateCoordinator

    client = Mock()
    client.ensure_token = AsyncMock()
    client.get_units = AsyncMock()

    coordinator = VacasaDataUpdateCoordinator.__new__(VacasaDataUpdateCoordinator)
    coordinator.client = client

    with (
        patch("asyncio.timeout", side_effect=asyncio.TimeoutError),
        pytest.raises(Exception, match="[Tt]imeout"),
    ):
        await coordinator._async_update_data()
