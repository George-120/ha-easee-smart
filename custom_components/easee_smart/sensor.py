"""Sensors for Easee Smart."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    MATCH_ALL,
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import EaseeSmartConfigEntry
from .const import ALL_STATUSES, SMART_STATES
from .entity import EaseeSmartEntity
from .manager import EaseeSmartManager


@dataclass(frozen=True, kw_only=True)
class EaseeSmartSensorDescription(SensorEntityDescription):
    """Sensor description with a value function."""

    value_fn: Callable[[EaseeSmartManager], Any]
    attr_fn: Callable[[EaseeSmartManager], dict[str, Any]] | None = None
    available_fn: Callable[[EaseeSmartManager], bool] = lambda m: True
    monetary: bool = False
    per_kwh: bool = False


def _last_session(m: EaseeSmartManager, key: str):
    return m.sessions[-1].get(key) if m.sessions else None


def _avg_month(m: EaseeSmartManager):
    totals = m.period_totals("month")
    return round(totals["cost"] / totals["energy"], 4) if totals["energy"] else None


def _phase(i: int):
    return lambda m: m.snapshot.phase_currents[i]


GENERAL: tuple[EaseeSmartSensorDescription, ...] = (
    EaseeSmartSensorDescription(
        key="charger_status",
        device_class=SensorDeviceClass.ENUM,
        options=ALL_STATUSES,
        value_fn=lambda m: m.snapshot.status if m.snapshot.status in ALL_STATUSES else "unknown",
        attr_fn=lambda m: m.card_payload(),
    ),
    EaseeSmartSensorDescription(
        key="smart_status",
        device_class=SensorDeviceClass.ENUM,
        options=SMART_STATES,
        value_fn=lambda m: m.snapshot.smart_state,
    ),
    EaseeSmartSensorDescription(
        key="target_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda m: m.snapshot.target_current,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    EaseeSmartSensorDescription(
        key="energy_needed",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
        value_fn=lambda m: m.snapshot.energy_needed,
    ),
    EaseeSmartSensorDescription(
        key="planned_start",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda m: m.snapshot.plan.next_start if m.snapshot.plan else None,
    ),
    EaseeSmartSensorDescription(
        key="planned_end",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda m: m.snapshot.plan.complete_by if m.snapshot.plan else None,
    ),
    EaseeSmartSensorDescription(
        key="planned_cost",
        monetary=True,
        suggested_display_precision=2,
        value_fn=lambda m: m.snapshot.plan.estimated_cost if m.snapshot.plan else None,
    ),
    EaseeSmartSensorDescription(
        key="current_price",
        per_kwh=True,
        suggested_display_precision=3,
        value_fn=lambda m: m.snapshot.price,
        attr_fn=lambda m: {
            "market_price": m.market_price(),
            "bidding_zone": m.zone,
            "prices_tomorrow": m.day_ahead.has_tomorrow,
            "source": "Energy-Charts (EPEX SPOT day-ahead)",
        },
    ),
    EaseeSmartSensorDescription(
        key="session_cost",
        monetary=True,
        suggested_display_precision=2,
        value_fn=lambda m: round(m.session.cost, 2) if m.session.start else 0.0,
    ),
    EaseeSmartSensorDescription(
        key="cost_today",
        monetary=True,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda m: m.period_totals("day")["cost"],
    ),
    EaseeSmartSensorDescription(
        key="cost_month",
        monetary=True,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda m: m.period_totals("month")["cost"],
    ),
    EaseeSmartSensorDescription(
        key="cost_total",
        monetary=True,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda m: round(m.totals["cost"], 2),
    ),
    EaseeSmartSensorDescription(
        key="energy_today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value_fn=lambda m: m.period_totals("day")["energy"],
    ),
    EaseeSmartSensorDescription(
        key="energy_month",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        value_fn=lambda m: m.period_totals("month")["energy"],
        attr_fn=lambda m: {"previous_month": m.period_totals("prev_month")},
    ),
    EaseeSmartSensorDescription(
        key="average_price_month",
        per_kwh=True,
        suggested_display_precision=3,
        value_fn=_avg_month,
    ),
    EaseeSmartSensorDescription(
        key="reimbursement_month",
        monetary=True,
        suggested_display_precision=2,
        value_fn=lambda m: round(m.period_totals("month")["energy"] * m.reimbursement, 2)
        if m.reimbursement is not None
        else None,
        available_fn=lambda m: m.reimbursement is not None,
        attr_fn=lambda m: {
            "previous_month": round(m.period_totals("prev_month")["energy"] * m.reimbursement, 2)
            if m.reimbursement is not None
            else None,
            "rate_per_kwh": m.reimbursement,
        },
    ),
    EaseeSmartSensorDescription(
        key="last_session_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=lambda m: _last_session(m, "energy"),
        attr_fn=lambda m: {"start": _last_session(m, "start"), "end": _last_session(m, "end")},
    ),
    EaseeSmartSensorDescription(
        key="last_session_cost",
        monetary=True,
        suggested_display_precision=2,
        value_fn=lambda m: _last_session(m, "cost"),
    ),
)

ERE: tuple[EaseeSmartSensorDescription, ...] = tuple(
    EaseeSmartSensorDescription(
        key=f"ere_{period}",
        monetary=True,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda m, period=period: m.ere_earned(period),
        attr_fn=lambda m: {"rate_per_kwh": m.ere_rate},
    )
    for period in ("month", "year", "total")
)

CAR: tuple[EaseeSmartSensorDescription, ...] = (
    EaseeSmartSensorDescription(
        key="car_soc",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda m: m.car_soc(m.active_car()),
        attr_fn=lambda m: m._car_payload() or {},
    ),
)

SURPLUS: tuple[EaseeSmartSensorDescription, ...] = (
    EaseeSmartSensorDescription(
        key="grid_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda m: m.snapshot.grid_power_kw,
    ),
    EaseeSmartSensorDescription(
        key="surplus_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda m: max(m.snapshot.surplus_kw, 0.0) if m.snapshot.surplus_kw is not None else None,
    ),
)

EQUALIZER: tuple[EaseeSmartSensorDescription, ...] = (
    *(
        EaseeSmartSensorDescription(
            key=f"phase_l{i + 1}_current",
            device_class=SensorDeviceClass.CURRENT,
            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=1,
            value_fn=_phase(i),
        )
        for i in range(3)
    ),
    EaseeSmartSensorDescription(
        key="phase_headroom",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda m: m.snapshot.phase_headroom,
        attr_fn=lambda m: {"main_fuse": m.snapshot.main_fuse},
    ),
    EaseeSmartSensorDescription(
        key="phase_load",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda m: m.snapshot.phase_load_pct,
    ),
)


VRM: tuple[EaseeSmartSensorDescription, ...] = (
    EaseeSmartSensorDescription(
        key="vrm_plan",
        device_class=SensorDeviceClass.ENUM,
        options=["waiting", "ok", "auth_error", "error"],
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda m: m.vrm.status if m.vrm else None,
        attr_fn=lambda m: m.vrm.attributes() if m.vrm else {},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EaseeSmartConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    manager = entry.runtime_data
    descriptions = list(GENERAL)
    if manager.cars:
        descriptions += CAR
    if manager.ere_rate is not None:
        descriptions += ERE
    if manager.has_surplus_source:
        descriptions += SURPLUS
    if manager.equalizer_entities or any(manager.phase_entities):
        descriptions += EQUALIZER
    if manager.vrm is not None:
        descriptions += VRM
    async_add_entities(EaseeSmartSensor(manager, d) for d in descriptions)


class EaseeSmartSensor(EaseeSmartEntity, SensorEntity):
    """A computed sensor."""

    entity_description: EaseeSmartSensorDescription
    # The card payload is large and changes all the time: keep every attribute out of the recorder database.
    _unrecorded_attributes = frozenset({MATCH_ALL})

    def __init__(self, manager: EaseeSmartManager, description: EaseeSmartSensorDescription) -> None:
        super().__init__(manager, description.key)
        self.entity_description = description
        currency = manager.hass.config.currency
        if description.monetary:
            self._attr_device_class = SensorDeviceClass.MONETARY
            self._attr_native_unit_of_measurement = currency
        elif description.per_kwh:
            self._attr_native_unit_of_measurement = f"{currency}/{UnitOfEnergy.KILO_WATT_HOUR}"

    @property
    def available(self) -> bool:
        return self.entity_description.available_fn(self.manager)

    @property
    def native_value(self):
        return self.entity_description.value_fn(self.manager)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attr_fn is None:
            return None
        return self.entity_description.attr_fn(self.manager)
