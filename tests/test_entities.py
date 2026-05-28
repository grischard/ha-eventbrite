"""Tests for Eventbrite entity helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest
from homeassistant.util import dt as dt_util

from custom_components.eventbrite.calendar import _calendar_event
from custom_components.eventbrite.image import (
    EventbriteFeaturedLogoImage,
    _content_type_from_url,
)
from custom_components.eventbrite.models import EventbriteEvent
from custom_components.eventbrite.select import _event_label
from custom_components.eventbrite.sensor import EventbriteUpcomingEventsSensor


def make_event(
    event_id: str = "1",
    logo_url: str | None = "https://img.example/logo.png",
) -> EventbriteEvent:
    return EventbriteEvent(
        id=event_id,
        title="Opening Night",
        start=datetime(2030, 1, 1, 19, 0, tzinfo=UTC),
        end=datetime(2030, 1, 1, 21, 0, tzinfo=UTC),
        url="https://eventbrite.example/events/1",
        description="Description",
        summary="Summary",
        logo_url=logo_url,
        logo_width=1200,
        logo_height=600,
        venue_name="Main Hall",
        venue_address="1 Main St",
        organiser_name="Example Org",
        status="live",
        is_online=False,
        updated_at=None,
    )


def test_calendar_event_uses_standard_fields_only() -> None:
    calendar_event = _calendar_event(make_event())

    assert calendar_event.uid == "1"
    assert calendar_event.summary == "Opening Night"
    assert calendar_event.location == "Main Hall"
    assert calendar_event.description is not None
    assert "https://eventbrite.example/events/1" in calendar_event.description


def test_select_label_is_compact() -> None:
    try:
        dt_util.set_default_time_zone(ZoneInfo("America/New_York"))

        label = _event_label(1, make_event())

        assert label == "1 · Opening Night · Tue 2:00 PM"
    finally:
        dt_util.set_default_time_zone(UTC)


def test_upcoming_sensor_uses_compact_local_time_payload() -> None:
    try:
        dt_util.set_default_time_zone(ZoneInfo("America/New_York"))
        sensor = EventbriteUpcomingEventsSensor.__new__(EventbriteUpcomingEventsSensor)
        sensor.coordinator = SimpleNamespace(upcoming_events=(make_event(),))

        attributes = sensor.extra_state_attributes
        events = attributes["events"]

        assert isinstance(events, list)
        assert events == [
            {
                "id": "1",
                "title": "Opening Night",
                "starts_at": "2030-01-01T14:00:00-05:00",
                "ends_at": "2030-01-01T16:00:00-05:00",
                "url": "https://eventbrite.example/events/1",
                "venue_name": "Main Hall",
                "status": "live",
                "is_online": False,
            }
        ]
    finally:
        dt_util.set_default_time_zone(UTC)


def test_content_type_from_url() -> None:
    assert (
        _content_type_from_url("https://img.example/logo.PNG?width=600") == "image/png"
    )
    assert _content_type_from_url("https://img.example/logo.jpg") == "image/jpeg"
    assert (
        _content_type_from_url("https://img.example/logo") == "application/octet-stream"
    )


@pytest.mark.asyncio
async def test_image_entity_fetches_and_caches_logo_bytes() -> None:
    image = EventbriteFeaturedLogoImage.__new__(EventbriteFeaturedLogoImage)
    image.coordinator = SimpleNamespace(
        featured_event=make_event(),
        client=SimpleNamespace(async_get_logo_bytes=AsyncMock(return_value=b"logo")),
    )
    image._cached_logo_key = None
    image._cached_logo_bytes = None

    assert await image.async_image() == b"logo"
    assert await image.async_image() == b"logo"
    image.coordinator.client.async_get_logo_bytes.assert_awaited_once()


@pytest.mark.asyncio
async def test_image_entity_returns_none_without_logo() -> None:
    image = EventbriteFeaturedLogoImage.__new__(EventbriteFeaturedLogoImage)
    image.coordinator = SimpleNamespace(
        featured_event=make_event(logo_url=None),
        client=SimpleNamespace(async_get_logo_bytes=AsyncMock()),
    )
    image._cached_logo_key = None
    image._cached_logo_bytes = None

    assert await image.async_image() is None


@pytest.mark.asyncio
async def test_image_entity_handles_unexpected_logo_fetch_errors() -> None:
    image = EventbriteFeaturedLogoImage.__new__(EventbriteFeaturedLogoImage)
    image.coordinator = SimpleNamespace(
        featured_event=make_event(),
        client=SimpleNamespace(
            async_get_logo_bytes=AsyncMock(side_effect=ValueError("bad url"))
        ),
    )
    image._cached_logo_key = None
    image._cached_logo_bytes = None

    assert await image.async_image() is None
