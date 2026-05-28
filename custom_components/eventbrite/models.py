"""Eventbrite payload models and normalization helpers."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape
from typing import cast

from .types import (
    EventbritePayloadMapping,
    EventbriteSensorPayload,
    EventbriteUpcomingSensorPayload,
)


@dataclass(slots=True, frozen=True)
class EventbriteEvent:
    """Normalized Eventbrite event data used internally by the integration."""

    id: str
    title: str
    start: datetime
    end: datetime
    url: str | None
    description: str | None
    summary: str | None
    logo_url: str | None
    logo_width: int | None
    logo_height: int | None
    venue_name: str | None
    venue_address: str | None
    organiser_name: str | None
    status: str | None
    is_online: bool
    updated_at: datetime | None


class EventbritePayloadError(ValueError):
    """Raised when an Eventbrite payload cannot be normalized."""


def normalise_eventbrite_event(
    payload: EventbritePayloadMapping,
) -> EventbriteEvent:
    """Normalize an Eventbrite event API payload."""

    event_id = _required_str(payload, "id")
    title = _localized_text(payload.get("name")) or event_id
    start = _parse_event_datetime(payload.get("start"), "start")
    end = _parse_event_datetime(payload.get("end"), "end")

    description = _localized_text(payload.get("description"))
    summary = _clean_text(payload.get("summary"))

    logo = payload.get("logo")
    logo = _as_mapping(logo)

    venue = payload.get("venue")
    venue = _as_mapping(venue)

    address = _as_mapping(venue.get("address"))

    organizer = payload.get("organizer") or payload.get("organiser")
    organizer = _as_mapping(organizer)
    logo_original = _as_mapping(logo.get("original"))

    return EventbriteEvent(
        id=event_id,
        title=title,
        start=start,
        end=end,
        url=_optional_str(payload.get("url")),
        description=description,
        summary=summary,
        logo_url=_optional_str(logo.get("url") or logo_original.get("url")),
        logo_width=_optional_int(logo.get("width") or logo_original.get("width")),
        logo_height=_optional_int(logo.get("height") or logo_original.get("height")),
        venue_name=_optional_str(venue.get("name")),
        venue_address=_venue_address(address),
        organiser_name=_optional_str(organizer.get("name")),
        status=_optional_str(payload.get("status")),
        is_online=bool(payload.get("online_event", False)),
        updated_at=_parse_optional_datetime(payload.get("changed")),
    )


def event_as_sensor_payload(
    event: EventbriteEvent,
    *,
    logo_entity_id: str | None = None,
    localise_datetime: Callable[[datetime], datetime] | None = None,
) -> EventbriteSensorPayload:
    """Return a stable JSON-like payload for sensor attributes."""

    payload: EventbriteSensorPayload = {
        "id": event.id,
        "title": event.title,
        "starts_at": _serialise_datetime(event.start, localise_datetime),
        "ends_at": _serialise_datetime(event.end, localise_datetime),
        "url": event.url,
        "summary": event.summary,
        "description": event.description,
        "logo_url": event.logo_url,
        "venue_name": event.venue_name,
        "venue_address": event.venue_address,
        "organiser_name": event.organiser_name,
        "status": event.status,
        "is_online": event.is_online,
    }
    if logo_entity_id is not None:
        payload["logo_entity_id"] = logo_entity_id
    return payload


def event_as_upcoming_sensor_payload(
    event: EventbriteEvent,
    *,
    localise_datetime: Callable[[datetime], datetime] | None = None,
) -> EventbriteUpcomingSensorPayload:
    """Return a compact upcoming-event payload for recorder-safe attributes."""

    return {
        "id": event.id,
        "title": event.title,
        "starts_at": _serialise_datetime(event.start, localise_datetime),
        "ends_at": _serialise_datetime(event.end, localise_datetime),
        "url": event.url,
        "venue_name": event.venue_name,
        "status": event.status,
        "is_online": event.is_online,
    }


def _serialise_datetime(
    value: datetime,
    localise_datetime: Callable[[datetime], datetime] | None,
) -> str:
    if localise_datetime is not None:
        value = localise_datetime(value)
    return value.isoformat()


def _required_str(payload: EventbritePayloadMapping, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise EventbritePayloadError(f"Missing required Eventbrite event field: {key}")
    return value


def _optional_str(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _optional_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _localized_text(value: object) -> str | None:
    if isinstance(value, str):
        return _clean_text(value)
    if not isinstance(value, Mapping):
        return None
    mapping = _as_mapping(value)
    html = mapping.get("html")
    if isinstance(html, str) and html:
        return _clean_text(html)
    return _clean_text(mapping.get("text"))


def _clean_text(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    text = re.sub(r"<[^>]+>", " ", value)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _parse_event_datetime(value: object, field: str) -> datetime:
    if not isinstance(value, Mapping):
        raise EventbritePayloadError(f"Missing Eventbrite {field} datetime")

    mapping = _as_mapping(value)
    parsed = _parse_optional_datetime(mapping.get("utc") or mapping.get("local"))
    if parsed is None:
        raise EventbritePayloadError(f"Malformed Eventbrite {field} datetime")
    return parsed


def _parse_optional_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as err:
        raise EventbritePayloadError(f"Malformed Eventbrite datetime: {value}") from err
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _venue_address(address: EventbritePayloadMapping) -> str | None:
    localized = _optional_str(address.get("localized_address_display"))
    if localized:
        return localized

    multi_line = address.get("localized_multi_line_address_display")
    if isinstance(multi_line, list):
        lines = [line for line in multi_line if isinstance(line, str) and line]
        if lines:
            return ", ".join(lines)

    parts = [
        address.get("address_1"),
        address.get("city"),
        address.get("region"),
        address.get("postal_code"),
        address.get("country"),
    ]
    compact_parts = [part for part in parts if isinstance(part, str) and part]
    if compact_parts:
        return ", ".join(compact_parts)
    return None


def _as_mapping(value: object) -> EventbritePayloadMapping:
    if isinstance(value, Mapping):
        return cast(EventbritePayloadMapping, value)
    return {}
