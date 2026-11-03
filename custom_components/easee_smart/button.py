"""Button: export last month's charging report as CSV."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.components.persistent_notification import async_create
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import EaseeSmartConfigEntry
from .const import DOMAIN
from .dashboard import async_create_dashboard
from .entity import EaseeSmartEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EaseeSmartConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    manager = entry.runtime_data
    entities: list[ButtonEntity] = [ExportReport(manager, "export_report"), CreateDashboard(manager, "create_dashboard")]
    if any(c.refresh_entity for c in manager.cars):
        entities.append(RefreshCar(manager, "refresh_car"))
    if any(c.start_entity for c in manager.cars):
        entities.append(StartCar(manager, "start_car"))
    async_add_entities(entities)


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


class RefreshCar(EaseeSmartEntity, ButtonEntity):
    """Ask the connected car for fresh data (battery level, plug)."""

    async def async_press(self) -> None:
        await self.manager.async_refresh_car()


class StartCar(EaseeSmartEntity, ButtonEntity):
    """Tell the connected car to start charging (for cars that fall asleep)."""

    async def async_press(self) -> None:
        await self.manager.async_force_car_start()


class CreateDashboard(EaseeSmartEntity, ButtonEntity):
    """Put the ready-made Easee Smart dashboard in the sidebar (or refresh it)."""

    _attr_entity_category = EntityCategory.CONFIG

    async def async_press(self) -> None:
        try:
            url = await async_create_dashboard(self.manager)
        except HomeAssistantError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="dashboard_failed", translation_placeholders={"error": str(err)}
            ) from err
        async_create(
            self.hass,
            f"[/{url}](/{url})",
            title=f"{self.manager.name} · Easee Smart dashboard",
            notification_id=f"easee_smart_dashboard_{self.manager.charger_id}",
        )
