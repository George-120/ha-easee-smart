"""Simulation of the manager with a minimal fake Home Assistant (no HA install needed)."""
import asyncio
import importlib
import json
import sys
import types
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from enum import StrEnum
from pathlib import Path

TZ = timezone(timedelta(hours=1))
CLOCK = {"now": datetime(2026, 11, 3, 20, 0, tzinfo=TZ)}


def _mod(name, **attrs):
    m = types.ModuleType(name)
    m.__dict__.update(attrs)
    sys.modules[name] = m
    return m


@dataclass
class State:
    entity_id: str
    state: str
    attributes: dict = field(default_factory=dict)


class States(dict):
    def get(self, eid):
        return dict.get(self, eid)


class Services:
    def __init__(self):
        self.calls = []

    def has_service(self, d, s):
        return True

    async def async_call(self, d, s, data, blocking=False):
        self.calls.append((d, s, dict(data)))


class Hass:
    def __init__(self, tmp):
        self.states = States()
        self.services = Services()
        self.config = types.SimpleNamespace(currency="EUR", country="NL", path=lambda *p: str(Path(tmp, *p)))
        self.tasks = []

    def async_create_task(self, coro):
        self.tasks.append(asyncio.ensure_future(coro))

    async def async_add_executor_job(self, fn, *a):
        return fn(*a)


class Disabler(StrEnum):
    INTEGRATION = "integration"


class EntityRegistry:
    def __init__(self, mapping):
        self.mapping = mapping

    def async_get_entity_id(self, domain, platform, unique_id):
        eid = self.mapping.get(unique_id)
        return eid if eid and eid.startswith(domain + ".") else None


REG = {}


class Store:
    def __init__(self, *a):
        self.data = None

    async def async_load(self):
        return self.data

    def async_delay_save(self, fn, delay):
        self.data = fn()

    async def async_save(self, data):
        self.data = data


def install_stubs():
    _mod("homeassistant")
    _mod("homeassistant.config_entries", ConfigEntry=object)
    _mod("homeassistant.const", ATTR_UNIT_OF_MEASUREMENT="unit_of_measurement", CONF_DEVICE_ID="device_id",
         STATE_UNAVAILABLE="unavailable", STATE_UNKNOWN="unknown")
    _mod("homeassistant.core", CALLBACK_TYPE=object, Event=object, HomeAssistant=object, callback=lambda f: f)
    _mod("homeassistant.helpers")
    devreg = types.SimpleNamespace(devices={})
    _mod("homeassistant.helpers.device_registry", DeviceEntry=object, async_get=lambda h: types.SimpleNamespace(async_get=lambda i: devreg.devices.get(i)))
    _mod("homeassistant.helpers.entity_registry", EntityRegistry=EntityRegistry, RegistryEntryDisabler=Disabler,
         async_get=lambda h: EntityRegistry(REG))
    _mod("homeassistant.helpers.dispatcher", async_dispatcher_send=lambda *a: None)
    _mod("homeassistant.helpers.event", async_track_state_change_event=lambda *a: (lambda: None),
         async_track_time_interval=lambda *a: (lambda: None))
    _mod("homeassistant.helpers.storage", Store=Store)
    _mod("homeassistant.exceptions", HomeAssistantError=Exception)
    _mod("homeassistant.components")
    _mod("homeassistant.helpers.aiohttp_client", async_get_clientsession=lambda h: None)
    if "aiohttp" not in sys.modules:
        _mod("aiohttp", ClientError=Exception, ClientTimeout=lambda **k: None)
    dt = _mod("homeassistant.util.dt", now=lambda: CLOCK["now"], utcnow=lambda: CLOCK["now"], as_local=lambda d: d.astimezone(TZ),
              parse_datetime=datetime.fromisoformat, as_utc=lambda d: d.astimezone(UTC),
              start_of_local_day=lambda: CLOCK["now"].astimezone(TZ).replace(hour=0, minute=0, second=0, microsecond=0))
    _mod("homeassistant.util", dt=dt)
    sys.modules["homeassistant"].helpers = sys.modules["homeassistant.helpers"]
    sys.modules["homeassistant.helpers"].device_registry = sys.modules["homeassistant.helpers.device_registry"]
    sys.modules["homeassistant.helpers"].entity_registry = sys.modules["homeassistant.helpers.entity_registry"]
    pkg = types.ModuleType("easee_smart")
    pkg.__path__ = [str(Path(__file__).parents[1] / "custom_components" / "easee_smart")]
    sys.modules["easee_smart"] = pkg
    return devreg


def make(tmp, options=None, equalizer=True, extra=None):
    devreg = install_stubs()
    for k in list(sys.modules):
        if k.startswith("easee_smart."):
            del sys.modules[k]
    mgr_mod = importlib.import_module("easee_smart.manager")
    devreg.devices["dev1"] = types.SimpleNamespace(identifiers={("easee", "EH1")}, name="Oprit", name_by_user=None, model="Charge Max")
    devreg.devices["dev2"] = types.SimpleNamespace(identifiers={("easee", "QP1")}, name="EQ", name_by_user=None, model="Equalizer")
    REG.clear()
    for k in ["status", "power", "session_energy", "lifetime_energy", "max_charger_limit"]:
        REG[f"EH1_{k}"] = f"sensor.c_{k}"
    for k in ["import_power", "export_power", "current", "voltage", "max_continuous_limit"]:
        REG[f"QP1_{k}"] = f"sensor.eq_{k}"
    hass = Hass(tmp)
    data = {"charger_device": "dev1", "phases": 3, "max_current": 16, "reimbursement_per_kwh": 0.23}
    if equalizer:
        data["equalizer_device"] = "dev2"
    data.update(extra or {})
    entry = types.SimpleNamespace(entry_id="E1", data=data,
                                  options=options or {})
    return hass, mgr_mod.EaseeSmartManager(hass, entry)


