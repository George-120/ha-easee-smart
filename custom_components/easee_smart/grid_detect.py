"""Find the sensors of a smart meter (P1) so the main connection is filled in automatically."""

from __future__ import annotations

import re

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_GRID_EXPORT_ENTITY,
    CONF_GRID_IMPORT_ENTITY,
    CONF_GRID_POWER_ENTITY,
    CONF_PHASE_L1_ENTITY,
    CONF_PHASE_L2_ENTITY,
    CONF_PHASE_L3_ENTITY,
)

# Integrations that read the grid meter itself, best first.
METER_PLATFORMS = (
    "homewizard",  # most accurate: reads the P1 port every second
    "dsmr",
    "dsmr_reader",
    "p1_monitor",
    "zonneplan_one",
    "tibber",
    "slimmelezer",
    "esphome",
    "enphase_envoy",
)

IMPORT_PATTERNS = (
    r"power_consumption$",
    r"electricity_consumption$",
    r"current_electricity_usage$",
    r"electricity_currently_delivered$",
    r"power_delivered$",
    r"active_power_import",
)
EXPORT_PATTERNS = (
    r"power_production$",
    r"electricity_production$",
    r"current_electricity_delivery$",
    r"electricity_currently_returned$",
    r"power_returned$",
    r"active_power_export",
)
NET_PATTERNS = (
    r"active_power_w$",  # HomeWizard P1: positive = import
    r"net_power_consumption$",  # Enphase consumption CT: positive = import
    r"p1.*_power$",
    r"active_power$",
    r"_power$",
)
PHASE_PATTERNS = (
    r"active_current_l{n}_a$",  # HomeWizard P1
    r"current_phase_l{n}$",
    r"active_current_l{n}",
    r"phase_currently_delivered_l{n}_a",
    r"current_l{n}$",
    r"_l{n}_current$",
)

# Entities that look like a meter but are solar production, not grid export.
EXCLUDE = re.compile(r"inverter|production_ct|forecast|next_|_today|easee|charger|socket|plug")


def suggest_grid_sensors(hass: HomeAssistant) -> dict[str, str]:
    """Best guess of import / export (or net) and phase-current sensors."""
    registry = er.async_get(hass)
    by_platform: dict[str, list[er.RegistryEntry]] = {}
    for entry in registry.entities.values():
        if entry.domain != "sensor" or entry.disabled_by or EXCLUDE.search(entry.entity_id):
            continue
        if entry.platform in METER_PLATFORMS:
            by_platform.setdefault(entry.platform, []).append(entry)

    for platform in METER_PLATFORMS:
        entries = by_platform.get(platform)
        if not entries:
            continue
        # Platforms with several device types (HomeWizard sockets, kWh meters): prefer the P1 meter.
        p1 = [e for e in entries if "p1" in e.entity_id.lower() or "p1" in str(e.unique_id).lower()]
        if p1:
            entries = p1
        power = [e for e in entries if _device_class(hass, e) == "power"]
        current = [e for e in entries if _device_class(hass, e) == "current"]
        found: dict[str, str] = {}
        imp = _first(power, IMPORT_PATTERNS)
        exp = _first(power, EXPORT_PATTERNS)
        if imp and exp and platform != "enphase_envoy":
            found[CONF_GRID_IMPORT_ENTITY] = imp
            found[CONF_GRID_EXPORT_ENTITY] = exp
        else:
            net = _first(power, NET_PATTERNS if platform != "enphase_envoy" else (r"net_power_consumption$",))
            if net:
                found[CONF_GRID_POWER_ENTITY] = net
        for n, key in ((1, CONF_PHASE_L1_ENTITY), (2, CONF_PHASE_L2_ENTITY), (3, CONF_PHASE_L3_ENTITY)):
            phase = _first(current, tuple(p.format(n=n) for p in PHASE_PATTERNS))
            if phase:
                found[key] = phase
        if CONF_GRID_IMPORT_ENTITY in found or CONF_GRID_POWER_ENTITY in found:
            return found
    return {}


def _device_class(hass: HomeAssistant, entry: er.RegistryEntry) -> str | None:
    state = hass.states.get(entry.entity_id)
    if state is not None and state.attributes.get("device_class"):
        return state.attributes["device_class"]
    return entry.device_class or entry.original_device_class


def _first(entries: list[er.RegistryEntry], patterns: tuple[str, ...]) -> str | None:
    for pattern in patterns:
        regex = re.compile(pattern)
        for entry in sorted(entries, key=lambda e: e.entity_id):
            if regex.search(entry.entity_id) or (entry.unique_id and regex.search(str(entry.unique_id))):
                return entry.entity_id
    return None
