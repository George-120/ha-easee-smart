"""Runtime manager: reads the Easee integration, runs smart charging, keeps sessions/costs."""

from __future__ import annotations

import asyncio
import csv
import io
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_DEVICE_ID,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .cars import Car, cars_from_options
from .const import (
    ACTIVE_CAR_AUTO,
    CHARGER_KEYS,
    CONF_BIDDING_ZONE,
    CONF_BOOST_RESET,
    CONF_CAR_REFRESH_MIN,
    CONF_CHARGER_DEVICE,
    CONF_EFFICIENCY,
    CONF_ENERGY_TAX,
    CONF_EQUALIZER_DEVICE,
    CONF_ERE_ENABLED,
    CONF_ERE_RATE,
    CONF_GRID_EXPORT_ENTITY,
    CONF_GRID_IMPORT_ENTITY,
    CONF_GRID_POWER_ENTITY,
    CONF_GRID_POWER_INVERTED,
    CONF_LANGUAGE,
    CONF_MAIN_FUSE,
    CONF_MARKUP,
    CONF_MAX_CURRENT,
    CONF_MIN_CURRENT,
    CONF_MODEL,
    CONF_NUDGE,
    CONF_PHASES,
    CONF_REIMBURSEMENT,
    CONF_SOLAR_BUFFER,
    CONF_SOLAR_START_DELAY,
    CONF_SOLAR_STOP_DELAY,
    CONF_VAT,
    CONF_VOLTAGE,
    CONNECTED_STATUSES,
    CONTROL_INTERVAL_S,
    CONTROL_REFRESH_S,
    CONTROL_TTL_MIN,
    DEFAULT_DEPARTURE,
    DEFAULT_EFFICIENCY,
    DEFAULT_MAIN_FUSE,
    DEFAULT_MAX_CURRENT,
    DEFAULT_PHASES,
    DEFAULT_TARGET_ENERGY,
    DEFAULT_TARGET_SOC,
    DEFAULT_VOLTAGE,
    EASEE_DOMAIN,
    EQUALIZER_KEYS,
    MAX_STORED_SESSIONS,
    MIN_CHARGE_CURRENT,
    MIN_SECONDS_BETWEEN_CHANGES,
    MODE_NORMAL,
    MODE_SMART,
    MODE_SOLAR,
    MODE_SOLAR_SMART,
    MODES,
    PHASE_ENTITY_KEYS,
    REPORT_DIR,
    SIGNAL_UPDATE,
    SMART_CHARGING_BOOST,
    SMART_CHARGING_CHEAP,
    SMART_CHARGING_FALLBACK,
    SMART_CHARGING_SOLAR,
    SMART_IDLE,
    SMART_NO_PRICES,
    SMART_NOT_CONNECTED,
    SMART_TARGET_REACHED,
    SMART_WAITING_CHEAP,
    SMART_WAITING_SOLAR,
    SOLAR_START_DELAY_S,
    SOLAR_STOP_DELAY_S,
    STATUS_DISCONNECTED,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .logic import (
    ChargePlan,
    PriceSlot,
    SolarRegulator,
    month_key,
    next_departure,
    plan_cheapest,
    power_for_amps,
    price_at,
)
from .prices import DayAheadPrices, default_zone, to_slots, zone_defaults

_LOGGER = logging.getLogger(__name__)


def easee_product_id(device: dr.DeviceEntry | None) -> str | None:
    """Return the Easee product id (serial) of an easee device."""
    if device is None:
        return None
    for ident in device.identifiers:
        # identifiers are normally (domain, id); some integrations store longer tuples
        if len(ident) >= 2 and ident[0] == EASEE_DOMAIN:
            return str(ident[1])
    return None


def resolve_entities(hass: HomeAssistant, product_id: str | None, keys: list[str]) -> dict[str, str]:
    """Map role -> entity_id using the unique ids of the easee integration."""
    if not product_id:
        return {}
    registry = er.async_get(hass)
    found: dict[str, str] = {}
    for key in keys:
        entity_id = _get_entity_id(registry, key, product_id)
        if entity_id:
            found[key] = entity_id
    return found


def _get_entity_id(registry: er.EntityRegistry, key: str, product_id: str) -> str | None:
    unique_id = f"{product_id}_{key}"
    for domain in ("sensor", "binary_sensor", "switch", "light", "button"):
        entity_id = registry.async_get_entity_id(domain, EASEE_DOMAIN, unique_id)
        if entity_id:
            return entity_id
    return None


def enable_disabled_entities(
    hass: HomeAssistant, product_id: str | None, keys: list[str]
) -> list[str]:
    """Enable entities of the easee integration that are disabled by default."""
    if not product_id:
        return []
    registry = er.async_get(hass)
    enabled: list[str] = []
    for key in keys:
        entity_id = _get_entity_id(registry, key, product_id)
        if not entity_id:
            continue
        entry = registry.async_get(entity_id)
        if entry and entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION:
            registry.async_update_entity(entity_id, disabled_by=None)
            enabled.append(entity_id)
    return enabled


@dataclass
class Settings:
    """User adjustable runtime settings (persisted)."""

    mode: str = MODE_NORMAL
    departure: str = DEFAULT_DEPARTURE
    target_energy: float = DEFAULT_TARGET_ENERGY
    target_soc: int = DEFAULT_TARGET_SOC
    active_car: str = ACTIVE_CAR_AUTO
    car_targets: dict = field(default_factory=dict)
    price_threshold: float | None = None
    boost: bool = False


@dataclass
class SessionTracker:
    """Charging session currently in progress."""

    start: str | None = None
    energy: float = 0.0
    cost: float = 0.0


@dataclass
class Snapshot:
    """Computed values shared with entities and the card."""

    status: str = "unknown"
    connected: bool = False
    power_kw: float | None = None
    session_energy: float | None = None
    lifetime_energy: float | None = None
    price: float | None = None
    prices: list[PriceSlot] = field(default_factory=list)
    plan: ChargePlan | None = None
    smart_state: str = SMART_IDLE
    target_current: int | None = None
    energy_needed: float | None = None
    surplus_kw: float | None = None
    grid_power_kw: float | None = None
    phase_currents: list[float | None] = field(default_factory=lambda: [None, None, None])
    phase_voltages: list[float | None] = field(default_factory=lambda: [None, None, None])
    main_fuse: float | None = None
    phase_headroom: float | None = None
    phase_load_pct: float | None = None


class EaseeSmartManager:
    """Coordinates everything for one charger."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY.format(entry.entry_id)
        )
        self.settings = Settings()
        self.session = SessionTracker()
        self.sessions: list[dict[str, Any]] = []
        self.days: dict[str, dict[str, float]] = {}
        self.totals = {"energy": 0.0, "cost": 0.0}
        self.last_lifetime: float | None = None
        self.snapshot = Snapshot()
        self.solar = SolarRegulator(
            min_current=MIN_CHARGE_CURRENT,
            max_current=DEFAULT_MAX_CURRENT,
            start_delay=SOLAR_START_DELAY_S,
            stop_delay=SOLAR_STOP_DELAY_S,
        )
        self._unsubs: list[CALLBACK_TYPE] = []
        self._controlling = False
        self._last_sent: int | None = None
        self._last_sent_at: datetime | None = None
        self._last_change_at: datetime | None = None
        self._stalled_since: datetime | None = None
        self._lock = asyncio.Lock()
        self._last_plugged: str | None = None
        self._last_car_refresh: datetime | None = None
        self._car_started_at: datetime | None = None
        self.charger_device_id: str = entry.data[CONF_CHARGER_DEVICE]
        self.equalizer_device_id: str | None = entry.data.get(CONF_EQUALIZER_DEVICE)
        devices = dr.async_get(hass)
        self.charger_device = devices.async_get(self.charger_device_id)
        self.equalizer_device = (
            devices.async_get(self.equalizer_device_id) if self.equalizer_device_id else None
        )
        self.charger_id = easee_product_id(self.charger_device)
        self.equalizer_id = easee_product_id(self.equalizer_device)
        self.day_ahead = DayAheadPrices(hass, self.zone)
        self.charger_entities: dict[str, str] = {}
        self.equalizer_entities: dict[str, str] = {}
        self.own_entities: dict[str, str] = {}

    # ------------------------------------------------------------------ options
    def _opt(self, key: str, default: Any = None) -> Any:
        if key in self.entry.options:
            return self.entry.options[key]
        return self.entry.data.get(key, default)

    @property
    def name(self) -> str:
        if self.charger_device:
            return self.charger_device.name_by_user or self.charger_device.name or "Easee"
        return "Easee"

    @property
    def model(self) -> str:
        return self._opt(CONF_MODEL) or (self.charger_device.model if self.charger_device else None) or "Easee"

    @property
    def phases(self) -> int:
        return int(self._opt(CONF_PHASES, DEFAULT_PHASES))

    @property
    def voltage(self) -> float:
        return float(self._opt(CONF_VOLTAGE, DEFAULT_VOLTAGE))

    @property
    def max_current(self) -> int:
        return int(self._opt(CONF_MAX_CURRENT, DEFAULT_MAX_CURRENT))

    @property
    def zone(self) -> str:
        return self._opt(CONF_BIDDING_ZONE) or default_zone(self.hass)

    def _price_parts(self) -> tuple[float, float, float]:
        defaults = zone_defaults(self.zone)
        markup = self._opt(CONF_MARKUP)
        tax = self._opt(CONF_ENERGY_TAX)
        vat = self._opt(CONF_VAT)
        return (
            float(markup) if markup not in (None, "") else 0.0,
            float(tax) if tax not in (None, "") else defaults["energy_tax"],
            float(vat) if vat not in (None, "") else defaults["vat"],
        )

    def _rebuild_prices(self) -> None:
        self.snapshot.prices = to_slots(self.day_ahead.points, *self._price_parts())

    @property
    def grid_entity(self) -> str | None:
        return self._opt(CONF_GRID_POWER_ENTITY) or None

    # ------------------------------------------------------------- advanced
    @property
    def min_current(self) -> int:
        return int(self._opt(CONF_MIN_CURRENT, MIN_CHARGE_CURRENT) or MIN_CHARGE_CURRENT)

    @property
    def efficiency(self) -> float:
        value = float(self._opt(CONF_EFFICIENCY, DEFAULT_EFFICIENCY) or DEFAULT_EFFICIENCY)
        return min(max(value, 50.0), 100.0) / 100

    @property
    def solar_buffer_kw(self) -> float:
        return float(self._opt(CONF_SOLAR_BUFFER, 0.0) or 0.0)

    def _apply_solar_settings(self) -> None:
        self.solar.min_current = self.min_current
        self.solar.max_current = self.max_current
        self.solar.start_delay = float(self._opt(CONF_SOLAR_START_DELAY, SOLAR_START_DELAY_S / 60) or 0) * 60
        self.solar.stop_delay = float(self._opt(CONF_SOLAR_STOP_DELAY, SOLAR_STOP_DELAY_S / 60) or 0) * 60

    # ----------------------------------------------------------------- cars
    @property
    def cars(self) -> list[Car]:
        return cars_from_options({**self.entry.data, **self.entry.options})

    @property
    def soc_entity(self) -> str | None:
        car = self.active_car()
        return car.soc_entity if car else None

    def _plugged(self, car: Car) -> bool | None:
        state = self._state(car.plug_entity)
        return None if state is None else state.state == "on"

    def active_car(self) -> Car | None:
        cars = self.cars
        if not cars:
            return None
        chosen = self.settings.active_car
        if chosen != ACTIVE_CAR_AUTO:
            for car in cars:
                if car.name == chosen:
                    return car
        plugged = [c for c in cars if self._plugged(c)]
        if len(plugged) == 1:
            return plugged[0]
        if self._last_plugged:
            for car in cars:
                if car.name == self._last_plugged:
                    return car
        return cars[0]

    def car_target(self, car: Car | None) -> int:
        if car is None:
            return self.settings.target_soc
        return int(self.settings.car_targets.get(car.name, car.target))

    def car_soc(self, car: Car | None) -> float | None:
        return self._float(car.soc_entity) if car else None

    @property
    def grid_import_entity(self) -> str | None:
        return self._opt(CONF_GRID_IMPORT_ENTITY) or None

    @property
    def grid_export_entity(self) -> str | None:
        return self._opt(CONF_GRID_EXPORT_ENTITY) or None

    @property
    def phase_entities(self) -> list[str | None]:
        return [self._opt(k) or None for k in PHASE_ENTITY_KEYS]

    @property
    def uses_meter(self) -> bool:
        """Main connection comes from the user's own meter instead of an Equalizer."""
        return not self.equalizer_entities and bool(
            self.grid_import_entity or self.grid_entity or any(self.phase_entities)
        )

    @property
    def has_surplus_source(self) -> bool:
        return bool(
            self.equalizer_entities.get("import_power") or self.grid_entity or self.grid_import_entity
        )

    @property
    def ere_rate(self) -> float | None:
        """ERE (emission reduction units) revenue per charged kWh, when enabled."""
        if not self._opt(CONF_ERE_ENABLED, False):
            return None
        value = self._opt(CONF_ERE_RATE)
        return float(value) if value not in (None, "") else 0.0

    def ere_earned(self, period: str) -> float | None:
        rate = self.ere_rate
        if rate is None:
            return None
        energy = self.totals["energy"] if period == "total" else self.period_totals(period)["energy"]
        return round(energy * rate, 2)

    @property
    def reimbursement(self) -> float | None:
        value = self._opt(CONF_REIMBURSEMENT)
        return float(value) if value not in (None, "") else None

    # ---------------------------------------------------------------- lifecycle
    async def async_setup(self) -> None:
        data = await self.store.async_load() or {}
        settings = data.get("settings", {})
        self.settings = Settings(
            mode=settings.get("mode", MODE_NORMAL) if settings.get("mode") in MODES else MODE_NORMAL,
            departure=settings.get("departure", DEFAULT_DEPARTURE),
            target_energy=float(settings.get("target_energy", DEFAULT_TARGET_ENERGY)),
            target_soc=int(settings.get("target_soc", DEFAULT_TARGET_SOC)),
            active_car=settings.get("active_car", ACTIVE_CAR_AUTO),
            car_targets=dict(settings.get("car_targets", {})),
            price_threshold=settings.get("price_threshold"),
            boost=bool(settings.get("boost", False)),
        )
        sess = data.get("session", {})
        self.session = SessionTracker(
            start=sess.get("start"), energy=sess.get("energy", 0.0), cost=sess.get("cost", 0.0)
        )
        self.sessions = data.get("sessions", [])
        self.days = data.get("days", {})
        self.totals = data.get("totals", {"energy": 0.0, "cost": 0.0})
        self.last_lifetime = data.get("last_lifetime")
        self._resolve()

    def _resolve(self) -> None:
        self.charger_entities = resolve_entities(self.hass, self.charger_id, CHARGER_KEYS)
        self.equalizer_entities = resolve_entities(self.hass, self.equalizer_id, EQUALIZER_KEYS)

    @callback
    def async_start(self) -> None:
        tracked = list(self.charger_entities.values()) + list(self.equalizer_entities.values())
        tracked += [
            e
            for e in (
                self.grid_entity,
                self.grid_import_entity,
                self.grid_export_entity,
                *[c.soc_entity for c in self.cars],
                *[c.plug_entity for c in self.cars],
                *self.phase_entities,
            )
            if e
        ]
        if tracked:
            self._unsubs.append(
                async_track_state_change_event(self.hass, tracked, self._handle_state_event)
            )
        self._unsubs.append(
            async_track_time_interval(
                self.hass, self._async_tick, timedelta(seconds=CONTROL_INTERVAL_S)
            )
        )
        self._recompute()
        self.hass.async_create_task(self._async_tick(dt_util.utcnow()))

    async def _async_refresh_prices(self) -> None:
        if await self.day_ahead.async_refresh():
            self._rebuild_prices()
            self._recompute()

    async def async_unload(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        if self._controlling:
            await self._async_restore_normal()
        await self.store.async_save(self._data_to_store())

    # ----------------------------------------------------------------- storage
    def _data_to_store(self) -> dict[str, Any]:
        return {
            "settings": self.settings.__dict__,
            "session": self.session.__dict__,
            "sessions": self.sessions[-MAX_STORED_SESSIONS:],
            "days": self.days,
            "totals": self.totals,
            "last_lifetime": self.last_lifetime,
        }

    def _save(self) -> None:
        self.store.async_delay_save(self._data_to_store, 10)

    # ------------------------------------------------------------- state reads
    def _state(self, entity_id: str | None):
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return None
        return state

    def _float(self, entity_id: str | None) -> float | None:
        state = self._state(entity_id)
        if state is None:
            return None
        try:
            return float(state.state)
        except (TypeError, ValueError):
            return None

    def _attr_float(self, entity_id: str | None, attr: str) -> float | None:
        state = self._state(entity_id)
        if state is None:
            return None
        try:
            value = state.attributes.get(attr)
            return None if value in (None, "") else float(value)
        except (TypeError, ValueError):
            return None

    def charger_value(self, key: str) -> float | None:
        return self._float(self.charger_entities.get(key))

    def equalizer_value(self, key: str) -> float | None:
        return self._float(self.equalizer_entities.get(key))

    def _power_kw(self, entity_id: str | None) -> float | None:
        state = self._state(entity_id)
        if state is None:
            return None
        try:
            value = float(state.state)
        except (TypeError, ValueError):
            return None
        unit = (state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) or "kW").lower()
        if unit == "w":
            value /= 1000
        elif unit == "mw":
            value *= 1000
        return value

    def current_price(self, now: datetime | None = None) -> float | None:
        now = now or dt_util.now()
        price = price_at(self.snapshot.prices, now) if self.snapshot.prices else None
        if price is not None:
            return price
        return self.charger_value("cost_per_kwh")

    def market_price(self, now: datetime | None = None) -> float | None:
        now = now or dt_util.now()
        for start, value in reversed(self.day_ahead.points):
            if start <= now:
                return round(value, 5)
        return None

    # -------------------------------------------------------------- recompute
    @callback
    def _handle_state_event(self, event: Event) -> None:
        entity_id = event.data.get("entity_id")
        if entity_id == self.charger_entities.get("lifetime_energy"):
            self._account_energy()
        if entity_id == self.charger_entities.get("status"):
            self._handle_status_change(event)
        for car in self.cars:
            new = event.data.get("new_state")
            if entity_id == car.plug_entity and new is not None and new.state == "on":
                self._last_plugged = car.name
        self._recompute()
        if entity_id in (
            self.charger_entities.get("status"),
            self.equalizer_entities.get("import_power"),
            self.equalizer_entities.get("export_power"),
            self.grid_entity,
            self.grid_import_entity,
            self.grid_export_entity,
        ):
            self.hass.async_create_task(self._async_control())

    def _recompute(self) -> None:
        snap = self.snapshot
        now = dt_util.now()
        status_state = self._state(self.charger_entities.get("status"))
        snap.status = status_state.state if status_state else "unknown"
        snap.connected = snap.status in CONNECTED_STATUSES
        snap.power_kw = self.charger_value("power")
        snap.session_energy = self.charger_value("session_energy")
        snap.lifetime_energy = self.charger_value("lifetime_energy")

        snap.price = self.current_price(now)

        # Equalizer / grid
        cur_entity = self.equalizer_entities.get("current")
        volt_entity = self.equalizer_entities.get("voltage")
        if self.equalizer_entities:
            snap.phase_currents = [
                self._attr_float(cur_entity, f"state_currentL{i}") for i in (1, 2, 3)
            ]
        else:
            snap.phase_currents = [self._float(e) for e in self.phase_entities]
        snap.phase_voltages = [
            self._attr_float(volt_entity, f"state_voltageNL{i}") for i in (1, 2, 3)
        ]
        fuse_entity = self.equalizer_entities.get("max_continuous_limit")
        if self.equalizer_entities:
            snap.main_fuse = self._float(fuse_entity) or self._attr_float(fuse_entity, "config_ratedCurrent")
        else:
            snap.main_fuse = float(self._opt(CONF_MAIN_FUSE, DEFAULT_MAIN_FUSE) or DEFAULT_MAIN_FUSE)
        valid = [c for c in snap.phase_currents if c is not None]
        if snap.main_fuse and valid:
            snap.phase_headroom = round(snap.main_fuse - max(valid), 1)
            snap.phase_load_pct = round(max(valid) / snap.main_fuse * 100, 0)
        else:
            snap.phase_headroom = None
            snap.phase_load_pct = None

        imp = self.equalizer_value("import_power")
        exp = self.equalizer_value("export_power")
        if imp is not None or exp is not None:
            snap.grid_power_kw = round((imp or 0.0) - (exp or 0.0), 3)
        elif self.grid_import_entity:
            imp_kw = self._power_kw(self.grid_import_entity)
            exp_kw = self._power_kw(self.grid_export_entity) if self.grid_export_entity else 0.0
            snap.grid_power_kw = (
                round((imp_kw or 0.0) - (exp_kw or 0.0), 3) if imp_kw is not None or exp_kw is not None else None
            )
        elif self.grid_entity:
            value = self._power_kw(self.grid_entity)
            if value is not None and self._opt(CONF_GRID_POWER_INVERTED, False):
                value = -value
            snap.grid_power_kw = round(value, 3) if value is not None else None
        else:
            snap.grid_power_kw = None
        snap.surplus_kw = -snap.grid_power_kw if snap.grid_power_kw is not None else None
        snap.energy_needed = self._energy_needed()
        async_dispatcher_send(self.hass, SIGNAL_UPDATE.format(self.entry.entry_id))

    def _energy_needed(self) -> float | None:
        """Energy still to deliver from the wall (battery energy / charging efficiency)."""
        car = self.active_car()
        soc = self.car_soc(car)
        if car is not None and soc is not None:
            battery = max(0.0, (self.car_target(car) - soc) / 100 * car.capacity)
            return round(battery / self.efficiency, 2)
        delivered = self.snapshot.session_energy if self.snapshot.connected else 0.0
        return round(max(0.0, self.settings.target_energy - (delivered or 0.0)), 2)

    # ------------------------------------------------------- energy & sessions
    def _account_energy(self) -> None:
        lifetime = self.charger_value("lifetime_energy")
        if lifetime is None:
            return
        if self.last_lifetime is None or lifetime < self.last_lifetime:
            self.last_lifetime = lifetime
            self._save()
            return
        delta = lifetime - self.last_lifetime
        if delta <= 0:
            return
        self.last_lifetime = lifetime
        if delta > 100:  # meter reset or first sync after a long gap
            self._save()
            return
        price = self.current_price()
        cost = delta * price if price is not None else 0.0
        today = dt_util.now().date().isoformat()
        bucket = self.days.setdefault(today, {"energy": 0.0, "cost": 0.0})
        bucket["energy"] = round(bucket["energy"] + delta, 4)
        bucket["cost"] = round(bucket["cost"] + cost, 4)
        self.totals["energy"] = round(self.totals["energy"] + delta, 4)
        self.totals["cost"] = round(self.totals["cost"] + cost, 4)
        if self.session.start:
            self.session.energy = round(self.session.energy + delta, 4)
            self.session.cost = round(self.session.cost + cost, 4)
        # keep ~14 months of daily buckets
        if len(self.days) > 430:
            for key in sorted(self.days)[: len(self.days) - 430]:
                self.days.pop(key)
        self._save()

    def _handle_status_change(self, event: Event) -> None:
        old = event.data.get("old_state")
        new = event.data.get("new_state")
        old_status = old.state if old else None
        new_status = new.state if new else None
        was = old_status in CONNECTED_STATUSES
        now_connected = new_status in CONNECTED_STATUSES
        if now_connected and not was and old_status not in (None, STATE_UNAVAILABLE, STATE_UNKNOWN):
            self._start_session()
        elif not now_connected and was and new_status == STATUS_DISCONNECTED:
            self._end_session()
        elif now_connected and not self.session.start:
            self._start_session()

    def _start_session(self) -> None:
        self.session = SessionTracker(start=dt_util.now().isoformat())
        self.solar.reset()
        self._save()

    def _end_session(self) -> None:
        if self.session.start:
            energy = self.snapshot.session_energy
            if energy is None or energy < self.session.energy:
                energy = self.session.energy
            record = {
                "start": self.session.start,
                "end": dt_util.now().isoformat(),
                "energy": round(energy, 3),
                "cost": round(self.session.cost, 2),
                "avg_price": round(self.session.cost / self.session.energy, 4)
                if self.session.energy
                else None,
            }
            if self.reimbursement is not None:
                record["reimbursement"] = round(energy * self.reimbursement, 2)
            self.sessions.append(record)
            self.sessions = self.sessions[-MAX_STORED_SESSIONS:]
        self.session = SessionTracker()
        if self._opt(CONF_BOOST_RESET, True):
            self.settings.boost = False
        self.solar.reset()
        self._save()

    # Aggregations for sensors / card
    def period_totals(self, period: str) -> dict[str, float]:
        today = dt_util.now().date()
        if period == "day":
            prefix = today.isoformat()
        elif period == "month":
            prefix = month_key(today)
        elif period == "prev_month":
            first = today.replace(day=1) - timedelta(days=1)
            prefix = month_key(first)
        elif period == "year":
            prefix = f"{today.year:04d}"
        else:
            return dict(self.totals)
        energy = sum(v["energy"] for k, v in self.days.items() if k.startswith(prefix))
        cost = sum(v["cost"] for k, v in self.days.items() if k.startswith(prefix))
        return {"energy": round(energy, 3), "cost": round(cost, 2)}

    def month_history(self, months: int = 12) -> list[dict[str, Any]]:
        out: dict[str, dict[str, float]] = {}
        for key, value in self.days.items():
            m = key[:7]
            bucket = out.setdefault(m, {"energy": 0.0, "cost": 0.0})
            bucket["energy"] += value["energy"]
            bucket["cost"] += value["cost"]
        result = []
        for m in sorted(out)[-months:]:
            entry = {"month": m, "energy": round(out[m]["energy"], 2), "cost": round(out[m]["cost"], 2)}
            if self.reimbursement is not None:
                entry["reimbursement"] = round(out[m]["energy"] * self.reimbursement, 2)
            result.append(entry)
        return result

    # ----------------------------------------------------------------- control
    async def _async_tick(self, _now: datetime) -> None:
        if self.day_ahead.needs_refresh(dt_util.now()):
            await self._async_refresh_prices()
        await self._async_periodic_car_refresh(dt_util.now())
        self._recompute()
        await self._async_control()

    async def _async_control(self) -> None:
        if self._lock.locked():
            return  # a control pass is already running; the next tick follows soon
        async with self._lock:
            await self._async_control_locked()

    async def _async_control_locked(self) -> None:
        snap = self.snapshot
        now = dt_util.now()
        mode = self.settings.mode
        self._apply_solar_settings()

        if mode == MODE_NORMAL and not self.settings.boost:
            snap.smart_state = SMART_IDLE
            snap.plan = None
            snap.target_current = None
            if self._controlling:
                await self._async_restore_normal()
            return

        if snap.status == "unknown" or not snap.connected:
            snap.smart_state = SMART_NOT_CONNECTED if snap.status != "unknown" else SMART_IDLE
            snap.plan = None
            snap.target_current = None
            self.solar.reset()
            return

        # "completed" while we hold the charger at 0 A is our own pause, not a full battery.
        held_by_us = self._controlling and (self._last_sent or 0) == 0
        if snap.status == "completed" and not self.settings.boost and not held_by_us:
            snap.smart_state = SMART_TARGET_REACHED
            snap.target_current = None
            return

        want = 0
        state = SMART_IDLE
        if self.settings.boost:
            want, state = self.max_current, SMART_CHARGING_BOOST
        else:
            want_smart = 0
            want_solar = 0
            needed = snap.energy_needed or 0.0
            if mode in (MODE_SMART, MODE_SOLAR_SMART):
                if needed <= 0:
                    snap.plan = None
                    state = SMART_TARGET_REACHED
                elif not snap.prices:
                    want_smart, state = self.max_current, SMART_NO_PRICES
                else:
                    departure = next_departure(now, _parse_time(self.settings.departure))
                    plan = plan_cheapest(
                        snap.prices,
                        now,
                        departure,
                        needed,
                        power_for_amps(self.max_current, self.phases, self.voltage),
                        self.settings.price_threshold,
                    )
                    snap.plan = plan
                    if plan.charge_now:
                        want_smart = self.max_current
                        state = SMART_CHARGING_FALLBACK if plan.fallback else SMART_CHARGING_CHEAP
                    else:
                        state = SMART_WAITING_CHEAP
            if mode in (MODE_SOLAR, MODE_SOLAR_SMART):
                if snap.surplus_kw is not None:
                    want_solar = self.solar.update(
                        now, snap.surplus_kw - self.solar_buffer_kw, snap.power_kw or 0.0, self.phases, self.voltage
                    )
                if mode == MODE_SOLAR:
                    state = SMART_CHARGING_SOLAR if want_solar > 0 else SMART_WAITING_SOLAR
                elif want_solar > 0 and want_solar >= want_smart:
                    state = SMART_CHARGING_SOLAR
            want = max(want_smart, want_solar)

        snap.smart_state = state
        snap.target_current = want
        await self._async_apply(want, now)
        async_dispatcher_send(self.hass, SIGNAL_UPDATE.format(self.entry.entry_id))

    async def _async_apply(self, want: int, now: datetime) -> None:
        changed = want != self._last_sent
        urgent = self._last_sent in (None, 0) and want > 0
        if not changed and self._last_sent_at and (now - self._last_sent_at).total_seconds() < CONTROL_REFRESH_S:
            await self._async_nudge(want, now)
            return
        if (
            changed
            and not urgent
            and self._last_change_at
            and (now - self._last_change_at).total_seconds() < MIN_SECONDS_BETWEEN_CHANGES
        ):
            return
        ok = await self._async_set_dynamic(want, CONTROL_TTL_MIN)
        if ok:
            self._controlling = True
            if changed:
                self._last_change_at = now
            self._last_sent = want
            self._last_sent_at = now

    async def _async_nudge(self, want: int, now: datetime) -> None:
        """Wake the car if we want charging but nothing flows (some cars sleep)."""
        snap = self.snapshot
        if not self._opt(CONF_NUDGE, True):
            return
        if want > 0 and snap.status in ("awaiting_start", "ready_to_charge") and (snap.power_kw or 0) < 0.2:
            self._stalled_since = self._stalled_since or now
            if (now - self._stalled_since).total_seconds() > 180:
                self._stalled_since = now
                await self.async_charger_command("resume")
                await self.async_force_car_start()
        else:
            self._stalled_since = None

    # ------------------------------------------------------------- car actions
    async def _async_action(self, entity_id: str | None) -> bool:
        """Press a button or turn on a switch/script/boolean of the car."""
        if not entity_id:
            return False
        domain = entity_id.split(".", 1)[0]
        service = {"button": "press", "input_button": "press"}.get(domain, "turn_on")
        try:
            await self.hass.services.async_call(domain, service, {"entity_id": entity_id}, blocking=True)
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Could not run %s.%s on %s: %s", domain, service, entity_id, err)
            return False
        return True

    async def async_force_car_start(self) -> bool:
        car = self.active_car()
        if car and car.start_entity:
            _LOGGER.debug("Forcing car %s to start charging via %s", car.name, car.start_entity)
            self._car_started_at = dt_util.now()
            return await self._async_action(car.start_entity)
        return False

    async def async_refresh_car(self) -> bool:
        car = self.active_car()
        if car and car.refresh_entity:
            self._last_car_refresh = dt_util.now()
            return await self._async_action(car.refresh_entity)
        return False

    async def _async_periodic_car_refresh(self, now: datetime) -> None:
        minutes = float(self._opt(CONF_CAR_REFRESH_MIN, 0) or 0)
        if minutes <= 0 or not self.snapshot.connected:
            return
        if self._last_car_refresh is None or (now - self._last_car_refresh).total_seconds() >= minutes * 60:
            await self.async_refresh_car()

    async def async_set_car_target(self, value: int) -> None:
        """Store the target for the active car and push it to the car's own charge limit."""
        car = self.active_car()
        if car is None:
            await self.async_set_setting("target_soc", int(value))
            return
        await self.async_set_setting("car_targets", {**self.settings.car_targets, car.name: int(value)})
        if car.limit_entity:
            domain = car.limit_entity.split(".", 1)[0]
            try:
                await self.hass.services.async_call(
                    domain, "set_value", {"entity_id": car.limit_entity, "value": int(value)}, blocking=True
                )
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("Could not set charge limit on %s: %s", car.limit_entity, err)

    async def _async_restore_normal(self) -> None:
        limit = self.charger_value("max_charger_limit") or self.max_current
        await self._async_set_dynamic(int(limit), 0)
        self._controlling = False
        self._last_sent = None
        self._last_sent_at = None

    async def _async_set_dynamic(self, current: int, ttl: int) -> bool:
        if not self.hass.services.has_service(EASEE_DOMAIN, "set_charger_dynamic_limit"):
            _LOGGER.warning("Easee integration services not available")
            return False
        try:
            await self.hass.services.async_call(
                EASEE_DOMAIN,
                "set_charger_dynamic_limit",
                {CONF_DEVICE_ID: self.charger_device_id, "current": int(current), "time_to_live": ttl},
                blocking=True,
            )
        except Exception as err:  # noqa: BLE001 - never let control crash the loop
            _LOGGER.warning("Could not set dynamic charger limit: %s", err)
            return False
        _LOGGER.debug("Dynamic charger limit set to %s A (ttl %s min)", current, ttl)
        return True

    async def async_charger_command(self, command: str) -> None:
        await self.hass.services.async_call(
            EASEE_DOMAIN,
            "action_command",
            {CONF_DEVICE_ID: self.charger_device_id, "action_command": command},
            blocking=True,
        )

    # --------------------------------------------------------------- settings
    async def async_set_setting(self, key: str, value: Any) -> None:
        setattr(self.settings, key, value)
        if key == "mode":
            self.solar.reset()
        self._last_change_at = None
        self._save()
        self._recompute()
        await self._async_control()

    # ----------------------------------------------------------------- report
    def sessions_for_month(self, month: str) -> list[dict[str, Any]]:
        return [s for s in self.sessions if str(s.get("start", "")).startswith(month)]

    async def async_export_report(self, month: str | None = None) -> dict[str, Any]:
        if not month:
            first = dt_util.now().date().replace(day=1) - timedelta(days=1)
            month = month_key(first)
        sessions = self.sessions_for_month(month)
        totals_energy = round(sum(s.get("energy", 0) for s in sessions), 3)
        totals_cost = round(sum(s.get("cost", 0) for s in sessions), 2)
        reimb = self.reimbursement
        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=";")
        writer.writerow(["charger", self.name, "model", self.model, "serial", self.charger_id or ""])
        writer.writerow(["month", month])
        writer.writerow([])
        ere = self.ere_rate
        writer.writerow(["start", "end", "energy_kwh", "cost", "avg_price_per_kwh", "reimbursement", "ere"])
        for s in sessions:
            writer.writerow(
                [
                    s.get("start"),
                    s.get("end"),
                    f"{s.get('energy', 0):.3f}".replace(".", ","),
                    f"{s.get('cost', 0):.2f}".replace(".", ","),
                    "" if s.get("avg_price") is None else f"{s['avg_price']:.4f}".replace(".", ","),
                    "" if reimb is None else f"{s.get('energy', 0) * reimb:.2f}".replace(".", ","),
                    "" if ere is None else f"{s.get('energy', 0) * ere:.2f}".replace(".", ","),
                ]
            )
        writer.writerow([])
        writer.writerow(
            [
                "total",
                "",
                f"{totals_energy:.3f}".replace(".", ","),
                f"{totals_cost:.2f}".replace(".", ","),
                "",
                "" if reimb is None else f"{totals_energy * reimb:.2f}".replace(".", ","),
                "" if ere is None else f"{totals_energy * ere:.2f}".replace(".", ","),
            ]
        )
        filename = f"{(self.charger_id or 'easee').lower()}-{month}.csv"
        folder = self.hass.config.path("www", REPORT_DIR)
        path = os.path.join(folder, filename)

        def _write() -> None:
            os.makedirs(folder, exist_ok=True)
            with open(path, "w", encoding="utf-8-sig", newline="") as handle:
                handle.write(buffer.getvalue())

        await self.hass.async_add_executor_job(_write)
        return {
            "month": month,
            "file": path,
            "url": f"/local/{REPORT_DIR}/{filename}",
            "sessions": len(sessions),
            "energy_kwh": totals_energy,
            "cost": totals_cost,
            "reimbursement": None if reimb is None else round(totals_energy * reimb, 2),
        }

    # ------------------------------------------------------------ card payload
    def _car_payload(self) -> dict[str, Any] | None:
        car = self.active_car()
        if car is None:
            return None
        rng = self._float(car.range_entity)
        return {
            "name": car.name,
            "image": car.image,
            "range_km": rng,
            "can_refresh": bool(car.refresh_entity),
            "soc": self.car_soc(car),
            "target": self.car_target(car),
            "capacity": car.capacity,
            "plugged": self._plugged(car),
        }

    def card_payload(self) -> dict[str, Any]:
        snap = self.snapshot
        plan = snap.plan
        now = dt_util.now()
        horizon = now - timedelta(hours=1)
        return {
            "model": self.model,
            "name": self.name,
            "charger_id": self.charger_id,
            "device_id": self.charger_device_id,
            "mode": self.settings.mode,
            "departure": self.settings.departure,
            "target_energy": self.settings.target_energy,
            "target_soc": self.car_target(self.active_car()),
            "car": self._car_payload(),
            "cars": [c.name for c in self.cars],
            "cars_detail": [
                {
                    "name": c.name,
                    "image": c.image,
                    "soc": self.car_soc(c),
                    "target": self.car_target(c),
                    "capacity": c.capacity,
                    "plugged": self._plugged(c),
                    "range_km": self._float(c.range_entity),
                }
                for c in self.cars
            ],
            "active_car_setting": self.settings.active_car,
            "boost": self.settings.boost,
            "smart_state": snap.smart_state,
            "currency": self.hass.config.currency,
            "language": self._opt(CONF_LANGUAGE) or "auto",
            "phases": self.phases,
            "max_current": self.max_current,
            "sources": self.charger_entities,
            "equalizer": self.equalizer_entities,
            "entities": self.own_entities,
            "price": snap.price,
            "market_price": self.market_price(),
            "zone": self.zone,
            "price_parts": dict(zip(("markup", "energy_tax", "vat"), self._price_parts(), strict=True)),
            "prices": [
                {"start": s.start.isoformat(), "end": s.end.isoformat(), "price": s.price}
                for s in snap.prices
                if s.end > horizon
            ][:200],
            "plan": [
                {"start": s.start.isoformat(), "end": s.end.isoformat(), "price": s.price}
                for s in (plan.slots if plan else [])
            ],
            "plan_cost": plan.estimated_cost if plan else None,
            "plan_avg_price": plan.average_price if plan else None,
            "next_start": plan.next_start.isoformat() if plan and plan.next_start else None,
            "complete_by": plan.complete_by.isoformat() if plan and plan.complete_by else None,
            "energy_needed": snap.energy_needed,
            "target_current": snap.target_current,
            "surplus_kw": snap.surplus_kw,
            "grid_power_kw": snap.grid_power_kw,
            "phase_currents": snap.phase_currents,
            "phase_voltages": snap.phase_voltages,
            "main_fuse": snap.main_fuse,
            "phase_headroom": snap.phase_headroom,
            "session": {
                "start": self.session.start,
                "energy": snap.session_energy,
                "cost": round(self.session.cost, 2),
            },
            "today": self.period_totals("day"),
            "month": self.period_totals("month"),
            "months": self.month_history(12),
            "sessions": list(reversed(self.sessions[-15:])),
            "reimbursement_per_kwh": self.reimbursement,
            "ere": None if self.ere_rate is None else {
                "rate": self.ere_rate,
                "month": self.ere_earned("month"),
                "year": self.ere_earned("year"),
                "total": self.ere_earned("total"),
            },
            "has_surplus_source": self.has_surplus_source,
            "uses_meter": self.uses_meter,
            "meter": {
                "import": self.grid_import_entity,
                "export": self.grid_export_entity,
                "net": self.grid_entity,
            },
            "has_soc": bool(self.cars),
        }


def _parse_time(value: str) -> time:
    try:
        parts = [int(p) for p in str(value).split(":")[:2]]
        return time(parts[0], parts[1] if len(parts) > 1 else 0)
    except (ValueError, IndexError):
        return time(7, 0)
