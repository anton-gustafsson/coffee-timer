from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_NOTIFY_MESSAGE,
    CONF_NOTIFY_SERVICE,
    CONF_NOTIFY_TITLE,
    CONF_PLUG_ENTITY,
    DEFAULT_NOTIFY_MESSAGE,
    DEFAULT_NOTIFY_SERVICE,
    DEFAULT_NOTIFY_TITLE,
    DOMAIN,
)


class CoffeeTimerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            entity_id = user_input[CONF_PLUG_ENTITY]
            if not self.hass.states.get(entity_id):
                errors[CONF_PLUG_ENTITY] = "entity_not_found"
            else:
                await self.async_set_unique_id(entity_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Coffee Timer", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PLUG_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="switch")
                    )
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> CoffeeTimerOptionsFlow:
        return CoffeeTimerOptionsFlow(config_entry)


class CoffeeTimerOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        opts = self._config_entry.options
        current_service = opts.get(CONF_NOTIFY_SERVICE, DEFAULT_NOTIFY_SERVICE)
        current_title = opts.get(CONF_NOTIFY_TITLE, DEFAULT_NOTIFY_TITLE)
        current_message = opts.get(CONF_NOTIFY_MESSAGE, DEFAULT_NOTIFY_MESSAGE)

        # Build dropdown from all registered notify services
        notify_options = sorted(
            f"notify.{svc}"
            for svc in self.hass.services.async_services().get("notify", {})
        )
        if current_service and current_service not in notify_options:
            notify_options.insert(0, current_service)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_NOTIFY_SERVICE, default=current_service): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=notify_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional(CONF_NOTIFY_TITLE, default=current_title): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                    ),
                    vol.Optional(CONF_NOTIFY_MESSAGE, default=current_message): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                    ),
                }
            ),
        )
