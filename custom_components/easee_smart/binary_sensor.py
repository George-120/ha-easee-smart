"""Binary sensors for Easee Smart."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import EaseeSmartConfigEntry
from .const import SMART_IDLE, SMART_NOT_CONNECTED
from .entity import EaseeSmartEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EaseeSmartConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    manager = entry.runtime_data
    async_add_entities([CarConnected(manager, "car_connected"), SmartActive(manager, "smart_active")])


class CarConnected(EaseeSmartEntity, BinarySensorEntity):
    """Car plugged in."""

    _attr_device_class = BinarySensorDeviceClass.PLUG

    @property
    def is_on(self) -> bool | None:
        if self.manager.snapshot.status == "unknown":
            return None
        return self.manager.snapshot.connected


class SmartActive(EaseeSmartEntity, BinarySensorEntity):
    """Smart control is currently steering the charger."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING

    @property
    def is_on(self) -> bool:
        return self.manager.snapshot.smart_state not in (SMART_IDLE, SMART_NOT_CONNECTED)
