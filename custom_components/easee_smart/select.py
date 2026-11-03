"""Charge mode select."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import EaseeSmartConfigEntry
from .const import ACTIVE_CAR_AUTO, MODES
from .entity import EaseeSmartEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EaseeSmartConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    manager = entry.runtime_data
    entities: list[SelectEntity] = [ChargeMode(manager, "charge_mode")]
    if manager.cars:
        entities.append(ActiveCar(manager, "active_car"))
    async_add_entities(entities)


class ChargeMode(EaseeSmartEntity, SelectEntity):
    """Normal / smart (cheapest) / solar / solar + smart."""

    _attr_options = MODES

    @property
    def current_option(self) -> str:
        return self.manager.settings.mode

    async def async_select_option(self, option: str) -> None:
        await self.manager.async_set_setting("mode", option)


class ActiveCar(EaseeSmartEntity, SelectEntity):
    """Which car is connected: automatic (plug sensor) or a fixed choice."""

    @property
    def options(self) -> list[str]:
        return [ACTIVE_CAR_AUTO, *[c.name for c in self.manager.cars]]

    @property
    def current_option(self) -> str:
        value = self.manager.settings.active_car
        return value if value in self.options else ACTIVE_CAR_AUTO

    @property
    def extra_state_attributes(self) -> dict:
        car = self.manager.active_car()
        return {"car": car.name if car else None}

    async def async_select_option(self, option: str) -> None:
        await self.manager.async_set_setting("active_car", option)