def setstate(hass, eid, state, **attrs):
    hass.states[eid] = State(eid, str(state), attrs)


def prices(hass, m):
    """Feed built-in day-ahead market prices (EUR/kWh) with zero taxes so values stay readable."""
    base = CLOCK["now"].replace(minute=0)
    m.day_ahead.points = [(base + timedelta(hours=i), 0.30 if i < 5 else 0.05 if i < 8 else 0.40) for i in range(14)]
    m.day_ahead.last_fetch = CLOCK["now"] + timedelta(days=1)  # no network in tests
    m.entry.options.update({"price_markup": 0.0, "energy_tax": 0.0, "vat_percent": 0.0})
    m._rebuild_prices()


def last_limit(hass):
    calls = [c for c in hass.services.calls if c[1] == "set_charger_dynamic_limit"]
    return calls[-1][2]["current"] if calls else None


def test_smart_waits_then_charges(tmp_path):
    async def run():
        hass, m = make(tmp_path)
        await m.async_setup()
        setstate(hass, "sensor.c_status", "awaiting_start")
        setstate(hass, "sensor.c_session_energy", 0)
        setstate(hass, "sensor.c_power", 0)
        setstate(hass, "sensor.c_lifetime_energy", 1000)
        setstate(hass, "sensor.eq_import_power", 0.5)
        setstate(hass, "sensor.eq_export_power", 0)
        setstate(hass, "sensor.eq_current", 3, state_currentL1=12.0, state_currentL2=4.0, state_currentL3=6.5)
        setstate(hass, "sensor.eq_max_continuous_limit", 25)
        prices(hass, m)
        await m.async_set_setting("target_energy", 30)
        await m.async_set_setting("mode", "smart")
        assert m.snapshot.smart_state == "waiting_cheap"
        assert last_limit(hass) == 0
        assert m.snapshot.phase_headroom == 13.0 and m.snapshot.phase_load_pct == 48
        # move into the cheap window
        CLOCK["now"] = CLOCK["now"] + timedelta(hours=5, minutes=5)
        m._recompute()
        await m._async_control()
        assert m.snapshot.smart_state == "charging_cheap"
        assert last_limit(hass) == 16
        # back to normal releases control
        await m.async_set_setting("mode", "normal")
        assert last_limit(hass) == 16 and not m._controlling
        CLOCK["now"] = datetime(2026, 11, 3, 20, 0, tzinfo=TZ)
    asyncio.run(run())


def test_solar_mode_uses_equalizer_surplus(tmp_path):
    async def run():
        hass, m = make(tmp_path)
        await m.async_setup()
        setstate(hass, "sensor.c_status", "awaiting_start")
        setstate(hass, "sensor.c_power", 0)
        setstate(hass, "sensor.eq_import_power", 0)
        setstate(hass, "sensor.eq_export_power", 6.0)
        await m.async_set_setting("mode", "solar")
        assert m.snapshot.smart_state == "waiting_solar" and last_limit(hass) == 0
        CLOCK["now"] += timedelta(seconds=130)
        m._recompute()
        await m._async_control()
        assert m.snapshot.smart_state == "charging_solar"
        assert last_limit(hass) == 8  # 6 kW / (3*230) = 8.7 A
        CLOCK["now"] = datetime(2026, 11, 3, 20, 0, tzinfo=TZ)
    asyncio.run(run())


def test_sessions_costs_and_report(tmp_path):
    async def run():
        hass, m = make(tmp_path)
        await m.async_setup()
        prices(hass, m)
        setstate(hass, "sensor.c_lifetime_energy", 1000)
        m._recompute()
        m._account_energy()
        old = State("sensor.c_status", "disconnected")
        setstate(hass, "sensor.c_status", "charging")
        m._handle_status_change(types.SimpleNamespace(data={"old_state": old, "new_state": hass.states["sensor.c_status"]}))
        assert m.session.start
        setstate(hass, "sensor.c_lifetime_energy", 1010)
        m._recompute()
        m._account_energy()
        assert m.session.energy == 10 and round(m.session.cost, 2) == 3.0
        setstate(hass, "sensor.c_session_energy", 10)
        m._recompute()
        m._handle_status_change(types.SimpleNamespace(data={"old_state": hass.states["sensor.c_status"], "new_state": State("sensor.c_status", "disconnected")}))
        assert m.sessions[-1]["energy"] == 10 and m.sessions[-1]["reimbursement"] == 2.3
        assert m.period_totals("month") == {"energy": 10.0, "cost": 3.0}
        res = await m.async_export_report("2026-11")
        text = res["csv"]
        assert "10,000" in text and res["sessions"] == 1 and res["reimbursement"] == 2.3
        assert "file" not in res and "url" not in res  # nothing in the public www folder
        assert not list(tmp_path.rglob("*.csv"))
        payload = m.card_payload()
        assert payload["month"]["energy"] == 10.0 and payload["sessions"][0]["cost"] == 3.0
    asyncio.run(run())


def test_main_connection_from_p1_meter(tmp_path):
    async def run():
        hass, m = make(tmp_path, equalizer=False, extra={
            "grid_import_entity": "sensor.p1_in", "grid_export_entity": "sensor.p1_out",
            "phase_l1_entity": "sensor.l1", "phase_l2_entity": "sensor.l2", "phase_l3_entity": "sensor.l3",
            "main_fuse": 35,
        })
        await m.async_setup()
        assert m.has_surplus_source and m.uses_meter
        setstate(hass, "sensor.c_status", "awaiting_start")
        setstate(hass, "sensor.c_power", 0)
        setstate(hass, "sensor.p1_in", 0, unit_of_measurement="W")
        setstate(hass, "sensor.p1_out", 4800, unit_of_measurement="W")
        for i, v in enumerate((7.1, 6.0, 30.5), 1):
            setstate(hass, f"sensor.l{i}", v)
        m._recompute()
        assert m.snapshot.grid_power_kw == -4.8 and m.snapshot.surplus_kw == 4.8
        assert m.snapshot.main_fuse == 35 and m.snapshot.phase_headroom == 4.5
        await m.async_set_setting("mode", "solar")
        CLOCK["now"] += timedelta(seconds=130)
        m._recompute()
        await m._async_control()
        assert last_limit(hass) == 6  # 4.8 kW / 690 = 6.9 A
        CLOCK["now"] = datetime(2026, 11, 3, 20, 0, tzinfo=TZ)
    asyncio.run(run())


