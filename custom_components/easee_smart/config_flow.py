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
from homeassistant.helpers import device_registry as dr, selector

from .const import (
    CONF_BATTERY_CAPACITY,
    CONF_CHARGER_DEVICE,
    CONF_ENABLE_ENTITIES,
    CONF_EQUALIZER_DEVICE,
    CONF_FIXED_PRICE,
    CONF_GRID_POWER_ENTITY,
    CONF_GRID_POWER_INVERTED,
    CONF_MAX_CURRENT,
    CONF_MODEL,
    CONF_PHASES,
    CONF_PRICE_ENTITY,
    CONF_REIMBURSEMENT,
    CONF_SOC_ENTITY,
    DEFAULT_BATTERY_CAPACITY,
    DEFAULT_MAX_CURRENT,
    DEFAULT_PHASES,
    DOMAIN,
    EASEE_DOMAIN,
    EASEE_MODELS,
    EQUALIZER_MODEL,
    MODEL_MAX_CURRENT,
    REQUIRED_CHARGER_KEYS,
    REQUIRED_EQUALIZER_KEYS,
)
from .manager import easee_product_id, enable_disabled_entities, resolve_entities

NO_EQUALIZER = "none"


def _easee_devices(hass: HomeAssistant) -> tuple[list[dr.DeviceEntry], list[dr.DeviceEntry]]:
    """Return (chargers, equalizers) known by the Easee integration."""
    registry = dr.async_get(hass)
    chargers: list[dr.DeviceEntry] = []
    equalizers: list[dr.DeviceEntry] = []
    for device in registry.devices.values():
        if not easee_product_id(device):
            continue
        if device.model == EQUALIZER_MODEL:
            equalizers.append(device)
        elif resolve_entities(hass, easee_product_id(device), ["status"]):
            chargers.append(device)
    return chargers, equalizers


def _label(device: dr.DeviceEntry) -> str:
    name = device.name_by_user or device.name or easee_product_id(device)
    model = device.model or "Easee"
    return f"{name} · {model} ({easee_product_id(device)})"


def _detect_model(device: dr.DeviceEntry | None) -> str:
    if device and device.model in EASEE_MODELS:
        return device.model
    return EASEE_MODELS[0]


def _energy_schema(hass: HomeAssistant, defaults: dict[str, Any], has_equalizer: bool) -> dict:
    currency = hass.config.currency
    schema: dict = {
        vol.Optional(
            CONF_PRICE_ENTITY,
            description={"suggested_value": defaults.get(CONF_PRICE_ENTITY)},
        ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
        vol.Optional(
            CONF_FIXED_PRICE,
            description={"suggested_value": defaults.get(CONF_FIXED_PRICE)},
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=2, step=0.001, unit_of_measurement=f"{currency}/kWh",
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
    }
    if not has_equalizer:
        schema[
            vol.Optional(
                CONF_GRID_POWER_ENTITY,
                description={"suggested_value": defaults.get(CONF_GRID_POWER_ENTITY)},
            )
        ] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="power")
        )
        schema[
            vol.Optional(CONF_GRID_POWER_INVERTED, default=defaults.get(CONF_GRID_POWER_INVERTED, False))
        ] = selector.BooleanSelector()
    schema.update(
        {
            vol.Optional(
                CONF_SOC_ENTITY,
                description={"suggested_value": defaults.get(CONF_SOC_ENTITY)},
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="battery")
            ),
            vol.Optional(
                CONF_BATTERY_CAPACITY,
                default=defaults.get(CONF_BATTERY_CAPACITY, DEFAULT_BATTERY_CAPACITY),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=5, max=200, step=1, unit_of_measurement="kWh",
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
    }


def _clean(data: dict[str, Any]) -> dict[str, Any]:
    out = {k: v for k, v in data.items() if v not in (None, "")}
    if CONF_PHASES in out:
        out[CONF_PHASES] = int(out[CONF_PHASES])
    if CONF_MAX_CURRENT in out:
        out[CONF_MAX_CURRENT] = int(out[CONF_MAX_CURRENT])
    return out


class EaseeSmartConfigFlow(ConfigFlow, domain=DOMAIN):
    """Three short steps: charger → settings → energy."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._charger: dr.DeviceEntry | None = None

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
            return await self.async_step_energy()
        model = _detect_model(self._charger)
        defaults = {
            CONF_MODEL: model,
            CONF_MAX_CURRENT: min(DEFAULT_MAX_CURRENT, MODEL_MAX_CURRENT.get(model, 32)),
        }
        return self.async_show_form(
            step_id="charger",
            data_schema=vol.Schema(_charger_schema(defaults)),
            description_placeholders={
                "name": self._charger.name_by_user or self._charger.name or "Easee" if self._charger else "Easee",
                "detected": model,
            },
        )

    async def async_step_energy(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        has_eq = CONF_EQUALIZER_DEVICE in self._data
        if user_input is not None:
            self._data.update(_clean(user_input))
            if self._data.pop(CONF_ENABLE_ENTITIES, False):
                registry = dr.async_get(self.hass)
                enable_disabled_entities(
                    self.hass, easee_product_id(self._charger), REQUIRED_CHARGER_KEYS
                )
                if has_eq:
                    enable_disabled_entities(
                        self.hass,
                        easee_product_id(registry.async_get(self._data[CONF_EQUALIZER_DEVICE])),
                        REQUIRED_EQUALIZER_KEYS,
                    )
            title = (self._charger.name_by_user or self._charger.name) if self._charger else "Easee"
            return self.async_create_entry(title=f"{title} Smart", data=self._data)
        return self.async_show_form(
            step_id="energy",
            data_schema=vol.Schema(_energy_schema(self.hass, {}, has_eq)),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return EaseeSmartOptionsFlow()


class EaseeSmartOptionsFlow(OptionsFlow):
    """Change charger settings and energy sources later."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        current = {**self.config_entry.data, **self.config_entry.options}
        has_eq = CONF_EQUALIZER_DEVICE in self.config_entry.data
        if user_input is not None:
            data = _clean(user_input)
            # Fields left empty must clear the earlier value (not fall back to setup data).
            for key in (
                CONF_PRICE_ENTITY,
                CONF_FIXED_PRICE,
                CONF_GRID_POWER_ENTITY,
                CONF_SOC_ENTITY,
                CONF_REIMBURSEMENT,
            ):
                data.setdefault(key, None)
            return self.async_create_entry(data=data)
        schema = {**_charger_schema(current), **_energy_schema(self.hass, current, has_eq)}
        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema))
