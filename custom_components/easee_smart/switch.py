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
    manager = entry.runtime_data
    entities: list[SwitchEntity] = [Boost(manager, "boost")]
    if manager.cars:
        entities.append(ManualKwh(manager, "manual_kwh"))
    async_add_entities(entities)


class Boost(EaseeSmartEntity, SwitchEntity):
    """Charge now at full current, ignoring the plan (resets on unplug)."""

    @property
    def is_on(self) -> bool:
        return self.manager.settings.boost

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.manager.async_set_setting("boost", True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.manager.async_set_setting("boost", False)


class ManualKwh(EaseeSmartEntity, SwitchEntity):
    """Charge a fixed number of kWh before departure instead of up to a battery percentage."""

    _attr_icon = "mdi:lightning-bolt-circle"

    @property
    def is_on(self) -> bool:
        return self.manager.settings.manual_kwh

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.manager.async_set_setting("manual_kwh", True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.manager.async_set_setting("manual_kwh", False)
