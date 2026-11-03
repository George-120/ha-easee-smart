"""Ready-made Lovelace dashboard, created with one button press.

Home Assistant has no public Python API to add a storage dashboard, so we use the
same collection the frontend talks to (reached through its websocket command).
"""

from __future__ import annotations

import inspect
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

if TYPE_CHECKING:
    from .manager import EaseeSmartManager

_LOGGER = logging.getLogger(__name__)

DASHBOARD_URL = "easee-smart"
DASHBOARD_ICON = "mdi:ev-station"

TEXT = {
    "nl": {
        "title": "Easee Smart", "charge": "Laden", "energy": "Energie & kosten", "all": "Alles in één",
        "charger": "Laadpaal", "control": "Bediening", "plan": "Planning", "grid": "Aansluiting",
        "costs": "Kosten", "history": "Laatste 24 uur", "price": "Prijs vandaag", "power": "Laadvermogen",
        "month": "Deze maand", "sub": "Slim laden met je Easee",
    },
    "en": {
        "title": "Easee Smart", "charge": "Charging", "energy": "Energy & costs", "all": "All in one",
        "charger": "Charger", "control": "Controls", "plan": "Planning", "grid": "Grid connection",
        "costs": "Costs", "history": "Last 24 hours", "price": "Price today", "power": "Charging power",
        "month": "This month", "sub": "Smart charging with your Easee",
    },
    "de": {
        "title": "Easee Smart", "charge": "Laden", "energy": "Energie & Kosten", "all": "Alles in einem",
        "charger": "Ladestation", "control": "Steuerung", "plan": "Planung", "grid": "Netzanschluss",
        "costs": "Kosten", "history": "Letzte 24 Stunden", "price": "Preis heute", "power": "Ladeleistung",
        "month": "Dieser Monat", "sub": "Intelligent laden mit deiner Easee",
    },
}


def _lang(manager: EaseeSmartManager) -> str:
    chosen = manager._opt("language") or "auto"
    lang = (chosen if chosen != "auto" else manager.hass.config.language) or "en"
    lang = lang.split("-")[0]
    return lang if lang in TEXT else "en"