def test_detects_zonneplan_and_dsmr_meters(tmp_path):
    install_stubs()
    sys.modules.pop("easee_smart.grid_detect", None)
    gd = importlib.import_module("easee_smart.grid_detect")

    def entry(eid, platform, dc):
        return types.SimpleNamespace(entity_id=eid, platform=platform, domain="sensor", disabled_by=None,
                                     unique_id=eid, device_class=None, original_device_class=dc)

    def run(entries):
        reg = types.SimpleNamespace(entities={e.entity_id: e for e in entries})
        sys.modules["homeassistant.helpers.entity_registry"].async_get = lambda h: reg
        hass = types.SimpleNamespace(states=States())
        return gd.suggest_grid_sensors(hass)

    zp = run([
        entry("sensor.connect_energiemeter_electricity_consumption", "zonneplan_one", "power"),
        entry("sensor.connect_energiemeter_electricity_production", "zonneplan_one", "power"),
        entry("sensor.envoy_1_current_power_production", "enphase_envoy", "power"),
        entry("sensor.envoy_1_current_net_power_consumption", "enphase_envoy", "power"),
    ])
    assert zp == {"grid_import_entity": "sensor.connect_energiemeter_electricity_consumption",
                  "grid_export_entity": "sensor.connect_energiemeter_electricity_production"}
    dsmr = run([
        entry("sensor.electricity_meter_power_consumption", "dsmr", "power"),
        entry("sensor.electricity_meter_power_production", "dsmr", "power"),
        entry("sensor.electricity_meter_current_phase_l1", "dsmr", "current"),
        entry("sensor.electricity_meter_current_phase_l2", "dsmr", "current"),
        entry("sensor.electricity_meter_current_phase_l3", "dsmr", "current"),
    ])
    assert dsmr["phase_l3_entity"] == "sensor.electricity_meter_current_phase_l3"
    envoy = run([entry("sensor.envoy_1_current_net_power_consumption", "enphase_envoy", "power"),
                 entry("sensor.envoy_1_current_power_production", "enphase_envoy", "power")])
    assert envoy == {"grid_power_entity": "sensor.envoy_1_current_net_power_consumption"}


def test_homewizard_p1_wins_over_zonneplan(tmp_path):
    install_stubs()
    sys.modules.pop("easee_smart.grid_detect", None)
    gd = importlib.import_module("easee_smart.grid_detect")

    def entry(eid, uid, platform, dc):
        return types.SimpleNamespace(entity_id=eid, platform=platform, domain="sensor", disabled_by=None,
                                     unique_id=uid, device_class=None, original_device_class=dc)

    entries = [
        entry("sensor.connect_energiemeter_electricity_consumption", "zp1", "zonneplan_one", "power"),
        entry("sensor.connect_energiemeter_electricity_production", "zp2", "zonneplan_one", "power"),
        entry("sensor.energysocket_5c2f_actueel_vermogen", "HWE-SKT_5c2f_active_power_w", "homewizard", "power"),
        entry("sensor.p1_meter_5c2f_actueel_vermogen", "HWE-P1_5c2f_active_power_w", "homewizard", "power"),
        entry("sensor.p1_meter_5c2f_actueel_vermogen_fase_1", "HWE-P1_5c2f_active_power_l1_w", "homewizard", "power"),
        *[entry(f"sensor.p1_meter_5c2f_actuele_stroom_fase_{n}", f"HWE-P1_5c2f_active_current_l{n}_a", "homewizard", "current") for n in (1, 2, 3)],
    ]
    reg = types.SimpleNamespace(entities={e.entity_id: e for e in entries})
    sys.modules["homeassistant.helpers.entity_registry"].async_get = lambda h: reg
    found = gd.suggest_grid_sensors(types.SimpleNamespace(states=States()))
    assert found == {
        "grid_power_entity": "sensor.p1_meter_5c2f_actueel_vermogen",
        "phase_l1_entity": "sensor.p1_meter_5c2f_actuele_stroom_fase_1",
        "phase_l2_entity": "sensor.p1_meter_5c2f_actuele_stroom_fase_2",
        "phase_l3_entity": "sensor.p1_meter_5c2f_actuele_stroom_fase_3",
    }


def test_energy_charts_prices_all_in(tmp_path):
    install_stubs()
    sys.modules.pop("easee_smart.prices", None)
    pr = importlib.import_module("easee_smart.prices")
    data = {"unix_seconds": [1793746800, 1793747700, 1793748600], "price": [200.13, None, 160.79], "unit": "EUR / MWh"}
    pts = pr.parse_energy_charts(data)
    assert len(pts) == 2 and pts[0][1] == 0.20013
    slots = pr.to_slots(pts, 0.0165, 0.0916, 21)
    assert slots[0].price == round((0.20013 + 0.0165 + 0.0916) * 1.21, 5)
    assert slots[0].end - slots[0].start == timedelta(minutes=15) * 1 or slots[0].end - slots[0].start == timedelta(minutes=30)
    assert pr.default_zone(types.SimpleNamespace(config=types.SimpleNamespace(country="DE"))) == "DE-LU"


