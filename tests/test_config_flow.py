"""Tests for the Eventbrite config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.eventbrite.api import EventbriteAuthError
from custom_components.eventbrite.const import (
    CONF_API_TOKEN,
    CONF_ORGANIZER_ID,
    DEFAULT_EVENT_STATUSES,
    DEFAULT_MAX_EVENTS,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
)

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


async def test_config_flow_success(hass: HomeAssistant) -> None:
    user_input = {
        "name": "My Org",
        CONF_API_TOKEN: "token",
        CONF_ORGANIZER_ID: "org-1",
        "collection_id": "",
        "search_query": "",
        "event_statuses": DEFAULT_EVENT_STATUSES,
        "max_events": float(DEFAULT_MAX_EVENTS),
        "scan_interval_minutes": float(DEFAULT_SCAN_INTERVAL_MINUTES),
        "filter_event_name_query": "",
    }

    with patch(
        "custom_components.eventbrite.config_flow.EventbriteApiClient.from_hass"
    ) as from_hass:
        from_hass.return_value.async_validate_token = AsyncMock()
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}, data=user_input
        )

    assert result["type"] == "create_entry"
    assert result["title"] == "My Org"
    assert result["data"][CONF_ORGANIZER_ID] == "org-1"
    assert result["data"]["max_events"] == DEFAULT_MAX_EVENTS
    assert result["data"]["scan_interval_minutes"] == DEFAULT_SCAN_INTERVAL_MINUTES


async def test_config_flow_requires_source(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
        data={
            "name": "My Org",
            CONF_API_TOKEN: "token",
            CONF_ORGANIZER_ID: "",
            "collection_id": "",
            "search_query": "",
            "event_statuses": DEFAULT_EVENT_STATUSES,
            "max_events": DEFAULT_MAX_EVENTS,
            "scan_interval_minutes": DEFAULT_SCAN_INTERVAL_MINUTES,
            "filter_event_name_query": "",
        },
    )

    assert result["type"] == "form"
    errors = result["errors"]
    assert errors is not None
    assert errors["base"] == "source_required"


async def test_config_flow_invalid_token(hass: HomeAssistant) -> None:
    user_input = {
        "name": "My Org",
        CONF_API_TOKEN: "token",
        CONF_ORGANIZER_ID: "org-1",
        "collection_id": "",
        "search_query": "",
        "event_statuses": DEFAULT_EVENT_STATUSES,
        "max_events": DEFAULT_MAX_EVENTS,
        "scan_interval_minutes": DEFAULT_SCAN_INTERVAL_MINUTES,
        "filter_event_name_query": "",
    }

    with patch(
        "custom_components.eventbrite.config_flow.EventbriteApiClient.from_hass"
    ) as from_hass:
        from_hass.return_value.async_validate_token = AsyncMock(
            side_effect=EventbriteAuthError
        )
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}, data=user_input
        )

    assert result["type"] == "form"
    errors = result["errors"]
    assert errors is not None
    assert errors["base"] == "invalid_auth"
