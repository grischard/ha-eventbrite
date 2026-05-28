"""Integration setup tests for Eventbrite."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eventbrite.const import (
    CONF_API_TOKEN,
    CONF_EVENT_STATUSES,
    CONF_MAX_EVENTS,
    CONF_NAME,
    CONF_ORGANIZER_ID,
    CONF_SCAN_INTERVAL_MINUTES,
    DOMAIN,
)
from custom_components.eventbrite.types import EventbritePayload

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


def assert_entity_state(
    hass: HomeAssistant,
    entity_id: str,
    expected_state: str,
) -> None:
    """Assert an entity exists and has the expected state."""

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == expected_state


def setup_payload(
    event_id: str,
    title: str,
    start: str,
    end: str,
) -> EventbritePayload:
    """Return a normalized Eventbrite-like API payload for setup tests."""

    return {
        "id": event_id,
        "name": {"text": title},
        "start": {"utc": start},
        "end": {"utc": end},
        "url": f"https://eventbrite.example/events/{event_id}",
        "summary": f"{title} summary",
        "description": {"text": f"{title} description"},
        "logo": {
            "url": f"https://img.example/{event_id}.png",
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


async def test_setup_entry_creates_entities_and_unloads(
    hass: HomeAssistant,
) -> None:
    """Set up all Eventbrite platforms with mocked API data."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="My Org",
        unique_id="eventbrite_organizer_52408308",
        data={
            CONF_NAME: "My Org",
            CONF_API_TOKEN: "token",
            CONF_ORGANIZER_ID: "52408308",
            CONF_EVENT_STATUSES: "live",
            CONF_MAX_EVENTS: 10,
            CONF_SCAN_INTERVAL_MINUTES: 30,
        },
    )
    entry.add_to_hass(hass)

    api_client = AsyncMock()
    api_client.async_get_events.return_value = [
        setup_payload(
            "2",
            "Second Event",
            "2030-01-02T18:00:00Z",
            "2030-01-02T20:00:00Z",
        ),
        setup_payload(
            "1",
            "First Event",
            "2030-01-01T18:00:00Z",
            "2030-01-01T20:00:00Z",
        ),
    ]
    api_client.async_get_logo_bytes.return_value = b"logo"

    with patch(
        "custom_components.eventbrite.EventbriteApiClient.from_hass",
        return_value=api_client,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    upcoming = hass.states.get("sensor.eventbrite_my_org_upcoming_events")
    featured = hass.states.get("sensor.eventbrite_my_org_featured_event")
    display = hass.states.get("select.eventbrite_my_org_display_event")
    calendar = hass.states.get("calendar.eventbrite_my_org")
    image = hass.states.get("image.eventbrite_my_org_featured_event_logo")

    assert upcoming is not None
    assert upcoming.state == "2"
    assert upcoming.attributes["events"][0]["id"] == "1"
    assert upcoming.attributes["events"][1]["id"] == "2"

    assert featured is not None
    assert featured.state == "First Event"
    assert featured.attributes["event_id"] == "1"
    assert (
        featured.attributes["logo_entity_id"]
        == "image.eventbrite_my_org_featured_event_logo"
    )

    assert display is not None
    assert display.state.startswith("1 · First Event ·")

    assert calendar is not None
    assert image is not None

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert_entity_state(
        hass,
        "sensor.eventbrite_my_org_upcoming_events",
        STATE_UNAVAILABLE,
    )
    assert_entity_state(
        hass,
        "sensor.eventbrite_my_org_featured_event",
        STATE_UNAVAILABLE,
    )
    assert_entity_state(
        hass,
        "select.eventbrite_my_org_display_event",
        STATE_UNAVAILABLE,
    )
    assert_entity_state(hass, "calendar.eventbrite_my_org", STATE_UNAVAILABLE)
    assert_entity_state(
        hass,
        "image.eventbrite_my_org_featured_event_logo",
        STATE_UNAVAILABLE,
    )
