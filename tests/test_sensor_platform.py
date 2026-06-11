"""Tests for Vacasa property sensors."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.vacasa import sensor as sensor_module
from custom_components.vacasa.api_client import ApiError
from custom_components.vacasa.const import STAY_TYPE_GUEST
from custom_components.vacasa.models import ReservationState, ReservationWindow
from custom_components.vacasa.sensor import (
    VacasaAddressSensor,
    VacasaBaseSensor,
    VacasaBathroomsSensor,
    VacasaBedroomsSensor,
    VacasaHotTubSensor,
    VacasaLocationSensor,
    VacasaMaintenanceSensor,
    VacasaMaxAdultsSensor,
    VacasaMaxChildrenSensor,
    VacasaMaxOccupancySensor,
    VacasaMaxPetsSensor,
    VacasaNextStaySensor,
    VacasaParkingSensor,
    VacasaPetFriendlySensor,
    VacasaRatingSensor,
    VacasaStatementSensor,
    VacasaTimezoneSensor,
)


def _coordinator(reservation_states=None):
    """Build a minimal coordinator mock."""
    c = Mock()
    c.reservation_states = reservation_states or {}
    return c


# ---------------------------------------------------------------------------
# VacasaBaseSensor helpers
# ---------------------------------------------------------------------------


def test_bool_to_yes_no_none():
    """_bool_to_yes_no returns None when the value is None."""
    assert VacasaBaseSensor._bool_to_yes_no(None) is None


def test_bool_to_yes_no_true():
    """_bool_to_yes_no returns 'Yes' for True."""
    assert VacasaBaseSensor._bool_to_yes_no(True) == "Yes"


def test_bool_to_yes_no_false():
    """_bool_to_yes_no returns 'No' for False."""
    assert VacasaBaseSensor._bool_to_yes_no(False) == "No"


def test_get_amenity_bool_present():
    """_get_amenity_bool returns Yes/No when the amenity flag is set."""
    sensor = VacasaHotTubSensor(
        coordinator=Mock(),
        unit_id="1",
        name="Unit",
        unit_attributes={"amenities": {"hotTub": True}},
    )
    assert sensor._get_amenity_bool("hotTub") == "Yes"


def test_get_amenity_bool_missing_amenities():
    """_get_amenity_bool returns None when there are no amenities."""
    sensor = VacasaHotTubSensor(
        coordinator=Mock(),
        unit_id="1",
        name="Unit",
        unit_attributes={},
    )
    assert sensor._get_amenity_bool("hotTub") is None


# ---------------------------------------------------------------------------
# Simple value sensors
# ---------------------------------------------------------------------------


def test_rating_sensor_native_value():
    """Rating sensor returns the rating from unit attributes."""
    sensor = VacasaRatingSensor(
        coordinator=Mock(),
        unit_id="1",
        name="Unit",
        unit_attributes={"rating": 4.7},
    )
    assert sensor.native_value == 4.7


def test_rating_sensor_missing():
    """Rating sensor returns None when attribute is absent."""
    sensor = VacasaRatingSensor(coordinator=Mock(), unit_id="1", name="Unit", unit_attributes={})
    assert sensor.native_value is None


def test_timezone_sensor_native_value():
    """Timezone sensor returns timezone string from unit attributes."""
    sensor = VacasaTimezoneSensor(
        coordinator=Mock(),
        unit_id="1",
        name="Unit",
        unit_attributes={"timezone": "America/Boise"},
    )
    assert sensor.native_value == "America/Boise"


def test_max_occupancy_sensor():
    """MaxOccupancy sensor returns the total occupancy limit."""
    sensor = VacasaMaxOccupancySensor(
        coordinator=Mock(), unit_id="1", name="Unit", unit_attributes={"maxOccupancyTotal": 8}
    )
    assert sensor.native_value == 8


def test_max_adults_sensor():
    """MaxAdults sensor returns the adult occupancy limit."""
    sensor = VacasaMaxAdultsSensor(
        coordinator=Mock(), unit_id="1", name="Unit", unit_attributes={"maxAdults": 6}
    )
    assert sensor.native_value == 6


def test_max_children_sensor():
    """MaxChildren sensor returns the children occupancy limit."""
    sensor = VacasaMaxChildrenSensor(
        coordinator=Mock(), unit_id="1", name="Unit", unit_attributes={"maxChildren": 4}
    )
    assert sensor.native_value == 4


def test_max_pets_sensor():
    """MaxPets sensor returns the pet limit."""
    sensor = VacasaMaxPetsSensor(
        coordinator=Mock(), unit_id="1", name="Unit", unit_attributes={"maxPets": 2}
    )
    assert sensor.native_value == 2


# ---------------------------------------------------------------------------
# Location sensor
# ---------------------------------------------------------------------------


def test_location_sensor_attributes():
    """Location sensor exposes coordinates and attributes."""
    sensor = VacasaLocationSensor(
        coordinator=Mock(),
        unit_id="2",
        name="Mountain Retreat",
        unit_attributes={"location": {"lat": 45.1234, "lng": -122.9876}},
    )
    assert sensor.native_value == "45.1234,-122.9876"
    assert sensor.extra_state_attributes == {"latitude": 45.1234, "longitude": -122.9876}


def test_location_sensor_missing_coords():
    """Location sensor returns None when location is absent."""
    sensor = VacasaLocationSensor(coordinator=Mock(), unit_id="2", name="Unit", unit_attributes={})
    assert sensor.native_value is None
    assert sensor.extra_state_attributes == {}


def test_location_sensor_partial_coords():
    """Missing lng means no location value is produced."""
    sensor = VacasaLocationSensor(
        coordinator=Mock(),
        unit_id="2",
        name="Unit",
        unit_attributes={"location": {"lat": 45.0}},
    )
    assert sensor.native_value is None


# ---------------------------------------------------------------------------
# Bedrooms sensor
# ---------------------------------------------------------------------------


def test_bedrooms_sensor_value_and_beds():
    """Bedrooms sensor returns bedroom count and filters out child beds."""
    sensor = VacasaBedroomsSensor(
        coordinator=Mock(),
        unit_id="3",
        name="Unit",
        unit_attributes={
            "amenities": {
                "rooms": {"bedrooms": 3},
                "beds": {"king": 2, "queen": 1, "child": 1},
            }
        },
    )
    assert sensor.native_value == 3
    assert sensor.extra_state_attributes == {"king_beds": 2, "queen_beds": 1}


def test_bedrooms_sensor_no_amenities():
    """Bedrooms sensor returns None when amenities are absent."""
    sensor = VacasaBedroomsSensor(coordinator=Mock(), unit_id="3", name="Unit", unit_attributes={})
    assert sensor.native_value is None
    assert sensor.extra_state_attributes == {}


def test_bedrooms_sensor_null_amenities():
    """Bedrooms sensor handles amenities/rooms/beds being explicitly None."""
    sensor = VacasaBedroomsSensor(
        coordinator=Mock(),
        unit_id="3",
        name="Unit",
        unit_attributes={"amenities": None},
    )
    assert sensor.native_value is None
    assert sensor.extra_state_attributes == {}

    sensor = VacasaBedroomsSensor(
        coordinator=Mock(),
        unit_id="3",
        name="Unit",
        unit_attributes={"amenities": {"rooms": None, "beds": None}},
    )
    assert sensor.native_value is None
    assert sensor.extra_state_attributes == {}


# ---------------------------------------------------------------------------
# Bathrooms sensor
# ---------------------------------------------------------------------------


def test_bathrooms_sensor_values():
    """Bathrooms sensor calculates totals and extra attributes."""
    sensor = VacasaBathroomsSensor(
        coordinator=Mock(),
        unit_id="3",
        name="Oceanfront Condo",
        unit_attributes={"amenities": {"rooms": {"bathrooms": {"full": 2, "half": 1}}}},
    )
    assert sensor.native_value == pytest.approx(2.5)
    assert sensor.extra_state_attributes == {"full_bathrooms": 2, "half_bathrooms": 1}


def test_bathrooms_sensor_empty():
    """Bathrooms sensor returns None when bathroom data is absent."""
    sensor = VacasaBathroomsSensor(coordinator=Mock(), unit_id="3", name="Unit", unit_attributes={})
    assert sensor.native_value is None
    assert sensor.extra_state_attributes == {}


def test_bathrooms_sensor_null_amenities():
    """Bathrooms sensor handles amenities/rooms/bathrooms being explicitly None."""
    sensor = VacasaBathroomsSensor(
        coordinator=Mock(),
        unit_id="3",
        name="Unit",
        unit_attributes={"amenities": None},
    )
    assert sensor.native_value is None
    assert sensor.extra_state_attributes == {}

    sensor = VacasaBathroomsSensor(
        coordinator=Mock(),
        unit_id="3",
        name="Unit",
        unit_attributes={"amenities": {"rooms": {"bathrooms": None}}},
    )
    assert sensor.native_value is None
    assert sensor.extra_state_attributes == {}


def test_bathrooms_sensor_null_leaf_values():
    """Bathrooms sensor handles full/half being explicitly None (key present, value null)."""
    sensor = VacasaBathroomsSensor(
        coordinator=Mock(),
        unit_id="3",
        name="Unit",
        unit_attributes={"amenities": {"rooms": {"bathrooms": {"full": None, "half": 2}}}},
    )
    # Must not raise TypeError; None leaf coerces to 0.
    assert sensor.native_value == 1.0
    assert sensor.extra_state_attributes == {"full_bathrooms": 0, "half_bathrooms": 2}


# ---------------------------------------------------------------------------
# HotTub / PetFriendly sensors
# ---------------------------------------------------------------------------


def test_hot_tub_sensor_yes():
    """HotTub sensor returns 'Yes' when hotTub amenity is True."""
    sensor = VacasaHotTubSensor(
        coordinator=Mock(),
        unit_id="1",
        name="Unit",
        unit_attributes={"amenities": {"hotTub": True}},
    )
    assert sensor.native_value == "Yes"


def test_hot_tub_sensor_no():
    """HotTub sensor returns 'No' when hotTub amenity is False."""
    sensor = VacasaHotTubSensor(
        coordinator=Mock(),
        unit_id="1",
        name="Unit",
        unit_attributes={"amenities": {"hotTub": False}},
    )
    assert sensor.native_value == "No"


def test_hot_tub_sensor_missing_amenities():
    """HotTub sensor returns None when amenities are absent."""
    sensor = VacasaHotTubSensor(coordinator=Mock(), unit_id="1", name="Unit", unit_attributes={})
    assert sensor.native_value is None


def test_pet_friendly_sensor_yes():
    """PetFriendly sensor returns 'Yes' when petsFriendly is True."""
    sensor = VacasaPetFriendlySensor(
        coordinator=Mock(),
        unit_id="1",
        name="Unit",
        unit_attributes={"amenities": {"petsFriendly": True}},
    )
    assert sensor.native_value == "Yes"


def test_pet_friendly_sensor_missing_amenities():
    """PetFriendly sensor returns None when amenities are absent."""
    sensor = VacasaPetFriendlySensor(
        coordinator=Mock(), unit_id="1", name="Unit", unit_attributes={}
    )
    assert sensor.native_value is None


# ---------------------------------------------------------------------------
# Parking sensor
# ---------------------------------------------------------------------------


def test_parking_sensor_total_and_attrs():
    """Parking sensor returns total spaces and converts -1 values to None."""
    sensor = VacasaParkingSensor(
        coordinator=Mock(),
        unit_id="1",
        name="Unit",
        unit_attributes={
            "parking": {
                "total": 2,
                "notes": "Street only",
                "accessible": True,
                "paid": False,
                "fourWheelDriveRequired": -1,
            }
        },
    )
    assert sensor.native_value == 2
    attrs = sensor.extra_state_attributes
    assert attrs["notes"] == "Street only"
    assert attrs["accessible"] is True
    assert attrs["paid"] is False
    assert attrs["fourWheelDriveRequired"] is None  # -1 converted to None


def test_parking_sensor_no_parking():
    """Parking sensor returns None when parking data is absent."""
    sensor = VacasaParkingSensor(coordinator=Mock(), unit_id="1", name="Unit", unit_attributes={})
    assert sensor.native_value is None
    assert sensor.extra_state_attributes == {}


# ---------------------------------------------------------------------------
# Address sensor
# ---------------------------------------------------------------------------


def test_address_sensor_full():
    """Address sensor builds a full address string and populates attributes."""
    sensor = VacasaAddressSensor(
        coordinator=Mock(),
        unit_id="1",
        name="Unit",
        unit_attributes={
            "address": {
                "address_1": "123 Main St",
                "city": "Portland",
                "state": "OR",
                "zip": "97201",
                "country": {"name": "United States", "code": "US"},
            }
        },
    )
    assert sensor.native_value == "123 Main St, Portland, OR, 97201, United States"
    attrs = sensor.extra_state_attributes
    assert attrs["city"] == "Portland"
    assert attrs["country"] == "United States"
    assert attrs["country_code"] == "US"


def test_address_sensor_empty():
    """Address sensor returns None when address data is absent."""
    sensor = VacasaAddressSensor(coordinator=Mock(), unit_id="1", name="Unit", unit_attributes={})
    assert sensor.native_value is None
    assert sensor.extra_state_attributes == {}


# ---------------------------------------------------------------------------
# Maintenance sensor
# ---------------------------------------------------------------------------


def test_maintenance_sensor_native_value():
    """Maintenance sensor starts with zero tickets."""
    sensor = VacasaMaintenanceSensor(
        coordinator=Mock(),
        unit_id="1",
        name="Unit",
        unit_attributes={},
    )
    assert sensor.native_value == 0
    assert sensor.extra_state_attributes == {
        "status_filter": "open",
        "open_ticket_ids": [],
        "tickets": [],
    }


@pytest.mark.asyncio
async def test_maintenance_sensor_update_from_api():
    """Maintenance sensor fetches and counts tickets from the API."""
    coordinator = Mock()
    coordinator.client = Mock()
    coordinator.client.get_maintenance = AsyncMock(
        return_value=[
            {
                "id": "t1",
                "attributes": {
                    "status": "open",
                    "title": "Leaky faucet",
                    "updatedAt": "2024-01-01",
                },
            }
        ]
    )

    sensor = VacasaMaintenanceSensor(
        coordinator=coordinator, unit_id="u1", name="Unit", unit_attributes={}
    )
    await sensor._async_update_from_api()

    assert sensor.native_value == 1
    attrs = sensor.extra_state_attributes
    assert attrs["open_ticket_ids"] == ["t1"]
    assert attrs["tickets"][0]["title"] == "Leaky faucet"


@pytest.mark.asyncio
async def test_maintenance_sensor_api_error_clears_tickets():
    """Maintenance sensor resets to zero on API errors."""
    coordinator = Mock()
    coordinator.client = Mock()
    coordinator.client.get_maintenance = AsyncMock(side_effect=ApiError("fail"))

    sensor = VacasaMaintenanceSensor(
        coordinator=coordinator, unit_id="u1", name="Unit", unit_attributes={}
    )
    sensor._tickets = [{"id": "old"}]
    await sensor._async_update_from_api()
    assert sensor.native_value == 0


# ---------------------------------------------------------------------------
# Statement sensor
# ---------------------------------------------------------------------------


def _make_statement_sensor():
    """Create a VacasaStatementSensor with minimal mocks."""
    coordinator = Mock()
    coordinator.client = Mock()
    config_entry = Mock()
    config_entry.entry_id = "entry1"
    config_entry.data = {"username": "user@example.com"}
    return VacasaStatementSensor(coordinator=coordinator, config_entry=config_entry)


def test_statement_sensor_no_statements():
    """Statement sensor returns 0 and empty attributes with no data."""
    sensor = _make_statement_sensor()
    assert sensor.native_value == 0
    assert sensor._latest_attributes() == {}


def test_statement_sensor_returns_zero_when_no_amount_field():
    """Statement sensor reports 0.0 (not the statement count) when no parseable amount."""
    sensor = _make_statement_sensor()
    sensor._statements = [
        {"id": "s1", "attributes": {"updatedAt": "2024-01-01"}},
        {"id": "s2", "attributes": {"updatedAt": "2024-02-01", "totalAmount": "not-a-number"}},
    ]
    sensor._latest = sensor._latest_statement()
    # No usable amount field; should return 0.0 rather than len(_statements) == 2.
    assert sensor.native_value == 0.0


def test_statement_sensor_latest_attributes_none():
    """_latest_attributes returns {} when _latest is None."""
    sensor = _make_statement_sensor()
    sensor._latest = None
    assert sensor._latest_attributes() == {}


def test_statement_sensor_picks_latest_by_updated_at():
    """Statement sensor picks the most recently updated statement."""
    sensor = _make_statement_sensor()
    sensor._statements = [
        {"id": "s1", "attributes": {"updatedAt": "2024-01-01", "totalAmount": 100}},
        {"id": "s2", "attributes": {"updatedAt": "2024-03-01", "totalAmount": 200}},
        {"id": "s3", "attributes": {"updatedAt": "2024-02-01", "totalAmount": 150}},
    ]
    sensor._latest = sensor._latest_statement()
    assert sensor._latest["id"] == "s2"
    assert sensor.native_value == 200.0


def test_statement_sensor_falls_back_to_period_end_date():
    """Statement sensor falls back to periodEndDate when updatedAt is absent."""
    sensor = _make_statement_sensor()
    sensor._statements = [
        {"id": "a", "attributes": {"periodEndDate": "2024-06-30", "totalAmount": 500}},
        {"id": "b", "attributes": {"periodEndDate": "2024-03-31", "totalAmount": 300}},
    ]
    sensor._latest = sensor._latest_statement()
    assert sensor._latest["id"] == "a"


def test_statement_sensor_extra_state_attributes():
    """Statement sensor exposes detailed attributes from the latest statement."""
    sensor = _make_statement_sensor()
    sensor._statements = [
        {
            "id": "s99",
            "attributes": {
                "updatedAt": "2024-05-01",
                "totalAmount": 1234.56,
                "periodStartDate": "2024-04-01",
                "periodEndDate": "2024-04-30",
                "status": "final",
            },
        }
    ]
    sensor._latest = sensor._statements[0]
    attrs = sensor.extra_state_attributes
    assert attrs["latest_statement_id"] == "s99"
    assert attrs["total_amount"] == 1234.56
    assert attrs["period_start"] == "2024-04-01"
    assert attrs["status"] == "final"
    assert attrs["statement_count"] == 1


def test_coerce_amount_int():
    """_coerce_amount converts int to float."""
    assert VacasaStatementSensor._coerce_amount(42) == 42.0


def test_coerce_amount_string_with_dollar():
    """_coerce_amount parses currency strings with $ and commas."""
    assert VacasaStatementSensor._coerce_amount("$1,234.56") == pytest.approx(1234.56)


def test_coerce_amount_invalid_string():
    """_coerce_amount returns None for non-numeric strings."""
    assert VacasaStatementSensor._coerce_amount("not-a-number") is None


def test_coerce_amount_none():
    """_coerce_amount returns None for None input."""
    assert VacasaStatementSensor._coerce_amount(None) is None


@pytest.mark.asyncio
async def test_statement_sensor_api_error():
    """Statement sensor clears data when the API raises an error."""
    sensor = _make_statement_sensor()
    sensor._coordinator.client.get_statements = AsyncMock(side_effect=ApiError("network fail"))
    sensor._statements = [{"id": "old"}]
    await sensor._async_update_from_api()
    assert sensor._statements == []
    assert sensor._latest is None


# ---------------------------------------------------------------------------
# VacasaNextStaySensor change-detection guard
# ---------------------------------------------------------------------------


def _next_stay_sensor():
    """Build a VacasaNextStaySensor with a minimal coordinator."""
    coordinator = _coordinator()
    return VacasaNextStaySensor(
        coordinator=coordinator,
        unit_id="u1",
        name="Unit",
        unit_attributes={"timezone": "UTC"},
    )


def _window(summary="Guest Booking", days_ahead=1):
    """Build a ReservationWindow with deterministic times."""
    now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return ReservationWindow(
        summary=summary,
        start=now + timedelta(days=days_ahead),
        end=now + timedelta(days=days_ahead + 2),
        stay_type=STAY_TYPE_GUEST,
    )


def test_next_stay_change_guard_no_write_when_same(monkeypatch):
    """Guard suppresses write when reservation data doesn't change."""
    fixed_now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(sensor_module.dt_util, "now", lambda: fixed_now)

    sensor = _next_stay_sensor()
    window = _window()
    state = ReservationState(upcoming=window)
    # Prime state
    sensor._update_from_state(state)
    # Put same state in coordinator cache so refresh returns same object
    sensor._coordinator.reservation_states["u1"] = state

    with patch.object(sensor, "async_write_ha_state") as mock_write:
        sensor._handle_coordinator_update()
        mock_write.assert_not_called()


