"""Base entity helpers for the Eventbrite integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import CONF_NAME, DOMAIN, EVENTBRITE_ATTRIBUTION
from .coordinator import EventbriteCoordinator


class EventbriteEntity(CoordinatorEntity[EventbriteCoordinator]):
    """Base class for Eventbrite entities."""

    _attr_attribution = EVENTBRITE_ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EventbriteCoordinator,
        *,
        unique_suffix: str,
        name: str | None,
        object_suffix: str | None,
    ) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        entry_uid = entry.unique_id or entry.entry_id
        configured_name = entry.data[CONF_NAME]
        object_name = slugify(configured_name)

        self._attr_name = name
        self._attr_unique_id = f"{entry_uid}_{unique_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_uid)},
            manufacturer="Eventbrite",
            name=f"Eventbrite {configured_name}",
        )

        self._attr_suggested_object_id = (
            f"eventbrite_{object_name}_{object_suffix}"
            if object_suffix
            else f"eventbrite_{object_name}"
        )
