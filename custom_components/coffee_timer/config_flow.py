from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_NOTIFY_MESSAGE,
    CONF_NOTIFY_RECIPIENTS,
    CONF_NOTIFY_SERVICE,
    CONF_NOTIFY_TITLE,
    CONF_PLUG_ENTITY,
    CONF_RECIPIENT_MESSAGE,
    CONF_RECIPIENT_NAME,
    CONF_RECIPIENT_SERVICE,
    CONF_RECIPIENT_TITLE,
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
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> CoffeeTimerOptionsFlow:
        return CoffeeTimerOptionsFlow(config_entry)


class CoffeeTimerOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry
        self._recipients: list[dict] | None = None

    # ------------------------------------------------------------------ helpers

    def _load_recipients(self) -> list[dict]:
        opts = self._config_entry.options
        if CONF_NOTIFY_RECIPIENTS in opts:
            return list(opts[CONF_NOTIFY_RECIPIENTS])
        # Migrate from legacy single-notify format
        service = opts.get(CONF_NOTIFY_SERVICE, "")
        if service:
            return [
                {
                    CONF_RECIPIENT_NAME: "Default",
                    CONF_RECIPIENT_SERVICE: service,
                    CONF_RECIPIENT_TITLE: opts.get(CONF_NOTIFY_TITLE, DEFAULT_NOTIFY_TITLE),
                    CONF_RECIPIENT_MESSAGE: opts.get(CONF_NOTIFY_MESSAGE, DEFAULT_NOTIFY_MESSAGE),
                }
            ]
        return []

    def _recipients_summary(self) -> str:
        if not self._recipients:
            return "None"
        return ", ".join(r[CONF_RECIPIENT_NAME] for r in self._recipients)

    def _notify_options(self) -> list[str]:
        options = sorted(
            f"notify.{svc}"
            for svc in self.hass.services.async_services().get("notify", {})
        )
        return options or [DEFAULT_NOTIFY_SERVICE]

    # ------------------------------------------------------------------ steps

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        if self._recipients is None:
            self._recipients = self._load_recipients()
        return await self.async_step_menu()

    async def async_step_menu(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        menu_options = ["add_recipient"]
        if self._recipients:
            menu_options.append("remove_recipient")
        menu_options.append("finish")
        return self.async_show_menu(
            step_id="menu",
            menu_options=menu_options,
            description_placeholders={"summary": self._recipients_summary()},
        )

    async def async_step_add_recipient(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input[CONF_RECIPIENT_NAME].strip()
            existing = {r[CONF_RECIPIENT_NAME] for r in self._recipients}
            if not name:
                errors[CONF_RECIPIENT_NAME] = "name_required"
            elif name in existing:
                errors[CONF_RECIPIENT_NAME] = "name_exists"
            else:
                self._recipients.append(
                    {
                        CONF_RECIPIENT_NAME: name,
                        CONF_RECIPIENT_SERVICE: user_input[CONF_RECIPIENT_SERVICE],
                        CONF_RECIPIENT_TITLE: user_input.get(
                            CONF_RECIPIENT_TITLE, DEFAULT_NOTIFY_TITLE
                        ),
                        CONF_RECIPIENT_MESSAGE: user_input.get(
                            CONF_RECIPIENT_MESSAGE, DEFAULT_NOTIFY_MESSAGE
                        ),
                    }
                )
                return await self.async_step_menu()

        return self.async_show_form(
            step_id="add_recipient",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_RECIPIENT_NAME): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                    ),
                    vol.Required(CONF_RECIPIENT_SERVICE): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=self._notify_options(),
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional(
                        CONF_RECIPIENT_TITLE, default=DEFAULT_NOTIFY_TITLE
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                    ),
                    vol.Optional(
                        CONF_RECIPIENT_MESSAGE, default=DEFAULT_NOTIFY_MESSAGE
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_remove_recipient(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            name = user_input[CONF_RECIPIENT_NAME]
            self._recipients = [
                r for r in self._recipients if r[CONF_RECIPIENT_NAME] != name
            ]
            return await self.async_step_menu()

        return self.async_show_form(
            step_id="remove_recipient",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_RECIPIENT_NAME): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[r[CONF_RECIPIENT_NAME] for r in self._recipients],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def async_step_finish(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        return self.async_create_entry(
            title="", data={CONF_NOTIFY_RECIPIENTS: self._recipients}
        )
