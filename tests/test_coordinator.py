"""Tests for Eventbrite coordinator normalization behavior."""

from __future__ import annotations

from types import SimpleNamespace

from custom_components.eventbrite.const import (
    CONF_EVENT_STATUSES,
    CONF_FILTER_EVENT_NAME_QUERY,
    CONF_MAX_EVENTS,
)
from custom_components.eventbrite.coordinator import EventbriteCoordinator
from custom_components.eventbrite.types import EventbritePayload


def payload(
    event_id: str,
    title: str,
    start: str,
    status: str = "live",
) -> EventbritePayload:
    return {
        "id": event_id,
        "name": {"text": title},
        "start": {"utc": start},
        "end": {"utc": start.replace("10:00:00Z", "12:00:00Z")},
        "status": status,
    }


def test_coordinator_normalises_sorts_filters_and_caps() -> None:
    coordinator = EventbriteCoordinator.__new__(EventbriteCoordinator)
    coordinator.config_entry = SimpleNamespace(
        data={
            CONF_EVENT_STATUSES: "live,started",
            CONF_MAX_EVENTS: 2,
            CONF_FILTER_EVENT_NAME_QUERY: "night|morning",
        },
        options={},
    )

    events = coordinator._normalise_events(
        [
            payload("3", "Filtered Afternoon", "2030-01-03T10:00:00Z"),
            payload("2", "Morning Session", "2030-01-02T10:00:00Z"),
            payload("1", "Opening Night", "2030-01-01T10:00:00Z"),
            payload("4", "Cancelled Night", "2030-01-04T10:00:00Z", "cancelled"),
        ]
    )

    assert [event.id for event in events] == ["1", "2"]


def test_coordinator_skips_malformed_event_when_others_are_valid() -> None:
    coordinator = EventbriteCoordinator.__new__(EventbriteCoordinator)
    coordinator.config_entry = SimpleNamespace(
        data={CONF_EVENT_STATUSES: "live", CONF_MAX_EVENTS: 10},
        options={},
    )

    events = coordinator._normalise_events(
        [
            {"id": "bad", "name": {"text": "Bad"}},
            payload("good", "Good Event", "2030-01-01T10:00:00Z"),
        ]
    )

    assert [event.id for event in events] == ["good"]
