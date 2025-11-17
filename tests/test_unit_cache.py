"""Regression tests for shared Vacasa unit caching."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.vacasa import VacasaData, VacasaDataUpdateCoordinator
from custom_components.vacasa import binary_sensor as binary_sensor_platform
from custom_components.vacasa import calendar as calendar_platform
from custom_components.vacasa import sensor as sensor_platform


@pytest.mark.asyncio
async def test_platforms_use_cached_units() -> None:
    """Platform setup reuses coordinator data without extra API calls."""

    hass = Mock()
    hass.loop = Mock()

    client = Mock()
    client.ensure_token = AsyncMock()
    client.get_units = AsyncMock(
        return_value=[
            {"id": "1", "attributes": {"name": "Unit 1", "code": "U1"}},
            {"id": "2", "attributes": {"name": "Unit 2", "code": "U2"}},
        ]
    )
    client.token_expiry = datetime.now(timezone.utc)

    coordinator = VacasaDataUpdateCoordinator(hass, client)
    coordinator.data = await coordinator._async_update_data()

    assert client.get_units.await_count == 1

    config_entry = SimpleNamespace(
        runtime_data=VacasaData(client=client, coordinator=coordinator)
    )

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
        await calendar_platform.async_setup_entry(
            hass, config_entry, async_add_entities
        )
        await binary_sensor_platform.async_setup_entry(
            hass, config_entry, async_add_entities
        )
        await sensor_platform.async_setup_entry(
            hass, config_entry, async_add_entities
        )

    assert client.get_units.await_count == 1