def test_cars_active_by_plug_target_efficiency_and_ere(tmp_path):
    async def run():
        cars = [
            {"name": "e-Niro", "soc": "sensor.niro_soc", "capacity": 64, "plug": "binary_sensor.niro_plug", "target": 80,
             "start_entity": "button.niro_start", "refresh_entity": "button.niro_refresh", "limit_entity": "number.niro_limit"},
            {"name": "Inster", "soc": "sensor.inster_soc", "capacity": 49, "plug": "binary_sensor.inster_plug", "target": 90},
        ]
        hass, m = make(tmp_path, equalizer=False, extra={"cars": cars, "charge_efficiency": 90, "ere_enabled": True, "ere_rate": 0.12})
        await m.async_setup()
        setstate(hass, "sensor.c_status", "awaiting_start")
        setstate(hass, "sensor.niro_soc", 30)
        setstate(hass, "sensor.inster_soc", 50)
        setstate(hass, "binary_sensor.niro_plug", "off")
        setstate(hass, "binary_sensor.inster_plug", "on")
        m._recompute()
        assert m.active_car().name == "Inster"
        # (90 - 50)% of 49 kWh / 0.9 efficiency
        assert m.snapshot.energy_needed == round(0.40 * 49 / 0.9, 2)
        # fixed kWh target, also with a car that reports its battery level
        await m.async_set_setting("target_energy", 12.0)
        await m.async_set_setting("manual_kwh", True)
        assert m.snapshot.energy_needed == 12.0 and m.card_payload()["manual_kwh"] is True
        await m.async_set_setting("manual_kwh", False)
        assert m.snapshot.energy_needed == round(0.40 * 49 / 0.9, 2)
        setstate(hass, "binary_sensor.inster_plug", "off")
        setstate(hass, "binary_sensor.niro_plug", "on")
        m._recompute()
        assert m.active_car().name == "e-Niro"
        await m.async_set_car_target(70)
        assert m.car_target(m.active_car()) == 70
        assert ("number", "set_value", {"entity_id": "number.niro_limit", "value": 70}) in hass.services.calls
        await m.async_refresh_car()
        await m.async_force_car_start()
        assert ("button", "press", {"entity_id": "button.niro_refresh"}) in hass.services.calls
        assert ("button", "press", {"entity_id": "button.niro_start"}) in hass.services.calls
        await m.async_set_setting("active_car", "Inster")
        assert m.active_car().name == "Inster"
        m.days = {"2026-11-03": {"energy": 100.0, "cost": 20.0}, "2026-10-01": {"energy": 50.0, "cost": 10.0}}
        m.totals = {"energy": 400.0, "cost": 80.0}
        assert m.ere_earned("month") == 12.0 and m.ere_earned("year") == 18.0 and m.ere_earned("total") == 48.0
        assert m.card_payload()["car"]["name"] == "Inster"
    asyncio.run(run())


def test_old_single_battery_sensor_migrates_to_a_car(tmp_path):
    install_stubs()
    sys.modules.pop("easee_smart.cars", None)
    cars = importlib.import_module("easee_smart.cars")
    out = cars.cars_from_options({"soc_entity": "sensor.ev", "battery_capacity": 64})
    assert len(out) == 1 and out[0].soc_entity == "sensor.ev" and out[0].capacity == 64
    assert cars.cars_from_options({"cars": [], "soc_entity": "sensor.ev"}) == []


def test_detect_car_entities_any_brand(tmp_path):
    install_stubs()
    sys.modules.pop("easee_smart.cars", None)
    cars = importlib.import_module("easee_smart.cars")

    def e(eid, dc=None, name=None, unit=None):
        return types.SimpleNamespace(entity_id=eid, domain=eid.split(".")[0], disabled_by=None, device_id="car1",
                                     original_device_class=dc, device_class=None, original_name=name,
                                     translation_key=None, unit_of_measurement=unit)

    entries = [
        e("sensor.e_niro_ev_battery_level", "battery", unit="%"),
        e("sensor.e_niro_gezondheid_ev_accu_soh", "battery", unit="%"),
        e("sensor.e_niro_12v_battery", "battery", unit="%"),
        e("binary_sensor.e_niro_ev_plugged_in", "plug"),
        e("button.e_niro_force_update"),
        e("switch.e_niro_ev_charging"),
        e("switch.e_niro_climate"),
        e("number.e_niro_ac_charging_limit", unit="%"),
        e("sensor.e_niro_ev_range", "distance", unit="km"),
    ]
    er_mod = sys.modules["homeassistant.helpers.entity_registry"]
    er_mod.async_entries_for_device = lambda reg, dev: entries
    sys.modules["homeassistant.helpers.device_registry"].async_get = lambda h: types.SimpleNamespace(
        async_get=lambda i: types.SimpleNamespace(name="Kia e-Niro", name_by_user=None, model="e-Niro"))
    hass = types.SimpleNamespace(states=States())
    for x in entries:
        setstate(hass, x.entity_id, "1", device_class=x.original_device_class, unit_of_measurement=x.unit_of_measurement)
    found = cars.detect_car_entities(hass, "car1")
    assert found["name"] == "Kia e-Niro"
    assert found["soc"] == "sensor.e_niro_ev_battery_level"
    assert found["plug"] == "binary_sensor.e_niro_ev_plugged_in"
    assert found["refresh_entity"] == "button.e_niro_force_update"
    assert found["start_entity"] == "switch.e_niro_ev_charging"
    assert found["limit_entity"] == "number.e_niro_ac_charging_limit"
    assert found["range_entity"] == "sensor.e_niro_ev_range"


