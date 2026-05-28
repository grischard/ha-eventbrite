"""Image entity for the featured Eventbrite event logo."""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .api import EventbriteError
from .coordinator import EventbriteCoordinator
from .entity import EventbriteEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eventbrite image entities."""

    coordinator: EventbriteCoordinator = entry.runtime_data
    async_add_entities([EventbriteFeaturedLogoImage(hass, coordinator)])


class EventbriteFeaturedLogoImage(EventbriteEntity, ImageEntity):
    """Image entity serving the featured event logo."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: EventbriteCoordinator,
    ) -> None:
        ImageEntity.__init__(self, hass)
        super().__init__(
            coordinator,
            unique_suffix="featured_event_logo",
            name="Featured event logo",
            object_suffix="featured_event_logo",
        )
        self._attr_image_last_updated: datetime | None = None
        self._cached_logo_key: tuple[str, str] | None = None
        self._cached_logo_bytes: bytes | None = None
        self._current_logo_key: tuple[str, str] | None = None

    @property
    def content_type(self) -> str:
        """Return the image content type."""

        event = self.coordinator.featured_event
        if event and event.logo_url:
            return _content_type_from_url(event.logo_url)
        return "application/octet-stream"

    @property
    def image_last_updated(self) -> datetime | None:
        """Return when the image last changed."""

        return self._attr_image_last_updated

    async def async_image(self) -> bytes | None:
        """Return the featured event logo image bytes."""

        logo_key = self._logo_key()
        if logo_key is None:
            return None
        if logo_key == self._cached_logo_key:
            return self._cached_logo_bytes

        _, logo_url = logo_key
        try:
            image_bytes = await self.coordinator.client.async_get_logo_bytes(logo_url)
        except EventbriteError:
            _LOGGER.warning("Unable to fetch Eventbrite featured event logo")
            return None

        self._cached_logo_key = logo_key
        self._cached_logo_bytes = image_bytes
        return image_bytes

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update image metadata when the featured logo changes."""

        logo_key = self._logo_key()
        if logo_key != self._current_logo_key:
            self._current_logo_key = logo_key
            self._cached_logo_key = None
            self._cached_logo_bytes = None
            self._attr_image_last_updated = dt_util.utcnow() if logo_key else None
        super()._handle_coordinator_update()

    def _logo_key(self) -> tuple[str, str] | None:
        event = self.coordinator.featured_event
        if event is None or event.logo_url is None:
            return None
        return (event.id, event.logo_url)


def _content_type_from_url(url: str) -> str:
    url = url.lower().split("?", 1)[0]
    if url.endswith(".png"):
        return "image/png"
    if url.endswith(".webp"):
        return "image/webp"
    if url.endswith(".gif"):
        return "image/gif"
    if url.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    return "application/octet-stream"
