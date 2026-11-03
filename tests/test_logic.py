"""Tests for the pure charging logic (run: python -m pytest tests)."""
import importlib.util
import pathlib
from datetime import datetime, time, timedelta, timezone

spec = importlib.util.spec_from_file_location(
    "logic", pathlib.Path(__file__).parents[1] / "custom_components/easee_smart/logic.py"
)
logic = importlib.util.module_from_spec(spec)
import sys

sys.modules["logic"] = logic
spec.loader.exec_module(logic)

TZ = timezone(timedelta(hours=1))
NOW = datetime(2026, 11, 3, 20, 0, tzinfo=TZ)


def hourly(prices, start=NOW):
    return [
        {"start": (start + timedelta(hours=i)).isoformat(), "end": (start + timedelta(hours=i + 1)).isoformat(), "value": p}
        for i, p in enumerate(prices)
    ]


def test_parse_nordpool_raw():
    slots = logic.parse_price_forecast({"raw_today": hourly([0.3, 0.2]), "raw_tomorrow": hourly([0.1], NOW + timedelta(hours=2))}, NOW)
    assert [s.price for s in slots] == [0.3, 0.2, 0.1]
    assert slots[0].hours == 1


def test_parse_float_lists_and_cents():
    attrs = {"today": [25.0] * 24, "tomorrow": [12.0] * 24}
    slots = logic.parse_price_forecast(attrs, NOW)
    assert len(slots) == 48
    assert slots[0].price == 0.25 and slots[-1].price == 0.12


def test_parse_quarter_hours_without_end():
    items = [{"from": (NOW + timedelta(minutes=15 * i)).isoformat(), "price": 0.2 + i / 100} for i in range(8)]
    slots = logic.parse_price_forecast({"prices": items}, NOW)
    assert len(slots) == 8
    assert slots[0].end - slots[0].start == timedelta(minutes=15)


def test_parse_zonneplan_units():
    items = [{"datetime": (NOW + timedelta(hours=i)).isoformat(), "electricity_price": 2_500_000} for i in range(3)]
    slots = logic.parse_price_forecast({"forecast": items}, NOW)
    assert slots[0].price == 0.25


def test_plan_picks_cheapest_before_departure():
    prices = [0.30, 0.28, 0.25, 0.10, 0.05, 0.08, 0.20, 0.40, 0.50, 0.01]
    slots = logic.parse_price_forecast({"raw_today": hourly(prices)}, NOW)
    dep = NOW + timedelta(hours=9)  # last (0.01) slot is after departure
    plan = logic.plan_cheapest(slots, NOW, dep, energy_needed_kwh=22, charge_power_kw=11)
    assert [s.price for s in plan.slots] == [0.05, 0.08]
    assert not plan.charge_now
    assert plan.next_start == NOW + timedelta(hours=4)
    assert plan.estimated_cost == round(11 * 0.05 + 11 * 0.08, 2)


def test_plan_charges_now_when_current_slot_is_cheap():
    slots = logic.parse_price_forecast({"raw_today": hourly([0.01, 0.3, 0.3])}, NOW)
    plan = logic.plan_cheapest(slots, NOW + timedelta(minutes=10), NOW + timedelta(hours=3), 5, 11)
    assert plan.charge_now


def test_plan_without_prices_is_safe():
    plan = logic.plan_cheapest([], NOW, NOW + timedelta(hours=8), 10, 11)
    assert plan.charge_now and plan.fallback


def test_plan_not_enough_hours_charges_now():
    slots = logic.parse_price_forecast({"raw_today": hourly([0.3, 0.1])}, NOW)
    plan = logic.plan_cheapest(slots, NOW, NOW + timedelta(hours=8), 50, 11)
    assert plan.charge_now and plan.fallback


def test_price_threshold_adds_slots():
    slots = logic.parse_price_forecast({"raw_today": hourly([0.3, -0.02, 0.2, 0.25])}, NOW)
    plan = logic.plan_cheapest(slots, NOW, NOW + timedelta(hours=4), 5, 11, always_below_price=0.21)
    assert sorted(s.price for s in plan.slots) == [-0.02, 0.2]


def test_departure_rolls_to_tomorrow():
    assert logic.next_departure(NOW, time(7, 0)) == datetime(2026, 11, 4, 7, 0, tzinfo=TZ)
    assert logic.next_departure(NOW, time(22, 0)) == datetime(2026, 11, 3, 22, 0, tzinfo=TZ)


def test_solar_regulator_hysteresis():
    reg = logic.SolarRegulator(min_current=6, max_current=16, start_delay=120, stop_delay=300)
    t = NOW
    # 5 kW export on 3 phases ~ 7 A, needs 2 minutes before starting
    assert reg.update(t, 5.0, 0.0, 3, 230) == 0
    assert reg.update(t + timedelta(seconds=150), 5.0, 0.0, 3, 230) == 7
    # charging 4.8 kW, surplus drops to -2 kW import -> available 2.8 kW (4 A): keep min for stop delay
    t2 = t + timedelta(seconds=180)
    for i in range(4):
        out = reg.update(t2 + timedelta(seconds=30 * i), -2.0, 4.8, 3, 230)
    assert out == 6
    assert reg.update(t2 + timedelta(seconds=400), -2.0, 4.8, 3, 230) == 0
    assert not reg.active


def test_amps_power_roundtrip():
    assert round(logic.power_for_amps(16, 3, 230), 2) == 11.04
    assert round(logic.amps_for_power(11.04, 3, 230)) == 16


def test_parse_zonneplan_quarter_hours():
    items = [
        {"start_date": (NOW + timedelta(minutes=15 * i)).isoformat(), "end_date": (NOW + timedelta(minutes=15 * (i + 1))).isoformat(),
         "price_tax_included": {"amount": 4553568}, "price_tax_excluded": {"amount": 3445087}, "sustainability_score": {"permille": 455}}
        for i in range(8)
    ]
    slots = logic.parse_price_forecast({"forecast": items}, NOW)
    assert len(slots) == 8 and slots[0].price == 0.45536 and slots[0].hours == 0.25