def test_suggest_only_real_cars_and_read_capacity(tmp_path):
    install_stubs()
    sys.modules.pop("easee_smart.cars", None)
    cars = importlib.import_module("easee_smart.cars")

    def e(eid, dev, dc=None, unit=None, name=None):
        return types.SimpleNamespace(entity_id=eid, domain=eid.split(".")[0], disabled_by=None, device_id=dev,
                                     original_device_class=dc, device_class=None, original_name=name,
                                     translation_key=None, unit_of_measurement=unit)

    entries = [
        # Victron AC system: a state of charge but nothing car-like
        e("sensor.ac_system_0_state_of_charge", "acsys", "battery", "%"),
        e("sensor.ac_system_0_power", "acsys", "power", "W"),
        # Inster via Victron: state of charge + range + capacity
        e("sensor.hyundai_inster_state_of_charge", "inster", "battery", "%"),
        e("sensor.hyundai_inster_range_to_go", "inster", "distance", "km"),
        e("sensor.hyundai_inster_battery_capacity", "inster", None, "kWh"),
    ]
    er_mod = sys.modules["homeassistant.helpers.entity_registry"]
    er_mod.async_get = lambda h: types.SimpleNamespace(entities={x.entity_id: x for x in entries})
    er_mod.async_entries_for_device = lambda reg, dev: [x for x in entries if x.device_id == dev]
    names = {"acsys": "AC system (0)", "inster": "Electric Vehicle (ID: 41)"}
    sys.modules["homeassistant.helpers.device_registry"].async_get = lambda h: types.SimpleNamespace(
        async_get=lambda i: types.SimpleNamespace(name=names[i], name_by_user=None, model=None))
    hass = types.SimpleNamespace(states=States())
    for x in entries:
        setstate(hass, x.entity_id, "46" if "capacity" in x.entity_id else "60",
                 device_class=x.original_device_class, unit_of_measurement=x.unit_of_measurement)
    assert cars.suggest_car_devices(hass) == ["inster"]
    found = cars.detect_car_entities(hass, "inster")
    assert found["capacity"] == 46
    assert found["soc"] == "sensor.hyundai_inster_state_of_charge"


def test_dashboard_has_all_cards(tmp_path):
    install_stubs()
    sys.modules.pop("easee_smart.dashboard", None)
    dash = importlib.import_module("easee_smart.dashboard")
    car = types.SimpleNamespace(name="e-Niro", soc_entity="sensor.niro_soc")
    own = {k: f"sensor.es_{k}" for k in ("charger_status", "smart_status", "current_price", "grid_power",
                                          "energy_today", "cost_month", "energy_month", "ere_month", "ere_total")}
    m = types.SimpleNamespace(own_entities=own, charger_entities={"power": "sensor.easee_power"}, cars=[car],
                              ere_rate=0.13, name="Easee", model="Charge Max", _opt=lambda k, d=None: "nl",
                              hass=types.SimpleNamespace(config=types.SimpleNamespace(language="nl")))
    cfg = dash.build_dashboard(m)
    text = json.dumps(cfg)
    for view in ("charger", "modes", "cars", "plan", "grid", "costs"):
        assert f"custom:easee-smart-{view}-card" in text
    assert "custom:easee-smart-card" in text
    assert cfg["views"][0]["title"] == "Laden"
    assert any(b.get("name") == "e-Niro" for b in cfg["views"][0]["badges"])

    class Owner:
        storage_collection = "COLL"

        def ws_create(self):
            pass

    import functools

    def wrap(f):
        @functools.wraps(f)
        def inner(*a):
            return f(*a)
        return inner

    ws = sys.modules.setdefault("homeassistant.components.websocket_api", types.ModuleType("homeassistant.components.websocket_api"))
    ws.DOMAIN = "websocket_api"
    hass = types.SimpleNamespace(data={"websocket_api": {"lovelace/dashboards/create": (wrap(wrap(Owner().ws_create)), None)}})
    assert dash._dashboards_collection(hass) == "COLL"


def test_dashboard_never_overwrites_a_user_dashboard(tmp_path):
    install_stubs()
    sys.modules.pop("easee_smart.dashboard", None)
    disk: dict = {}

    class PersistentStore(Store):
        def __init__(self, hass, version, key):
            self.key = key

        async def async_load(self):
            return disk.get(self.key)

        async def async_save(self, data):
            disk[self.key] = data

    sys.modules["homeassistant.helpers.storage"].Store = PersistentStore

    class Board:
        def __init__(self, config=None):
            self.config = config

        async def async_load(self, force):
            if self.config is None:
                raise ValueError("empty")
            return self.config

        async def async_save(self, config):
            self.config = config

    user_board = Board({"views": [{"title": "Mine", "cards": [{"type": "entities"}]}]})
    lovelace = types.SimpleNamespace(dashboards={"easee-smart": user_board})

    class Coll:
        async def async_create_item(self, item):
            lovelace.dashboards[item["url_path"]] = Board()

    _mod("homeassistant.components.lovelace")
    _mod("homeassistant.components.lovelace.const", LOVELACE_DATA="lovelace")
    _mod("homeassistant.components.frontend", async_panel_exists=lambda h, u: False)
    dash = importlib.import_module("easee_smart.dashboard")
    dash._dashboards_collection = lambda h: Coll()

    own = {"charger_status": "sensor.es_status"}
    m = types.SimpleNamespace(own_entities=own, charger_entities={}, cars=[], ere_rate=None, name="Easee",
                              model=None, _opt=lambda k, d=None: "en", charger_id="EH1",
                              entry=types.SimpleNamespace(entry_id="e1"))
    m.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="en"), data={"lovelace": lovelace},
                                   config_entries=types.SimpleNamespace(async_entries=lambda d: [1]))

    url = asyncio.run(dash.async_create_dashboard(m))
    assert url == "easee-smart-2"                                   # user's dashboard is taken: pick a free url
    assert user_board.config["views"][0]["title"] == "Mine"         # ...and leave it untouched
    assert lovelace.dashboards["easee-smart-2"].config["views"][0]["sections"]
    lovelace.dashboards["easee-smart-2"].config = {"views": []}
    assert asyncio.run(dash.async_create_dashboard(m)) == "easee-smart-2"  # ours: refreshed in place
    assert lovelace.dashboards["easee-smart-2"].config["views"]
    assert user_board.config["views"][0]["title"] == "Mine"

    # a dashboard made by 1.5.0-1.5.4 (our header, only our cards) is adopted instead of duplicated
    disk.clear()
    legacy = Board(dash.build_dashboard(m))
    lovelace.dashboards = {"easee-smart": legacy}
    assert asyncio.run(dash.async_create_dashboard(m)) == "easee-smart"
    assert disk["easee_smart.dashboards"] == {"owned": {"e1": "easee-smart"}}


