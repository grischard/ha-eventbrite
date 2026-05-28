"""Tests for Eventbrite model normalization."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from custom_components.eventbrite.models import (
    EventbritePayloadError,
    event_as_sensor_payload,
    normalise_eventbrite_event,
)
from custom_components.eventbrite.types import EventbritePayload


def event_payload(**overrides: object) -> EventbritePayload:
    payload: EventbritePayload = {
        "id": "123",
        "name": {"text": "Launch Night"},
        "start": {"utc": "2026-06-01T18:00:00Z"},
        "end": {"utc": "2026-06-01T20:00:00Z"},
        "url": "https://eventbrite.example/events/123",
        "summary": "Short summary",
        "description": {"html": "<p>Full <strong>description</strong></p>"},
        "logo": {
            "url": "https://img.example/logo.png",
            "width": 1200,
            "height": 600,
        },
        "venue": {
            "name": "Main Hall",
            "address": {"localized_address_display": "1 Main St"},
        },
        "organizer": {"name": "Example Org"},
        "status": "live",
        "online_event": False,
        "changed": "2026-05-01T10:00:00Z",
    }
    payload.update(overrides)
    return payload


def test_normalise_eventbrite_event() -> None:
    event = normalise_eventbrite_event(event_payload())

    assert event.id == "123"
    assert event.title == "Launch Night"
    assert event.start == datetime(2026, 6, 1, 18, 0, tzinfo=UTC)
    assert event.end == datetime(2026, 6, 1, 20, 0, tzinfo=UTC)
    assert event.description == "Full description"
    assert event.logo_url == "https://img.example/logo.png"
    assert event.venue_name == "Main Hall"
    assert event.venue_address == "1 Main St"
    assert event.organiser_name == "Example Org"


def test_normalise_prefers_original_logo_url() -> None:
    event = normalise_eventbrite_event(
        event_payload(
            logo={
                "url": "https://img.example/cropped.png",
                "width": 400,
                "height": 400,
                "original": {
                    "url": "https://img.example/original.png",
                    "width": 1200,
                    "height": 600,
                },
            }
        )
    )

    assert event.logo_url == "https://img.example/original.png"


def test_normalise_prefer_html_description_over_text() -> None:
    event = normalise_eventbrite_event(
        event_payload(
            description={
                "text": "Short summary",
                "html": "<p>Full <strong>description</strong></p>",
            }
        )
    )

    assert event.description == "Full description"


def test_event_as_sensor_payload_includes_logo_entity_id() -> None:
    event = normalise_eventbrite_event(event_payload())

    payload = event_as_sensor_payload(
        event, logo_entity_id="image.eventbrite_my_org_featured_event_logo"
    )

    assert payload["id"] == "123"
    assert payload["starts_at"] == "2026-06-01T18:00:00+00:00"
    assert payload["logo_entity_id"] == "image.eventbrite_my_org_featured_event_logo"


def test_normalise_raises_on_bad_dates() -> None:
    with pytest.raises(EventbritePayloadError):
        normalise_eventbrite_event(event_payload(start={"utc": "not-a-date"}))
