"""Tests for the Vacasa configuration flow."""

import pytest
import voluptuous as vol

from custom_components.vacasa.config_flow import (
    VacasaOptionsFlowHandler,
    validate_email,
    validate_password,
)


def test_options_flow_has_step_init():
    """Options flow handler exposes async_step_init."""
    assert hasattr(VacasaOptionsFlowHandler(), "async_step_init")


@pytest.mark.parametrize(
    "email",
    [
        "user@example.com",
        "first.last+tag@sub.domain.org",
    ],
)
def test_validate_email_accepts_valid_addresses(email: str) -> None:
    """Valid e-mail addresses should be returned unchanged (stripped)."""
    assert validate_email(email) == email.strip()


@pytest.mark.parametrize(
    "email",
    [
        "",
        "not-an-email",
        "missing@",
        "@nodomain.com",
        "spaces in@address.com",
    ],
)
def test_validate_email_rejects_invalid_addresses(email: str) -> None:
    """Invalid e-mail addresses should raise vol.Invalid."""
    with pytest.raises(vol.Invalid):
        validate_email(email)


def test_validate_password_accepts_valid_password() -> None:
    """Passwords of 8+ non-whitespace characters should be accepted."""
    assert validate_password("securepassword") == "securepassword"


@pytest.mark.parametrize(
    "password",
    [
        "",  # empty
        "short",  # too short (< 8 chars)
        "       ",  # whitespace only
    ],
)
def test_validate_password_rejects_invalid_passwords(password: str) -> None:
    """Passwords that are empty, too short, or whitespace should raise vol.Invalid."""
    with pytest.raises(vol.Invalid):
        validate_password(password)


@pytest.mark.parametrize("value", [None, 123, []])
def test_validate_email_rejects_non_string(value) -> None:
    """None/non-string usernames raise vol.Invalid, not an unhandled error."""
    with pytest.raises(vol.Invalid):
        validate_email(value)
