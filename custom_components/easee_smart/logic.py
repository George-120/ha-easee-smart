"""Pure charging logic for Easee Smart (no Home Assistant imports, unit-testable)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
import math
from statistics import median
from typing import Any
from collections.abc import Iterable

START_KEYS = ("start", "from", "start_time", "startsAt", "starts_at", "time", "datetime", "date", "hour", "readingDate")
END_KEYS = ("end", "till", "to", "end_time", "endsAt", "ends_at", "until")
PRICE_KEYS = (
    "value",
    "price",
    "total",
    "price_per_kwh",
    "electricity_price",
    "marketPrice",
    "market_price",
    "priceIncludingVat",
    "price_incl",
    "all_in_price",
    "tariff",
)
FLOAT_LIST_KEYS = {
    "today": 0,
    "tomorrow": 1,
    "prices_today": 0,
    "prices_tomorrow": 1,
    "today_prices": 0,
    "tomorrow_prices": 1,
}


@dataclass(frozen=True)
class PriceSlot:
    """One price period."""

    start: datetime
    end: datetime
    price: float

    @property
    def hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600


def _parse_dt(value: Any, tz) -> datetime | None:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        txt = value.strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(txt)
        except ValueError:
            return None
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalise_unit(prices: list[float]) -> float:
    """Return divisor to convert to currency/kWh (handles ct/kWh and 1e-7 units)."""
    if not prices:
        return 1.0
    typical = median(abs(p) for p in prices)
    if typical > 1000:
        return 10_000_000.0
    if typical > 5:
        return 100.0
    return 1.0


def parse_price_forecast(attributes: dict[str, Any] | None, now: datetime) -> list[PriceSlot]:
    """Find a price forecast in the attributes of any common price sensor."""
    if not attributes:
        return []
    tz = now.tzinfo
    raw: dict[datetime, tuple[datetime | None, float]] = {}

    for key, value in attributes.items():
        if not isinstance(value, (list, tuple)) or not value:
            continue
        first = value[0]
        if isinstance(first, dict):
            skey = next((k for k in START_KEYS if k in first), None)
            pkey = next((k for k in PRICE_KEYS if k in first), None)
            if skey is None or pkey is None:
                continue
            ekey = next((k for k in END_KEYS if k in first), None)
            for item in value:
                if not isinstance(item, dict):
                    continue
                start = _parse_dt(item.get(skey), tz)
                price = _to_float(item.get(pkey))
                if start is None or price is None:
                    continue
                end = _parse_dt(item.get(ekey), tz) if ekey else None
                raw.setdefault(start, (end, price))
        elif key in FLOAT_LIST_KEYS and all(_to_float(v) is not None for v in value):
            day = now.date() + timedelta(days=FLOAT_LIST_KEYS[key])
            step = timedelta(hours=24) / len(value)
            base = datetime.combine(day, time(0), tzinfo=tz)
            for idx, v in enumerate(value):
                start = base + step * idx
                raw.setdefault(start, (start + step, float(v)))

    if not raw:
        return []
    starts = sorted(raw)
    gaps = [(b - a) for a, b in zip(starts, starts[1:], strict=False) if b > a]
    default_len = min(gaps) if gaps else timedelta(hours=1)
    divisor = _normalise_unit([raw[s][1] for s in starts])
    slots: list[PriceSlot] = []
    for idx, start in enumerate(starts):
        end, price = raw[start]
        if end is None or end <= start:
            nxt = starts[idx + 1] if idx + 1 < len(starts) else None
            end = nxt if nxt and nxt - start <= default_len * 4 else start + default_len
        slots.append(PriceSlot(start, end, round(price / divisor, 5)))
    return slots


def price_at(slots: Iterable[PriceSlot], moment: datetime) -> float | None:
    for slot in slots:
        if slot.start <= moment < slot.end:
            return slot.price
    return None


def next_departure(now: datetime, departure: time) -> datetime:
    dep = datetime.combine(now.date(), departure, tzinfo=now.tzinfo)
    if dep <= now + timedelta(minutes=5):
        dep += timedelta(days=1)
    return dep


@dataclass
class ChargePlan:
    """Result of planning cheapest slots."""

    slots: list[PriceSlot] = field(default_factory=list)
    charge_now: bool = False
    hours_needed: float = 0.0
    hours_covered: float = 0.0
    estimated_cost: float | None = None
    average_price: float | None = None
    next_start: datetime | None = None
    complete_by: datetime | None = None
    fallback: bool = False


def plan_cheapest(
    slots: list[PriceSlot],
    now: datetime,
    departure: datetime,
    energy_needed_kwh: float,
    charge_power_kw: float,
    always_below_price: float | None = None,
) -> ChargePlan:
    """Pick the cheapest periods between now and departure to deliver the energy."""
    plan = ChargePlan()
    if energy_needed_kwh <= 0 or charge_power_kw <= 0:
        return plan
    plan.hours_needed = energy_needed_kwh / charge_power_kw

    window: list[PriceSlot] = []
    for slot in slots:
        if slot.end <= now or slot.start >= departure:
            continue
        start = max(slot.start, now)
        end = min(slot.end, departure)
        if end > start:
            window.append(PriceSlot(start, end, slot.price))

    if not window:
        # No price information at all: charge now (safe default).
        plan.fallback = True
        plan.charge_now = True
        return plan

    chosen: list[PriceSlot] = []
    remaining = plan.hours_needed
    for slot in sorted(window, key=lambda s: (s.price, s.start)):
        if remaining <= 0:
            break
        chosen.append(slot)
        remaining -= slot.hours
    if always_below_price is not None:
        for slot in window:
            if slot.price <= always_below_price and slot not in chosen:
                chosen.append(slot)

    chosen.sort(key=lambda s: s.start)
    plan.slots = chosen
    plan.hours_covered = _hours(chosen)
    if remaining > 0:
        # Prices do not reach far enough; charge as soon as possible for the rest.
        plan.charge_now = True
        plan.fallback = True
    if chosen:
        plan.charge_now = plan.charge_now or any(s.start <= now < s.end for s in chosen)
        plan.next_start = next((s.start for s in chosen if s.end > now), None)
        plan.complete_by = chosen[-1].end
        energy = 0.0
        cost = 0.0
        left = energy_needed_kwh
        for s in sorted(chosen, key=lambda s: (s.price, s.start)):
            e = min(left, s.hours * charge_power_kw)
            if e <= 0:
                break
            cost += e * s.price
            energy += e
            left -= e
        plan.estimated_cost = round(cost, 2)
        plan.average_price = round(cost / energy, 4) if energy else None
    return plan


def _hours(slots: Iterable[PriceSlot]) -> float:
    return sum(s.hours for s in slots)


def amps_for_power(power_kw: float, phases: int, voltage: float) -> float:
    if phases <= 0 or voltage <= 0:
        return 0.0
    return power_kw * 1000 / (phases * voltage)


def power_for_amps(amps: float, phases: int, voltage: float) -> float:
    return amps * phases * voltage / 1000


@dataclass
class SolarRegulator:
    """Turns grid surplus into a charge current with start/stop hysteresis."""

    min_current: int = 6
    max_current: int = 16
    start_delay: float = 120
    stop_delay: float = 300
    _above_since: datetime | None = None
    _below_since: datetime | None = None
    active: bool = False
    _history: list[float] = field(default_factory=list)

    def reset(self) -> None:
        self._above_since = None
        self._below_since = None
        self.active = False
        self._history.clear()

    def update(
        self,
        now: datetime,
        surplus_kw: float,
        current_charge_kw: float,
        phases: int,
        voltage: float,
    ) -> int:
        """Return wanted current (0 = do not charge).

        surplus_kw: export minus import measured at the grid connection
        (positive = power flowing to the grid). The charger's own consumption
        is part of that measurement, so it is added back.
        """
        available_kw = surplus_kw + max(current_charge_kw, 0.0)
        self._history.append(available_kw)
        self._history = self._history[-4:]
        smooth = sum(self._history) / len(self._history)
        amps = amps_for_power(smooth, phases, voltage)
        wanted = int(math.floor(amps))

        if wanted >= self.min_current:
            self._below_since = None
            if not self.active:
                self._above_since = self._above_since or now
                if (now - self._above_since).total_seconds() >= self.start_delay:
                    self.active = True
            if self.active:
                return min(wanted, self.max_current)
            return 0

        self._above_since = None
        if self.active:
            self._below_since = self._below_since or now
            if (now - self._below_since).total_seconds() >= self.stop_delay:
                self.active = False
                return 0
            return self.min_current
        return 0


def month_key(day: date) -> str:
    return f"{day.year:04d}-{day.month:02d}"