def build_dashboard(manager: EaseeSmartManager) -> dict[str, Any]:
    """Lovelace config with every Easee Smart card, nicely grouped."""
    t = TEXT[_lang(manager)]
    own = manager.own_entities
    status = own.get("charger_status")
    if not status:
        raise HomeAssistantError("Easee Smart status sensor not ready yet")
    power = manager.charger_entities.get("power")

    def card(view: str | None = None, **extra: Any) -> dict[str, Any]:
        kind = f"custom:easee-smart-{view}-card" if view else "custom:easee-smart-card"
        return {"type": kind, "entity": status, **extra}

    def heading(text: str, icon: str) -> dict[str, Any]:
        return {"type": "heading", "heading": text, "icon": icon, "heading_style": "title"}

    def badge(key: str, *, entity: str | None = None, name: str | None = None) -> dict[str, Any] | None:
        eid = entity or own.get(key)
        if not eid:
            return None
        out: dict[str, Any] = {"type": "entity", "entity": eid, "show_name": bool(name), "show_state": True, "show_icon": True}
        if name:
            out["name"] = name
        return out

    badges = [
        badge("smart_status"),
        badge("current_price"),
        badge("surplus_power") or badge("grid_power"),
        badge("energy_today"),
        badge("cost_month"),
        badge("ere_month") if manager.ere_rate else None,
    ]
    for car in manager.cars:
        if car.soc_entity:
            badges.append(badge("", entity=car.soc_entity, name=car.name))
    badges = [b for b in badges if b]

    history_entities = [e for e in (power, own.get("grid_power"), own.get("target_current")) if e]
    energy_cards: list[dict[str, Any]] = [heading(t["history"], "mdi:chart-line")]
    if history_entities:
        energy_cards.append({"type": "history-graph", "title": t["power"], "hours_to_show": 24, "entities": history_entities})
    if own.get("current_price"):
        energy_cards.append({"type": "history-graph", "title": t["price"], "hours_to_show": 24,
                             "entities": [own["current_price"]]})

    month_tiles = [
        {"type": "tile", "entity": own[k], "vertical": True, "grid_options": {"columns": 6}}
        for k in ("energy_month", "cost_month", "average_price_month", "ere_month", "ere_year", "ere_total")
        if own.get(k) and (not k.startswith("ere") or manager.ere_rate)
    ]

    sections = [
        {"type": "grid", "cards": [heading(t["charger"], "mdi:ev-station"), card("charger")]},
        {"type": "grid", "cards": [heading(t["control"], "mdi:tune-variant"), card("modes"), card("cars")]},
        {"type": "grid", "cards": [heading(t["plan"], "mdi:calendar-clock"), card("plan")]},
    ]
    energy_sections = [
        {"type": "grid", "cards": [heading(t["grid"], "mdi:transmission-tower"), card("grid")]},
        {"type": "grid", "cards": [heading(t["costs"], "mdi:cash-multiple"), card("costs"),
                                   *([heading(t["month"], "mdi:calendar-month"), *month_tiles] if month_tiles else [])]},
        {"type": "grid", "cards": energy_cards},
    ]
    header = {
        "layout": "responsive",
        "badges_position": "bottom",
        "card": {"type": "markdown", "text_only": True,
                 "content": f"# {manager.name}\n{t['sub']}"},
    }
    return {
        "title": t["title"],
        "views": [
            {"title": t["charge"], "path": "laden", "icon": "mdi:ev-station", "type": "sections",
             "max_columns": 3, "dense_section_placement": True, "header": header, "badges": badges,
             "sections": sections},
            {"title": t["energy"], "path": "energie", "icon": "mdi:chart-box-outline", "type": "sections",
             "max_columns": 3, "dense_section_placement": True, "header": header, "badges": badges,
             "sections": energy_sections},
            {"title": t["all"], "path": "alles", "icon": "mdi:view-dashboard-outline", "type": "sections",
             "max_columns": 2, "sections": [{"type": "grid", "cards": [card(None, tab="charge")]}]},
        ],
    }


def _dashboards_collection(hass: HomeAssistant):
    """The storage collection behind lovelace/dashboards/* (no public accessor)."""
    from homeassistant.components import websocket_api

    handlers = hass.data.get(websocket_api.DOMAIN) or {}
    entry = handlers.get("lovelace/dashboards/create")
    if not entry:
        return None
    func = inspect.unwrap(entry[0])
    owner = getattr(func, "__self__", None)
    return getattr(owner, "storage_collection", None)


async def async_create_dashboard(manager: EaseeSmartManager, overwrite: bool = True) -> str:
    """Create (or refresh) the Easee Smart dashboard. Returns its url path."""
    from homeassistant.components.lovelace.const import LOVELACE_DATA

    hass = manager.hass
    config = build_dashboard(manager)
    url = DASHBOARD_URL if len(hass.config_entries.async_entries(DOMAIN)) <= 1 else f"{DASHBOARD_URL}-{manager.charger_id or manager.entry.entry_id}".lower()
    data = hass.data.get(LOVELACE_DATA)
    if data is None:
        raise HomeAssistantError("Lovelace is not loaded")
    store = data.dashboards.get(url)
    if store is None:
        coll = _dashboards_collection(hass)
        if coll is None:
            raise HomeAssistantError("Could not reach the dashboards collection")
        try:
            await coll.async_create_item(
                {"url_path": url, "title": config["title"], "icon": DASHBOARD_ICON,
                 "show_in_sidebar": True, "require_admin": False, "mode": "storage"}
            )
        except HomeAssistantError:
            raise
        except Exception as err:  # vol.Invalid etc.
            raise HomeAssistantError(str(err)) from err
        store = data.dashboards.get(url)
        if store is None:
            raise HomeAssistantError("Dashboard was not registered")
    elif not overwrite:
        return url
    await store.async_save(config)
    _LOGGER.info("Easee Smart dashboard written to /%s", url)
    return url
