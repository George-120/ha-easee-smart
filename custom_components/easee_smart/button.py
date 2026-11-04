"""Buttons: monthly report totals and car actions."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.components.persistent_notification import async_create
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
    entities: list[ButtonEntity] = [ExportReport(manager, "export_report")]
    if any(c.refresh_entity for c in manager.cars):
        entities.append(RefreshCar(manager, "refresh_car"))
    if any(c.start_entity for c in manager.cars):
        entities.append(StartCar(manager, "start_car"))
    async_add_entities(entities)


class ExportReport(EaseeSmartEntity, ButtonEntity):
    """Show last month's totals; the CSV comes from the export_report action or the card."""

    async def async_press(self) -> None:
        # Only the totals go into the notification; the CSV itself is returned by the
        # easee_smart.export_report action and downloaded by the card (never stored in /config/www).
        result = await self.manager.async_export_report()
        async_create(
            self.hass,
            f"{result['sessions']} · {result['energy_kwh']} kWh · {result['cost']} {self.hass.config.currency}",
            title=f"{self.manager.name} · {result['month']}",
            notification_id=f"easee_smart_report_{self.manager.charger_id}",
        )


class RefreshCar(EaseeSmartEntity, ButtonEntity):
    """Ask the connected car for fresh data (battery level, plug)."""

    async def async_press(self) -> None:
        await self.manager.async_refresh_car()


class StartCar(EaseeSmartEntity, ButtonEntity):
    """Tell the connected car to start charging (for cars that fall asleep)."""

    async def async_press(self) -> None:
        await self.manager.async_force_car_start()
