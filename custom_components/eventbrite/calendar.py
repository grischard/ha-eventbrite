"""Calendar entity for Eventbrite events."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import EventbriteCoordinator
from .entity import EventbriteEntity
from .models import EventbriteEvent


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eventbrite calendar entity."""

    coordinator: EventbriteCoordinator = entry.runtime_data
    async_add_entities([EventbriteCalendar(coordinator)])


class EventbriteCalendar(EventbriteEntity, CalendarEntity):
    """Calendar containing Eventbrite events."""

    def __init__(self, coordinator: EventbriteCoordinator) -> None:
        super().__init__(
            coordinator,
            unique_suffix="calendar",
            name=None,
            object_suffix=None,
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""

        if not self.coordinator.upcoming_events:
            return None
        return _calendar_event(self.coordinator.upcoming_events[0])

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return events overlapping the requested date range."""

        return [
            _calendar_event(event)
            for event in self.coordinator.upcoming_events
            if event.start < end_date and event.end > start_date
        ]


def _calendar_event(event: EventbriteEvent) -> CalendarEvent:
    description_parts = [part for part in (event.summary, event.url) if part]
    return CalendarEvent(
        uid=event.id,
        summary=event.title,
        start=event.start,
        end=event.end,
        location=event.venue_name or event.venue_address,
        description="\n\n".join(description_parts) or None,
    )
