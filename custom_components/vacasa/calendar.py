"""Calendar platform for Vacasa integration."""

import logging
from datetime import datetime, timedelta
from functools import partial
from typing import Any, Callable

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import VacasaConfigEntry, VacasaDataUpdateCoordinator
from .api_client import VacasaApiClient
from .const import (
    DOMAIN,
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
        unit_id = unit.get("id")
        attributes = unit.get("attributes", {})
        name = attributes.get("name", f"Vacasa Unit {unit_id}")
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
        self._checkin_time = unit_attributes.get("checkInTime")
        self._checkout_time = unit_attributes.get("checkOutTime")
        self._timezone = unit_attributes.get("timezone")
        self._event_cache: dict[str, list[CalendarEvent]] = {}
        self._reservation_windows: dict[str, ReservationWindow] = {}
        self._current_event: CalendarEvent | None = None
        self._next_event: CalendarEvent | None = None
        self._unsubscribe_start_timer: Callable[[], None] | None = None
        self._unsubscribe_end_timer: Callable[[], None] | None = None

        # Entity properties
        self._attr_unique_id = f"vacasa_calendar_{unit_id}"
        self._attr_name = f"Vacasa {name}"

        # Set device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, unit_id)},
            "name": f"Vacasa {name}",
            "manufacturer": "Vacasa",
            "model": "Vacation Rental",
            "sw_version": "1.0",
        }

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
        state = "on" if self._current_event is not None else "off"
        _LOGGER.debug(
            "Calendar %s state: %s (current_event: %s)",
            self._name,
            state,
            self._current_event.summary if self._current_event else "None",
        )
        return state

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
        self._schedule_boundary_timers()
        self._broadcast_reservation_state()

    async def async_get_current_event(self) -> CalendarEvent | None:
        """Get the current event if active right now, otherwise None."""
        if self._current_event is None and self._next_event is None:
            self._current_event, self._next_event = await self._determine_current_and_next_events()
            self._schedule_boundary_timers()
            self._broadcast_reservation_state()
        return self._current_event

    async def async_get_next_event(self) -> CalendarEvent | None:
        """Get the next upcoming event (for display purposes)."""
        if self._current_event is None and self._next_event is None:
            self._current_event, self._next_event = await self._determine_current_and_next_events()
            self._schedule_boundary_timers()
            self._broadcast_reservation_state()
        if self._current_event:
            return self._current_event
        return self._next_event

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
        # Query from 60 days ago to catch any currently active reservations that started in the past
        # but are still in progress (e.g., guest checking out today but checked in weeks ago)
        start_date = now_local - timedelta(days=60)
        end_date = now_local + timedelta(days=365)
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
            if value is None:
                return None
            return dt_util.as_utc(value)

        for event in sorted(events, key=lambda evt: _as_utc(evt.start) or now_utc):
            start_utc = _as_utc(event.start)
            end_utc = _as_utc(event.end)

            if start_utc is None or end_utc is None:
                continue

            in_progress = start_utc <= now_utc < end_utc
            upcoming = start_utc > now_utc

            # Enhanced debug logging to diagnose timing issues
            _LOGGER.debug(
                "Event %s: start=%s, end=%s, now=%s, in_progress=%s, upcoming=%s",
                event.summary,
                start_utc.isoformat(),
                end_utc.isoformat(),
                now_utc.isoformat(),
                in_progress,
                upcoming,
            )
            _LOGGER.debug(
                "  Comparison details: start_utc_ts=%s, end_utc_ts=%s, now_utc_ts=%s",
                start_utc.timestamp(),
                end_utc.timestamp(),
                now_utc.timestamp(),
            )
            _LOGGER.debug(
                "  Original event times: start=%s (tzinfo=%s), end=%s (tzinfo=%s)",
                event.start.isoformat() if event.start else "None",
                event.start.tzinfo if event.start else "None",
                event.end.isoformat() if event.end else "None",
                event.end.tzinfo if event.end else "None",
            )
            _LOGGER.debug(
                "  Boolean checks: (start_utc <= now_utc)=%s, (now_utc < end_utc)=%s",
                start_utc <= now_utc,
                now_utc < end_utc,
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
                _LOGGER.warning(
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
                _LOGGER.warning(
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
        """Handle a scheduled reservation boundary timer.

        This callback is executed on a worker thread by Home Assistant's timer system,
        so we must use call_soon_threadsafe to schedule work on the event loop.
        """
        if not self.hass:
            return

        _LOGGER.warning(
            "BOUNDARY TIMER (%s) FIRED for %s! Scheduled: %s, Actual: %s",
            boundary,
            self._name,
            scheduled_time.isoformat(),
            dt_util.utcnow().isoformat(),
        )

        # Schedule dispatcher send on event loop thread
        self.hass.loop.call_soon_threadsafe(
            async_dispatcher_send,
            self.hass,
            SIGNAL_RESERVATION_BOUNDARY,
            self._unit_id,
            boundary,
        )

        # Schedule boundary refresh on event loop thread
        self.hass.loop.call_soon_threadsafe(
            lambda: self.hass.async_create_task(self._boundary_refresh(boundary))
        )

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

        if (
            parsed_dt.hour == 0
            and parsed_dt.minute == 0
            and parsed_dt.second == 0
            and parsed_dt.microsecond == 0
        ):
            return None

        return normalized

    def _reservation_to_event(  # noqa: C901
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
            property_checkin_time = self._normalize_time_value(self._checkin_time)
            property_checkout_time = self._normalize_time_value(self._checkout_time)

            # Create datetime objects based on available information
            if checkin_time:
                # Use time from reservation
                start_dt_str = f"{start_date}T{checkin_time}"
            elif property_checkin_time:
                # Use property-specific time
                start_dt_str = f"{start_date}T{property_checkin_time}"
            else:
                # No time available, default to 4:00 PM (16:00)
                start_dt_str = f"{start_date}T16:00:00"

            if checkout_time:
                # Use time from reservation
                end_dt_str = f"{end_date}T{checkout_time}"
            elif property_checkout_time:
                # Use property-specific time
                end_dt_str = f"{end_date}T{property_checkout_time}"
            else:
                # No time available, default to 10:00 AM (10:00)
                end_dt_str = f"{end_date}T10:00:00"

            # Parse datetime strings
            start_dt = dt_util.parse_datetime(start_dt_str)
            end_dt = dt_util.parse_datetime(end_dt_str)

            if not start_dt or not end_dt:
                return None

            # Handle timezone properly
            # For all-day events (no specific time), don't apply timezone
            is_all_day_start = "T00:00:00" in start_dt_str
            is_all_day_end = "T00:00:00" in end_dt_str

            if is_all_day_start and is_all_day_end:
                # This is an all-day event
                _LOGGER.debug(
                    "Creating all-day event for %s from %s to %s",
                    self._name,
                    start_date,
                    end_date,
                )
                # No timezone needed for all-day events
            else:
                # This is a timed event, apply timezone
                if self._timezone:
                    from zoneinfo import ZoneInfo

                    try:
                        tz = ZoneInfo(self._timezone)
                        _LOGGER.debug("Using property timezone: %s", self._timezone)

                        # Create timezone-aware datetime objects
                        if not is_all_day_start:
                            # Use replace with zoneinfo to handle DST correctly
                            naive_start = start_dt.replace(tzinfo=None)
                            start_dt = naive_start.replace(tzinfo=tz)
                            _LOGGER.debug("Start time with TZ: %s", start_dt)

                        if not is_all_day_end:
                            # Use replace with zoneinfo to handle DST correctly
                            naive_end = end_dt.replace(tzinfo=None)
                            end_dt = naive_end.replace(tzinfo=tz)
                            _LOGGER.debug("End time with TZ: %s", end_dt)
                    except Exception as e:
                        _LOGGER.warning("Error applying timezone %s: %s", self._timezone, e)
                        # Fall back to local timezone
                        if not is_all_day_start:
                            start_dt = dt_util.as_local(start_dt)
                        if not is_all_day_end:
                            end_dt = dt_util.as_local(end_dt)
                else:
                    # No property timezone, use local timezone
                    _LOGGER.debug("No property timezone, using local timezone")
                    if not is_all_day_start:
                        start_dt = dt_util.as_local(start_dt)
                    if not is_all_day_end:
                        end_dt = dt_util.as_local(end_dt)

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

            # Create summary based on stay type
            summary_prefix = STAY_TYPE_TO_NAME[stay_type]

            if stay_type == STAY_TYPE_GUEST and first_name and last_name:
                summary = f"{summary_prefix}: {first_name} {last_name}"
            elif stay_type == STAY_TYPE_OWNER and hold_who_booked:
                summary = f"{summary_prefix}: {hold_who_booked}"
            elif hold_type:
                summary = f"{summary_prefix}: {hold_type}"
            else:
                summary = summary_prefix

            # Create description
            description_parts = []

            # Add check-in and check-out information
            if checkin_time and checkin_time != "00:00:00":
                description_parts.append(f"Check-in: {start_date} {checkin_time[:5]}")
            elif self._checkin_time:
                description_parts.append(f"Check-in: {start_date} {self._checkin_time[:5]}")
            else:
                description_parts.append(f"Check-in: {start_date} 16:00")

            if checkout_time and checkout_time != "00:00:00":
                description_parts.append(f"Check-out: {end_date} {checkout_time[:5]}")
            elif self._checkout_time:
                description_parts.append(f"Check-out: {end_date} {self._checkout_time[:5]}")
            else:
                description_parts.append(f"Check-out: {end_date} 10:00")

            description_parts.append("")

            if stay_type == STAY_TYPE_GUEST:
                description_parts.append("Type: Guest booking")
            elif stay_type == STAY_TYPE_OWNER:
                description_parts.append("Type: Owner stay")
            elif stay_type == STAY_TYPE_MAINTENANCE:
                description_parts.append("Type: Maintenance")
            elif stay_type == STAY_TYPE_BLOCK:
                description_parts.append("Type: Block")
                if hold_type:
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
                first_name=first_name,
                last_name=last_name,
                hold_who_booked=hold_who_booked,
                hold_type=hold_type,
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
        first_name: str | None,
        last_name: str | None,
        hold_who_booked: str | None,
        hold_type: str | None,
    ) -> ReservationWindow:
        """Create a structured reservation window for dispatcher consumers."""
        guest_name = self._resolve_guest_name(
            stay_type,
            first_name=first_name,
            last_name=last_name,
            hold_who_booked=hold_who_booked,
            hold_type=hold_type,
        )

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