def test_equalizer_show_setting_and_options_override(tmp_path):
    async def run():
        hass, m = make(tmp_path)
        await m.async_setup()
        info = m.card_payload()["equalizer_info"]
        assert info["show"] is True and info["linked"] is True and info["model"] == "Equalizer"   # auto: linked → shown
        m.entry.options["show_equalizer"] = "hide"
        assert m.card_payload()["equalizer_info"]["show"] is False

        # an Equalizer chosen later in the options wins over the setup data, "none" removes it
        hass, m = make(tmp_path, equalizer=False, options={"equalizer_device": "dev2"})
        assert m.equalizer_device_id == "dev2"
        hass, m = make(tmp_path, options={"equalizer_device": "none"})
        await m.async_setup()
        assert m.equalizer_device_id is None and m.card_payload()["equalizer_info"]["show"] is False
        m.entry.options["show_equalizer"] = "show"
        assert m.card_payload()["equalizer_info"] == {"show": True, "linked": False}
    asyncio.run(run())


def test_phase_switcher_logic():
    install_stubs()
    sys.modules.pop("easee_smart.logic", None)
    logic = importlib.import_module("easee_smart.logic")
    p = logic.PhaseSwitcher(confirm_s=300, min_interval_s=900)
    p1, p3 = p.thresholds(230)
    assert round(p1, 2) == 1.38 and round(p3, 2) == 4.14
    t = datetime(2026, 6, 1, 12, 0, tzinfo=TZ)
    assert p.update(t, 2.0, 230) == 3                      # not yet: has to hold for 5 minutes
    assert p.update(t + timedelta(minutes=5), 2.0, 230) == 1
    assert p.update(t + timedelta(minutes=10), 5.0, 230) == 1   # too soon after the last switch
    assert p.update(t + timedelta(minutes=21), 5.0, 230) == 1   # starts the 5-minute confirm
    assert p.update(t + timedelta(minutes=26), 5.0, 230) == 3
    assert p.update(t + timedelta(minutes=50), 4.3, 230) == 3   # 4.3 kW still fits 3 phases


def test_solar_switches_to_one_phase_and_back(tmp_path):
    async def run():
        hass, m = make(tmp_path, equalizer=False, extra={"grid_power_entity": "sensor.p1"})
        sys.modules["easee_smart.manager"].PHASE_RESTART_DELAY_S = 0
        await m.async_setup()
        setstate(hass, "sensor.c_status", "awaiting_start")
        setstate(hass, "sensor.c_power", 0)
        setstate(hass, "sensor.p1", -2.2)  # 2.2 kW export: too little for 3 phases, enough for 1
        m._recompute()
        await m.async_set_setting("mode", "solar")
        for _ in range(4):
            CLOCK["now"] += timedelta(minutes=2)
            m._recompute()
            await m._async_control()
        modes = [c[2]["phase_mode"] for c in hass.services.calls if c[1] == "set_charger_phase_mode"]
        assert modes == ["1_phase"]
        assert m.active_phases == 1 and m.card_payload()["active_phases"] == 1
        assert ("easee", "action_command", {"device_id": "dev1", "action_command": "pause"}) in hass.services.calls
        assert m.snapshot.smart_state == "charging_solar" and last_limit(hass) == 9   # 2.2 kW / 230 V
        # back to normal: the charger gets its own phase setting back
        await m.async_set_setting("mode", "normal")
        modes = [c[2]["phase_mode"] for c in hass.services.calls if c[1] == "set_charger_phase_mode"]
        assert modes == ["1_phase", "auto_phase"] and m.active_phases is None
        CLOCK["now"] = datetime(2026, 11, 3, 20, 0, tzinfo=TZ)
    asyncio.run(run())


def test_session_default_mode_and_no_prices_wait(tmp_path):
    async def run():
        hass, m = make(tmp_path, options={"session_mode": "smart", "no_prices_action": "wait"})
        await m.async_setup()
        assert m.settings.mode == "normal"
        m._start_session()
        assert m.settings.mode == "smart"                     # new session → the chosen default mode
        setstate(hass, "sensor.c_status", "awaiting_start")
        setstate(hass, "sensor.c_power", 0)
        await m.async_set_setting("target_energy", 20)
        assert m.snapshot.smart_state == "no_prices" and last_limit(hass) == 0   # waits instead of charging
        m.entry.options["no_prices_action"] = "charge"
        await m._async_control()
        assert last_limit(hass) == 16
        m.entry.options["session_mode"] = "keep"
        m.settings.mode = "solar"
        m._start_session()
        assert m.settings.mode == "solar"
    asyncio.run(run())


def test_hourly_prices():
    install_stubs()
    sys.modules.pop("easee_smart.prices", None)
    prices_mod = importlib.import_module("easee_smart.prices")
    logic = importlib.import_module("easee_smart.logic")
    base = datetime(2026, 11, 4, 0, 0, tzinfo=TZ)
    quarters = [logic.PriceSlot(base + timedelta(minutes=15 * i), base + timedelta(minutes=15 * (i + 1)), p)
                for i, p in enumerate([0.20, 0.24, 0.28, 0.32, 0.10, 0.10, 0.10, 0.10])]
    hours = prices_mod.to_hourly(quarters)
    assert [round(h.price, 2) for h in hours] == [0.26, 0.10]
    assert hours[0].end - hours[0].start == timedelta(hours=1)


