"""Ready-made Lovelace dashboard, created with one button press.

Home Assistant has no public Python API to add a storage dashboard, so we use the
same collection the frontend talks to (reached through its websocket command).
"""

from __future__ import annotations

import inspect
import json
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import CARD_BASE, DOMAIN

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
        "b_mode": "Modus", "b_price": "Stroomprijs", "b_surplus": "Zon over", "b_grid": "Net", "b_today": "Geladen vandaag", "b_cost": "Kosten maand", "b_ere": "ERE maand",
    },
    "en": {
        "title": "Easee Smart", "charge": "Charging", "energy": "Energy & costs", "all": "All in one",
        "charger": "Charger", "control": "Controls", "plan": "Planning", "grid": "Grid connection",
        "costs": "Costs", "history": "Last 24 hours", "price": "Price today", "power": "Charging power",
        "month": "This month", "sub": "Smart charging with your Easee",
        "b_mode": "Mode", "b_price": "Price", "b_surplus": "Solar surplus", "b_grid": "Grid", "b_today": "Charged today", "b_cost": "Costs month", "b_ere": "ERE month",
    },
    "de": {
        "title": "Easee Smart", "charge": "Laden", "energy": "Energie & Kosten", "all": "Alles in einem",
        "charger": "Ladestation", "control": "Steuerung", "plan": "Planung", "grid": "Netzanschluss",
        "costs": "Kosten", "history": "Letzte 24 Stunden", "price": "Preis heute", "power": "Ladeleistung",
        "month": "Dieser Monat", "sub": "Intelligent laden mit deiner Easee",
        "b_mode": "Modus", "b_price": "Strompreis", "b_surplus": "PV-Überschuss", "b_grid": "Netz", "b_today": "Heute geladen", "b_cost": "Kosten Monat", "b_ere": "ERE Monat",
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
        badge("smart_status", name=t["b_mode"]),
        badge("current_price", name=t["b_price"]),
        badge("surplus_power", name=t["b_surplus"]) or badge("grid_power", name=t["b_grid"]),
        badge("energy_today", name=t["b_today"]),
        badge("cost_month", name=t["b_cost"]),
        badge("ere_month", name=t["b_ere"]) if manager.ere_rate else None,
    ]
    for car in manager.cars:
        if car.soc_entity:
            badges.append(badge("", entity=car.soc_entity, name=car.name))
    badges = [b for b in badges if b]

    sections = [
        {"type": "grid", "cards": [heading(t["charger"], "mdi:ev-station"), card("charger")]},
        {"type": "grid", "cards": [heading(t["control"], "mdi:tune-variant"), card("modes"), card("cars")]},
        {"type": "grid", "cards": [heading(t["plan"], "mdi:calendar-clock"), card("plan")]},
    ]
    energy_sections = [
        {"type": "grid", "cards": [heading(t["grid"], "mdi:transmission-tower"),
                                   *([card("equalizer")] if getattr(manager, "show_equalizer", False) else []),
                                   card("grid")]},
        {"type": "grid", "cards": [heading(t["costs"], "mdi:cash-multiple"), card("costs")]},
    ]
    header = {
        "layout": "responsive",
        "badges_position": "bottom",
        "card": {"type": "markdown", "text_only": True,
                 "content": (
                     f'# <img src="{CARD_BASE}/logo.png" width="44" height="44" alt=""> Easee Smart Charging\n'
                     f"{manager.name}{' · ' + manager.model if manager.model else ''} — {t['sub']}"
                 )},
    }
    return {
        "title": t["title"],
        "views": [
            {"title": t["charge"], "path": "laden", "icon": "mdi:ev-station", "type": "sections",
             "max_columns": 3, "dense_section_placement": True, "header": header, "badges": badges,
             "sections": sections},
            {"title": t["energy"], "path": "energie", "icon": "mdi:chart-box-outline", "type": "sections",
             "max_columns": 2, "dense_section_placement": True, "header": header, "badges": badges,
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


STORE_KEY = f"{DOMAIN}.dashboards"
STORE_VERSION = 1
MARKER = f"{CARD_BASE}/logo.png"  # in the header of every dashboard we generate


def _looks_like_ours(config: dict[str, Any] | None) -> bool:
    """Dashboards made by 1.5.0-1.5.4 (before ownership was recorded): our header, only our cards."""
    if not isinstance(config, dict):
        return False
    views = config.get("views") or []
    if not views:
        return False
    for view in views:
        header = json.dumps(view.get("header") or {})
        cards = [c for sec in view.get("sections") or [] for c in sec.get("cards") or []]
        if view is views[0] and MARKER not in header:
            return False
        for card in cards:
            kind = str(card.get("type", ""))
            if not (kind.startswith("custom:easee-smart") or kind == "heading"):
                return False
    return True


def _url_taken(hass: HomeAssistant, data: Any, url: str) -> bool:
    from homeassistant.components.frontend import async_panel_exists

    return url in data.dashboards or async_panel_exists(hass, url)


async def async_create_dashboard(manager: EaseeSmartManager) -> str:
    """Create the Easee Smart dashboard, or refresh the one this integration created.

    A dashboard the user made (or any dashboard we did not create) is never overwritten:
    when the preferred url is taken we pick the next free one.
    """
    from homeassistant.components.lovelace.const import LOVELACE_DATA
    from homeassistant.helpers.storage import Store

    hass = manager.hass
    data = hass.data.get(LOVELACE_DATA)
    if data is None:
        raise HomeAssistantError("Lovelace is not loaded")
    config = build_dashboard(manager)
    entry_id = manager.entry.entry_id

    store: Store = Store(hass, STORE_VERSION, STORE_KEY)
    owned: dict[str, str] = ((await store.async_load()) or {}).get("owned", {})

    base = DASHBOARD_URL if len(hass.config_entries.async_entries(DOMAIN)) <= 1 else f"{DASHBOARD_URL}-{manager.charger_id or entry_id}".lower()
    url = owned.get(entry_id)
    if url and url in data.dashboards:
        target = data.dashboards[url]  # ours: refresh it
    else:
        url = None
        # adopt a dashboard an earlier version created before ownership was recorded
        existing = data.dashboards.get(base)
        if existing is not None and base not in owned.values():
            try:
                current = await existing.async_load(False)
            except Exception:  # noqa: BLE001 - empty or unreadable config: not ours
                current = None
            if _looks_like_ours(current):
                url = base
        if url is None:
            url = base
            n = 2
            while _url_taken(hass, data, url):
                url = f"{base}-{n}"
                n += 1
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
        target = data.dashboards.get(url)
        if target is None:
            raise HomeAssistantError("Dashboard was not registered")
        owned[entry_id] = url
        await store.async_save({"owned": owned})

    await target.async_save(config)
    _LOGGER.info("Easee Smart dashboard written to /%s", url)
    return url
