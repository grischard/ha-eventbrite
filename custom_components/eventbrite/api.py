"""Async Eventbrite API client."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import cast

from aiohttp import ClientError, ClientResponse, ClientSession
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_COLLECTION_ID,
    CONF_EVENT_STATUSES,
    CONF_ORGANIZER_ID,
    CONF_SEARCH_QUERY,
    DEFAULT_EVENT_STATUSES,
)
from .types import EventbriteConfig, EventbritePayload, EventbriteRequestParams

API_BASE_URL = "https://www.eventbriteapi.com/v3"
DEFAULT_EXPANSIONS = "venue,organizer,logo"
REQUEST_TIMEOUT = 20


class EventbriteError(Exception):
    """Base Eventbrite API error."""


class EventbriteAuthError(EventbriteError):
    """Raised when Eventbrite rejects the token or permissions."""


class EventbriteRateLimitError(EventbriteError):
    """Raised when Eventbrite rate limits a request."""

    def __init__(self, retry_after: int | None = None) -> None:
        super().__init__("Eventbrite API rate limit exceeded")
        self.retry_after = retry_after


class EventbriteResponseError(EventbriteError):
    """Raised for non-auth Eventbrite API failures."""


@dataclass(slots=True)
class EventbriteApiClient:
    """Small async client for Eventbrite API access."""

    session: ClientSession
    api_token: str

    @classmethod
    def from_hass(cls, hass: HomeAssistant, api_token: str) -> EventbriteApiClient:
        """Create a client using Home Assistant's shared aiohttp session."""

        return cls(async_get_clientsession(hass), api_token)

    async def async_validate_token(self) -> None:
        """Validate the configured token with a minimal API request."""

        await self._request_json("GET", "/users/me/")

    async def async_get_events(
        self,
        config: EventbriteConfig,
        *,
        max_pages: int = 10,
    ) -> list[EventbritePayload]:
        """Fetch Eventbrite events for the configured source."""

        path = self._events_path(config)
        params: dict[str, str | int] = {
            "expand": DEFAULT_EXPANSIONS,
            "status": str(config.get(CONF_EVENT_STATUSES) or DEFAULT_EVENT_STATUSES),
        }
        if search_query := config.get(CONF_SEARCH_QUERY):
            params["q"] = str(search_query)

        events: list[EventbritePayload] = []
        page = 1
        continuation: str | None = None

        while page <= max_pages:
            page_params = dict(params)
            page_params["page"] = page
            if continuation:
                page_params["continuation"] = continuation

            payload = await self._request_json("GET", path, params=page_params)
            page_events = payload.get("events")
            if not isinstance(page_events, list):
                raise EventbriteResponseError(
                    "Eventbrite response did not include events"
                )
            events.extend(
                event
                for page_event in page_events
                if (event := _payload_with_str_keys(page_event)) is not None
            )

            pagination = _payload_with_str_keys(payload.get("pagination"))
            if pagination is None:
                break
            next_continuation = pagination.get("continuation")
            continuation = (
                next_continuation if isinstance(next_continuation, str) else None
            )
            has_more = bool(pagination.get("has_more_items"))
            page_count = pagination.get("page_count")
            if not has_more and (not isinstance(page_count, int) or page >= page_count):
                break
            page += 1

        return events

    async def async_get_logo_bytes(self, url: str) -> bytes:
        """Fetch logo image bytes from Eventbrite's CDN."""

        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                response = await self.session.get(url)
        except (TimeoutError, ClientError) as err:
            raise EventbriteResponseError("Unable to fetch Eventbrite logo") from err

        async with response:
            await self._raise_for_response(response)
            return await response.read()

    def _events_path(self, config: EventbriteConfig) -> str:
        if organizer_id := config.get(CONF_ORGANIZER_ID):
            return f"/organizers/{organizer_id}/events/"
        if collection_id := config.get(CONF_COLLECTION_ID):
            return f"/collections/{collection_id}/events/"
        if config.get(CONF_SEARCH_QUERY):
            return "/events/search/"
        raise EventbriteResponseError("No Eventbrite event source configured")

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: EventbriteRequestParams | None = None,
    ) -> EventbritePayload:
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_token}",
        }
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                response = await self.session.request(
                    method, f"{API_BASE_URL}{path}", headers=headers, params=params
                )
        except (TimeoutError, ClientError) as err:
            raise EventbriteResponseError(
                "Unable to communicate with Eventbrite"
            ) from err

        async with response:
            await self._raise_for_response(response)
            try:
                payload = await response.json()
            except (ClientError, ValueError) as err:
                raise EventbriteResponseError(
                    "Eventbrite returned malformed JSON"
                ) from err
            if not isinstance(payload, dict):
                raise EventbriteResponseError(
                    "Eventbrite returned an unexpected payload"
                )
            typed_payload = _payload_with_str_keys(payload)
            if typed_payload is None:
                raise EventbriteResponseError("Eventbrite payload keys were invalid")
            return typed_payload

    async def _raise_for_response(self, response: ClientResponse) -> None:
        if response.status in (401, 403):
            raise EventbriteAuthError("Eventbrite rejected the configured token")
        if response.status == 429:
            raise EventbriteRateLimitError(_retry_after(response))
        if response.status >= 500:
            raise EventbriteResponseError(
                f"Eventbrite server error: HTTP {response.status}"
            )
        if response.status >= 400:
            raise EventbriteResponseError(
                f"Eventbrite API error: HTTP {response.status}"
            )


def _retry_after(response: ClientResponse) -> int | None:
    retry_after = response.headers.get("Retry-After")
    if retry_after is None:
        return None
    try:
        return int(retry_after)
    except ValueError:
        return None


def _payload_with_str_keys(value: object) -> EventbritePayload | None:
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        return cast(EventbritePayload, value)
    return None