def test_next_stay_change_guard_writes_when_changed(monkeypatch):
    """Guard writes state when upcoming reservation changes."""
    fixed_now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(sensor_module.dt_util, "now", lambda: fixed_now)

    sensor = _next_stay_sensor()
    old_window = _window("Guest Booking")
    new_window = _window("Owner Stay")

    sensor._update_from_state(ReservationState(upcoming=old_window))
    sensor._coordinator.reservation_states["u1"] = ReservationState(upcoming=new_window)

    with patch.object(sensor, "async_write_ha_state") as mock_write:
        sensor._handle_coordinator_update()
        mock_write.assert_called_once()


def test_next_stay_sensor_current_reservation(monkeypatch):
    """Next stay sensor identifies current stays and exposes metadata."""
    fixed_now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(sensor_module.dt_util, "now", lambda: fixed_now)

    coordinator = Mock()
    coordinator.reservation_states = {}

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

    state = ReservationState(
        current=ReservationWindow(
            reservation_id="current",
            summary="Guest Booking",
            start=datetime(2023, 12, 31, tzinfo=timezone.utc),
            end=datetime(2024, 1, 3, tzinfo=timezone.utc),
            stay_type=STAY_TYPE_GUEST,
            guest_name="Jane Doe",
            guest_count=4,
        ),
        upcoming=ReservationWindow(
            reservation_id="future",
            summary="Guest Booking",
            start=datetime(2024, 2, 1, tzinfo=timezone.utc),
            end=datetime(2024, 2, 5, tzinfo=timezone.utc),
            stay_type=STAY_TYPE_GUEST,
        ),
    )

    sensor._update_from_state(state)

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
    coordinator.reservation_states = {}

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

    sensor._update_from_state(
        ReservationState(
            upcoming=ReservationWindow(
                reservation_id="upcoming",
                summary="Guest Booking",
                start=datetime(2024, 1, 3, tzinfo=timezone.utc),
                end=datetime(2024, 1, 5, tzinfo=timezone.utc),
                stay_type=STAY_TYPE_GUEST,
            )
        )
    )

    assert sensor.native_value == "Guest Booking in 2 days"

    attrs = sensor.extra_state_attributes
    assert attrs["days_until_checkin"] == 2
    assert attrs["is_current"] is False
    assert attrs["is_upcoming"] is True


def test_next_stay_reservation_state_signal(monkeypatch):
    """Reservation state signals update the next stay sensor when unit matches."""
    fixed_now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(sensor_module.dt_util, "now", lambda: fixed_now)

    coordinator = Mock()
    coordinator.reservation_states = {}

    sensor = VacasaNextStaySensor(
        coordinator=coordinator,
        unit_id="42",
        name="Signal Test",
        unit_attributes={"timezone": "UTC"},
    )

    state = ReservationState(
        upcoming=ReservationWindow(
            reservation_id="signal",
            summary="Guest Booking",
            start=datetime(2024, 1, 3, tzinfo=timezone.utc),
            end=datetime(2024, 1, 5, tzinfo=timezone.utc),
            stay_type=STAY_TYPE_GUEST,
        )
    )

    with patch.object(sensor, "async_write_ha_state") as mock_write:
        sensor._handle_reservation_state("other", state)
        mock_write.assert_not_called()
        assert sensor.native_value == "No upcoming reservations"

        sensor._handle_reservation_state("42", state)
        mock_write.assert_called_once()
        assert sensor.native_value == "Guest Booking in 2 days"
