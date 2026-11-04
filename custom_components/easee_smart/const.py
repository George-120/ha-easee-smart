"""Constants for Easee Smart."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "easee_smart"
EASEE_DOMAIN: Final = "easee"
VERSION: Final = "1.11.2"

CARD_BASE: Final = "/easee_smart"
CARD_URL: Final = f"{CARD_BASE}/easee-smart-card.js"

# ---- config entry keys -------------------------------------------------------
CONF_CHARGER_DEVICE: Final = "charger_device"
CONF_EQUALIZER_DEVICE: Final = "equalizer_device"
CONF_SHOW_EQUALIZER: Final = "show_equalizer"
SHOW_EQUALIZER_OPTIONS: Final = ["auto", "show", "hide"]
NO_EQUALIZER: Final = "none"
CONF_MODEL: Final = "model"
CONF_PHASES: Final = "phases"
CONF_VOLTAGE: Final = "voltage"
CONF_MAX_CURRENT: Final = "max_current"
CONF_BIDDING_ZONE: Final = "bidding_zone"
CONF_MIN_CURRENT: Final = "min_current"
CONF_SOLAR_START_DELAY: Final = "solar_start_delay"
CONF_SOLAR_STOP_DELAY: Final = "solar_stop_delay"
CONF_PHASE_SWITCHING: Final = "phase_switching"
CONF_SESSION_MODE: Final = "session_mode"
SESSION_MODE_KEEP: Final = "keep"
CONF_NO_PRICES: Final = "no_prices_action"
NO_PRICES_CHARGE: Final = "charge"
NO_PRICES_WAIT: Final = "wait"
PHASE_MODE_1: Final = "1_phase"
CONF_PRICE_RESOLUTION: Final = "price_resolution"
CONF_PV_POWER: Final = "pv_power_entity"
CONF_PV_FORECAST: Final = "pv_forecast"
CONF_PV_FORECAST_SENSOR: Final = "pv_forecast_entity"
CONF_PV_KWP: Final = "pv_kwp"
CONF_PHASE_CONFIRM: Final = "phase_confirm_minutes"
CONF_PHASE_INTERVAL: Final = "phase_interval_minutes"
PV_FORECAST_NONE: Final = "none"
PV_FORECAST_OWN: Final = "own"
PV_FORECAST_SENSOR: Final = "sensor"
PV_FORECAST_OPTIONS: Final = ["none", "own", "sensor"]
PV_FORECAST_REFRESH_S: Final = 1800
SOLAR_TRUST: Final = 0.8  # share of the expected solar energy smart charging counts on
DEFAULT_PHASE_CONFIRM_MIN: Final = 3
DEFAULT_PHASE_INTERVAL_MIN: Final = 15
RESOLUTION_QUARTER: Final = "quarter"
RESOLUTION_HOUR: Final = "hour"
PHASE_MODE_3: Final = "3_phase"
PHASE_MODE_AUTO: Final = "auto_phase"
PHASE_RESTART_DELAY_S: Final = 5
CONF_SOLAR_BUFFER: Final = "solar_buffer"
CONF_EFFICIENCY: Final = "charge_efficiency"
CONF_BOOST_RESET: Final = "boost_reset_on_unplug"
CONF_NUDGE: Final = "resume_nudge"
CONF_CAR_REFRESH_MIN: Final = "car_refresh_minutes"
CONF_ERE_ENABLED: Final = "ere_enabled"
CONF_ERE_RATE: Final = "ere_rate"
CONF_LANGUAGE: Final = "language"
LANGUAGES: Final = ["auto", "nl", "en", "de"]
DEFAULT_EFFICIENCY: Final = 90
ACTIVE_CAR_AUTO: Final = "auto"
CONF_MARKUP: Final = "price_markup"
CONF_ENERGY_TAX: Final = "energy_tax"
CONF_VAT: Final = "vat_percent"
CONF_GRID_POWER_ENTITY: Final = "grid_power_entity"
CONF_GRID_POWER_INVERTED: Final = "grid_power_inverted"
CONF_SOC_ENTITY: Final = "soc_entity"
CONF_BATTERY_CAPACITY: Final = "battery_capacity"
CONF_REIMBURSEMENT: Final = "reimbursement_per_kwh"
CONF_ENABLE_ENTITIES: Final = "enable_source_entities"
CONF_GRID_IMPORT_ENTITY: Final = "grid_import_entity"
CONF_GRID_EXPORT_ENTITY: Final = "grid_export_entity"
CONF_PHASE_L1_ENTITY: Final = "phase_l1_entity"
CONF_PHASE_L2_ENTITY: Final = "phase_l2_entity"
CONF_PHASE_L3_ENTITY: Final = "phase_l3_entity"
CONF_MAIN_FUSE: Final = "main_fuse"
PHASE_ENTITY_KEYS: Final = [CONF_PHASE_L1_ENTITY, CONF_PHASE_L2_ENTITY, CONF_PHASE_L3_ENTITY]
GRID_KEYS: Final = [
    "grid_import_entity",
    "grid_export_entity",
    "grid_power_entity",
    "phase_l1_entity",
    "phase_l2_entity",
    "phase_l3_entity",
]
DEFAULT_MAIN_FUSE: Final = 25
MAIN_FUSE_SIZES: Final = ["25", "35", "40", "50", "63", "80"]

DEFAULT_PHASES: Final = 3
DEFAULT_VOLTAGE: Final = 230
DEFAULT_MAX_CURRENT: Final = 16
DEFAULT_BATTERY_CAPACITY: Final = 60.0
DEFAULT_TARGET_ENERGY: Final = 20.0
DEFAULT_TARGET_SOC: Final = 80
DEFAULT_DEPARTURE: Final = "07:00"

MIN_CHARGE_CURRENT: Final = 6

# Control timing
CONTROL_INTERVAL_S: Final = 30
CONTROL_TTL_MIN: Final = 15  # dynamic limit falls back to normal if HA stops
CONTROL_REFRESH_S: Final = 300  # re-send same limit to refresh the TTL
MIN_SECONDS_BETWEEN_CHANGES: Final = 60
SOLAR_START_DELAY_S: Final = 120
SOLAR_STOP_DELAY_S: Final = 300

# ---- charger models (product codes as used by the Easee cloud) ----------------
EASEE_MODELS: Final = [
    "Easee Home",
    "Easee Charge",
    "Charge Lite",
    "Charge Max",
    "Charge Up",
    "Charge Core",
    "Charge Pro",
    "Charge One",
]
MODEL_MAX_CURRENT: Final = {
    "Easee Home": 32,
    "Easee Charge": 32,
    "Charge Lite": 32,
    "Charge Max": 32,
    "Charge Up": 32,
    "Charge Core": 32,
    "Charge Pro": 32,
    "Charge One": 32,
}
EQUALIZER_MODEL: Final = "Equalizer"

# ---- source entity keys from the existing Easee integration ------------------
# unique_id in the easee integration is f"{product_id}_{key}"
CHARGER_KEYS: Final = [
    "status",
    "power",
    "session_energy",
    "lifetime_energy",
    "online",
    "cable_locked",
    "cable_locked_permanently",
    "is_enabled",
    "smart_charging",
    "current",
    "voltage",
    "output_limit",
    "dynamic_charger_limit",
    "max_charger_limit",
    "reason_for_no_current",
    "phase_mode",
    "cost_per_kwh",
    "energy_last_hour",
]
EQUALIZER_KEYS: Final = [
    "online",
    "import_power",
    "export_power",
    "current",
    "voltage",
    "import_energy",
    "export_energy",
    "max_continuous_limit",
    "temp_max",
    "surplus",
]
# Entities the smart features need; disabled-by-default ones get enabled on request
REQUIRED_CHARGER_KEYS: Final = [
    "status",
    "power",
    "session_energy",
    "lifetime_energy",
    "current",
    "dynamic_charger_limit",
    "max_charger_limit",
    "output_limit",
    "reason_for_no_current",
]
REQUIRED_EQUALIZER_KEYS: Final = [
    "import_power",
    "export_power",
    "current",
    "voltage",
    "max_continuous_limit",
]

# Easee status strings (from the easee integration)
STATUS_DISCONNECTED: Final = "disconnected"
STATUS_CHARGING: Final = "charging"
STATUS_COMPLETED: Final = "completed"
STATUS_OFFLINE: Final = "offline"
CONNECTED_STATUSES: Final = {
    "awaiting_start",
    "charging",
    "completed",
    "ready_to_charge",
    "awaiting_authorization",
    "awaiting_load_balancing",
    "awaiting_smart_start",
    "awaiting_scheduled_start",
    "paused_due_to_equalizer",
    "start_charging",
    "stop_charging",
    "authenticating",
}
ALL_STATUSES: Final = [
    "disconnected",
    "awaiting_start",
    "charging",
    "completed",
    "error",
    "ready_to_charge",
    "awaiting_authorization",
    "de_authorizing",
    "start_charging",
    "stop_charging",
    "offline",
    "awaiting_load_balancing",
    "awaiting_smart_start",
    "awaiting_scheduled_start",
    "authenticating",
    "paused_due_to_equalizer",
    "searching_for_master",
    "erratic_ev",
    "error_temperature_too_high",
    "error_dead_powerboard",
    "error_overcurrent",
    "error_pen_fault",
    "unknown",
]

# ---- modes -------------------------------------------------------------------
MODE_NORMAL: Final = "normal"
MODE_SMART: Final = "smart"
MODE_SOLAR: Final = "solar"
MODE_SOLAR_SMART: Final = "solar_smart"
MODES: Final = [MODE_NORMAL, MODE_SMART, MODE_SOLAR, MODE_SOLAR_SMART]

TARGET_ENERGY: Final = "energy"
TARGET_SOC: Final = "soc"

# smart status
SMART_IDLE: Final = "idle"
SMART_NOT_CONNECTED: Final = "not_connected"
SMART_WAITING_CHEAP: Final = "waiting_cheap"
SMART_CHARGING_CHEAP: Final = "charging_cheap"
SMART_CHARGING_SOLAR: Final = "charging_solar"
SMART_WAITING_SOLAR: Final = "waiting_solar"
SMART_CHARGING_BOOST: Final = "charging_boost"
SMART_CHARGING_FALLBACK: Final = "charging_fallback"
SMART_TARGET_REACHED: Final = "target_reached"
SMART_NO_PRICES: Final = "no_prices"
SMART_STATES: Final = [
    SMART_IDLE,
    SMART_NOT_CONNECTED,
    SMART_WAITING_CHEAP,
    SMART_CHARGING_CHEAP,
    SMART_CHARGING_SOLAR,
    SMART_WAITING_SOLAR,
    SMART_CHARGING_BOOST,
    SMART_CHARGING_FALLBACK,
    SMART_TARGET_REACHED,
    SMART_NO_PRICES,
]

SIGNAL_UPDATE: Final = "easee_smart_update_{}"
STORAGE_VERSION: Final = 1
STORAGE_KEY: Final = "easee_smart.{}"
MAX_STORED_SESSIONS: Final = 500

