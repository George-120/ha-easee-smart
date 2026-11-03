"""Number entities: charge target and price threshold."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import EaseeSmartConfigEntry
from .entity import EaseeSmartEntity
from .manager import EaseeSmartManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EaseeSmartConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    manager = entry.runtime_data
    entities: list[NumberEntity] = [TargetEnergy(manager, "target_energy"), PriceThreshold(manager, "price_threshold")]
    if manager.cars:
        entities.append(TargetSoc(manager, "target_soc"))
    async_add_entities(entities)


class TargetEnergy(EaseeSmartEntity, NumberEntity):
    """Energy to add before departure (kWh)."""

    _attr_native_min_value = 1
    _attr_native_max_value = 120
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_mode = NumberMode.BOX

    @property
    def native_value(self) -> float:
        return self.manager.settings.target_energy

    async def async_set_native_value(self, value: float) -> None:
        await self.manager.async_set_setting("target_energy", float(value))


class TargetSoc(EaseeSmartEntity, NumberEntity):
    """Battery percentage to reach before departure."""

    _attr_native_min_value = 10
    _attr_native_max_value = 100
    _attr_native_step = 5
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER

    @property
    def native_value(self) -> int:
        return self.manager.car_target(self.manager.active_car())

    async def async_set_native_value(self, value: float) -> None:
        await self.manager.async_set_car_target(int(value))


class PriceThreshold(EaseeSmartEntity, NumberEntity):
    """Always charge when the price is at or below this value."""

    _attr_native_min_value = -1.0
    _attr_native_max_value = 1.0
    _attr_native_step = 0.01
    _attr_mode = NumberMode.BOX

    def __init__(self, manager: EaseeSmartManager, key: str) -> None:
        super().__init__(manager, key)
        self._attr_native_unit_of_measurement = f"{manager.hass.config.currency}/kWh"

    @property
    def native_value(self) -> float | None:
        return self.manager.settings.price_threshold

    async def async_set_native_value(self, value: float) -> None:
        await self.manager.async_set_setting("price_threshold", round(float(value), 3))
