"""Tests for Vacasa property sensors."""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from custom_components.vacasa import sensor as sensor_module
from custom_components.vacasa.const import STAY_TYPE_GUEST
from custom_components.vacasa.sensor import (
    VacasaBathroomsSensor,
    VacasaHomeInfoSensor,
    VacasaLocationSensor,
    VacasaNextStaySensor,
    VacasaRatingSensor,
    VacasaTimezoneSensor,
)


def test_rating_sensor_native_value():
    """Rating sensor returns rating from attributes."""
    sensor = VacasaRatingSensor(
        coordinator=Mock(),
        unit_id="1",
        name="Unit",
        unit_attributes={"rating": 4.7},
    )
    assert sensor.native_value == 4.7


def test_timezone_sensor_native_value():
    """Timezone sensor returns timezone from attributes."""
    sensor = VacasaTimezoneSensor(
        coordinator=Mock(),
        unit_id="1",
        name="Unit",
        unit_attributes={"timezone": "America/Boise"},
    )
    assert sensor.native_value == "America/Boise"


def test_location_sensor_attributes():
    """Location sensor exposes coordinates and attributes."""
    sensor = VacasaLocationSensor(
        coordinator=Mock(),
        unit_id="2",
        name="Mountain Retreat",
        unit_attributes={"location": {"lat": 45.1234, "lng": -122.9876}},
    )

    assert sensor.native_value == "45.1234,-122.9876"
    assert sensor.extra_state_attributes == {
        "latitude": 45.1234,
        "longitude": -122.9876,
    }


def test_bathrooms_sensor_values():
    """Bathrooms sensor calculates totals and extra attributes."""
    sensor = VacasaBathroomsSensor(
        coordinator=Mock(),
        unit_id="3",
        name="Oceanfront Condo",
        unit_attributes={
            "amenities": {
                "rooms": {
                    "bathrooms": {
                        "full": 2,
                        "half": 1,
                    }
                }
            }
        },
    )

    assert sensor.native_value == pytest.approx(2.5)
    assert sensor.extra_state_attributes == {
        "full_bathrooms": 2,
        "half_bathrooms": 1,
    }


def test_next_stay_sensor_current_reservation(monkeypatch):
    """Next stay sensor identifies current stays and exposes metadata."""
    fixed_now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(sensor_module.dt_util, "now", lambda: fixed_now)

    coordinator = Mock()
    coordinator.client = Mock()
    coordinator.client.categorize_reservation.return_value = STAY_TYPE_GUEST

    unit_attributes = {
        "timezone": "UTC",
        "checkInTime": "16:00",
        "checkOutTime": "10:00",
    }
    sensor = VacasaNextStaySensor(
        coordinator=coordinator,
        unit_id="4",
        name="Downtown Loft",
        unit_attributes=unit_attributes,
    )

    reservations = [
        {
            "id": "past",
            "attributes": {
                "startDate": "2023-12-20",
                "endDate": "2023-12-24",
            },
        },
        {
            "id": "current",
            "attributes": {
                "startDate": "2023-12-31",
                "endDate": "2024-01-03",
                "firstName": "Jane",
                "lastName": "Doe",
                "guestCount": 4,
            },
        },
        {
            "id": "future",
            "attributes": {
                "startDate": "2024-02-01",
                "endDate": "2024-02-05",
            },
        },
    ]

    next_reservation = sensor._find_next_stay(reservations)
    assert next_reservation is not None
    assert next_reservation["id"] == "current"

    sensor._reservation = next_reservation

    assert sensor.native_value == "Guest Booking (currently occupied)"

    attrs = sensor.extra_state_attributes
    assert attrs["reservation_id"] == "current"
    assert attrs["guest_name"] == "Jane Doe"
    assert attrs["guest_count"] == 4
    assert attrs["stay_duration_nights"] == 3
    assert attrs["is_current"] is True
    assert attrs["is_upcoming"] is False


