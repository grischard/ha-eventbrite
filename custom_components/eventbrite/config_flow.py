"""Config flow for the Eventbrite integration."""

from __future__ import annotations

import hashlib
import re

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector

from .api import EventbriteApiClient, EventbriteAuthError, EventbriteError
from .const import (
    CONF_API_TOKEN,
    CONF_COLLECTION_ID,
    CONF_EVENT_STATUSES,
    CONF_FILTER_EVENT_NAME_QUERY,
    CONF_MAX_EVENTS,
    CONF_ORGANIZER_ID,
    CONF_SCAN_INTERVAL_MINUTES,
    CONF_SEARCH_QUERY,
    DEFAULT_EVENT_STATUSES,
    DEFAULT_MAX_EVENTS,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
)

UserInput = dict[str, object]


class EventbriteConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an Eventbrite config flow."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> EventbriteOptionsFlowHandler:
        """Create the options flow."""

        return EventbriteOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: UserInput | None = None
    ) -> ConfigFlowResult:
        """Handle setup initiated by the user."""

        errors: dict[str, str] = {}

        if user_input is not None:
            errors = _validate_user_input(user_input)
            if not errors:
                unique_id = _source_unique_id(user_input)
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                client = EventbriteApiClient.from_hass(
                    self.hass, _string_value(user_input, CONF_API_TOKEN)
                )
                try:
                    await client.async_validate_token()
                except EventbriteAuthError:
                    errors["base"] = "invalid_auth"
                except EventbriteError:
                    errors["base"] = "cannot_connect"
                else:
                    return self.async_create_entry(
                        title=_string_value(user_input, CONF_NAME),
                        data=user_input,
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input),
            errors=errors,
        )


class EventbriteOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Eventbrite options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: UserInput | None = None
    ) -> ConfigFlowResult:
        """Manage Eventbrite options."""

        errors: dict[str, str] = {}
        if user_input is not None:
            if regex := user_input.get(CONF_FILTER_EVENT_NAME_QUERY):
                if not isinstance(regex, str):
                    errors[CONF_FILTER_EVENT_NAME_QUERY] = "invalid_regex"
                else:
                    try:
                        re.compile(regex)
                    except re.error:
                        errors[CONF_FILTER_EVENT_NAME_QUERY] = "invalid_regex"

            if not errors:
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(self._config_entry),
            errors=errors,
        )


def _user_schema(user_input: UserInput | None) -> vol.Schema:
    defaults = user_input or {}
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "")): str,
            vol.Required(CONF_API_TOKEN): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
            vol.Optional(
                CONF_ORGANIZER_ID,
                default=defaults.get(CONF_ORGANIZER_ID, ""),
            ): str,
            vol.Optional(
                CONF_COLLECTION_ID,
                default=defaults.get(CONF_COLLECTION_ID, ""),
            ): str,
            vol.Optional(
                CONF_SEARCH_QUERY,
                default=defaults.get(CONF_SEARCH_QUERY, ""),
            ): str,
            vol.Optional(
                CONF_EVENT_STATUSES,
                default=defaults.get(CONF_EVENT_STATUSES, DEFAULT_EVENT_STATUSES),
            ): str,
            vol.Optional(
                CONF_MAX_EVENTS,
                default=defaults.get(CONF_MAX_EVENTS, DEFAULT_MAX_EVENTS),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=50, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Optional(
                CONF_SCAN_INTERVAL_MINUTES,
                default=defaults.get(
                    CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=5, max=1440, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Optional(
                CONF_FILTER_EVENT_NAME_QUERY,
                default=defaults.get(CONF_FILTER_EVENT_NAME_QUERY, ""),
            ): str,
        }
    )


def _options_schema(config_entry: config_entries.ConfigEntry) -> vol.Schema:
    data = {**config_entry.data, **config_entry.options}
    return vol.Schema(
        {
            vol.Optional(
                CONF_EVENT_STATUSES,
                default=data.get(CONF_EVENT_STATUSES, DEFAULT_EVENT_STATUSES),
            ): str,
            vol.Optional(
                CONF_MAX_EVENTS,
                default=data.get(CONF_MAX_EVENTS, DEFAULT_MAX_EVENTS),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=50, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Optional(
                CONF_SCAN_INTERVAL_MINUTES,
                default=data.get(
                    CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=5, max=1440, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Optional(
                CONF_FILTER_EVENT_NAME_QUERY,
                default=data.get(CONF_FILTER_EVENT_NAME_QUERY, ""),
            ): str,
        }
    )


def _validate_user_input(user_input: UserInput) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not any(
        user_input.get(key)
        for key in (CONF_ORGANIZER_ID, CONF_COLLECTION_ID, CONF_SEARCH_QUERY)
    ):
        errors["base"] = "source_required"

    if regex := user_input.get(CONF_FILTER_EVENT_NAME_QUERY):
        if not isinstance(regex, str):
            errors[CONF_FILTER_EVENT_NAME_QUERY] = "invalid_regex"
        else:
            try:
                re.compile(regex)
            except re.error:
                errors[CONF_FILTER_EVENT_NAME_QUERY] = "invalid_regex"

    return errors


def _source_unique_id(user_input: UserInput) -> str:
    if organizer_id := user_input.get(CONF_ORGANIZER_ID):
        return f"eventbrite_organizer_{organizer_id}"
    if collection_id := user_input.get(CONF_COLLECTION_ID):
        return f"eventbrite_collection_{collection_id}"
    digest = hashlib.sha256(str(user_input[CONF_SEARCH_QUERY]).encode()).hexdigest()[
        :12
    ]
    return f"eventbrite_search_{digest}"


def _string_value(user_input: UserInput, key: str) -> str:
    value = user_input[key]
    if not isinstance(value, str):
        raise TypeError(f"Expected {key} to be a string")
    return value
