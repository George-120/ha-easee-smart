"""Config flow for Easee Smart: pick your charger from the Easee integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import selector

from .cars import (
    ACTION_DOMAINS,
    CONF_CARS,
    DEFAULT_CAR_TARGET,
    F_CAPACITY,
    F_DEVICE,
    F_IMAGE,
    F_LIMIT,
    F_NAME,
    F_PLUG,
    F_RANGE,
    F_REFRESH,
    F_SOC,
    F_START,
    F_TARGET,
    MAX_CARS,
    cars_from_options,
    detect_car_entities,
    suggest_car_devices,
)
from .cars import (
    DEFAULT_CAPACITY as DEFAULT_CAR_CAPACITY,
)
from .const import (
    CONF_BIDDING_ZONE,
    CONF_BOOST_RESET,
    CONF_CAR_REFRESH_MIN,
    CONF_CHARGER_DEVICE,
    CONF_EFFICIENCY,
    CONF_ENABLE_ENTITIES,
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
    CONF_PHASE_SWITCHING,
    CONF_PHASES,
    CONF_PRICE_RESOLUTION,
    CONF_REIMBURSEMENT,
    CONF_SESSION_MODE,
    CONF_SHOW_EQUALIZER,
    CONF_SOLAR_BUFFER,
    CONF_SOLAR_START_DELAY,
    CONF_SOLAR_STOP_DELAY,
    CONF_VAT,
    DEFAULT_EFFICIENCY,
    DEFAULT_MAIN_FUSE,
    DEFAULT_MAX_CURRENT,
    DEFAULT_PHASES,
    DOMAIN,
    EASEE_DOMAIN,
    EASEE_MODELS,
    EQUALIZER_MODEL,
    GRID_KEYS,
    LANGUAGES,
    MAIN_FUSE_SIZES,
    MIN_CHARGE_CURRENT,
    MODEL_MAX_CURRENT,
    MODES,
    NO_EQUALIZER,
    NO_PRICES_CHARGE,
    NO_PRICES_WAIT,
    PHASE_ENTITY_KEYS,
    REQUIRED_CHARGER_KEYS,
    REQUIRED_EQUALIZER_KEYS,
    RESOLUTION_HOUR,
    RESOLUTION_QUARTER,
    SESSION_MODE_KEEP,
    SHOW_EQUALIZER_OPTIONS,
    SOLAR_START_DELAY_S,
    SOLAR_STOP_DELAY_S,
)
from .grid_detect import suggest_grid_sensors
from .manager import easee_product_id, enable_disabled_entities, resolve_entities
from .prices import BIDDING_ZONES, default_zone, zone_defaults


def _easee_devices(hass: HomeAssistant) -> tuple[list[dr.DeviceEntry], list[dr.DeviceEntry]]:
    """Return (chargers, equalizers) known by the Easee integration."""
    registry = dr.async_get(hass)
    chargers: list[dr.DeviceEntry] = []
    equalizers: list[dr.DeviceEntry] = []
    seen: set[str] = set()
    for entry in hass.config_entries.async_entries(EASEE_DOMAIN):
        for device in dr.async_entries_for_config_entry(registry, entry.entry_id):
            pid = easee_product_id(device)
            if not pid or device.id in seen:
                continue
            seen.add(device.id)
            if device.model == EQUALIZER_MODEL:
                equalizers.append(device)
            elif resolve_entities(hass, pid, ["status"]):
                chargers.append(device)
    return chargers, equalizers


def _easee_rated(hass: HomeAssistant, device: dr.DeviceEntry | None, attr: str) -> int | None:
    """Read circuit/site fuse sizes that the Easee integration exposes on the status sensor."""
    status = resolve_entities(hass, easee_product_id(device), ["status"]).get("status") if device else None
    state = hass.states.get(status) if status else None
    try:
        value = int(float(state.attributes.get(attr))) if state else None
    except (TypeError, ValueError):
        return None
    return value if value and value > 0 else None


def _label(device: dr.DeviceEntry) -> str:
    name = device.name_by_user or device.name or easee_product_id(device)
    model = device.model or "Easee"
    return f"{name} · {model} ({easee_product_id(device)})"


def _detect_model(device: dr.DeviceEntry | None) -> str:
    if device and device.model in EASEE_MODELS:
        return device.model
    return EASEE_MODELS[0]


def _energy_schema(hass: HomeAssistant, defaults: dict[str, Any]) -> dict:
    currency = hass.config.currency
    zone = defaults.get(CONF_BIDDING_ZONE) or default_zone(hass)
    zd = zone_defaults(zone)

    def money(key: str, default: float, maximum: float = 1.0) -> tuple:
        value = defaults.get(key)
        return (
            vol.Optional(key, default=value if value is not None else default),
            selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=maximum, step="any", unit_of_measurement=f"{currency}/kWh",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        )

    schema: dict = {
        vol.Required(CONF_BIDDING_ZONE, default=zone): selector.SelectSelector(
            selector.SelectSelectorConfig(options=BIDDING_ZONES, mode=selector.SelectSelectorMode.DROPDOWN)
        ),
    }
    schema[vol.Optional(CONF_PRICE_RESOLUTION, default=defaults.get(CONF_PRICE_RESOLUTION) or RESOLUTION_QUARTER)] = selector.SelectSelector(
        selector.SelectSelectorConfig(options=[RESOLUTION_QUARTER, RESOLUTION_HOUR], translation_key="price_resolution")
    )
    schema.update(dict([money(CONF_MARKUP, 0.0), money(CONF_ENERGY_TAX, zd["energy_tax"])]))
    vat = defaults.get(CONF_VAT)
    schema[vol.Optional(CONF_VAT, default=vat if vat is not None else zd["vat"])] = selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=30, step=0.5, unit_of_measurement="%", mode=selector.NumberSelectorMode.BOX)
    )
    schema.update(
        {
            vol.Optional(CONF_ERE_ENABLED, default=bool(defaults.get(CONF_ERE_ENABLED, False))): selector.BooleanSelector(),
            vol.Optional(CONF_ERE_RATE, default=defaults.get(CONF_ERE_RATE) or 0.0): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=1, step="any", unit_of_measurement=f"{currency}/kWh",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_REIMBURSEMENT,
                description={"suggested_value": defaults.get(CONF_REIMBURSEMENT)},
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=2, step=0.001, unit_of_measurement=f"{currency}/kWh",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        }
    )
    return schema


def _grid_schema(defaults: dict[str, Any]) -> dict:
    """Main connection: smart meter sensors and main fuse (only without an Equalizer)."""

    def ent(key: str, device_class: str) -> tuple:
        return (
            vol.Optional(key, description={"suggested_value": defaults.get(key)}),
            selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class=device_class)),
        )

    schema: dict = dict(
        [
            ent(CONF_GRID_IMPORT_ENTITY, "power"),
            ent(CONF_GRID_EXPORT_ENTITY, "power"),
            ent(CONF_GRID_POWER_ENTITY, "power"),
        ]
    )
    schema[vol.Optional(CONF_GRID_POWER_INVERTED, default=defaults.get(CONF_GRID_POWER_INVERTED, False))] = (
        selector.BooleanSelector()
    )
    schema.update(dict(ent(k, "current") for k in PHASE_ENTITY_KEYS))
    schema[vol.Required(CONF_MAIN_FUSE, default=str(defaults.get(CONF_MAIN_FUSE, DEFAULT_MAIN_FUSE)))] = (
        selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=MAIN_FUSE_SIZES, custom_value=True, mode=selector.SelectSelectorMode.DROPDOWN
            )
        )
    )
    return schema


def _action_selector() -> selector.EntitySelector:
    return selector.EntitySelector(selector.EntitySelectorConfig(domain=ACTION_DOMAINS))


def _car_schema(d: dict[str, Any], editing: bool) -> dict:
    """All settings of one car; detected entities come in as suggested values."""

    def opt(key: str, sel) -> tuple:
        return vol.Optional(key, description={"suggested_value": d.get(key)}), sel

    schema: dict = {
        vol.Required(F_NAME, default=d.get(F_NAME) or "Auto"): selector.TextSelector(),
    }
    schema.update(
        dict(
            [
                opt(F_IMAGE, selector.TextSelector()),
                opt(F_SOC, selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor"))),
            ]
        )
    )
    schema[vol.Required(F_CAPACITY, default=d.get(F_CAPACITY) or DEFAULT_CAR_CAPACITY)] = selector.NumberSelector(
        selector.NumberSelectorConfig(min=5, max=200, step=0.5, unit_of_measurement="kWh", mode=selector.NumberSelectorMode.BOX)
    )
    schema[vol.Required(F_TARGET, default=d.get(F_TARGET) or DEFAULT_CAR_TARGET)] = selector.NumberSelector(
        selector.NumberSelectorConfig(min=10, max=100, step=5, unit_of_measurement="%", mode=selector.NumberSelectorMode.SLIDER)
    )
    schema.update(
        dict(
            [
                opt(F_PLUG, selector.EntitySelector(selector.EntitySelectorConfig(domain="binary_sensor"))),
                opt(F_START, _action_selector()),
                opt(F_REFRESH, _action_selector()),
                opt(F_LIMIT, selector.EntitySelector(selector.EntitySelectorConfig(domain=["number", "input_number"]))),
                opt(F_RANGE, selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor"))),
            ]
        )
    )
    if editing:
        schema[vol.Optional("remove", default=False)] = selector.BooleanSelector()
    return schema


def _clean_car(user_input: dict[str, Any], device_id: str | None) -> dict[str, Any]:
    car = {k: v for k, v in user_input.items() if k != "remove" and v not in (None, "")}
    if device_id:
        car[F_DEVICE] = device_id
    if F_CAPACITY in car:
        car[F_CAPACITY] = float(car[F_CAPACITY])
    if F_TARGET in car:
        car[F_TARGET] = int(car[F_TARGET])
    return car


def _device_step_schema(hass: HomeAssistant, configured: set[str]) -> dict:
    suggested = suggest_car_devices(hass, configured)
    return {
        vol.Optional(F_DEVICE, description={"suggested_value": suggested[0] if suggested else None}): selector.DeviceSelector(
            selector.DeviceSelectorConfig()
        ),
    }


def _advanced_schema(defaults: dict[str, Any]) -> dict:
    def num(key: str, default: float, lo: float, hi: float, step: float, unit: str) -> tuple:
        value = defaults.get(key)
        return (
            vol.Optional(key, default=value if value is not None else default),
            selector.NumberSelector(
                selector.NumberSelectorConfig(min=lo, max=hi, step=step, unit_of_measurement=unit, mode=selector.NumberSelectorMode.BOX)
            ),
        )

    schema = dict(
        [
            num(CONF_MIN_CURRENT, MIN_CHARGE_CURRENT, 6, 16, 1, "A"),
            num(CONF_SOLAR_START_DELAY, SOLAR_START_DELAY_S / 60, 0, 30, 0.5, "min"),
            num(CONF_SOLAR_STOP_DELAY, SOLAR_STOP_DELAY_S / 60, 0, 60, 0.5, "min"),
            num(CONF_SOLAR_BUFFER, 0.0, 0, 5, 0.05, "kW"),
            num(CONF_EFFICIENCY, DEFAULT_EFFICIENCY, 50, 100, 1, "%"),
            num(CONF_CAR_REFRESH_MIN, 0, 0, 240, 5, "min"),
        ]
    )
    schema[vol.Optional(CONF_LANGUAGE, default=defaults.get(CONF_LANGUAGE) or "auto")] = selector.SelectSelector(
        selector.SelectSelectorConfig(options=LANGUAGES, translation_key="language", mode=selector.SelectSelectorMode.DROPDOWN)
    )
    schema[vol.Optional(CONF_BOOST_RESET, default=defaults.get(CONF_BOOST_RESET, True))] = selector.BooleanSelector()
    schema[vol.Optional(CONF_NUDGE, default=defaults.get(CONF_NUDGE, True))] = selector.BooleanSelector()
    return schema


def _charger_schema(defaults: dict[str, Any]) -> dict:
    return {
        vol.Required(CONF_MODEL, default=defaults.get(CONF_MODEL, EASEE_MODELS[0])): selector.SelectSelector(
            selector.SelectSelectorConfig(options=EASEE_MODELS, mode=selector.SelectSelectorMode.DROPDOWN)
        ),
        vol.Required(CONF_PHASES, default=str(defaults.get(CONF_PHASES, DEFAULT_PHASES))): selector.SelectSelector(
            selector.SelectSelectorConfig(options=["1", "3"], translation_key="phases")
        ),
        vol.Required(CONF_MAX_CURRENT, default=defaults.get(CONF_MAX_CURRENT, DEFAULT_MAX_CURRENT)): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=6, max=32, step=1, unit_of_measurement="A",
                mode=selector.NumberSelectorMode.SLIDER,
            )
        ),
        # Easee chargers switch between 1 and 3 phases: solar charging on 1 phase from 6 A (≈1.4 kW)
        vol.Optional(CONF_PHASE_SWITCHING, default=defaults.get(CONF_PHASE_SWITCHING, True)): selector.BooleanSelector(),
        vol.Optional(CONF_SESSION_MODE, default=defaults.get(CONF_SESSION_MODE) or SESSION_MODE_KEEP): selector.SelectSelector(
            selector.SelectSelectorConfig(options=[SESSION_MODE_KEEP, *MODES], translation_key="session_mode", mode=selector.SelectSelectorMode.DROPDOWN)
        ),
        vol.Optional(CONF_NO_PRICES, default=defaults.get(CONF_NO_PRICES) or NO_PRICES_CHARGE): selector.SelectSelector(
            selector.SelectSelectorConfig(options=[NO_PRICES_CHARGE, NO_PRICES_WAIT], translation_key="no_prices_action")
        ),
    }


def _clean(data: dict[str, Any]) -> dict[str, Any]:
    out = {k: v for k, v in data.items() if v not in (None, "")}
    if CONF_PHASES in out:
        out[CONF_PHASES] = int(out[CONF_PHASES])
    if CONF_MAX_CURRENT in out:
        out[CONF_MAX_CURRENT] = int(out[CONF_MAX_CURRENT])
    if CONF_MAIN_FUSE in out:
        try:
            out[CONF_MAIN_FUSE] = int(float(out[CONF_MAIN_FUSE]))
        except (TypeError, ValueError):
            out[CONF_MAIN_FUSE] = DEFAULT_MAIN_FUSE
    return out


class EaseeSmartConfigFlow(ConfigFlow, domain=DOMAIN):
    """Three short steps: charger → settings → energy."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._charger: dr.DeviceEntry | None = None
        self._car: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if not self.hass.config_entries.async_entries(EASEE_DOMAIN):
            return self.async_abort(reason="easee_missing")
        chargers, equalizers = _easee_devices(self.hass)
        if not chargers:
            return self.async_abort(reason="no_chargers")

        if user_input is not None:
            device_id = user_input[CONF_CHARGER_DEVICE]
            self._charger = dr.async_get(self.hass).async_get(device_id)
            await self.async_set_unique_id(easee_product_id(self._charger))
            self._abort_if_unique_id_configured()
            self._data[CONF_CHARGER_DEVICE] = device_id
            eq = user_input.get(CONF_EQUALIZER_DEVICE, NO_EQUALIZER)
            if eq != NO_EQUALIZER:
                self._data[CONF_EQUALIZER_DEVICE] = eq
            self._data[CONF_ENABLE_ENTITIES] = user_input.get(CONF_ENABLE_ENTITIES, True)
            return await self.async_step_charger()

        configured = {e.unique_id for e in self._async_current_entries()}
        options = [
            selector.SelectOptionDict(value=d.id, label=_label(d))
            for d in chargers
            if easee_product_id(d) not in configured
        ]
        if not options:
            return self.async_abort(reason="already_configured")
        eq_options = [selector.SelectOptionDict(value=NO_EQUALIZER, label="—")] + [
            selector.SelectOptionDict(value=d.id, label=_label(d)) for d in equalizers
        ]
        schema = {
            vol.Required(CONF_CHARGER_DEVICE, default=options[0]["value"]): selector.SelectSelector(
                selector.SelectSelectorConfig(options=options, mode=selector.SelectSelectorMode.LIST)
            ),
            vol.Optional(
                CONF_EQUALIZER_DEVICE,
                default=equalizers[0].id if len(equalizers) == 1 else NO_EQUALIZER,
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(options=eq_options, mode=selector.SelectSelectorMode.DROPDOWN)
            ),
            vol.Optional(CONF_ENABLE_ENTITIES, default=True): selector.BooleanSelector(),
        }
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema),
            description_placeholders={"count": str(len(options))},
        )

    async def async_step_charger(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._data.update(_clean(user_input))
            if CONF_EQUALIZER_DEVICE in self._data:
                return await self.async_step_energy()
            return await self.async_step_grid()
        model = _detect_model(self._charger)
        circuit = _easee_rated(self.hass, self._charger, "circuit_ratedCurrent")
        defaults = {
            CONF_MODEL: model,
            CONF_MAX_CURRENT: max(6, min(circuit or DEFAULT_MAX_CURRENT, MODEL_MAX_CURRENT.get(model, 32))),
        }
        return self.async_show_form(
            step_id="charger",
            data_schema=vol.Schema(_charger_schema(defaults)),
            description_placeholders={
                "name": self._charger.name_by_user or self._charger.name or "Easee" if self._charger else "Easee",
                "detected": model,
            },
        )

    async def async_step_grid(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Main connection: lets solar charging see export without an Equalizer."""
        if user_input is not None:
            self._data.update(_clean(user_input))
            return await self.async_step_energy()
        suggested = suggest_grid_sensors(self.hass)
        found = ", ".join(suggested.values()) or "—"
        site_fuse = _easee_rated(self.hass, self._charger, "site_ratedCurrent")
        if site_fuse:
            suggested[CONF_MAIN_FUSE] = site_fuse
        return self.async_show_form(
            step_id="grid",
            data_schema=vol.Schema(_grid_schema(suggested)),
            description_placeholders={"found": found},
        )

    async def async_step_energy(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._data.update(_clean(user_input))
            return await self.async_step_cars()
        return self.async_show_form(
            step_id="energy",
            data_schema=vol.Schema(_energy_schema(self.hass, {})),
        )

    async def async_step_cars(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Optionally link a car now (more cars can be added later)."""
        if user_input is not None:
            device_id = user_input.get(F_DEVICE)
            if not device_id:
                return self._finish()
            self._car = detect_car_entities(self.hass, device_id)
            return await self.async_step_car_details()
        return self.async_show_form(step_id="cars", data_schema=vol.Schema(_device_step_schema(self.hass, set())))

    async def async_step_car_details(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._data[CONF_CARS] = [_clean_car(user_input, self._car.get(F_DEVICE))]
            return self._finish()
        return self.async_show_form(step_id="car_details", data_schema=vol.Schema(_car_schema(self._car, False)))

    def _finish(self) -> ConfigFlowResult:
        has_eq = CONF_EQUALIZER_DEVICE in self._data
        if self._data.pop(CONF_ENABLE_ENTITIES, False):
            registry = dr.async_get(self.hass)
            enable_disabled_entities(self.hass, easee_product_id(self._charger), REQUIRED_CHARGER_KEYS)
            if has_eq:
                enable_disabled_entities(
                    self.hass,
                    easee_product_id(registry.async_get(self._data[CONF_EQUALIZER_DEVICE])),
                    REQUIRED_EQUALIZER_KEYS,
                )
        title = (self._charger.name_by_user or self._charger.name) if self._charger else "Easee"
        return self.async_create_entry(title=f"{title} Smart", data=self._data)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return EaseeSmartOptionsFlow()


class EaseeSmartOptionsFlow(OptionsFlow):
    """Change settings later: charger, main connection, prices and costs."""

    def _current(self) -> dict[str, Any]:
        return {**self.config_entry.data, **self.config_entry.options}

    def _save(self, user_input: dict[str, Any], cleared: list[str]) -> ConfigFlowResult:
        data = {**self.config_entry.options, **_clean(user_input)}
        # Fields left empty clear the earlier value instead of falling back to the setup data.
        for key in cleared:
            if key not in user_input or user_input[key] in (None, ""):
                data[key] = None
        return self.async_create_entry(data=data)

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        menu = ["charger", "equalizer", "energy", "cars", "advanced", "dashboard"]
        if self._current().get(CONF_EQUALIZER_DEVICE) in (None, "", NO_EQUALIZER):
            menu.insert(2, "grid")
        return self.async_show_menu(step_id="init", menu_options=menu)

    async def async_step_equalizer(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Link (or unlink) an Easee Equalizer and choose whether the cards show it."""
        _chargers, equalizers = _easee_devices(self.hass)
        current = self._current()
        if user_input is not None:
            eq = user_input.get(CONF_EQUALIZER_DEVICE) or NO_EQUALIZER
            if eq != NO_EQUALIZER and eq != current.get(CONF_EQUALIZER_DEVICE):
                device = dr.async_get(self.hass).async_get(eq)
                enable_disabled_entities(self.hass, easee_product_id(device), REQUIRED_EQUALIZER_KEYS)
            data = {**self.config_entry.options, CONF_EQUALIZER_DEVICE: eq,
                    CONF_SHOW_EQUALIZER: user_input.get(CONF_SHOW_EQUALIZER, "auto")}
            return self.async_create_entry(data=data)
        chosen = current.get(CONF_EQUALIZER_DEVICE)
        if chosen in (None, ""):
            # nothing filled in yet: pop up the Equalizer the Easee integration knows
            chosen = equalizers[0].id if equalizers else NO_EQUALIZER
        options = [selector.SelectOptionDict(value=NO_EQUALIZER, label="—")] + [
            selector.SelectOptionDict(value=d.id, label=_label(d)) for d in equalizers
        ]
        if chosen not in [o["value"] for o in options]:
            chosen = NO_EQUALIZER
        schema = {
            vol.Required(CONF_EQUALIZER_DEVICE, default=chosen): selector.SelectSelector(
                selector.SelectSelectorConfig(options=options, mode=selector.SelectSelectorMode.DROPDOWN)
            ),
            vol.Required(CONF_SHOW_EQUALIZER, default=current.get(CONF_SHOW_EQUALIZER) or "auto"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=SHOW_EQUALIZER_OPTIONS, translation_key="show_equalizer")
            ),
        }
        return self.async_show_form(
            step_id="equalizer",
            data_schema=vol.Schema(schema),
            description_placeholders={"found": ", ".join(_label(d) for d in equalizers) or "—"},
        )

    async def async_step_dashboard(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Put the ready-made dashboard in the sidebar (or refresh it)."""
        from .dashboard import async_create_dashboard

        errors: dict[str, str] = {}
        if user_input is not None:
            manager = getattr(self.config_entry, "runtime_data", None)
            try:
                if manager is None:
                    raise HomeAssistantError("not loaded")
                url = await async_create_dashboard(manager)
            except HomeAssistantError:
                errors["base"] = "dashboard_failed"
            else:
                return self.async_abort(reason="dashboard_created", description_placeholders={"url": f"/{url}"})
        return self.async_show_form(step_id="dashboard", data_schema=vol.Schema({}), errors=errors)

    async def async_step_charger(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self._save(user_input, [])
        return self.async_show_form(step_id="charger", data_schema=vol.Schema(_charger_schema(self._current())))

    async def async_step_grid(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self._save(user_input, list(GRID_KEYS))
        current = self._current()
        if not any(current.get(k) for k in GRID_KEYS):
            suggested = suggest_grid_sensors(self.hass)
            current = {**current, **{k: v for k, v in suggested.items() if not current.get(k)}}
        return self.async_show_form(
            step_id="grid",
            data_schema=vol.Schema(_grid_schema(current)),
            description_placeholders={"found": ", ".join(v for k, v in current.items() if k in GRID_KEYS and v) or "—"},
        )

    async def async_step_energy(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self._save(user_input, [CONF_REIMBURSEMENT])
        return self.async_show_form(step_id="energy", data_schema=vol.Schema(_energy_schema(self.hass, self._current())))

    # ------------------------------------------------------------------ cars
    def _cars(self) -> list[dict[str, Any]]:
        return [dict(c.raw) for c in cars_from_options(self._current())]

    def _save_cars(self, cars: list[dict[str, Any]]) -> ConfigFlowResult:
        data = {**self.config_entry.options, CONF_CARS: cars, "soc_entity": None, "battery_capacity": None}
        return self.async_create_entry(data=data)

    async def async_step_cars(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        cars = self._cars()
        menu = []
        if len(cars) < MAX_CARS:
            menu.append("car_add")
        if cars:
            menu.append("car_pick")
        return self.async_show_menu(step_id="cars", menu_options=menu)

    async def async_step_car_add(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            device_id = user_input.get(F_DEVICE)
            self._car = detect_car_entities(self.hass, device_id) if device_id else {}
            self._car_index = None
            return await self.async_step_car_details()
        configured = {c.get(F_DEVICE) for c in self._cars() if c.get(F_DEVICE)}
        return self.async_show_form(step_id="car_add", data_schema=vol.Schema(_device_step_schema(self.hass, configured)))

    async def async_step_car_pick(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        cars = self._cars()
        if user_input is not None:
            self._car_index = int(user_input["car"])
            self._car = cars[self._car_index]
            return await self.async_step_car_details()
        options = [selector.SelectOptionDict(value=str(i), label=c.get(F_NAME) or f"Auto {i + 1}") for i, c in enumerate(cars)]
        return self.async_show_form(
            step_id="car_pick",
            data_schema=vol.Schema(
                {vol.Required("car", default="0"): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=options, mode=selector.SelectSelectorMode.LIST)
                )}
            ),
        )

    async def async_step_car_details(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        editing = getattr(self, "_car_index", None) is not None
        if user_input is not None:
            cars = self._cars()
            if editing:
                if user_input.get("remove"):
                    cars.pop(self._car_index)
                else:
                    cars[self._car_index] = _clean_car(user_input, self._car.get(F_DEVICE))
            else:
                cars.append(_clean_car(user_input, self._car.get(F_DEVICE)))
            return self._save_cars(cars[:MAX_CARS])
        return self.async_show_form(step_id="car_details", data_schema=vol.Schema(_car_schema(self._car, editing)))

    async def async_step_advanced(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self._save(user_input, [])
        return self.async_show_form(step_id="advanced", data_schema=vol.Schema(_advanced_schema(self._current())))
