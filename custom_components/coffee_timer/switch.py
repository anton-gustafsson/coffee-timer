from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .coordinator import CoffeeTimerCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: CoffeeTimerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([CoffeeTimerSwitch(coordinator, entry)])


class CoffeeTimerSwitch(SwitchEntity, RestoreEntity):
    _attr_has_entity_name = True
    _attr_name = "Enabled"
    _attr_icon = "mdi:coffee"

    def __init__(self, coordinator: CoffeeTimerCoordinator, entry: ConfigEntry) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_enabled"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Coffee Timer",
            manufacturer="DIY",
            model="Smart Plug Timer",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state == "on":
            self._coordinator.enable()
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def is_on(self) -> bool:
        return self._coordinator.enabled

    @property
    def extra_state_attributes(self) -> dict:
        next_brew = self._coordinator.next_brew
        return {"next_brew_time": next_brew.isoformat() if next_brew else None}

    async def async_turn_on(self, **kwargs) -> None:
        self._coordinator.enable()

    async def async_turn_off(self, **kwargs) -> None:
        self._coordinator.disable()
