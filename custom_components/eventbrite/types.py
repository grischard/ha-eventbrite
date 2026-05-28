"""Shared type aliases for the Eventbrite integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import NotRequired, TypedDict

type EventbriteConfig = Mapping[str, object]
type EventbritePayload = dict[str, object]
type EventbritePayloadMapping = Mapping[str, object]
type EventbriteRequestParams = Mapping[str, str | int]


class EventbriteSensorPayload(TypedDict):
    """Stable Eventbrite event payload exposed in sensor attributes."""

    id: str
    title: str
    starts_at: str
    ends_at: str
    url: str | None
    summary: str | None
    description: str | None
    logo_url: str | None
    venue_name: str | None
    venue_address: str | None
    organiser_name: str | None
    status: str | None
    is_online: bool
    logo_entity_id: NotRequired[str]
    event_id: NotRequired[str]


class EventbriteUpcomingSensorPayload(TypedDict):
    """Compact upcoming-event payload exposed in sensor attributes."""

    id: str
    title: str
    starts_at: str
    ends_at: str
    url: str | None
    venue_name: str | None
    status: str | None
    is_online: bool
