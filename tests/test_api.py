"""Tests for the Eventbrite API client."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import SimpleNamespace, TracebackType
from typing import ClassVar, cast

import pytest
from aiohttp import ClientSession
from yarl import URL

from custom_components.eventbrite.api import EventbriteApiClient
from custom_components.eventbrite.const import (
    CONF_EVENT_STATUSES,
    CONF_ORGANIZER_ID,
)
from custom_components.eventbrite.types import EventbritePayload


@dataclass(slots=True)
class ApiCall:
    """Recorded fake API call."""

    method: str
    url: str
    params: Mapping[str, str | int] | None


class FakeResponse:
    """Minimal aiohttp-like response for API client tests."""

    status: ClassVar[int] = 200
    headers: ClassVar[dict[str, str]] = {}

    def __init__(self, payload: EventbritePayload) -> None:
        self._payload = payload

    async def __aenter__(self) -> FakeResponse:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    async def json(self) -> EventbritePayload:
        return self._payload

    async def read(self) -> bytes:
        return b"image"


@pytest.mark.asyncio
async def test_organizer_events_endpoint_uses_continuation() -> None:
    calls: list[ApiCall] = []

    async def request(
        method: str,
        url: str,
        headers: Mapping[str, str] | None = None,  # pylint: disable=unused-argument
        params: Mapping[str, str | int] | None = None,
    ) -> FakeResponse:
        calls.append(ApiCall(method=method, url=url, params=params))
        if len(calls) == 1:
            return FakeResponse(
                {
                    "events": [{"id": "1"}],
                    "pagination": {
                        "has_more_items": True,
                        "continuation": "next-page",
                    },
                }
            )
        return FakeResponse(
            {
                "events": [{"id": "2"}],
                "pagination": {"has_more_items": False},
            }
        )

    client = EventbriteApiClient(
        cast(ClientSession, SimpleNamespace(request=request)), "token"
    )

    events = await client.async_get_events(
        {
            CONF_ORGANIZER_ID: "52408308",
            CONF_EVENT_STATUSES: "live",
        }
    )

    assert events == [{"id": "1"}, {"id": "2"}]
    assert calls[0].url.endswith("/v3/organizers/52408308/events/")
    assert calls[0].params is not None
    assert calls[0].params["status"] == "live"
    assert calls[1].params is not None
    assert calls[1].params["continuation"] == "next-page"


@pytest.mark.asyncio
async def test_logo_fetch_uses_image_request_headers() -> None:
    captured_headers: Mapping[str, str] | None = None

    async def get(
        url: URL,
        headers: Mapping[str, str] | None = None,
    ) -> FakeResponse:
        nonlocal captured_headers
        captured_headers = headers
        assert isinstance(url, URL)
        assert str(url) == "https://img.example/logo.png"
        return FakeResponse({})

    client = EventbriteApiClient(cast(ClientSession, SimpleNamespace(get=get)), "token")

    assert await client.async_get_logo_bytes("https://img.example/logo.png") == b"image"
    assert captured_headers is not None
    headers = dict(captured_headers)
    assert headers["Accept"].startswith("image/")
    assert headers["User-Agent"] == "HomeAssistant-Eventbrite/0.1"
