"""Base entity for Easee Smart."""

from __future__ import annotations

import inspect

from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, EASEE_DOMAIN, SIGNAL_UPDATE, VERSION
from .manager import EaseeSmartManager

# Home Assistant 2026.8+ links a device to its parent with `via_device_id` (the parent's
# registry id); `via_device` (identifier tuple) is deprecated and raises in some code paths.
_VIA_DEVICE_ID = "via_device_id" in inspect.signature(dr.DeviceRegistry.async_get_or_create).parameters


def _device_info(manager: EaseeSmartManager) -> DeviceInfo:
    info = DeviceInfo(
        identifiers={(DOMAIN, manager.charger_id or manager.entry.entry_id)},
        name=f"{manager.name} Smart",
        manufacturer="Easee Smart Charging (community)",
        model=manager.model,
        sw_version=VERSION,
    )
    if _VIA_DEVICE_ID:
        if manager.charger_device_id:
            info["via_device_id"] = manager.charger_device_id
    elif manager.charger_id:
        info["via_device"] = (EASEE_DOMAIN, manager.charger_id)
    return info


class EaseeSmartEntity(Entity):
    """Common bits: device, naming, update signal."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, manager: EaseeSmartManager, key: str) -> None:
        self.manager = manager
        self.key = key
        self._attr_translation_key = key
        self._attr_unique_id = f"{manager.charger_id}_smart_{key}"
        self._attr_device_info = _device_info(manager)

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
