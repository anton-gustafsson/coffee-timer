from __future__ import annotations

import datetime
import logging
from collections.abc import Callable

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_time
import homeassistant.util.dt as dt_util

_LOGGER = logging.getLogger(__name__)


class CoffeeTimerCoordinator:
    def __init__(
        self,
        hass: HomeAssistant,
        plug_entity: str,
        notify_recipients: list[dict] | None = None,
    ) -> None:
        self.hass = hass
        self._plug_entity = plug_entity
        self._recipients: list[dict] = list(notify_recipients or [])
        self._recipient_enabled: dict[str, bool] = {}
        self._notify_entity_ids: dict[str, str] = {}
        self._enabled = False
        self._brew_time = datetime.time(7, 0)
        self._next_brew: datetime.datetime | None = None
        self._unsub: Callable | None = None
        self._listeners: list[Callable] = []

    # ------------------------------------------------------------------ listeners

    def async_add_listener(self, listener: Callable) -> Callable:
        self._listeners.append(listener)

        def remove() -> None:
            self._listeners.remove(listener)

        return remove

    def _notify(self) -> None:
        for listener in self._listeners:
            listener()

    # ------------------------------------------------------------------ properties

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def brew_time(self) -> datetime.time:
        return self._brew_time

    @property
    def next_brew(self) -> datetime.datetime | None:
        return self._next_brew

    @property
    def recipients(self) -> list[dict]:
        return self._recipients

    @property
    def notify_entity_ids(self) -> list[str]:
        return [
            self._notify_entity_ids[r["name"]]
            for r in self._recipients
            if r["name"] in self._notify_entity_ids
        ]

    # ------------------------------------------------------------------ notify recipients

    def register_notify_entity(self, name: str, entity_id: str) -> None:
        self._notify_entity_ids[name] = entity_id
        self._notify()

    def is_recipient_enabled(self, name: str) -> bool:
        return self._recipient_enabled.get(name, True)

    def set_recipient_enabled(self, name: str, enabled: bool) -> None:
        self._recipient_enabled[name] = enabled
        self._notify()

    # ------------------------------------------------------------------ public API

    def enable(self) -> None:
        self._enabled = True
        self._schedule()
        self._notify()

    def disable(self) -> None:
        self._enabled = False
        self._cancel()
        self._notify()

    def set_brew_time(self, t: datetime.time) -> None:
        self._brew_time = t
        if self._enabled:
            self._schedule()
        self._notify()

    # ------------------------------------------------------------------ scheduling

    def _schedule(self) -> None:
        self._cancel()
        now = dt_util.now()
        scheduled = now.replace(
            hour=self._brew_time.hour,
            minute=self._brew_time.minute,
            second=0,
            microsecond=0,
        )
        if scheduled <= now:
            scheduled += datetime.timedelta(days=1)
        self._next_brew = scheduled
        self._unsub = async_track_point_in_time(self.hass, self._fire, scheduled)

    def _cancel(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None
        self._next_brew = None

    @callback
    def _fire(self, _fire_time: datetime.datetime) -> None:
        self._unsub = None
        self._next_brew = None
        self.hass.async_create_task(self._async_fire())

    async def _async_fire(self) -> None:
        await self.hass.services.async_call(
            "homeassistant", "turn_on", {"entity_id": self._plug_entity}
        )
        await self._send_notifications()
        self._enabled = False
        self._notify()

    async def _send_notifications(self) -> None:
        for recipient in self._recipients:
            name = recipient.get("name", "")
            if not self._recipient_enabled.get(name, True):
                continue
            service = recipient.get("service", "")
            if not service:
                continue
            try:
                domain, svc = service.rsplit(".", 1)
                await self.hass.services.async_call(
                    domain,
                    svc,
                    {
                        "title": recipient.get("title", ""),
                        "message": recipient.get("message", ""),
                    },
                    blocking=False,
                )
            except Exception:
                _LOGGER.exception(
                    "Failed to send coffee timer notification to %s via %s", name, service
                )
