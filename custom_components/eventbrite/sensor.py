"""Sensor entities for the Eventbrite integration."""

from __future__ import annotations

from collections.abc import Mapping

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import NO_UPCOMING_EVENTS
from .coordinator import EventbriteCoordinator
from .entity import EventbriteEntity
from .models import event_as_sensor_payload


async def async_setup_entry(  # NOSONAR
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eventbrite sensor entities."""

    coordinator: EventbriteCoordinator = entry.runtime_data
    async_add_entities(
        [
            EventbriteUpcomingEventsSensor(coordinator),
            EventbriteFeaturedEventSensor(coordinator),
        ]
    )


class EventbriteUpcomingEventsSensor(EventbriteEntity, SensorEntity):
    """Sensor exposing a bounded list of upcoming events."""

    _attr_icon = "mdi:calendar-heart-outline"

    def __init__(self, coordinator: EventbriteCoordinator) -> None:
        super().__init__(
            coordinator,
            unique_suffix="upcoming_events",
            name="Upcoming events",
            object_suffix="upcoming_events",
        )

    @property
    def native_value(self) -> int:
        """Return the number of upcoming events."""

        return len(self.coordinator.upcoming_events)

    @property
    def extra_state_attributes(self) -> Mapping[str, object]:
        """Return upcoming event attributes."""

        return {
            "events": [
                event_as_sensor_payload(event)
                for event in self.coordinator.upcoming_events
            ]
        }


class EventbriteFeaturedEventSensor(EventbriteEntity, SensorEntity):
    """Sensor exposing the selected featured event."""

    _attr_icon = "mdi:calendar-star"

    def __init__(self, coordinator: EventbriteCoordinator) -> None:
        super().__init__(
            coordinator,
            unique_suffix="featured_event",
            name="Featured event",
            object_suffix="featured_event",
        )

    @property
    def native_value(self) -> str:
        """Return the featured event title."""

        event = self.coordinator.featured_event
        return event.title if event else NO_UPCOMING_EVENTS

    @property
    def extra_state_attributes(self) -> Mapping[str, object]:
        """Return featured event attributes."""

        event = self.coordinator.featured_event
        if event is None:
            return {}
        return event_as_sensor_payload(event, logo_entity_id=self._logo_entity_id()) | {
            "event_id": event.id
        }

    def _logo_entity_id(self) -> str:
        object_id = self._attr_suggested_object_id
        if object_id is None:
            msg = "Eventbrite logo entity object ID is not initialized"
            raise RuntimeError(msg)
        return f"image.{object_id.replace('featured_event', 'featured_event_logo')}"
