"""Simulation of the manager with a minimal fake Home Assistant (no HA install needed)."""
import asyncio
import importlib
import sys
import types
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
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
        self.config = types.SimpleNamespace(currency="EUR", path=lambda *p: str(Path(tmp, *p)))
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
    dt = _mod("homeassistant.util.dt", now=lambda: CLOCK["now"], utcnow=lambda: CLOCK["now"])
    _mod("homeassistant.util", dt=dt)
    sys.modules["homeassistant"].helpers = sys.modules["homeassistant.helpers"]
    sys.modules["homeassistant.helpers"].device_registry = sys.modules["homeassistant.helpers.device_registry"]
    sys.modules["homeassistant.helpers"].entity_registry = sys.modules["homeassistant.helpers.entity_registry"]
    pkg = types.ModuleType("easee_smart")
    pkg.__path__ = [str(Path(__file__).parents[1] / "custom_components" / "easee_smart")]
    sys.modules["easee_smart"] = pkg
    return devreg


def make(tmp, options=None):
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
    entry = types.SimpleNamespace(entry_id="E1", data={"charger_device": "dev1", "equalizer_device": "dev2", "phases": 3, "max_current": 16,
                                                         "price_entity": "sensor.price", "reimbursement_per_kwh": 0.23},
                                  options=options or {})
    return hass, mgr_mod.EaseeSmartManager(hass, entry)


def setstate(hass, eid, state, **attrs):
    hass.states[eid] = State(eid, str(state), attrs)


def prices(hass):
    base = CLOCK["now"].replace(minute=0)
    raw = [{"start": (base + timedelta(hours=i)).isoformat(), "end": (base + timedelta(hours=i + 1)).isoformat(),
            "value": 0.30 if i < 5 else 0.05 if i < 8 else 0.40} for i in range(14)]
    setstate(hass, "sensor.price", 0.30, raw_today=raw)


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
        prices(hass)
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
        prices(hass)
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
        text = Path(res["file"]).read_text(encoding="utf-8-sig")
        assert "10,000" in text and res["sessions"] == 1 and res["reimbursement"] == 2.3
        payload = m.card_payload()
        assert payload["month"]["energy"] == 10.0 and payload["sessions"][0]["cost"] == 3.0
    asyncio.run(run())
