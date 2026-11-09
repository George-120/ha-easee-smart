"""Runtime manager: reads the Easee integration, runs smart charging, keeps sessions/costs."""

from __future__ import annotations

import asyncio
import csv
import io
import logging
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Any

from homeassistant.components import persistent_notification
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
    async_call_later,
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
    CONF_NO_PRICES,
    CONF_NUDGE,
    CONF_PHASE_CONFIRM,
    CONF_PHASE_INTERVAL,
    CONF_PHASE_SWITCHING,
    CONF_PHASES,
    CONF_PRICE_RESOLUTION,
    CONF_PV_FORECAST,
    CONF_PV_FORECAST_SENSOR,
    CONF_PV_KWP,
    CONF_PV_POWER,
    CONF_REIMBURSEMENT,
    CONF_SESSION_MODE,
    CONF_SHOW_EQUALIZER,
    CONF_SOLAR_BUFFER,
    CONF_SOLAR_START_DELAY,
    CONF_SOLAR_STOP_DELAY,
    CONF_TEST_CHARGE,
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
    DEFAULT_PHASE_CONFIRM_MIN,
    DEFAULT_PHASE_INTERVAL_MIN,
    DEFAULT_PHASES,
    DEFAULT_TARGET_ENERGY,
    DEFAULT_TARGET_SOC,
    DEFAULT_VOLTAGE,
    DOMAIN,
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
    NO_EQUALIZER,
    NO_PRICES_WAIT,
    PHASE_ENTITY_KEYS,
    PHASE_MODE_1,
    PHASE_MODE_3,
    PHASE_MODE_AUTO,
    PHASE_RESTART_DELAY_S,
    PV_FORECAST_OWN,
    PV_FORECAST_REFRESH_S,
    PV_FORECAST_SENSOR,
    RESOLUTION_HOUR,
    SESSION_MODE_KEEP,
    SIGNAL_UPDATE,
    SMART_CHARGING_BOOST,
    SMART_CHARGING_CHEAP,
    SMART_CHARGING_FALLBACK,
    SMART_CHARGING_SOLAR,
    SMART_IDLE,
    SMART_NO_PRICES,
    SMART_NOT_CONNECTED,
    SMART_TARGET_REACHED,
    SMART_TEST_CHARGE,
    SMART_TEST_FAILED,
    SMART_WAITING_CHEAP,
    SMART_WAITING_SOLAR,
    SOLAR_START_DELAY_S,
    SOLAR_STOP_DELAY_S,
    SOLAR_TRUST,
    STATUS_DISCONNECTED,
    STORAGE_KEY,
    STORAGE_VERSION,
    TEST_CHARGE_SECONDS,
    TEST_CHARGE_TIMEOUT_S,
    VERSION,
)
from .logic import (
    ChargePlan,
    PhaseSwitcher,
    PriceSlot,
    SolarRegulator,
    charge_schedule,
    hours_between,
    month_key,
    next_departure,
    plan_cheapest,
    power_for_amps,
    price_at,
    solar_energy_until,
    solar_outlook,
)
from .prices import DayAheadPrices, default_zone, to_hourly, to_slots, zone_defaults

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
    manual_kwh: bool = False  # charge a fixed number of kWh, also when a car with a battery level is linked


