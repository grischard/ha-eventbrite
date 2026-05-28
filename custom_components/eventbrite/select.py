"""Select entity for choosing the featured Eventbrite event."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import NO_UPCOMING_EVENTS
from .coordinator import EventbriteCoordinator
from .entity import EventbriteEntity
from .models import EventbriteEvent


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eventbrite select entities."""

    coordinator: EventbriteCoordinator = entry.runtime_data
    async_add_entities([EventbriteDisplayEventSelect(coordinator)])


class EventbriteDisplayEventSelect(EventbriteEntity, SelectEntity):
    """Select entity that controls which event is featured."""

    _attr_icon = "mdi:calendar-cursor"

    def __init__(self, coordinator: EventbriteCoordinator) -> None:
        super().__init__(
            coordinator,
            unique_suffix="display_event",
            name="Display event",
            object_suffix="display_event",
        )

    @property
    def options(self) -> list[str]:
        """Return event labels."""

        events = self.coordinator.upcoming_events
        if not events:
            return [NO_UPCOMING_EVENTS]
        return [
            _event_label(index, event) for index, event in enumerate(events, start=1)
        ]

    @property
    def current_option(self) -> str | None:
        """Return the current featured event option."""

        event = self.coordinator.featured_event
        if event is None:
            return NO_UPCOMING_EVENTS
        events = self.coordinator.upcoming_events
        for index, candidate in enumerate(events, start=1):
            if candidate.id == event.id:
                return _event_label(index, candidate)
        return None

    async def async_select_option(self, option: str) -> None:
        """Select an event option."""

        if option == NO_UPCOMING_EVENTS and not self.coordinator.upcoming_events:
            return

        for index, event in enumerate(self.coordinator.upcoming_events, start=1):
            if option == _event_label(index, event):
                self.coordinator.select_event_id(event.id)
                return

        raise HomeAssistantError(f"Unknown Eventbrite display event option: {option}")


def _event_label(index: int, event: EventbriteEvent) -> str:
    starts_at = dt_util.as_local(event.start).strftime("%a %-I:%M %p")
    return f"{index} · {event.title} · {starts_at}"