def test_solar_outlook_thresholds():
    install_stubs()
    sys.modules.pop("easee_smart.logic", None)
    logic = importlib.import_module("easee_smart.logic")
    base = datetime(2026, 6, 1, 10, 0, tzinfo=TZ)
    slots = [logic.PriceSlot(base + timedelta(hours=i), base + timedelta(hours=i + 1), 0.2) for i in range(4)]
    hour = lambda i: (base + timedelta(hours=i)).astimezone(logic.UTC_TZ)  # noqa: E731
    pv = {hour(0): 1.0, hour(1): 2.5, hour(2): 6.0, hour(3): 20.0}
    out = logic.solar_outlook(slots, pv, {}, min_current=6, max_current=16, phases=3,
                              phase_switching=True, voltage=230, buffer_kw=0)
    charge = [round(x.charge_kw, 2) for x in out]
    # 1.0-0.35 < 1.4 → nothing; 2.15 → 1 phase; 5.65 → 3 phases; 19.65 → capped at 16 A × 3 × 230 V
    assert charge == [0.0, 2.15, 5.65, 11.04]
    no_switch = logic.solar_outlook(slots, pv, {}, min_current=6, max_current=16, phases=3,
                                    phase_switching=False, voltage=230)
    assert [round(x.charge_kw, 2) for x in no_switch][1] == 0.0
    assert round(logic.solar_energy_until(out, base, base + timedelta(hours=3)), 2) == 7.8


def test_solar_smart_buys_less_with_forecast(tmp_path):
    async def run():
        CLOCK["now"] = datetime(2026, 6, 1, 6, 0, tzinfo=TZ)
        hass, m = make(tmp_path, options={"pv_forecast": "sensor", "pv_forecast_entity": "sensor.fc",
                                          "pv_power_entity": "sensor.pv"})
        await m.async_setup()
        setstate(hass, "sensor.c_status", "awaiting_start")
        setstate(hass, "sensor.c_power", 0)
        setstate(hass, "sensor.eq_import_power", 0.3)
        setstate(hass, "sensor.eq_export_power", 0)
        setstate(hass, "sensor.pv", 0, unit_of_measurement="W")
        base = CLOCK["now"].replace(minute=0)
        # 6 kW expected from 9:00 to 15:00 (hour END labels, Wh per hour, like Enphase Envoy Local)
        hourly = [[(base + timedelta(hours=i + 1)).astimezone(UTC).isoformat(), 6000 if 3 <= i < 9 else 0] for i in range(24)]
        setstate(hass, "sensor.fc", 10, hourly=hourly)
        m.day_ahead.points = [(base + timedelta(hours=i), 0.10 + 0.01 * i) for i in range(24)]
        m.day_ahead.last_fetch = CLOCK["now"] + timedelta(days=1)
        m.entry.options.update({"price_markup": 0.0, "energy_tax": 0.0, "vat_percent": 0.0})
        m._rebuild_prices()
        await m.async_set_setting("departure", "17:00")
        await m.async_set_setting("target_energy", 30)
        await m.async_set_setting("mode", "solar_smart")
        sol = m.card_payload()["solar"]
        assert sol["source"] == "sensor" and sol["until_departure_kwh"] > 30   # ~5.65 kW × 6 h
        assert sol["grid_kwh"] < 30 and sol["grid_kwh"] >= 0
        assert any(x["charge"] > 0 for x in sol["slots"])
        await m.async_set_setting("mode", "smart")
        assert m.card_payload()["solar"]["grid_kwh"] == 30   # plain smart does not count on the sun
        CLOCK["now"] = datetime(2026, 11, 3, 20, 0, tzinfo=TZ)
    asyncio.run(run())


def test_charge_schedule_sun_first_then_grid():
    install_stubs()
    sys.modules.pop("easee_smart.logic", None)
    logic = importlib.import_module("easee_smart.logic")
    base = datetime(2026, 6, 1, 10, 0, tzinfo=TZ)
    slots = [logic.PriceSlot(base + timedelta(minutes=15 * i), base + timedelta(minutes=15 * (i + 1)), 0.2) for i in range(8)]
    sun = {slots[0].start: 4.0, slots[1].start: 4.0}
    rows = logic.charge_schedule(slots, base, None, 4.0, 11.0, grid_slots={slots[4].start, slots[5].start},
                                 solar_kw=sun, use_solar=True, grid_always=False)
    # 2 × 1 kWh sun, then 2 kWh from the grid in the first planned (cheap) quarter: max 2.75 kWh per quarter
    assert [(g, u) for _, g, u in rows[:6]] == [(0, 1.0), (0, 1.0), (0, 0), (0, 0), (2.0, 0), (0, 0)]
    normal = logic.charge_schedule(slots, base, None, 3.0, 11.0, grid_slots=None, solar_kw=None,
                                   use_solar=False, grid_always=True)
    assert [g for _, g, _ in normal[:3]] == [2.75, 0.25, 0]


def test_history_splits_grid_and_sun(tmp_path):
    async def run():
        hass, m = make(tmp_path)
        await m.async_setup()
        setstate(hass, "sensor.c_status", "charging")
        setstate(hass, "sensor.c_power", 6.0)
        setstate(hass, "sensor.eq_import_power", 2.0)   # 6 kW charging, 2 kW from the grid → 4 kW sun
        setstate(hass, "sensor.eq_export_power", 0)
        m._recompute()
        CLOCK["now"] += timedelta(seconds=60)
        m._recompute()
        hist = m.card_payload()["history"]
        assert len(hist) == 1 and round(hist[0]["grid"], 3) == round(2 / 60, 3) and round(hist[0]["sun"], 3) == round(4 / 60, 3)
        CLOCK["now"] = datetime(2026, 11, 3, 20, 0, tzinfo=TZ)
    asyncio.run(run())


def test_normal_schedule_only_when_plugged(tmp_path):
    async def run():
        hass, m = make(tmp_path)
        await m.async_setup()
        prices(hass, m)
        await m.async_set_setting("target_energy", 10)
        setstate(hass, "sensor.c_status", "disconnected")
        m._recompute()
        assert m.card_payload()["schedule"] == []
        setstate(hass, "sensor.c_status", "awaiting_start")
        m._recompute()
        sched = m.card_payload()["schedule"]
        assert sched and round(sum(x["grid"] for x in sched), 2) == 10.0
    asyncio.run(run())


