"""Tests for Vacasa calendar platform."""

from datetime import timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.vacasa.calendar import VacasaCalendar
from custom_components.vacasa.const import STAY_TYPE_GUEST
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
                    }
                }
            ]
        }
    )

    calendar = VacasaCalendar(
        coordinator=Mock(),
        client=client,
        unit_id="1",
        name="Unit 1",
        code="U1",
        unit_attributes={"timezone": "UTC"},
    )

    event = await calendar.async_get_current_event()
    assert event is not None
    assert event.summary == "Guest Booking"
