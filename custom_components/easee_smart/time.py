"""Departure time entity."""

from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import EaseeSmartConfigEntry
from .entity import EaseeSmartEntity
from .manager import _parse_time


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EaseeSmartConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([DepartureTime(entry.runtime_data, "departure_time")])


class DepartureTime(EaseeSmartEntity, TimeEntity):
    """The car must be ready at this time."""

    @property
    def native_value(self) -> time:
        return _parse_time(self.manager.settings.departure)

    async def async_set_value(self, value: time) -> None:
        await self.manager.async_set_setting("departure", value.strftime("%H:%M"))