def test_next_stay_sensor_upcoming_reservation(monkeypatch):
    """Next stay sensor reports calendar days for upcoming stays."""
    fixed_now = datetime(2024, 1, 1, 7, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(sensor_module.dt_util, "now", lambda: fixed_now)

    coordinator = Mock()
    coordinator.client = Mock()
    coordinator.client.categorize_reservation.return_value = STAY_TYPE_GUEST

    unit_attributes = {
        "timezone": "UTC",
        "checkInTime": "16:00",
        "checkOutTime": "10:00",
    }
    sensor = VacasaNextStaySensor(
        coordinator=coordinator,
        unit_id="5",
        name="Cozy Cottage",
        unit_attributes=unit_attributes,
    )

    sensor._reservation = {
        "id": "upcoming",
        "attributes": {
            "startDate": "2024-01-03",
            "endDate": "2024-01-05",
        },
    }

    assert sensor.native_value == "Guest Booking in 2 days"

    attrs = sensor.extra_state_attributes
    assert attrs["days_until_checkin"] == 2
    assert attrs["is_current"] is False
    assert attrs["is_upcoming"] is True


def test_home_info_sensor_handles_nested_attributes():
    """Home info sensor extracts status from nested API payloads."""
    sensor = VacasaHomeInfoSensor(
        coordinator=Mock(),
        unit_id="5",
        name="Forest Cabin",
        unit_attributes={},
    )

    sensor._home_info = {
        "data": {
            "id": "5",
            "attributes": {
                "homeStatus": "Clean",
                "lastInspectionDate": "2024-01-15",
            },
        }
    }

    assert sensor.native_value == "Clean"
    assert sensor.extra_state_attributes["last_inspection_date"] == "2024-01-15"


def test_home_info_sensor_handles_list_payloads():
    """Home info sensor supports list responses from the API."""
    sensor = VacasaHomeInfoSensor(
        coordinator=Mock(),
        unit_id="6",
        name="Lakeside Retreat",
        unit_attributes={},
    )

    sensor._home_info = [
        {
            "attributes": {
                "status": "Ready",
                "cleanScore": 95,
            }
        }
    ]

    assert sensor.native_value == "Ready"
    assert sensor.extra_state_attributes["clean_score"] == 95


def test_home_info_sensor_combines_new_api_payloads():
    """Aggregated API payloads expose the expected attributes."""
    sensor = VacasaHomeInfoSensor(
        coordinator=Mock(),
        unit_id="7",
        name="Seaside Haven",
        unit_attributes={},
    )

    sensor._home_info = {
        "summary": {
            "homeId": "7",
            "name": "Seaside Haven",
            "active": True,
        },
        "activity": {
            "lastInspectionDate": "2025-11-09T17:00:00Z",
            "nextCleanScheduled": "2025-11-17",
            "averageGuestCleanScore": 4.9,
        },
        "latestInspection": {
            "inspectionId": "abcd-1234",
            "date": "2025-11-09T17:22:00Z",
            "totalItemsInspected": 35,
            "spaces": ["Kitchen", "Bedroom"],
        },
        "attributes": {
            "homeStatus": "Clean",
            "lastInspectionDate": "2025-11-09T17:00:00Z",
            "nextCleanScheduled": "2025-11-17",
            "averageGuestCleanScore": 4.9,
            "inspectionId": "abcd-1234",
            "totalItemsInspected": 35,
            "spaces": ["Kitchen", "Bedroom"],
        },
    }

    assert sensor.native_value == "Clean"
    attrs = sensor.extra_state_attributes
    assert attrs["last_inspection_date"] == "2025-11-09T17:00:00Z"
    assert attrs["next_clean_date"] == "2025-11-17"
    assert attrs["clean_score"] == 4.9
    assert attrs["total_items_inspected"] == 35
    assert attrs["spaces"] == ["Kitchen", "Bedroom"]


def test_home_info_sensor_uses_active_flag_when_no_status():
    """Boolean active flag provides a fallback home status."""
    sensor = VacasaHomeInfoSensor(
        coordinator=Mock(),
        unit_id="8",
        name="Woodland Escape",
        unit_attributes={},
    )

    sensor._home_info = {
        "attributes": {
            "active": False,
            "lastCleanDate": "2025-11-01",
        }
    }

    assert sensor.native_value == "Inactive"
    assert sensor.extra_state_attributes["last_clean_date"] == "2025-11-01"
