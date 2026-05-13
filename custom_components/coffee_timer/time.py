from __future__ import annotations

import datetime

from homeassistant.components.time import TimeEntity
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
    async_add_entities([CoffeeTimerTimeEntity(coordinator, entry)])


class CoffeeTimerTimeEntity(TimeEntity, RestoreEntity):
    _attr_has_entity_name = True
    _attr_name = "Brew Time"

    def __init__(self, coordinator: CoffeeTimerCoordinator, entry: ConfigEntry) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_brew_time"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Coffee Timer",
            manufacturer="DIY",
            model="Smart Plug Timer",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in ("unknown", "unavailable"):
            try:
                restored = datetime.time.fromisoformat(last_state.state)
                # Set directly so we don't trigger a reschedule before switch restores
                self._coordinator._brew_time = restored
            except ValueError:
                pass
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def native_value(self) -> datetime.time:
        return self._coordinator.brew_time

    async def async_set_value(self, value: datetime.time) -> None:
        self._coordinator.set_brew_time(value)