def test_plan_reports_energy_that_does_not_fit_before_departure():
    logic = importlib.import_module("easee_smart.logic")
    base = datetime(2026, 11, 4, 21, 30, tzinfo=TZ)
    slots = [logic.PriceSlot(base + timedelta(minutes=15 * i), base + timedelta(minutes=15 * (i + 1)), 0.3) for i in range(8)]
    plan = logic.plan_cheapest(slots, base, base + timedelta(minutes=30), 56.9, 11.0)
    assert plan.window_kwh == 5.5 and plan.short_kwh == 51.4
    plan = logic.plan_cheapest(slots, base, base + timedelta(hours=2), 10.0, 11.0)
    assert plan.short_kwh == 0


def test_departure_too_close_plans_for_tomorrow_and_power_limits(tmp_path):
    async def run():
        CLOCK["now"] = datetime(2026, 11, 4, 21, 51, tzinfo=TZ)
        cars = [{"name": "E-Niro", "soc": "sensor.niro_soc", "capacity": 64, "plug": "binary_sensor.niro_plug", "target": 100}]
        hass, m = make(tmp_path, equalizer=False, extra={"cars": cars, "charge_efficiency": 90})
        await m.async_setup()
        setstate(hass, "sensor.c_status", "disconnected")
        setstate(hass, "sensor.c_power", 0)
        setstate(hass, "sensor.c_max_charger_limit", 16)
        setstate(hass, "sensor.niro_soc", 20)
        setstate(hass, "binary_sensor.niro_plug", "off")
        base = CLOCK["now"].replace(hour=0, minute=0)
        m.day_ahead.points = [(base + timedelta(hours=i), 0.10 if 26 <= i < 32 else 0.30) for i in range(48)]
        m.day_ahead.last_fetch = CLOCK["now"] + timedelta(days=1)
        m.entry.options.update({"price_markup": 0.0, "energy_tax": 0.0, "vat_percent": 0.0})
        m._rebuild_prices()
        await m.async_set_setting("departure", "22:00")
        await m.async_set_setting("mode", "smart")
        p = m.card_payload()
        assert p["energy_needed"] == round(0.8 * 64 / 0.9, 2)
        assert p["charge_power_kw"] == 11.04 and p["charger_power_kw"] == 11.04
        assert p["departure_moved"] is True and p["departure_at"].startswith("2026-11-05T22:00")
        assert p["plan_short_kwh"] == 0
        starts = [s["start"] for s in p["plan"]]
        assert starts and all(s >= "2026-11-05T02:00" and s < "2026-11-05T22:00" for s in starts)
        # the charger's own maximum (Easee app) caps the configured current
        setstate(hass, "sensor.c_max_charger_limit", 10)
        assert m.max_current == 10 and m.charger_power_kw == 6.9
        setstate(hass, "sensor.c_max_charger_limit", 16)
        # a car that never takes more than 7.2 kW: measured after two sessions
        for _ in range(2):
            setstate(hass, "binary_sensor.niro_plug", "on")
            m._start_session()
            setstate(hass, "sensor.c_power", 7.2)
            setstate(hass, "sensor.c_session_energy", 10)
            m._recompute()
            m._end_session()
        assert m.car_power_kw(m.active_car()) == (7.2, "measured")
        assert m.charge_power_kw == 7.2
        CLOCK["now"] = datetime(2026, 11, 3, 20, 0, tzinfo=TZ)
    asyncio.run(run())


def test_departure_choice_sticks_during_a_session(tmp_path):
    async def run():
        CLOCK["now"] = datetime(2026, 11, 4, 23, 0, tzinfo=TZ)
        hass, m = make(tmp_path, equalizer=False)
        await m.async_setup()
        setstate(hass, "sensor.c_status", "charging")
        setstate(hass, "sensor.c_session_energy", 0)
        m._recompute()
        await m.async_set_setting("departure", "07:00")
        await m.async_set_setting("target_energy", 50)
        dep = m._departure(CLOCK["now"])
        assert dep.day == 5 and not m._departure_moved
        # 03:00, still 50 kWh to go (> 4 h at 11 kW): keeps 07:00 today, does not move to tomorrow
        CLOCK["now"] = datetime(2026, 11, 5, 3, 0, tzinfo=TZ)
        m._recompute()
        assert m._departure(CLOCK["now"]) == dep and not m._departure_moved
        CLOCK["now"] = datetime(2026, 11, 3, 20, 0, tzinfo=TZ)
    asyncio.run(run())


def test_payload_entities_is_a_copy(tmp_path):
    async def run():
        hass, m = make(tmp_path, equalizer=False)
        await m.async_setup()
        first = m.card_payload()["entities"]
        m.own_entities["charge_mode"] = "select.x"
        assert "charge_mode" not in first and m.card_payload()["entities"]["charge_mode"] == "select.x"
    asyncio.run(run())


def test_smart_schedule_shows_sun_share_in_grid_slots():
    logic = importlib.import_module("easee_smart.logic")
    base = datetime(2026, 11, 5, 12, 0, tzinfo=TZ)
    slots = [logic.PriceSlot(base + timedelta(minutes=15 * i), base + timedelta(minutes=15 * (i + 1)), 0.3) for i in range(4)]
    rows = logic.charge_schedule(slots, base, base + timedelta(hours=2), 8.0, 11.0,
                                 grid_slots={slots[0].start, slots[1].start, slots[2].start}, solar_kw=None,
                                 use_solar=False, grid_always=False, surplus_kw={s.start: 2.0 for s in slots})
    grid = sum(r[1] for r in rows)
    sun = sum(r[2] for r in rows)
    assert round(grid + sun, 2) == 8.0 and rows[0][2] == 0.5 and rows[0][1] == 2.25 and rows[3] == (slots[3].start, 0.0, 0.0)
