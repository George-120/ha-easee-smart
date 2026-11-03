"""Boost switch: charge at full power now, until the car is unplugged."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import EaseeSmartConfigEntry
from .entity import EaseeSmartEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EaseeSmartConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([Boost(entry.runtime_data, "boost")])


class Boost(EaseeSmartEntity, SwitchEntity):
    """Charge now at full current, ignoring the plan (resets on unplug)."""

    @property
    def is_on(self) -> bool:
        return self.manager.settings.boost

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.manager.async_set_setting("boost", True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.manager.async_set_setting("boost", False)
