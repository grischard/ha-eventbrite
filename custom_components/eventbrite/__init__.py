"""Home Assistant setup for the Eventbrite integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import EventbriteApiClient
from .const import CONF_API_TOKEN, PLATFORMS
from .coordinator import EventbriteCoordinator

EventbriteConfigEntry = ConfigEntry[EventbriteCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: EventbriteConfigEntry) -> bool:
    """Set up Eventbrite from a config entry."""

    client = EventbriteApiClient.from_hass(hass, entry.data[CONF_API_TOKEN])
    coordinator = EventbriteCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EventbriteConfigEntry) -> bool:
    """Unload an Eventbrite config entry."""

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(
    hass: HomeAssistant, entry: EventbriteConfigEntry
) -> None:
    """Reload the config entry after options changes."""

    await hass.config_entries.async_reload(entry.entry_id)
