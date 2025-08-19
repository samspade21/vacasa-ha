"""Tests for Vacasa property sensors."""

from unittest.mock import Mock

from custom_components.vacasa.sensor import VacasaRatingSensor, VacasaTimezoneSensor


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
