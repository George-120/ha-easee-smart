"""Easee Smart Charging: smart charging, Equalizer insight, costs and an app-style card on top of the Easee integration."""

from __future__ import annotations

import logging
from pathlib import Path

import voluptuous as vol
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import (
    ConfigEntryNotReady,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.helpers.typing import ConfigType

from .const import (
    CARD_BASE,
    CARD_URL,
    DOMAIN,
    EASEE_DOMAIN,
    VERSION,
)
from .dashboard import async_create_dashboard
from .manager import EaseeSmartManager

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.TIME,
    Platform.SWITCH,
    Platform.BUTTON,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type EaseeSmartConfigEntry = ConfigEntry[EaseeSmartManager]

SERVICE_EXPORT_REPORT = "export_report"
SERVICE_SET_MODE = "set_mode"
SERVICE_CREATE_DASHBOARD = "create_dashboard"
ATTR_MONTH = "month"
ATTR_CONFIG_ENTRY = "config_entry_id"
ATTR_MODE = "mode"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the dashboard card and services once."""
    await _async_register_card(hass)

    async def _manager_for(call: ServiceCall) -> EaseeSmartManager:
        entry_id = call.data.get(ATTR_CONFIG_ENTRY)
        entries = [
            e for e in hass.config_entries.async_loaded_entries(DOMAIN)
            if entry_id in (None, e.entry_id)
        ]
        if not entries:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="no_charger"
            )
        return entries[0].runtime_data

    async def _export(call: ServiceCall) -> ServiceResponse:
        manager = await _manager_for(call)
        month = call.data.get(ATTR_MONTH)
        return await manager.async_export_report(month)

    async def _set_mode(call: ServiceCall) -> None:
        manager = await _manager_for(call)
        await manager.async_set_setting("mode", call.data[ATTR_MODE])

    hass.services.async_register(
        DOMAIN,
        SERVICE_EXPORT_REPORT,
        _export,
        schema=vol.Schema(
            {
                vol.Optional(ATTR_CONFIG_ENTRY): cv.string,
                vol.Optional(ATTR_MONTH): vol.Match(r"^\d{4}-\d{2}$"),
            }
        ),
        supports_response=SupportsResponse.OPTIONAL,
    )
    async def _create_dashboard(call: ServiceCall) -> ServiceResponse:
        manager = await _manager_for(call)
        try:
            url = await async_create_dashboard(manager)
        except HomeAssistantError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="dashboard_failed", translation_placeholders={"error": str(err)}
            ) from err
        return {"url_path": url}

    # Writes Lovelace config, so admins only.
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_CREATE_DASHBOARD,
        _create_dashboard,
        schema=vol.Schema({vol.Optional(ATTR_CONFIG_ENTRY): cv.string}),
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_MODE,
        _set_mode,
        schema=vol.Schema(
            {
                vol.Optional(ATTR_CONFIG_ENTRY): cv.string,
                vol.Required(ATTR_MODE): vol.In(["normal", "smart", "solar", "solar_smart"]),
            }
        ),
    )
    return True


async def _async_register_card(hass: HomeAssistant) -> None:
    """Serve the card and load it in the frontend (no dashboard changes needed)."""
    folder = Path(__file__).parent / "frontend"
    try:
        # serves the card script and the charger image from one folder
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_BASE, str(folder), cache_headers=False)]
        )
    except RuntimeError:
        # already registered (e.g. after a reload)
        pass
    from homeassistant.components.frontend import add_extra_js_url

    add_extra_js_url(hass, f"{CARD_URL}?v={VERSION}")


async def async_setup_entry(hass: HomeAssistant, entry: EaseeSmartConfigEntry) -> bool:
    """Set up one charger."""
    if not hass.config_entries.async_loaded_entries(EASEE_DOMAIN):
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN, translation_key="easee_not_loaded"
        )
    manager = EaseeSmartManager(hass, entry)
    await manager.async_setup()
    if not manager.charger_entities.get("status"):
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN, translation_key="charger_not_found"
        )
    entry.runtime_data = manager
    _async_remove_old_entities(hass, manager)
    hass.async_create_background_task(_async_remove_public_reports(hass, manager), f"{DOMAIN} cleanup")
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    manager.async_start()
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


def _async_remove_old_entities(hass: HomeAssistant, manager: EaseeSmartManager) -> None:
    """Remove entities older versions created that no longer exist."""
    from homeassistant.helpers import entity_registry as er

    reg = er.async_get(hass)
    # 1.5.0-1.5.4 had a "Create dashboard" button; that is now admin-only (options flow / admin action).
    if entity_id := reg.async_get_entity_id("button", DOMAIN, f"{manager.charger_id}_smart_create_dashboard"):
        reg.async_remove(entity_id)


async def _async_remove_public_reports(hass: HomeAssistant, manager: EaseeSmartManager) -> None:
    """Delete monthly CSVs that versions before 1.6.0 wrote to /config/www/easee_smart (served without login).

    Only files with the exact name pattern those versions used are removed.
    """
    import re

    folder = Path(hass.config.path("www", "easee_smart"))
    pattern = re.compile(rf"^{re.escape((manager.charger_id or 'easee').lower())}-\d{{4}}-\d{{2}}\.csv$")

    def _clean() -> list[str]:
        if not folder.is_dir():
            return []
        removed = []
        for file in folder.iterdir():
            if file.is_file() and pattern.match(file.name):
                file.unlink()
                removed.append(file.name)
        if not any(folder.iterdir()):
            folder.rmdir()
        return removed

    try:
        removed = await hass.async_add_executor_job(_clean)
    except OSError as err:
        _LOGGER.warning("Could not remove old public reports in %s: %s", folder, err)
        return
    if removed:
        _LOGGER.info("Removed %d old public report(s) from %s", len(removed), folder)


async def _async_reload(hass: HomeAssistant, entry: EaseeSmartConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: EaseeSmartConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_unload()
    return unloaded
