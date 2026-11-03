"""Button: export last month's charging report as CSV."""

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
    async_add_entities([ExportReport(entry.runtime_data, "export_report")])


class ExportReport(EaseeSmartEntity, ButtonEntity):
    """Write a CSV with all sessions of the previous month."""

    async def async_press(self) -> None:
        result = await self.manager.async_export_report()
        async_create(
            self.hass,
            f"[{result['url']}]({result['url']}) — {result['sessions']} · "
            f"{result['energy_kwh']} kWh · {result['cost']} {self.hass.config.currency}",
            title=f"{self.manager.name} · {result['month']}",
            notification_id=f"easee_smart_report_{self.manager.charger_id}",
        )
