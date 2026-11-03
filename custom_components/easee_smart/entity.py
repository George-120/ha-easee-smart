"""Base entity for Easee Smart."""

from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, EASEE_DOMAIN, SIGNAL_UPDATE, VERSION
from .manager import EaseeSmartManager


class EaseeSmartEntity(Entity):
    """Common bits: device, naming, update signal."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, manager: EaseeSmartManager, key: str) -> None:
        self.manager = manager
        self.key = key
        self._attr_translation_key = key
        self._attr_unique_id = f"{manager.charger_id}_smart_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, manager.charger_id or manager.entry.entry_id)},
            name=f"{manager.name} Smart",
            manufacturer="Easee Smart Charging (community)",
            model=manager.model,
            sw_version=VERSION,
            via_device=(EASEE_DOMAIN, manager.charger_id) if manager.charger_id else None,
        )

    async def async_added_to_hass(self) -> None:
        self.manager.own_entities[self.key] = self.entity_id
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATE.format(self.manager.entry.entry_id),
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()
