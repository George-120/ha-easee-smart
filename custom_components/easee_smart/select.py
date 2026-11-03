"""Charge mode select."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import EaseeSmartConfigEntry
from .const import MODES
from .entity import EaseeSmartEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EaseeSmartConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([ChargeMode(entry.runtime_data, "charge_mode")])


class ChargeMode(EaseeSmartEntity, SelectEntity):
    """Normal / smart (cheapest) / solar / solar + smart."""

    _attr_options = MODES

    @property
    def current_option(self) -> str:
        return self.manager.settings.mode

    async def async_select_option(self, option: str) -> None:
        await self.manager.async_set_setting("mode", option)
