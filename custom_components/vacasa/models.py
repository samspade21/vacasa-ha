"""Shared models for the Vacasa integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class ReservationWindow:
    """Represents a reservation window for a property."""

    reservation_id: str | None = None
    summary: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    stay_type: str | None = None
    guest_name: str | None = None
    guest_count: int | None = None


@dataclass(slots=True)
class ReservationState:
    """Tracks the current and next reservation windows for a unit."""

    current: ReservationWindow | None = None
    upcoming: ReservationWindow | None = None
