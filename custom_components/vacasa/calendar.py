"""Calendar platform for Vacasa integration."""

import logging
from datetime import datetime, time, timedelta
from functools import partial
from typing import Any, Callable
from zoneinfo import ZoneInfo

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import (
    VacasaConfigEntry,
    VacasaDataUpdateCoordinator,
    _extract_unit_info,
    _make_unit_device_info,
)
from .api_client import VacasaApiClient
from .const import (
    CALENDAR_LOOKAHEAD_DAYS,
    CALENDAR_LOOKBACK_DAYS,
    DEFAULT_CHECKIN_TIME,
    DEFAULT_CHECKOUT_TIME,
    SIGNAL_RESERVATION_BOUNDARY,
    SIGNAL_RESERVATION_STATE,
    STAY_TYPE_BLOCK,
    STAY_TYPE_GUEST,
    STAY_TYPE_MAINTENANCE,
    STAY_TYPE_OWNER,
    STAY_TYPE_TO_CATEGORY,
    STAY_TYPE_TO_NAME,
)
from .models import ReservationState, ReservationWindow

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: VacasaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Vacasa calendar platform."""
    data = config_entry.runtime_data
    client = data.client
    coordinator = data.coordinator

    # Get all units from the coordinator cache
    units = coordinator.data.get("units") if coordinator.data else None
    if units is None:
        _LOGGER.warning("Vacasa unit data unavailable while setting up calendars")
        return

    _LOGGER.info("Found %d Vacasa units for calendars", len(units))

    # Create a calendar entity for each unit
    entities = []
    for unit in units:
        unit_id, attributes, name = _extract_unit_info(unit)
        code = attributes.get("code", "")

        entity = VacasaCalendar(
            coordinator=coordinator,
            client=client,
            unit_id=unit_id,
            name=name,
            code=code,
            unit_attributes=attributes,
        )
        entities.append(entity)

    async_add_entities(entities, True)


class VacasaCalendar(CoordinatorEntity[VacasaDataUpdateCoordinator], CalendarEntity):
    """Representation of a Vacasa calendar."""

    def __init__(
        self,
        coordinator: VacasaDataUpdateCoordinator,
        client: VacasaApiClient,
        unit_id: str,
        name: str,
        code: str,
        unit_attributes: dict[str, Any],
    ) -> None:
        """Initialize the Vacasa calendar."""
        super().__init__(coordinator)
        self._client = client
        self._unit_id = unit_id
        self._name = name
        self._code = code
        self._unit_attributes = unit_attributes
        self._property_checkin_time = self._normalize_time_value(unit_attributes.get("checkInTime"))
        self._property_checkout_time = self._normalize_time_value(
            unit_attributes.get("checkOutTime")
        )

        tz_str = unit_attributes.get("timezone")
        if tz_str:
            try:
                ZoneInfo(tz_str)
                self._timezone: str | None = tz_str
            except Exception:
                _LOGGER.warning(
                    "Invalid timezone %r for unit %s; falling back to local time",
                    tz_str,
                    unit_id,
                )
                self._timezone = None
        else:
            self._timezone = None
        self._event_cache: dict[str, list[CalendarEvent]] = {}
        self._reservation_windows: dict[str, ReservationWindow] = {}
        self._current_event: CalendarEvent | None = None
        self._next_event: CalendarEvent | None = None
        self._events_loaded: bool = False
        self._unsubscribe_start_timer: Callable[[], None] | None = None
        self._unsubscribe_end_timer: Callable[[], None] | None = None

        # Entity properties
        self._attr_unique_id = f"vacasa_calendar_{unit_id}"
        self._attr_name = f"Vacasa {name}"

        self._attr_device_info = _make_unit_device_info(unit_id, name)

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        return self._current_event

    @property
    def state(self) -> str:
        """Return the state of the calendar entity.

        Returns 'on' if there's a current event happening now, 'off' otherwise.
        This is critical for the binary sensor occupancy detection to work properly.
        """
        return "on" if self._current_event is not None else "off"

    @property
    def event_types(self) -> list[str]:
        """Return a list of supported event types."""
        return list(STAY_TYPE_TO_CATEGORY.values())

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Get all events in a specific time frame."""
        # Convert to YYYY-MM-DD format for API
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        # Check if we have cached events for this date range
        cache_key = f"{start_str}_{end_str}"
        if cache_key in self._event_cache:
            return self._event_cache[cache_key]

        try:
            # Get categorized reservations
            categorized = await self._client.get_categorized_reservations(
                self._unit_id, start_str, end_str
            )

            events = []
            for stay_type, reservations in categorized.items():
                for reservation in reservations:
                    event = self._reservation_to_event(reservation, stay_type)
                    if event:
                        events.append(event)

            # Cache the events
            self._event_cache[cache_key] = events

            return events
        except Exception as err:
            _LOGGER.error("Error getting events for %s: %s", self._name, err)
            return []

    async def async_update(self) -> None:
        """Update the entity.

        This is only used by the generic entity update service.
        """
        await self.coordinator.async_request_refresh()
        await self._update_current_event()

    async def _update_current_event(self) -> None:
        """Update cached current and next events."""
        self._current_event, self._next_event = await self._determine_current_and_next_events()
        self._events_loaded = True
        self._schedule_boundary_timers()
        self._broadcast_reservation_state()

    async def _ensure_events_loaded(self) -> None:
        """Lazily populate current and next events if not already loaded."""
        if not self._events_loaded:
            await self._update_current_event()

    async def async_get_current_event(self) -> CalendarEvent | None:
        """Get the current event if active right now, otherwise None."""
        await self._ensure_events_loaded()
        return self._current_event

    async def async_get_next_event(self) -> CalendarEvent | None:
        """Get the next upcoming event (for display purposes)."""
        await self._ensure_events_loaded()
        return self._current_event or self._next_event

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        # Update current event when entity is added to hass
        await self._update_current_event()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up when entity is removed from hass."""
        self._cancel_boundary_timers()
        self.coordinator.reservation_states.pop(self._unit_id, None)
        await super().async_will_remove_from_hass()

    def _handle_coordinator_update(self) -> None:
        """Handle coordinator update."""
        # Update current event when coordinator updates
        self.hass.async_create_task(self._async_coordinator_update())

    async def _async_coordinator_update(self) -> None:
        """Handle coordinator update asynchronously."""
        try:
            # Clear event cache to ensure fresh data
            self._event_cache.clear()
            self._reservation_windows.clear()
            self._events_loaded = False

            # Update current and next events based on fresh data
            await self._update_current_event()

            # Write the state to Home Assistant
            self.async_write_ha_state()

            _LOGGER.debug(
                "Successfully updated calendar state for %s - current event: %s, state: %s",
                self._name,
                self._current_event.summary if self._current_event else "None",
                self.state,
            )
        except Exception as err:
            _LOGGER.error("Error during coordinator update for calendar %s: %s", self._name, err)

    async def _determine_current_and_next_events(
        self,
    ) -> tuple[CalendarEvent | None, CalendarEvent | None]:
        """Determine the current and next events for the property."""
        now_local = dt_util.now()
        now_utc = dt_util.utcnow()
        # Query from CALENDAR_LOOKBACK_DAYS ago to catch active reservations started in the past
        # (e.g., guest checking out today but checked in weeks ago)
        start_date = now_local - timedelta(days=CALENDAR_LOOKBACK_DAYS)
        end_date = now_local + timedelta(days=CALENDAR_LOOKAHEAD_DAYS)
        events = await self.async_get_events(self.hass, start_date, end_date)

        _LOGGER.debug(
            "Evaluating %d events for %s at %s",
            len(events),
            self._name,
            now_utc.isoformat(),
        )

        current_event: CalendarEvent | None = None
        next_event: CalendarEvent | None = None

        def _as_utc(value: datetime | None) -> datetime | None:
            return dt_util.as_utc(value) if value is not None else None

        event_tuples = [(event, _as_utc(event.start), _as_utc(event.end)) for event in events]

        for event, start_utc, end_utc in sorted(event_tuples, key=lambda t: t[1] or now_utc):
            if start_utc is None or end_utc is None:
                continue

            in_progress = start_utc <= now_utc < end_utc
            upcoming = start_utc > now_utc

            _LOGGER.debug(
                "Event %s: start=%s, end=%s, in_progress=%s, upcoming=%s",
                event.summary,
                start_utc.isoformat(),
                end_utc.isoformat(),
                in_progress,
                upcoming,
            )

            if in_progress:
                current_event = event
                continue

            if upcoming and next_event is None:
                next_event = event
                if current_event:
                    break

        if current_event:
            _LOGGER.debug(
                "Current event for %s set to %s (start=%s, end=%s)",
                self._name,
                current_event.summary,
                current_event.start.isoformat() if current_event.start else "unknown",
                current_event.end.isoformat() if current_event.end else "unknown",
            )
        else:
            _LOGGER.debug("No current event identified for %s", self._name)

        if next_event:
            _LOGGER.debug(
                "Next event for %s set to %s (start=%s)",
                self._name,
                next_event.summary,
                next_event.start.isoformat() if next_event.start else "unknown",
            )
        else:
            _LOGGER.debug("No upcoming event identified for %s", self._name)

        return current_event, next_event

    def _cancel_boundary_timers(self) -> None:
        """Cancel any scheduled boundary refresh timers."""
        if self._unsubscribe_start_timer:
            self._unsubscribe_start_timer()
            self._unsubscribe_start_timer = None
        if self._unsubscribe_end_timer:
            self._unsubscribe_end_timer()
            self._unsubscribe_end_timer = None

    def _schedule_boundary_timers(self) -> None:
        """Schedule refresh timers aligned with reservation boundaries."""
        if not self.hass:
            return

        self._cancel_boundary_timers()

        now_utc = dt_util.utcnow()

        if self._current_event and getattr(self._current_event, "end", None):
            end_utc = dt_util.as_utc(self._current_event.end)
            if end_utc and end_utc > now_utc:
                self._unsubscribe_end_timer = async_track_point_in_time(
                    self.hass,
                    partial(self._handle_boundary_timer, boundary="checkout"),
                    end_utc,
                )
                _LOGGER.debug(
                    "Scheduled checkout refresh for %s at %s "
                    "(local: %s, original: %s with tz: %s). Event: %s",
                    self._name,
                    end_utc.isoformat(),
                    dt_util.as_local(end_utc).isoformat(),
                    self._current_event.end.isoformat(),
                    self._current_event.end.tzinfo,
                    self._current_event.summary,
                )

        if self._next_event and getattr(self._next_event, "start", None):
            start_utc = dt_util.as_utc(self._next_event.start)
            if start_utc and start_utc > now_utc:
                self._unsubscribe_start_timer = async_track_point_in_time(
                    self.hass,
                    partial(self._handle_boundary_timer, boundary="checkin"),
                    start_utc,
                )
                _LOGGER.debug(
                    "Scheduled check-in refresh for %s at %s "
                    "(local: %s, original: %s with tz: %s). Event: %s",
                    self._name,
                    start_utc.isoformat(),
                    dt_util.as_local(start_utc).isoformat(),
                    self._next_event.start.isoformat(),
                    self._next_event.start.tzinfo,
                    self._next_event.summary,
                )

    def _handle_boundary_timer(self, scheduled_time: datetime, *, boundary: str) -> None:
        """Handle a scheduled reservation boundary timer."""
        if not self.hass:
            return

        _LOGGER.debug(
            "Boundary timer (%s) fired for %s. Scheduled: %s, Actual: %s",
            boundary,
            self._name,
            scheduled_time.isoformat(),
            dt_util.utcnow().isoformat(),
        )

        async_dispatcher_send(self.hass, SIGNAL_RESERVATION_BOUNDARY, self._unit_id, boundary)
        self.hass.async_create_task(self._boundary_refresh(boundary))

    async def _boundary_refresh(self, boundary: str) -> None:
        """Refresh coordinator and calendar state at reservation boundaries."""
        _LOGGER.debug("Starting boundary refresh (%s) for %s", boundary, self._name)

        # Immediately update current event using existing event cache.
        # The calendar has sufficient cached event data from periodic coordinator updates
        # to determine that a boundary has passed. Awaiting coordinator refresh here
        # would block sensor updates by 3-10 seconds until the API call completes.
        # The coordinator's normal periodic refresh cycle will fetch fresh data soon.
        await self._update_current_event()
        self.async_write_ha_state()

    def _broadcast_reservation_state(self) -> None:
        """Store the latest reservation state and notify listeners."""
        if not self.hass:
            return

        state = ReservationState(
            current=self._event_to_window(self._current_event),
            upcoming=self._event_to_window(self._next_event),
        )

        self.coordinator.reservation_states[self._unit_id] = state

        async_dispatcher_send(
            self.hass,
            SIGNAL_RESERVATION_STATE,
            self._unit_id,
            state,
        )

    def _event_to_window(self, event: CalendarEvent | None) -> ReservationWindow | None:
        """Convert a CalendarEvent into a ReservationWindow."""
        if not event:
            return None

        window = self._reservation_windows.get(event.uid)
        if window:
            return window

        return ReservationWindow(
            summary=event.summary,
            start=event.start,
            end=event.end,
        )

    def _normalize_time_value(self, time_value: Any) -> str | None:
        """Return a usable time string or None when the value represents midnight."""
        if not isinstance(time_value, str):
            return None

        normalized = time_value.strip()
        if not normalized:
            return None

        try:
            parsed_dt = dt_util.parse_datetime(f"1970-01-01T{normalized}")
        except Exception:  # pragma: no cover - defensive parsing
            return normalized

        if parsed_dt is None:
            return normalized

        if parsed_dt.time() == time(0, 0, 0):
            return None

        return normalized

    @staticmethod
    def _resolve_time(
        reservation_time: str | None,
        property_time: str | None,
        default_time: str,
    ) -> str:
        """Return the first non-falsy time value from the priority chain."""
        return reservation_time or property_time or default_time

    def _apply_timezone(self, dt: datetime, is_all_day: bool) -> datetime:
        """Apply the property timezone (or local fallback) to a naive datetime."""
        if is_all_day:
            return dt
        if self._timezone:
            return dt.replace(tzinfo=None).replace(tzinfo=ZoneInfo(self._timezone))
        return dt_util.as_local(dt)

    def _reservation_to_event(
        self, reservation: dict[str, Any], stay_type: str
    ) -> CalendarEvent | None:
        """Convert a reservation to a calendar event."""
        try:
            attributes = reservation.get("attributes", {})

            # Get start and end dates
            start_date = attributes.get("startDate")
            end_date = attributes.get("endDate")

            if not start_date or not end_date:
                return None

            # Get check-in and check-out times from the reservation or property
            checkin_time = self._normalize_time_value(attributes.get("checkinTime"))
            checkout_time = self._normalize_time_value(attributes.get("checkoutTime"))
            property_checkin_time = self._property_checkin_time
            property_checkout_time = self._property_checkout_time

            # Build datetime strings using first available time source
            checkin_time_resolved = self._resolve_time(
                checkin_time, property_checkin_time, DEFAULT_CHECKIN_TIME
            )
            checkout_time_resolved = self._resolve_time(
                checkout_time, property_checkout_time, DEFAULT_CHECKOUT_TIME
            )
            start_dt_str = f"{start_date}T{checkin_time_resolved}"
            end_dt_str = f"{end_date}T{checkout_time_resolved}"

            # Parse datetime strings
            start_dt = dt_util.parse_datetime(start_dt_str)
            end_dt = dt_util.parse_datetime(end_dt_str)

            if not start_dt or not end_dt:
                return None

            # Apply timezone; skip for all-day events (both sides at midnight)
            is_all_day_start = "T00:00:00" in start_dt_str
            is_all_day_end = "T00:00:00" in end_dt_str

            if is_all_day_start and is_all_day_end:
                _LOGGER.debug(
                    "Creating all-day event for %s from %s to %s",
                    self._name,
                    start_date,
                    end_date,
                )
            else:
                _LOGGER.debug(
                    "Applying %s timezone for %s",
                    self._timezone or "local",
                    self._name,
                )
                start_dt = self._apply_timezone(start_dt, is_all_day_start)
                end_dt = self._apply_timezone(end_dt, is_all_day_end)

            # Get guest/owner information
            first_name = attributes.get("firstName", "")
            last_name = attributes.get("lastName", "")

            # Get owner hold information
            owner_hold = attributes.get("ownerHold")
            hold_type = ""
            hold_who_booked = ""
            hold_note = ""

            if owner_hold:
                hold_type = owner_hold.get("holdType", "")
                hold_who_booked = owner_hold.get("holdWhoBooked", "")
                hold_note = owner_hold.get("holdExternalNote", "")

            # Create summary using the same name resolution as ReservationWindow
            summary_prefix = STAY_TYPE_TO_NAME[stay_type]
            guest_name = self._resolve_guest_name(
                stay_type,
                first_name=first_name,
                last_name=last_name,
                hold_who_booked=hold_who_booked,
                hold_type=hold_type,
            )
            summary = f"{summary_prefix}: {guest_name}" if guest_name else summary_prefix

            # Create description
            description_parts = []

            # Add check-in and check-out information (reuse already-resolved values)
            description_parts.append(f"Check-in: {start_date} {checkin_time_resolved[:5]}")
            description_parts.append(f"Check-out: {end_date} {checkout_time_resolved[:5]}")

            description_parts.append("")

            type_name = STAY_TYPE_TO_NAME.get(stay_type)
            if type_name:
                description_parts.append(f"Type: {type_name}")
            if stay_type == STAY_TYPE_BLOCK and hold_type:
                description_parts.append(f"Block type: {hold_type}")

            if hold_who_booked and stay_type != STAY_TYPE_OWNER:
                description_parts.append(f"Booked by: {hold_who_booked}")

            if hold_note:
                description_parts.append(f"Note: {hold_note}")

            description = "\n".join(description_parts)

            reservation_identifier = reservation.get("id")
            if reservation_identifier is None:
                reservation_identifier = f"{start_date}_{end_date}_{stay_type}"
            else:
                reservation_identifier = str(reservation_identifier)

            # Create the event with datetime objects for start and end
            event = CalendarEvent(
                uid=f"reservation_{reservation_identifier}",
                summary=summary,
                start=start_dt,
                end=end_dt,
                location=self._name,
                description=description,
            )

            window = self._build_reservation_window(
                summary=summary,
                start=start_dt,
                end=end_dt,
                stay_type=stay_type,
                reservation_id=reservation.get("id"),
                guest_count=attributes.get("guestCount"),
                guest_name=guest_name,
            )

            self._reservation_windows[event.uid] = window

            return event
        except Exception as err:
            _LOGGER.error("Error converting reservation to event: %s", err)
            return None

    def _build_reservation_window(
        self,
        *,
        summary: str,
        start: datetime,
        end: datetime,
        stay_type: str,
        reservation_id: str | None,
        guest_count: int | None,
        guest_name: str | None,
    ) -> ReservationWindow:
        """Create a structured reservation window for dispatcher consumers."""
        return ReservationWindow(
            reservation_id=str(reservation_id) if reservation_id is not None else None,
            summary=summary,
            start=start,
            end=end,
            stay_type=stay_type,
            guest_name=guest_name,
            guest_count=guest_count,
        )

    def _resolve_guest_name(
        self,
        stay_type: str,
        *,
        first_name: str | None,
        last_name: str | None,
        hold_who_booked: str | None,
        hold_type: str | None,
    ) -> str | None:
        """Map reservation metadata to a person-friendly label."""
        if stay_type == STAY_TYPE_GUEST:
            parts = [part for part in (first_name, last_name) if part]
            if parts:
                return " ".join(parts)

        if stay_type == STAY_TYPE_OWNER and hold_who_booked:
            return hold_who_booked

        if stay_type in (STAY_TYPE_BLOCK, STAY_TYPE_MAINTENANCE) and hold_type:
            return hold_type

        if hold_who_booked:
            return hold_who_booked

        return None
