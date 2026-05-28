"""Constants for the Eventbrite integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "eventbrite"

CONF_API_TOKEN = "api_token"  # nosec B105
CONF_COLLECTION_ID = "collection_id"
CONF_EVENT_STATUSES = "event_statuses"
CONF_FILTER_EVENT_NAME_QUERY = "filter_event_name_query"
CONF_MAX_EVENTS = "max_events"
CONF_NAME = "name"
CONF_ORGANIZER_ID = "organizer_id"
CONF_SCAN_INTERVAL_MINUTES = "scan_interval_minutes"
CONF_SEARCH_QUERY = "search_query"

DEFAULT_EVENT_STATUSES = "live,started"
DEFAULT_MAX_EVENTS = 10
DEFAULT_SCAN_INTERVAL_MINUTES = 30

EVENTBRITE_ATTRIBUTION = "Data provided by Eventbrite"

NO_UPCOMING_EVENTS = "No upcoming events"

PLATFORMS = [
    Platform.CALENDAR,
    Platform.SENSOR,
    Platform.SELECT,
    Platform.IMAGE,
]
