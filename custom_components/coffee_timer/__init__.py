from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import Event, HomeAssistant
import homeassistant.helpers.config_validation as cv

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
from .coordinator import CoffeeTimerCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["time", "switch"]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
CARD_URL = "/coffee_timer/coffee_timer_card.js"
CARD_PATH = Path(__file__).parent / "coffee_timer_card.js"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    # Serve the Lovelace card JS from inside the component directory
    try:
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(CARD_PATH), cache_headers=True)]
        )
    except Exception:
        try:
            hass.http.register_static_path(CARD_URL, str(CARD_PATH), cache_headers=True)
        except Exception:
            _LOGGER.warning("Could not register static path for coffee_timer_card.js")

    async def _register_lovelace_resource(_event: Event) -> None:
        try:
            resources = hass.data["lovelace"]["resources"]
            existing = {r["url"] for r in resources.async_items()}
            if CARD_URL not in existing:
                await resources.async_create_item({"res_type": "module", "url": CARD_URL})
                _LOGGER.debug("Registered coffee-timer-card as Lovelace resource")
        except Exception:
            _LOGGER.debug(
                "Could not auto-register Lovelace resource — add %s manually if using yaml mode",
                CARD_URL,
            )

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _register_lovelace_resource)
    return True


def _coordinator_from_entry(hass: HomeAssistant, entry: ConfigEntry) -> CoffeeTimerCoordinator:
    opts = entry.options
    return CoffeeTimerCoordinator(
        hass,
        entry.data[CONF_PLUG_ENTITY],
        notify_service=opts.get(CONF_NOTIFY_SERVICE, DEFAULT_NOTIFY_SERVICE),
        notify_title=opts.get(CONF_NOTIFY_TITLE, DEFAULT_NOTIFY_TITLE),
        notify_message=opts.get(CONF_NOTIFY_MESSAGE, DEFAULT_NOTIFY_MESSAGE),
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = _coordinator_from_entry(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    coordinator: CoffeeTimerCoordinator = hass.data[DOMAIN][entry.entry_id]
    opts = entry.options
    coordinator.update_notify_options(
        opts.get(CONF_NOTIFY_SERVICE, DEFAULT_NOTIFY_SERVICE),
        opts.get(CONF_NOTIFY_TITLE, DEFAULT_NOTIFY_TITLE),
        opts.get(CONF_NOTIFY_MESSAGE, DEFAULT_NOTIFY_MESSAGE),
    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator: CoffeeTimerCoordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.disable()
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
