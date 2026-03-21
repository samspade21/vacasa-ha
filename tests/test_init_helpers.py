"""Tests for module-level helpers in custom_components/vacasa/__init__.py."""

from unittest.mock import Mock

from custom_components.vacasa import _iter_coordinator_units


def _coordinator(units=None, data_is_none=False):
    """Build a minimal coordinator mock."""
    c = Mock()
    c.reservation_states = {}
    if data_is_none:
        c.data = None
    else:
        c.data = {"units": units} if units is not None else {}
    return c


def test_iter_coordinator_units_yields_valid_units():
    """Generator yields (unit_id, attributes, name) for each valid unit."""
    units = [
        {"id": "u1", "attributes": {"name": "Beach House", "code": "BH"}},
        {"id": "u2", "attributes": {"name": "Mountain Cabin", "code": "MC"}},
    ]
    coordinator = _coordinator(units=units)
    results = list(_iter_coordinator_units(coordinator, "test platform"))
    assert len(results) == 2
    assert results[0][0] == "u1"
    assert results[0][2] == "Beach House"
    assert results[1][0] == "u2"


def test_iter_coordinator_units_none_data_yields_nothing():
    """When coordinator.data is None, generator yields nothing and logs a warning."""
    coordinator = _coordinator(data_is_none=True)
    results = list(_iter_coordinator_units(coordinator, "test platform"))
    assert results == []


def test_iter_coordinator_units_missing_units_key_yields_nothing():
    """When coordinator.data has no 'units' key, the generator yields nothing."""
    coordinator = Mock()
    coordinator.data = {}  # no "units" key → .get returns None
    results = list(_iter_coordinator_units(coordinator, "test platform"))
    assert results == []


def test_iter_coordinator_units_skips_unit_without_id():
    """Units with no id are silently skipped; valid units are still yielded."""
    units = [
        {"id": "", "attributes": {"name": "No-ID Unit"}},
        {"id": "valid", "attributes": {"name": "Valid Unit"}},
    ]
    coordinator = _coordinator(units=units)
    results = list(_iter_coordinator_units(coordinator, "test platform"))
    assert len(results) == 1
    assert results[0][0] == "valid"


def test_iter_coordinator_units_empty_list():
    """Empty units list yields nothing."""
    coordinator = _coordinator(units=[])
    results = list(_iter_coordinator_units(coordinator, "test platform"))
    assert results == []


def test_iter_coordinator_units_attributes_passed_through():
    """Attributes dict and name are correctly unpacked from the unit."""
    units = [
        {"id": "u1", "attributes": {"name": "Cabin", "code": "CB", "rating": 4.8}},
    ]
    coordinator = _coordinator(units=units)
    unit_id, attributes, name = next(iter(_iter_coordinator_units(coordinator, "x")))
    assert unit_id == "u1"
    assert attributes["rating"] == 4.8
    assert name == "Cabin"
