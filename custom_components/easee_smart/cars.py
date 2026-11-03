"""Cars: open for every brand. Each car is a set of entities from any integration."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

MAX_CARS = 6
DEFAULT_CAPACITY = 60.0
DEFAULT_CAR_TARGET = 80
CONF_CARS = "cars"

# Fields of one car (stored as a dict in options["cars"])
F_NAME = "name"
F_DEVICE = "device_id"
F_IMAGE = "image"
F_SOC = "soc"
F_CAPACITY = "capacity"
F_TARGET = "target"
F_PLUG = "plug"
F_START = "start_entity"
F_REFRESH = "refresh_entity"
F_LIMIT = "limit_entity"
F_RANGE = "range_entity"
ENTITY_FIELDS = (F_SOC, F_PLUG, F_START, F_REFRESH, F_LIMIT, F_RANGE)

# Domains that can be "pressed" or "turned on"
ACTION_DOMAINS = ["switch", "button", "script", "input_boolean", "input_button"]


@dataclass(frozen=True)
class Car:
    """One car the charger can see."""

    index: int
    name: str
    soc_entity: str | None
    capacity: float
    plug_entity: str | None
    target: int
    image: str | None = None
    device_id: str | None = None
    start_entity: str | None = None
    refresh_entity: str | None = None
    limit_entity: str | None = None
    range_entity: str | None = None
    raw: dict = field(default_factory=dict, compare=False)


def car_from_dict(index: int, d: dict[str, Any]) -> Car:
    return Car(
        index=index,
        name=(d.get(F_NAME) or "").strip() or f"Auto {index + 1}",
        soc_entity=d.get(F_SOC) or None,
        capacity=float(d.get(F_CAPACITY) or DEFAULT_CAPACITY),
        plug_entity=d.get(F_PLUG) or None,
        target=int(d.get(F_TARGET) or DEFAULT_CAR_TARGET),
        image=(d.get(F_IMAGE) or "").strip() or None,
        device_id=d.get(F_DEVICE) or None,
        start_entity=d.get(F_START) or None,
        refresh_entity=d.get(F_REFRESH) or None,
        limit_entity=d.get(F_LIMIT) or None,
        range_entity=d.get(F_RANGE) or None,
        raw=dict(d),
    )


def cars_from_options(opts: dict[str, Any]) -> list[Car]:
    """Configured cars; migrates the single battery sensor of v1.3."""
    raw = opts.get(CONF_CARS)
    if isinstance(raw, list):
        return [car_from_dict(i, d) for i, d in enumerate(raw) if isinstance(d, dict)]
    if opts.get("soc_entity"):
        return [
            car_from_dict(
                0,
                {F_NAME: "Auto 1", F_SOC: opts["soc_entity"], F_CAPACITY: opts.get("battery_capacity")},
            )
        ]
    return []


# --------------------------------------------------------------------- detect
NOT_A_CAR = re.compile(
    r"iphone|ipad|phone|pixel|galaxy_s|watch|tablet|laptop|macbook|airpods|remote|"
    r"door|window|motion|thermostat|smoke|bms|powerwall|home_battery|thuisaccu|victron|"
    r"inverter|ups|energysocket|p1_meter",
    re.I,
)
SOC_HINT = re.compile(r"ev_battery_level|state_of_charge|\bsoc\b|_soc|battery_level|charge_level|accuniveau|battery", re.I)
SOC_EXCLUDE = re.compile(r"soh|health|gezondheid|target|doel|limit|range|temperature|12v|aux|capacity|voltage", re.I)
PLUG_HINT = re.compile(r"plug|cable|kabel|stekker|charger_connected|connected_to_charger|plugged", re.I)
START_HINT = re.compile(r"start_charg|charge_start|charging_start|^switch\..*charg(e|ing|er)(_switch)?$|laden_starten|charge_control", re.I)
START_EXCLUDE = re.compile(r"climate|heat|defrost|seat|window|steering|port|schedule|limit", re.I)
REFRESH_HINT = re.compile(r"force_update|refresh|update_data|request_update|wake|ververs|poll|sync", re.I)
LIMIT_HINT = re.compile(r"charge_limit|charging_limit|target_soc|target_state_of_charge|ac_charging_limit|charge_target|max_soc|laadlimiet|laaddoel", re.I)
RANGE_HINT = re.compile(r"range|actieradius|bereik", re.I)


def _dc(hass: HomeAssistant, entry: er.RegistryEntry) -> str | None:
    state = hass.states.get(entry.entity_id)
    if state is not None and state.attributes.get("device_class"):
        return state.attributes["device_class"]
    return entry.device_class or entry.original_device_class


def _unit(hass: HomeAssistant, entry: er.RegistryEntry) -> str | None:
    state = hass.states.get(entry.entity_id)
    return state.attributes.get("unit_of_measurement") if state else entry.unit_of_measurement


def _usable(hass: HomeAssistant, entity_id: str) -> bool:
    state = hass.states.get(entity_id)
    return state is not None and state.state not in ("unavailable",)


def _pick(entries: list[er.RegistryEntry], regex: re.Pattern, exclude: re.Pattern | None = None) -> str | None:
    hits = [
        e for e in entries
        if regex.search(e.entity_id) or regex.search(str(e.original_name or "")) or regex.search(str(e.translation_key or ""))
    ]
    if exclude:
        hits = [e for e in hits if not exclude.search(e.entity_id)]
    return sorted(hits, key=lambda e: e.entity_id)[0].entity_id if hits else None


def detect_car_entities(hass: HomeAssistant, device_id: str) -> dict[str, Any]:
    """Guess every entity Easee Smart can use from one car device (any brand)."""
    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get(device_id)
    entries = [
        e for e in er.async_entries_for_device(ent_reg, device_id)
        if not e.disabled_by
    ]
    out: dict[str, Any] = {F_DEVICE: device_id}
    if device:
        out[F_NAME] = device.name_by_user or device.name

    sensors = [e for e in entries if e.domain == "sensor"]
    socs = [
        e for e in sensors
        if (_dc(hass, e) == "battery" or _unit(hass, e) == "%")
        and SOC_HINT.search(f"{e.entity_id} {e.original_name or ''} {e.translation_key or ''}")
        and not SOC_EXCLUDE.search(e.entity_id)
        and _usable(hass, e.entity_id)
    ]
    if socs:
        best = sorted(
            socs,
            key=lambda e: (0 if re.search(r"ev_battery_level|state_of_charge|soc", e.entity_id) else 1, e.entity_id),
        )[0]
        out[F_SOC] = best.entity_id

    plugs = [e for e in entries if e.domain == "binary_sensor" and (_dc(hass, e) == "plug" or PLUG_HINT.search(e.entity_id))]
    if plugs:
        out[F_PLUG] = sorted(plugs, key=lambda e: (0 if _dc(hass, e) == "plug" else 1, e.entity_id))[0].entity_id

    actions = [e for e in entries if e.domain in ("switch", "button")]
    start = _pick(actions, START_HINT, START_EXCLUDE)
    if start:
        out[F_START] = start
    refresh = _pick([e for e in entries if e.domain == "button"], REFRESH_HINT)
    if refresh:
        out[F_REFRESH] = refresh
    limit = _pick([e for e in entries if e.domain == "number"], LIMIT_HINT)
    if limit:
        out[F_LIMIT] = limit
    rng = _pick([e for e in sensors if _dc(hass, e) == "distance" or RANGE_HINT.search(e.entity_id)], RANGE_HINT, re.compile(r"total|odometer|kilometerstand", re.I))
    if rng:
        out[F_RANGE] = rng

    for e in entries:  # a picture the integration already provides (Tesla, VW, Mercedes …)
        state = hass.states.get(e.entity_id)
        if state is not None and state.attributes.get("entity_picture"):
            out[F_IMAGE] = state.attributes["entity_picture"]
            break
    return out


def suggest_car_devices(hass: HomeAssistant, exclude: set[str] | None = None) -> list[str]:
    """Devices that look like a car: they have an EV battery level sensor."""
    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)
    exclude = exclude or set()
    found: list[str] = []
    for e in ent_reg.entities.values():
        if (
            e.domain != "sensor"
            or e.disabled_by
            or not e.device_id
            or e.device_id in exclude
            or e.device_id in found
            or _dc(hass, e) != "battery"
            or not re.search(r"ev_battery|state_of_charge|\bsoc\b|_soc", e.entity_id, re.I)
            or SOC_EXCLUDE.search(e.entity_id)
            or NOT_A_CAR.search(e.entity_id)
            or not _usable(hass, e.entity_id)
        ):
            continue
        device = dev_reg.async_get(e.device_id)
        label = f"{device.name_by_user or device.name or ''} {device.model or ''}" if device else ""
        if NOT_A_CAR.search(label):
            continue
        found.append(e.device_id)
    return found