@dataclass
class SessionTracker:
    """Charging session currently in progress."""

    start: str | None = None
    energy: float = 0.0
    cost: float = 0.0
    peak_kw: float = 0.0  # highest power seen while the charger was allowed its full current
    tested: bool = False  # the test charge for this session is done (or not needed)


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
    plan_preview: ChargePlan | None = None
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
        self.phase_switch = PhaseSwitcher()
        self.solar_forecast = None  # SolarForecast when "own" forecast is chosen
        self.house_profile: dict[int, float] = {}  # local hour -> learned house use (kW)
        self.car_peaks: dict[str, list[float]] = {}  # car name -> peak charging power of recent sessions
        self._save_pending = False
        self._rerun = False
        self._phase_retry_after: datetime | None = None
        self._departure_moved = False
        self._sticky_departure: tuple[str, datetime, bool] | None = None
        self._house_sampled_at: datetime | None = None
        self.solar_slots: list = []
        self.history: dict[str, list[float]] = {}  # quarter start (UTC ISO) -> [kWh from grid, kWh from sun]
        self._history_at: datetime | None = None
        self.active_phases: int | None = None  # what we set on the charger (None = untouched)
        self._phase_original: str | None = None  # the charger's own phase mode before we changed it
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
        # per car: (soc, lifetime kWh, session kWh) at the moment the car last reported a new SoC
        self._soc_ref: dict[int, tuple[float, float | None, float | None]] = {}
        # short test charge at the start of a session: None (not done), running, ok, failed
        self._test_state: str | None = None
        self._test_since: datetime | None = None
        self._test_flow_since: datetime | None = None
        self._test_woken = False
        self._test_stop = False
        self.charger_device_id: str = entry.data[CONF_CHARGER_DEVICE]
        # Options win over setup data, so an Equalizer can be added or removed later.
        eq = {**entry.data, **entry.options}.get(CONF_EQUALIZER_DEVICE)
        self.equalizer_device_id: str | None = None if eq in (None, "", NO_EQUALIZER) else eq
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
        """Configured maximum, never above the charger's own maximum limit (set in the Easee app)."""
        configured = int(self._opt(CONF_MAX_CURRENT, DEFAULT_MAX_CURRENT))
        charger = self.charger_value("max_charger_limit")
        if charger is not None and charger >= 6:
            return max(6, min(configured, int(charger)))
        return configured

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
        slots = to_slots(self.day_ahead.points, *self._price_parts())
        if self._opt(CONF_PRICE_RESOLUTION) == RESOLUTION_HOUR:
            slots = to_hourly(slots)
        self.snapshot.prices = slots

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
        self.phase_switch.min_current = self.min_current
        self.phase_switch.confirm_s = float(self._opt(CONF_PHASE_CONFIRM, DEFAULT_PHASE_CONFIRM_MIN) or 0) * 60
        self.phase_switch.min_interval_s = float(self._opt(CONF_PHASE_INTERVAL, DEFAULT_PHASE_INTERVAL_MIN) or 0) * 60
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
            manual_kwh=bool(settings.get("manual_kwh", False)),
        )
        sess = data.get("session", {})
        self.session = SessionTracker(
            start=sess.get("start"), energy=sess.get("energy", 0.0), cost=sess.get("cost", 0.0),
            peak_kw=float(sess.get("peak_kw") or 0.0), tested=bool(sess.get("tested", True)),
        )
        self.sessions = data.get("sessions", [])
        self.days = data.get("days", {})
        self.totals = data.get("totals", {"energy": 0.0, "cost": 0.0})
        self.last_lifetime = data.get("last_lifetime")
        self._phase_original = data.get("phase_original")
        self.house_profile = {int(k): float(v) for k, v in (data.get("house_profile") or {}).items()}
        self.car_peaks = {str(k): [float(x) for x in v][-5:] for k, v in (data.get("car_peaks") or {}).items() if isinstance(v, list)}
        sticky = data.get("sticky_departure")
        if isinstance(sticky, list) and len(sticky) == 3 and self.session.start:
            when = dt_util.parse_datetime(str(sticky[1]))
            if when is not None:
                self._sticky_departure = (str(sticky[0]), when, bool(sticky[2]))
        self.history = {
            k: [float(x) for x in v][:3] + [0.0] * (3 - len(v))
            for k, v in (data.get("history") or {}).items()
            if isinstance(v, list) and 2 <= len(v) <= 3
        }
        self.active_phases = data.get("active_phases")
        if self.active_phases in (1, 3):
            self.phase_switch.reset(self.active_phases)
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
                self.pv_power_entity,
                self.pv_forecast_entity,
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
        if self.pv_source == PV_FORECAST_OWN and self.pv_power_entity:
            from .solar_forecast import SolarForecast

            self.solar_forecast = SolarForecast(self.hass, self.entry.entry_id, self.pv_power_entity, self.pv_kwp)
            self._unsubs.append(
                async_track_time_interval(self.hass, self._async_refresh_forecast, timedelta(seconds=PV_FORECAST_REFRESH_S))
            )
            self.hass.async_create_task(self._async_refresh_forecast())
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
        async with self._lock:
            if self._controlling:
                await self._async_restore_normal()
            await self._async_restore_phases()
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
            "phase_original": self._phase_original,
            "house_profile": {str(k): v for k, v in self.house_profile.items()},
            "car_peaks": self.car_peaks,
            "history": self.history,
            "active_phases": self.active_phases,
            "sticky_departure": [self._sticky_departure[0], self._sticky_departure[1].isoformat(), self._sticky_departure[2]]
            if self._sticky_departure else None,
        }

    def _save(self) -> None:
        # async_delay_save re-arms its timer on every call; with a fast meter it would never fire.
        # Arm it once and let it run.
        if self._save_pending:
            return
        self._save_pending = True

        def _data() -> dict[str, Any]:
            self._save_pending = False
            return self._data_to_store()

        self.store.async_delay_save(_data, 10)

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
        if (self.session.start and snap.power_kw and (self._last_sent is None or self._last_sent >= self.max_current)
                and (self.active_phases or self.phases) == self.phases):
            self.session.peak_kw = max(self.session.peak_kw, round(snap.power_kw, 2))
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
        self._learn_house_use(snap)
        self._record_history(snap)
        snap.energy_needed = self._energy_needed()
        async_dispatcher_send(self.hass, SIGNAL_UPDATE.format(self.entry.entry_id))

    def _energy_needed(self) -> float | None:
        """Energy still to deliver from the wall (battery energy / charging efficiency)."""
        car = self.active_car()
        soc = self.car_soc(car)
        if car is not None and soc is not None and not self.settings.manual_kwh:
            battery = (self.car_target(car) - soc) / 100 * car.capacity
            # Cars report their SoC slowly (sometimes once an hour): count what went in since that report,
            # otherwise the plan keeps charging on an old percentage and overshoots the target.
            battery -= self._delivered_since_soc(car, soc) * self.efficiency
            return round(max(0.0, battery) / self.efficiency, 2)
        delivered = self.snapshot.session_energy if self.snapshot.connected else 0.0
        return round(max(0.0, self.settings.target_energy - (delivered or 0.0)), 2)

    def _delivered_since_soc(self, car: Car, soc: float) -> float:
        """kWh delivered by the charger since the car last reported a different SoC."""
        connected = self.snapshot.connected
        lifetime = self.charger_value("lifetime_energy")
        session = self.snapshot.session_energy if connected else None
        ref = self._soc_ref.get(car.index)
        if ref is None or ref[0] != soc or not connected:
            self._soc_ref[car.index] = (soc, lifetime, session)
            return 0.0
        deltas = [0.0]
        if lifetime is not None and ref[1] is not None and lifetime >= ref[1]:
            deltas.append(lifetime - ref[1])
        if session is not None and ref[2] is not None and session >= ref[2]:
            deltas.append(session - ref[2])
        return min(max(deltas), car.capacity)

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
        now_connected = new_status in CONNECTED_STATUSES
        # Offline / unavailable / unknown say nothing about the cable: a blip must not end or restart a session.
        if new_status == STATUS_DISCONNECTED and self.session.start:
            self._end_session()
        elif now_connected and (not self.session.start or old_status == STATUS_DISCONNECTED):
            if self.session.start:
                self._end_session()  # a disconnect we missed
            self._start_session()

    def _start_session(self) -> None:
        self.session = SessionTracker(start=dt_util.now().isoformat())
        self.solar.reset()
        self._test_state = None
        self._test_woken = False
        # "Mode for a new session": the user picks it in the options (keep = leave as is).
        chosen = self._opt(CONF_SESSION_MODE) or SESSION_MODE_KEEP
        if chosen in MODES and chosen != self.settings.mode:
            self.settings.mode = chosen
            self._last_change_at = None
        self._save()

    def _end_session(self) -> None:
        self._sticky_departure = None
        if self.session.start:
            energy = self.snapshot.session_energy
            if energy is None or energy < self.session.energy:
                energy = self.session.energy
            car = self.active_car()
            if car is not None and self.session.peak_kw >= 1.0 and energy and energy >= 2:
                self.car_peaks[car.name] = [*self.car_peaks.get(car.name, []), self.session.peak_kw][-5:]
            record = {
                "car": car.name if car else None,
                "peak_kw": self.session.peak_kw or None,
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
            self._rerun = True  # a pass is running (e.g. a phase change): run once more right after it
            return
        async with self._lock:
            for _ in range(3):
                self._rerun = False
                await self._async_control_locked()
                if not self._rerun:
                    break
        # the plan is made here: push it to the entities and the card now, not on the next tick
        async_dispatcher_send(self.hass, SIGNAL_UPDATE.format(self.entry.entry_id))

    async def _async_control_locked(self) -> None:
        snap = self.snapshot
        now = dt_util.now()
        mode = self.settings.mode
        self._apply_solar_settings()
        self.solar_slots = self._solar_outlook(snap)
        snap.plan_preview = self._preview_plan(snap, now)

        if mode == MODE_NORMAL and not self.settings.boost:
            snap.smart_state = SMART_IDLE
            snap.plan = None
            snap.target_current = None
            if self._controlling:
                await self._async_restore_normal()
            await self._async_restore_phases()
            return

        if snap.status == "unknown" or not snap.connected:
            snap.smart_state = SMART_NOT_CONNECTED if snap.status != "unknown" else SMART_IDLE
            snap.plan = None
            snap.target_current = None
            self.solar.reset()
            await self._async_restore_phases()
            return

        # "completed" while we hold the charger at 0 A is our own pause, not a full battery.
        held_by_us = self._controlling and (self._last_sent or 0) == 0
        if snap.status == "completed" and not self.settings.boost and not held_by_us:
            snap.smart_state = SMART_TARGET_REACHED
            snap.target_current = None
            return

        want = 0
        want_smart = 0
        solar_phases = self.phases
        state = SMART_IDLE
        if self.settings.boost:
            want, state = self.max_current, SMART_CHARGING_BOOST
        else:
            want_solar = 0
            needed = snap.energy_needed or 0.0
            if mode in (MODE_SMART, MODE_SOLAR_SMART):
                if needed <= 0:
                    snap.plan = None
                    state = SMART_TARGET_REACHED
                elif not snap.prices:
                    # No day-ahead prices: charge now (default, the car is never left empty) or wait.
                    if self._opt(CONF_NO_PRICES) == NO_PRICES_WAIT:
                        state = SMART_NO_PRICES
                    else:
                        want_smart, state = self.max_current, SMART_NO_PRICES
                else:
                    departure = self._departure(now)
                    plan = self._plan_grid(snap, now, departure, self._grid_needed(needed, now, departure, mode), mode)
                    snap.plan = plan
                    if plan.charge_now:
                        want_smart = self.max_current
                        state = SMART_CHARGING_FALLBACK if plan.fallback else SMART_CHARGING_CHEAP
                    else:
                        state = SMART_WAITING_CHEAP
            if mode in (MODE_SOLAR, MODE_SOLAR_SMART):
                if snap.surplus_kw is not None:
                    if self.phase_switching:
                        available = snap.surplus_kw - self.solar_buffer_kw + max(snap.power_kw or 0.0, 0.0)
                        solar_phases = self.phase_switch.update(now, available, self.voltage)
                    # the current is worked out for the phases the charger really uses now, not the wish
                    want_solar = self.solar.update(
                        now, snap.surplus_kw - self.solar_buffer_kw, snap.power_kw or 0.0, self.shown_phases, self.voltage
                    )
                if mode == MODE_SOLAR:
                    state = SMART_CHARGING_SOLAR if want_solar > 0 else SMART_WAITING_SOLAR
                elif want_solar > 0 and want_solar >= want_smart:
                    state = SMART_CHARGING_SOLAR
            want = max(want_smart, want_solar)

        want, state = self._test_charge(snap, now, want, state)

        # Solar on little sun → 1 phase; anything that needs full power (boost, cheap hours) → 3.
        solar_only = mode in (MODE_SOLAR, MODE_SOLAR_SMART) and not self.settings.boost and want_smart == 0
        await self._async_ensure_phases(solar_phases if solar_only else 3)

        snap.smart_state = state
        snap.target_current = want
        force, self._test_stop = self._test_stop, False
        await self._async_apply(want, now, force=force)
        async_dispatcher_send(self.hass, SIGNAL_UPDATE.format(self.entry.entry_id))

    # ------------------------------------------------------------ solar panels
    @property
    def pv_power_entity(self) -> str | None:
        return self._opt(CONF_PV_POWER) or None

    @property
    def pv_forecast_entity(self) -> str | None:
        return self._opt(CONF_PV_FORECAST_SENSOR) or None if self.pv_source == PV_FORECAST_SENSOR else None

    @property
    def pv_source(self) -> str:
        return self._opt(CONF_PV_FORECAST) or "none"

    @property
    def pv_kwp(self) -> float | None:
        value = self._opt(CONF_PV_KWP)
        try:
            return float(value) if value else None
        except (TypeError, ValueError):
            return None

    def pv_now_kw(self) -> float | None:
        value = self._float(self.pv_power_entity)
        if value is None:
            return None
        state = self.hass.states.get(self.pv_power_entity)
        unit = str(state.attributes.get("unit_of_measurement", "W")).lower() if state else "w"
        return max(0.0, value if unit == "kw" else value / 1000)

    def _learn_house_use(self, snap: Snapshot) -> None:
        """Learn what the house uses per hour of the day (without the car): pv + grid - charger."""
        pv = self.pv_now_kw()
        if pv is None or snap.grid_power_kw is None:
            return
        now = dt_util.now()
        if self._house_sampled_at and (now - self._house_sampled_at).total_seconds() < 60:
            return
        self._house_sampled_at = now
        house = max(0.0, pv + snap.grid_power_kw - max(snap.power_kw or 0.0, 0.0))
        old = self.house_profile.get(now.hour)
        # slow average: one evening with the oven on should not change the plan much
        self.house_profile[now.hour] = round(house if old is None else old + (house - old) * 0.03, 3)

    def _record_history(self, snap: Snapshot) -> None:
        """Per quarter hour: kWh charged from the grid, from the sun, and what the panels made."""
        now = dt_util.utcnow()
        last, self._history_at = self._history_at, now
        if last is None:
            return
        seconds = min(120.0, (now - last).total_seconds())  # gaps (restart) are not filled in
        if seconds <= 0:
            return
        hours = seconds / 3600
        power = max(snap.power_kw or 0.0, 0.0)
        pv = self.pv_now_kw()
        if power < 0.05 and not pv:
            return
        start = now.replace(minute=now.minute - now.minute % 15, second=0, microsecond=0)
        row = self.history.setdefault(start.isoformat(), [0.0, 0.0, 0.0])
        if len(row) < 3:
            row.append(0.0)
        if power >= 0.05:
            grid_import = max(snap.grid_power_kw or 0.0, 0.0) if snap.grid_power_kw is not None else power
            sun_kw = max(0.0, min(power, power - grid_import))
            row[0] = round(row[0] + (power - sun_kw) * hours, 4)
            row[1] = round(row[1] + sun_kw * hours, 4)
        if pv:
            row[2] = round(row[2] + pv * hours, 4)
        cutoff = (now - timedelta(hours=48)).isoformat()
        for key in [k for k in self.history if k < cutoff]:
            del self.history[key]
        self._save()

    def pv_forecast_kw(self) -> dict[datetime, float]:
        """Hour start (UTC) -> expected kW of the solar panels."""
        if self.pv_source == PV_FORECAST_OWN and self.solar_forecast is not None:
            return self.solar_forecast.hourly_kw()
        if self.pv_source == PV_FORECAST_SENSOR and self.pv_forecast_entity:
            from .solar_forecast import hourly_from_attribute

            state = self.hass.states.get(self.pv_forecast_entity)
            return hourly_from_attribute(state.attributes.get("hourly")) if state else {}
        return {}

    async def _async_refresh_forecast(self, *_: Any) -> None:
        if self.solar_forecast is not None:
            await self.solar_forecast.async_update()
            async_dispatcher_send(self.hass, SIGNAL_UPDATE.format(self.entry.entry_id))

    def _solar_outlook(self, snap: Snapshot) -> list:
        forecast = self.pv_forecast_kw()
        if not forecast or not snap.prices:
            return []
        return solar_outlook(
            snap.prices, forecast, self.house_profile,
            min_current=self.min_current, max_current=self.max_current, phases=self.phases,
            phase_switching=self.phase_switching, voltage=self.voltage, buffer_kw=self.solar_buffer_kw,
        )

    def _schedule_payload(self, now: datetime, plan: ChargePlan | None) -> list[dict[str, Any]]:
        """Per price slot what will happen: kWh from the grid and from the sun (for the chart)."""
        snap = self.snapshot
        needed = snap.energy_needed or 0.0
        if needed <= 0 or not snap.prices:
            return []
        mode = MODE_NORMAL if self.settings.boost else self.settings.mode
        if mode == MODE_NORMAL and not snap.connected:
            return []  # Normal charges from the moment the car is plugged in: nothing to plan yet
        departure = self._departure(now)
        grid_slots = {s.start for s in plan.slots} if plan and mode in (MODE_SMART, MODE_SOLAR_SMART) else set()
        solar_kw = {x.start: x.charge_kw for x in self.solar_slots} if self.solar_slots else {}
        rows = charge_schedule(
            [s for s in snap.prices if s.end > now - timedelta(hours=1)][:240],
            now,
            None if mode == MODE_NORMAL else departure,
            needed,
            self.charge_power_kw,
            grid_slots=grid_slots,
            solar_kw=solar_kw,
            use_solar=mode in (MODE_SOLAR, MODE_SOLAR_SMART),
            grid_always=mode == MODE_NORMAL,
            grid_budget=self._grid_needed(needed, now, departure, mode) if mode == MODE_SOLAR_SMART else None,
            surplus_kw={x.start: x.surplus_kw for x in self.solar_slots} if self.solar_slots else None,
        )
        return [{"start": start.isoformat(), "grid": grid, "sun": sun} for start, grid, sun in rows if grid or sun]

    def _solar_payload(self, now: datetime) -> dict[str, Any] | None:
        if self.pv_source == "none":
            return None
        slots = self.solar_slots or []
        departure = self._departure(now)
        needed = self.snapshot.energy_needed or 0.0
        sun = solar_energy_until(slots, now, departure) if slots else 0.0
        fc = self.solar_forecast.data if self.solar_forecast is not None else None
        days: dict[str, float] = {}
        for start, kw in self.pv_forecast_kw().items():
            key = dt_util.as_local(start).date().isoformat()
            days[key] = days.get(key, 0.0) + kw
        today = dt_util.now().date()
        return {
            "source": self.pv_source,
            "pv_now_kw": self.pv_now_kw(),
            "today_kwh": round(days.get(today.isoformat(), 0.0), 2) if days else None,
            "tomorrow_kwh": round(days.get((today + timedelta(days=1)).isoformat(), 0.0), 2) if days else None,
            "until_departure_kwh": round(sun, 2),
            "counted_kwh": round(min(needed, sun * SOLAR_TRUST), 2) if self.settings.mode == MODE_SOLAR_SMART else None,
            "grid_kwh": round(self._grid_needed(needed, now, departure, self.settings.mode), 2),
            "departure": departure.isoformat(),
            "error": fc.error if fc else None,
            "calibration": fc.calibration if fc else None,
            "pv_hourly": [
                {"start": start.isoformat(), "kw": round(kw, 3)}
                for start, kw in sorted(self.pv_forecast_kw().items())
                if start >= dt_util.as_utc(dt_util.start_of_local_day() - timedelta(days=1))
                and start < dt_util.as_utc(dt_util.start_of_local_day() + timedelta(days=2))
            ],
            "slots": [
                {"start": x.start.isoformat(), "end": x.end.isoformat(), "pv": x.pv_kw, "house": x.house_kw, "charge": x.charge_kw}
                for x in slots if x.end > now - timedelta(hours=1)
            ][:200],
        }

    def _grid_needed(self, needed: float, now: datetime, departure: datetime, mode: str) -> float:
        """Solar + smart: energy the sun is expected to give before departure is not bought."""
        if mode != MODE_SOLAR_SMART or not self.solar_slots:
            return needed
        sun = solar_energy_until(self.solar_slots, now, departure) * SOLAR_TRUST
        return max(0.0, needed - sun)

    # ------------------------------------------------------------ phase switching
    @property
    def phase_switching(self) -> bool:
        """Automatic 1/3-phase switching for solar charging (3-phase installs, on by default)."""
        return (
            self.phases == 3
            and bool(self._opt(CONF_PHASE_SWITCHING, True))
            and self._phase_mode_from_charger() != PHASE_MODE_1
            and self.hass.services.has_service(EASEE_DOMAIN, "set_charger_phase_mode")
        )

    def _phase_mode_from_charger(self) -> str | None:
        """The charger's own phase setting, read from the Easee integration."""
        if self._phase_original:
            return self._phase_original
        state = self._state(self.charger_entities.get("phase_mode"))
        if state is None:
            return None
        text = str(state.state).lower()
        if "auto" in text or text == "2":
            return PHASE_MODE_AUTO
        if "single" in text or "1" in text or "one" in text:
            return PHASE_MODE_1
        if "three" in text or "3" in text:
            return PHASE_MODE_3
        return None

    @property
    def shown_phases(self) -> int:
        """Phases the charger uses now as far as we know (for the cards)."""
        return self.active_phases or self.phases

    async def _async_ensure_phases(self, target: int) -> None:
        if not self.phase_switching:
            return
        if self.active_phases is None and target == 3:
            return  # never touched the charger: nothing to do
        if self.active_phases == target:
            return
        now = dt_util.utcnow()
        if self._phase_retry_after and now < self._phase_retry_after:
            return
        if self._phase_original is None:
            self._phase_original = self._phase_mode_from_charger() or PHASE_MODE_AUTO
        mode = PHASE_MODE_1 if target == 1 else (
            self._phase_original if self._phase_original != PHASE_MODE_1 else PHASE_MODE_3
        )
        if await self._async_set_phase_mode(mode, restart=self.snapshot.connected):
            self.active_phases = target
            self.phase_switch.reset(target)
            self._phase_retry_after = None
            self._save()
        else:
            # keep what the charger really does and do not hammer the cloud
            self.phase_switch.reset(self.shown_phases)
            self._phase_retry_after = now + timedelta(seconds=self.phase_switch.min_interval_s)

    async def _async_restore_phases(self) -> None:
        """Give the charger its own phase setting back when we stop solar charging."""
        if self.active_phases is None or self._phase_original is None:
            return
        if self.active_phases != 3 and not await self._async_set_phase_mode(self._phase_original, restart=False):
            return  # try again on a later pass; keep what we know
        self.active_phases = None
        self._phase_original = None
        self.phase_switch.reset(3)
        self._save()

    async def _async_set_phase_mode(self, mode: str, restart: bool) -> bool:
        """Easee applies a new phase mode at the start of a session, so pause and resume."""
        paused = False
        try:
            if restart:
                await self.async_charger_command("pause")
                paused = True
            await self.hass.services.async_call(
                EASEE_DOMAIN,
                "set_charger_phase_mode",
                {CONF_DEVICE_ID: self.charger_device_id, "phase_mode": mode},
                blocking=True,
            )
            if paused:
                await asyncio.sleep(PHASE_RESTART_DELAY_S)
        except Exception as err:  # noqa: BLE001 - never let control crash the loop
            _LOGGER.warning("Could not set charger phase mode to %s: %s", mode, err)
            return False
        finally:
            if paused:
                try:
                    await self.async_charger_command("resume")
                except Exception as err:  # noqa: BLE001
                    _LOGGER.warning("Could not resume the charger after a phase change: %s", err)
        _LOGGER.info("Charger phase mode set to %s", mode)
        return True

    # ------------------------------------------------------- power & departure
    @property
    def charger_power_kw(self) -> float:
        """What the charger can deliver: configured current, capped by the charger's own maximum."""
        return round(power_for_amps(self.max_current, self.phases, self.voltage), 2)

    def car_power_kw(self, car: Car | None) -> tuple[float | None, str | None]:
        """Max AC charging power of the car: set by the user, otherwise measured in earlier sessions."""
        if car is None:
            return None, None
        try:
            set_kw = float(car.raw.get("max_kw") or 0)
        except (TypeError, ValueError):
            set_kw = 0.0
        if set_kw > 0:
            return set_kw, "set"
        peaks = [p for p in self.car_peaks.get(car.name, []) if p >= 1.0]
        if len(peaks) >= 2:
            measured = round(max(peaks), 1)
            if measured < self.charger_power_kw * 0.9:
                return measured, "measured"
        return None, None

    @property
    def charge_power_kw(self) -> float:
        """Power used for planning: the lower of the charger and the car."""
        car_kw, _src = self.car_power_kw(self.active_car())
        return round(min(self.charger_power_kw, car_kw) if car_kw else self.charger_power_kw, 2)

    def _departure(self, now: datetime) -> datetime:
        """Next "ready at" moment. When today's is too close to charge what is needed, plan for tomorrow."""
        # During a session the choice made at the start sticks, so a long charge is never pushed a day back.
        key = self.settings.departure
        sticky = self._sticky_departure
        if self.session.start and sticky and sticky[0] == key and now < sticky[1]:
            self._departure_moved = sticky[2]
            return sticky[1]
        dep = next_departure(now, _parse_time(self.settings.departure))
        needed = self.snapshot.energy_needed or 0.0
        power = self.charge_power_kw
        moved = False
        # Only a "ready at" that is just ahead (< 3 h) moves; further away it keeps the real time and
        # charges what fits (the card then warns what does not).
        ahead = hours_between(now, dep)
        if needed > 0 and power > 0 and ahead < needed / power and ahead < 3:
            dep += timedelta(days=1)
            moved = True
        self._departure_moved = moved
        if self.session.start:
            if not sticky or sticky[0] != key or now >= sticky[1]:
                self._sticky_departure = (key, dep, moved)
                self._save()
        return dep

    def _plan_grid(self, snap: Snapshot, now: datetime, departure: datetime, grid_kwh: float, mode: str) -> ChargePlan:
        """Cheapest grid slots. In Solar + smart, sun expected inside a chosen slot takes room the grid
        cannot use there, so plan once more with that amount added."""
        power = self.charge_power_kw
        plan = plan_cheapest(snap.prices, now, departure, grid_kwh, power, self.settings.price_threshold)
        if mode == MODE_SOLAR_SMART and plan.slots and self.solar_slots:
            sun = {x.start: x.charge_kw for x in self.solar_slots}
            overlap = sum(min(power, sun.get(sl.start, 0.0)) * sl.hours for sl in plan.slots)
            if overlap > 0.05:
                plan = plan_cheapest(snap.prices, now, departure, grid_kwh + overlap, power, self.settings.price_threshold)
        return plan

    def _preview_plan(self, snap: Snapshot, now: datetime) -> ChargePlan | None:
        """What smart charging would plan right now (shown even in normal mode or unplugged)."""
        needed = snap.energy_needed or 0.0
        if needed <= 0 or not snap.prices:
            return None
        try:
            departure = self._departure(now)
            grid = self._grid_needed(needed, now, departure, self.settings.mode)
            if grid <= 0:
                return None
            return self._plan_grid(snap, now, departure, grid, self.settings.mode)
        except (TypeError, ValueError):
            return None

    @property
    def solar_start_kw(self) -> float:
        """Surplus needed before solar charging starts (min. current + buffer)."""
        phases = 1 if self.phase_switching else self.phases
        return round(power_for_amps(self.min_current, phases, self.voltage) + self.solar_buffer_kw, 2)

    def _test_charge(self, snap: Snapshot, now: datetime, want: int, state: str) -> tuple[int, str]:
        """Charge a few seconds at the start of a session to check the plug and the car.

        Only when nothing would charge right now; if charging happens anyway, that is the test.
        No current after a while: wake the car once, then report a problem.
        """
        if not self._opt(CONF_TEST_CHARGE, True) or self.settings.boost or self._test_state == "ok":
            return want, state
        flowing = snap.status == "charging" or (snap.power_kw or 0.0) >= 0.5
        if self._test_state is None:
            if not self.session.start or self.session.tested:
                return want, state
            if want > 0 or self.session.energy > 0.05:
                if flowing or self.session.energy > 0.05:
                    self._test_done("ok")
                return want, state
            self._test_state, self._test_since, self._test_flow_since = "running", now, None
            _LOGGER.debug("Test charge started")
        if self._test_state == "running":
            if flowing:
                if self._test_flow_since is None:
                    self._test_flow_since = now
                    # end the test right on time instead of on the next tick
                    async_call_later(self.hass, TEST_CHARGE_SECONDS + 0.5, self._async_test_tick)
                if (now - self._test_flow_since).total_seconds() >= TEST_CHARGE_SECONDS:
                    self._test_done("ok")
                    self._test_stop = want == 0
                    _LOGGER.debug("Test charge ok")
                    return want, state
                return max(want, self.min_current), SMART_TEST_CHARGE
            elapsed = (now - (self._test_since or now)).total_seconds()
            if elapsed >= TEST_CHARGE_TIMEOUT_S:
                self._test_done("failed")
                self._test_stop = want == 0
                self._notify_test_failed()
                return want, SMART_TEST_FAILED if want == 0 else state
            if elapsed >= 30 and not self._test_woken and self._opt(CONF_NUDGE, True):
                self._test_woken = True
                self.hass.async_create_task(self._async_wake_car())
            return max(want, self.min_current), SMART_TEST_CHARGE
        # failed: show it until the car charges after all or the cable is removed
        if flowing:
            self._test_done("ok")
            persistent_notification.async_dismiss(self.hass, f"{DOMAIN}_test_{self.entry.entry_id}")
            return want, state
        return want, SMART_TEST_FAILED if want == 0 else state

    def _test_done(self, result: str) -> None:
        self._test_state = result
        self.session.tested = True
        self._save()

    async def _async_test_tick(self, _now: datetime) -> None:
        await self._async_control()

    async def _async_wake_car(self) -> None:
        try:
            await self.async_charger_command("resume")
            await self.async_force_car_start()
        except Exception as err:  # noqa: BLE001 - a cloud hiccup must not stop the test
            _LOGGER.debug("Could not wake the car: %s", err)

    def _notify_test_failed(self) -> None:
        car = self.active_car()
        persistent_notification.async_create(
            self.hass,
            (
                f"The test charge at the start of this session got no current"
                f"{' from ' + car.name if car else ''}. "
                "Check that the plug sits well in the car and the charger, and that no charge timer "
                "or charge limit is active in the car."
            ),
            title="Easee Smart Charging: test charge failed",
            notification_id=f"{DOMAIN}_test_{self.entry.entry_id}",
        )

    async def _async_apply(self, want: int, now: datetime, force: bool = False) -> None:
        changed = want != self._last_sent
        urgent = (self._last_sent in (None, 0) and want > 0) or force
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
                try:
                    await self.async_charger_command("resume")
                    await self.async_force_car_start()
                except Exception as err:  # noqa: BLE001 - a cloud hiccup must not stop the control pass
                    _LOGGER.debug("Could not nudge the charger: %s", err)
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
        # Returned to the caller only (service response / card download). Nothing is written
        # to /config/www, because that folder is served without authentication.
        return {
            "month": month,
            "filename": f"easee-smart-{month}.csv",
            "csv": buffer.getvalue(),
            "sessions": len(sessions),
            "energy_kwh": totals_energy,
            "cost": totals_cost,
            "reimbursement": None if reimb is None else round(totals_energy * reimb, 2),
            "ere": None if ere is None else round(totals_energy * ere, 2),
        }

    # ------------------------------------------------------------ card payload
    @property
    def show_equalizer(self) -> bool:
        """Show the Equalizer in the cards: auto = when one is linked."""
        choice = self._opt(CONF_SHOW_EQUALIZER) or "auto"
        if choice == "hide":
            return False
        if choice == "show":
            return True
        return bool(self.equalizer_entities)

    def _equalizer_info(self) -> dict[str, Any] | None:
        if not self.equalizer_device:
            return {"show": False} if not self.show_equalizer else {"show": True, "linked": False}
        d = self.equalizer_device
        return {
            "show": self.show_equalizer,
            "linked": True,
            "name": getattr(d, "name_by_user", None) or getattr(d, "name", None) or "Equalizer",
            "model": getattr(d, "model", None),
            "sw_version": getattr(d, "sw_version", None),
        }

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
        plan = snap.plan or snap.plan_preview
        now = dt_util.now()
        horizon = dt_util.start_of_local_day() - timedelta(days=1)  # the chart can show yesterday too
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
            "manual_kwh": self.settings.manual_kwh,
            "smart_state": snap.smart_state,
            "currency": self.hass.config.currency,
            "language": self._opt(CONF_LANGUAGE) or "auto",
            "phases": self.phases,
            "active_phases": self.shown_phases,
            "phase_switching": self.phase_switching,
            "no_prices_action": self._opt(CONF_NO_PRICES) or "charge",
            "solar": self._solar_payload(now),
            "schedule": self._schedule_payload(now, plan),
            "history": [
                {"start": k, "grid": round(v[0], 3), "sun": round(v[1], 3), "pv": round(v[2], 3) if len(v) > 2 else 0}
                for k, v in sorted(self.history.items())
                if k >= dt_util.as_utc(dt_util.start_of_local_day() - timedelta(days=1)).isoformat()
            ],
            "max_current": self.max_current,
            "sources": dict(self.charger_entities),
            "equalizer": dict(self.equalizer_entities) if isinstance(self.equalizer_entities, dict) else self.equalizer_entities,
            "equalizer_info": self._equalizer_info(),
            "entities": dict(self.own_entities),  # a copy: HA only sends attributes that changed
            "entry_id": self.entry.entry_id,
            "card_version": VERSION,
            "price": snap.price,
            "market_price": self.market_price(),
            "zone": self.zone,
            "price_resolution": self._opt(CONF_PRICE_RESOLUTION) or "quarter",
            "price_parts": dict(zip(("markup", "energy_tax", "vat"), self._price_parts(), strict=True)),
            "prices": [
                {"start": s.start.isoformat(), "end": s.end.isoformat(), "price": s.price}
                for s in snap.prices
                if s.end > horizon
            ][:400],
            "plan": [
                {"start": s.start.isoformat(), "end": s.end.isoformat(), "price": s.price}
                for s in (plan.slots if plan else [])
            ],
            "plan_preview": bool(plan is not None and snap.plan is None),
            "solar_start_kw": self.solar_start_kw,
            "plan_cost": plan.estimated_cost if plan else None,
            "plan_avg_price": plan.average_price if plan else None,
            "next_start": plan.next_start.isoformat() if plan and plan.next_start else None,
            "complete_by": plan.complete_by.isoformat() if plan and plan.complete_by else None,
            "plan_short_kwh": plan.short_kwh if plan else 0,
            "plan_window_kwh": plan.window_kwh if plan else None,
            "charge_power_kw": self.charge_power_kw,
            "charger_power_kw": self.charger_power_kw,
            "car_power_kw": self.car_power_kw(self.active_car())[0],
            "car_power_source": self.car_power_kw(self.active_car())[1],
            "departure_at": self._departure(now).isoformat(),
            "departure_moved": self._departure_moved,
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
            "has_soc": bool(self.active_car() and self.active_car().soc_entity),
        }


def _parse_time(value: str) -> time:
    try:
        parts = [int(p) for p in str(value).split(":")[:2]]
        return time(parts[0], parts[1] if len(parts) > 1 else 0)
    except (ValueError, IndexError):
        return time(7, 0)
