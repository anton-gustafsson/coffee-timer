from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

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

PLATFORMS = ["time", "switch"]


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
