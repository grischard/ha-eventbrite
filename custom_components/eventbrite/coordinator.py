"""Coordinator for the Eventbrite integration."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import timedelta
from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    EventbriteApiClient,
    EventbriteAuthError,
    EventbriteError,
    EventbriteRateLimitError,
    EventbriteResponseError,
)
from .const import (
    CONF_EVENT_STATUSES,
    CONF_FILTER_EVENT_NAME_QUERY,
    CONF_MAX_EVENTS,
    CONF_SCAN_INTERVAL_MINUTES,
    DEFAULT_EVENT_STATUSES,
    DEFAULT_MAX_EVENTS,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
)
from .models import EventbriteEvent, EventbritePayloadError, normalise_eventbrite_event
from .types import EventbritePayload

_LOGGER = logging.getLogger(__name__)

DEFAULT_OPTIONS: Final[dict[str, str | bool | int]] = {
    CONF_EVENT_STATUSES: DEFAULT_EVENT_STATUSES,
    CONF_MAX_EVENTS: DEFAULT_MAX_EVENTS,
    CONF_SCAN_INTERVAL_MINUTES: DEFAULT_SCAN_INTERVAL_MINUTES,
}


@dataclass(slots=True, frozen=True)
class EventbriteCoordinatorData:
    """Data shared by all Eventbrite entities."""

    events: tuple[EventbriteEvent, ...]


class EventbriteCoordinator(DataUpdateCoordinator[EventbriteCoordinatorData]):
    """Fetch and normalize Eventbrite events for a config entry."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: EventbriteApiClient,
    ) -> None:
        self.client = client
        self.selected_event_id: str | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=timedelta(
                minutes=max(
                    1,
                    _option_int(config_entry, CONF_SCAN_INTERVAL_MINUTES),
                )
            ),
            always_update=False,
        )

    @property
    def events(self) -> tuple[EventbriteEvent, ...]:
        """Return upcoming events."""

        return self.data.events if self.data else ()

    @property
    def upcoming_events(self) -> tuple[EventbriteEvent, ...]:
        """Return upcoming events."""

        return self.events

    @property
    def featured_event(self) -> EventbriteEvent | None:
        """Return the selected featured event."""

        events = self.events
        if not events:
            return None
        if self.selected_event_id:
            for event in events:
                if event.id == self.selected_event_id:
                    return event
        return events[0]

    async def _async_update_data(self) -> EventbriteCoordinatorData:
        """Fetch all Eventbrite events and normalize them."""

        try:
            payloads = await self.client.async_get_events(
                _entry_config(self.config_entry)
            )
        except EventbriteAuthError as err:
            raise ConfigEntryAuthFailed("Eventbrite authentication failed") from err
        except EventbriteRateLimitError as err:
            message = "Eventbrite rate limit exceeded"
            if err.retry_after:
                message = f"{message}; retry after {err.retry_after} seconds"
            raise UpdateFailed(message) from err
        except EventbriteResponseError as err:
            raise UpdateFailed(f"Error communicating with Eventbrite: {err}") from err
        except EventbriteError as err:
            raise UpdateFailed(f"Unexpected Eventbrite error: {err}") from err

        events = self._normalise_events(payloads)
        if self.selected_event_id not in {event.id for event in events}:
            self.selected_event_id = events[0].id if events else None

        return EventbriteCoordinatorData(events=tuple(events))

    def select_event_id(self, event_id: str | None) -> None:
        """Set the featured event by event ID and publish updated entity state."""

        if event_id and event_id not in {event.id for event in self.events}:
            raise ValueError(f"Unknown Eventbrite event ID: {event_id}")
        self.selected_event_id = event_id
        self.async_set_updated_data(EventbriteCoordinatorData(events=self.events))

    def _normalise_events(
        self, payloads: list[EventbritePayload]
    ) -> list[EventbriteEvent]:
        now = dt_util.utcnow()
        statuses = _configured_statuses(self.config_entry)
        max_events = _option_int(self.config_entry, CONF_MAX_EVENTS)
        title_pattern = _compiled_filter(self.config_entry)

        events: list[EventbriteEvent] = []
        malformed = 0

        for payload in payloads:
            try:
                event = normalise_eventbrite_event(payload)
            except EventbritePayloadError:
                malformed += 1
                _LOGGER.warning("Skipping malformed Eventbrite event payload")
                continue

            if event.end < now:
                continue
            if statuses and event.status and event.status not in statuses:
                continue
            if title_pattern and not title_pattern.search(event.title):
                continue
            events.append(event)

        if malformed and not events and payloads:
            raise UpdateFailed("All Eventbrite event payloads were malformed")

        events.sort(key=lambda event: event.start)
        return events[:max_events]


def _entry_config(config_entry: ConfigEntry) -> dict[str, object]:
    return {**config_entry.data, **config_entry.options}


def _option(config_entry: ConfigEntry, key: str) -> object:
    return config_entry.options.get(
        key, config_entry.data.get(key, DEFAULT_OPTIONS.get(key))
    )


def _option_int(config_entry: ConfigEntry, key: str) -> int:
    value = _option(config_entry, key)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value)
    raise TypeError(f"Expected integer option for {key}")


def _configured_statuses(config_entry: ConfigEntry) -> set[str]:
    statuses = _option(config_entry, CONF_EVENT_STATUSES)
    if isinstance(statuses, str):
        return {status.strip() for status in statuses.split(",") if status.strip()}
    if isinstance(statuses, list):
        return {str(status).strip() for status in statuses if str(status).strip()}
    return set()


def _compiled_filter(config_entry: ConfigEntry) -> re.Pattern[str] | None:
    query = _option(config_entry, CONF_FILTER_EVENT_NAME_QUERY)
    if not isinstance(query, str) or not query:
        return None
    return re.compile(query, re.IGNORECASE)
