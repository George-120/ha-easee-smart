"""Solar forecast, calibrated on your own inverter (same model as Enphase Envoy Local).

Weather comes from Open-Meteo (free, no account): hourly global, direct and diffuse
irradiance for the location of Home Assistant, the average of three weather models
(DWD ICON, ECMWF IFS, Météo-France). From the position of the sun the irradiance on the
panels is computed. From the long-term statistics of the linked inverter power sensor the
integration learns the orientation and tilt, how many Wh the system makes per Wh/m², a
shade map, and a seasonal correction; today's measured production corrects the next hours.

Works with any inverter brand: link one power sensor (W or kW) of the solar panels.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
# Weather archive (reanalysis, back to 1940) for learning from a long history.
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
# The forecasts the same models made in the past: learning from these makes the
# calibration match what the forecast will see.
HISTORICAL_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"
# Backtested on archived forecasts against real production: the average of
# these three beats every single model and every other combination tried.
WEATHER_MODELS = ("dwd_icon_seamless", "ecmwf_ifs025", "meteofrance_seamless")
HOURLY = "shortwave_radiation,direct_normal_irradiance,diffuse_radiation,temperature_2m,wind_speed_10m"
LEARN_DAYS = 365
MODEL = 4  # bump when the learning changes: everything is learned again
STORAGE_VERSION = 1
PAST_DAYS = 14
FORECAST_DAYS = 4  # today in UTC can still be yesterday locally
MIN_DAY_IRRADIANCE = 250  # Wh/m² - darker days say little about the system
DEFAULT_TILT = 35.0
DEFAULT_AZIMUTH = 180.0  # compass degrees, 180 = south
PERFORMANCE_RATIO = 0.85
ALBEDO = 0.2
RELEARN_EVERY = timedelta(hours=20)
AZIMUTHS = range(0, 360, 15)  # coarse search, refined around the best
TILTS = (15, 25, 35, 45, 55)
MIN_FIT_DAYS = 20  # days of history before orientation and shade are learned
SHADE_AZ = 15  # shade map cells: degrees of sun azimuth ...
SHADE_EL = 5  # ... and sun elevation
SHADE_PRIOR = 1500.0  # Wh/m² of evidence before a cell may differ from 1
SHADE_LIMITS = (0.3, 1.6)
SNOW_RATIO = 0.25  # a bright day producing less than this share is snow/outage
RECENT_DAYS = 45  # the factor follows the season: learned again on the last weeks
RECENT_MIN_DAYS = 12
RECENT_LIMITS = (0.7, 1.4)
TEMP_COEFF = -0.0037  # per °C cell temperature above 25 °C (crystalline silicon)
CELL_HEATING = 0.032  # °C per W/m² in still air (open rack ~0.03)
INTRADAY_HOURS = 3.0  # how long the measured deviation of today keeps counting


@dataclass
class ForecastData:
    """What the sensors and cards show."""

    hourly: dict[datetime, float] = field(default_factory=dict)  # hour end (UTC) -> Wh in that hour
    today: float | None = None  # kWh
    tomorrow: float | None = None
    day_after: float | None = None
    so_far: float | None = None  # kWh expected until now today
    yesterday: float | None = None  # kWh the forecast gave for yesterday
    next_hour: float | None = None  # Wh expected in the next full hour
    best_hour_tomorrow: datetime | None = None  # start of tomorrow's sunniest hour
    power_now: float | None = None  # W
    calibration: dict[str, dict[str, Any]] = field(default_factory=dict)
    updated: datetime | None = None
    error: str | None = None


@dataclass
class Weather:
    """Hourly irradiance, keyed by the end of the hour (UTC), means over that hour."""

    ghi: dict[datetime, float]
    dni: dict[datetime, float]
    dhi: dict[datetime, float]
    temp: dict[datetime, float] = field(default_factory=dict)  # °C
    wind: dict[datetime, float] = field(default_factory=dict)  # km/h


# --------------------------------------------------------------- sun maths


def sun_position(moment: datetime, lat: float, lon: float) -> tuple[float, float]:
    """(elevation, azimuth) of the sun in degrees; azimuth from north, clockwise (NOAA)."""
    utc = dt_util.as_utc(moment)
    day = utc.timetuple().tm_yday
    hour = utc.hour + utc.minute / 60 + utc.second / 3600
    gamma = 2 * math.pi / 365 * (day - 1 + (hour - 12) / 24)
    eqtime = 229.18 * (
        0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma)
    )
    decl = (
        0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma) + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma)
    )
    true_solar = hour * 60 + eqtime + 4 * lon
    ha = math.radians(true_solar / 4 - 180)
    phi = math.radians(lat)
    cos_zen = math.sin(phi) * math.sin(decl) + math.cos(phi) * math.cos(decl) * math.cos(ha)
    zen = math.acos(max(-1.0, min(1.0, cos_zen)))
    return 90 - math.degrees(zen), _az_from_north(ha, phi, decl, zen)


def _az_from_north(ha: float, phi: float, decl: float, zen: float) -> float:
    """Solar azimuth from north, clockwise."""
    sin_az = -math.sin(ha) * math.cos(decl) / (math.sin(zen) or 1e-9)
    cos_az = (math.sin(decl) - math.sin(phi) * math.cos(zen)) / ((math.cos(phi) * math.sin(zen)) or 1e-9)
    return math.degrees(math.atan2(sin_az, cos_az)) % 360


def plane_irradiance(
    ghi: float, dni: float, dhi: float, elevation: float, sun_az: float, tilt: float, azimuth: float
) -> float:
    """W/m² on a plane (isotropic sky)."""
    if ghi <= 0:
        return 0.0
    t = math.radians(tilt)
    zen = math.radians(90 - elevation)
    cos_aoi = math.cos(zen) * math.cos(t) + math.sin(zen) * math.sin(t) * math.cos(
        math.radians(sun_az - azimuth)
    )
    beam = dni * max(0.0, cos_aoi) if elevation > 0 else 0.0
    sky = dhi * (1 + math.cos(t)) / 2
    ground = ghi * ALBEDO * (1 - math.cos(t)) / 2
    return max(0.0, beam + sky + ground)


def plane_series(
    weather: Weather, lat: float, lon: float, tilt: float, azimuth: float, sun: dict[datetime, tuple[float, float]]
) -> dict[datetime, float]:
    """Hourly W/m² on a roof surface (sun position at the middle of the hour)."""
    out: dict[datetime, float] = {}
    for end, ghi in weather.ghi.items():
        elev, az = sun[end]
        g = plane_irradiance(
            ghi, weather.dni.get(end, 0.0), weather.dhi.get(end, 0.0), elev, az, tilt, azimuth
        )
        out[end] = g * temperature_factor(g, weather.temp.get(end), weather.wind.get(end))
    return out


def temperature_factor(irradiance: float, air: float | None, wind: float | None) -> float:
    """Panels lose ~0.37 %/°C above 25 °C: hot summer panels make less per W/m².

    Without this the calibration (mostly learned in summer) forecasts autumn
    and winter too low; backtested: bias -9 % -> -4 %.
    """
    if air is None or irradiance <= 0:
        return 1.0
    cell = air + irradiance * CELL_HEATING / (1 + 0.05 * (wind if wind is not None else 10.0))
    return max(0.7, min(1.2, 1 + TEMP_COEFF * (cell - 25)))


# ------------------------------------------------------------- the model


def _hours_for_fit(
    production: dict[datetime, float],
    weather: Weather,
    sun: dict[datetime, tuple[float, float]],
) -> list[tuple[float, ...]]:
    """Daylight hours with production as tuples ready for fast plane maths.

    (actual, ghi, beam, dhi, cos zenith, sin zenith * cos az, sin zenith * sin az)
    """
    rows = []
    for end, actual in production.items():
        ghi = weather.ghi.get(end)
        if ghi is None or end not in sun:
            continue
        elev, az = sun[end]
        if elev <= 2:
            continue
        zen = math.radians(90 - elev)
        a = math.radians(az)
        rows.append(
            (
                actual,
                ghi,
                weather.dni.get(end, 0.0),
                weather.dhi.get(end, 0.0),
                math.cos(zen),
                math.sin(zen) * math.cos(a),
                math.sin(zen) * math.sin(a),
            )
        )
    return rows


def _plane_fast(row: tuple[float, ...], ct: float, st: float, ca: float, sa: float) -> float:
    _, ghi, dni, dhi, cz, szc, szs = row
    if ghi <= 0:
        return 0.0
    cos_aoi = cz * ct + st * (szc * ca + szs * sa)
    return dni * max(0.0, cos_aoi) + dhi * (1 + ct) / 2 + ghi * ALBEDO * (1 - ct) / 2


def _shape_error(rows: list[tuple[float, ...]], tilt: float, azimuth: float) -> float:
    """1 - R² of production against plane irradiance with one free scale."""
    t, a = math.radians(tilt), math.radians(azimuth)
    ct, st, ca, sa = math.cos(t), math.sin(t), math.cos(a), math.sin(a)
    pg = gg = pp = 0.0
    for row in rows:
        g = _plane_fast(row, ct, st, ca, sa)
        p = row[0]
        pg += p * g
        gg += g * g
        pp += p * p
    if gg <= 0 or pp <= 0:
        return 1.0
    return 1 - pg * pg / (gg * pp)


def fit_orientation(
    production: dict[datetime, float],
    weather: Weather,
    lat: float,
    lon: float,
    sun: dict[datetime, tuple[float, float]],
) -> tuple[float, float, float] | None:
    """Orientation whose irradiance best explains the production, hour by hour.

    Returns (tilt, azimuth, fit error) or None without enough history. All
    daylight hours are used (not only clear days): over a year the weather
    evens out and the timing of production gives the orientation.
    """
    rows = _hours_for_fit(production, weather, sun)
    days = {dt_util.as_local(end).date() for end in production if end in weather.ghi}
    if len(days) < MIN_FIT_DAYS or len(rows) < MIN_FIT_DAYS * 6:
        return None
    best = min(
        ((float(t), float(a), _shape_error(rows, t, a)) for t in TILTS for a in AZIMUTHS),
        key=lambda x: x[2],
    )
    # Refine around the best coarse cell.
    fine = [
        (t, (best[1] + da) % 360)
        for t in (best[0] - 5, best[0], best[0] + 5)
        if 5 <= t <= 70
        for da in (-10, -5, 0, 5, 10)
    ]
    for t, a in fine:
        error = _shape_error(rows, t, a)
        if error < best[2]:
            best = (float(t), float(a), error)
    return best


def shade_cell(elevation: float, azimuth: float) -> str:
    """Key of the shade map cell for a sun position."""
    return f"{int(azimuth // SHADE_AZ)}_{int(max(0.0, elevation) // SHADE_EL)}"


def learn_factor_and_shade(
    production: dict[datetime, float],
    plane: dict[datetime, float],
    sun: dict[datetime, tuple[float, float]],
) -> tuple[float, int, dict[str, float]] | None:
    """Wh per Wh/m² of a roof surface and its shade map.

    Days with snow on the panels (or an outage) are left out: on a bright day
    they produce almost nothing and would drag the factor down.
    """
    by_day: dict[str, list[datetime]] = {}
    for end in production:
        if end in plane:
            by_day.setdefault(dt_util.as_local(end).date().isoformat(), []).append(end)
    days = [h for h in by_day.values() if len(h) >= 8 and sum(plane[x] for x in h) >= MIN_DAY_IRRADIANCE]
    if not days:
        return None
    sum_a = sum(production[x] for h in days for x in h)
    sum_g = sum(plane[x] for h in days for x in h)
    if sum_a <= 0 or sum_g <= 0:
        return None
    factor = sum_a / sum_g
    kept = [
        h for h in days
        if sum(production[x] for x in h) >= SNOW_RATIO * factor * sum(plane[x] for x in h)
    ]
    if not kept:
        return None
    sum_a = sum(production[x] for h in kept for x in h)
    sum_g = sum(plane[x] for h in kept for x in h)
    factor = sum_a / sum_g
    shade: dict[str, float] = {}
    if len(kept) >= MIN_FIT_DAYS:
        cells: dict[str, list[float]] = {}
        for h in kept:
            for x in h:
                if x not in sun or sun[x][0] <= 0:
                    continue
                c = cells.setdefault(shade_cell(*sun[x]), [0.0, 0.0])
                c[0] += production[x]
                c[1] += plane[x] * factor
        prior = SHADE_PRIOR * factor
        for key, (actual, expected) in cells.items():
            ratio = (actual + prior) / (expected + prior)
            ratio = min(SHADE_LIMITS[1], max(SHADE_LIMITS[0], ratio))
            if abs(ratio - 1) >= 0.02:
                shade[key] = round(ratio, 3)
    return factor, len(kept), shade


def recent_ratio(
    production: dict[datetime, float],
    plane: dict[datetime, float],
    sun: dict[datetime, tuple[float, float]],
    factor: float,
    shade: dict[str, float],
) -> tuple[float, int]:
    """Measured / expected over the last RECENT_DAYS (shade map included).

    Backtested walk-forward on the last 50 days: daily error 13 % -> 10.5 %,
    bias -4 % -> 0 %.
    """
    since = dt_util.utcnow() - timedelta(days=RECENT_DAYS)
    by_day: dict[str, list[datetime]] = {}
    for end in production:
        if end >= since and end in plane:
            by_day.setdefault(dt_util.as_local(end).date().isoformat(), []).append(end)
    actual = expected = 0.0
    days = 0
    for hours in by_day.values():
        exp = sum(
            plane[x] * factor * (shade.get(shade_cell(*sun[x]), 1.0) if x in sun and plane[x] else 1.0)
            for x in hours
        )
        act = sum(production[x] for x in hours)
        if len(hours) < 8 or exp < MIN_DAY_IRRADIANCE * factor or act < SNOW_RATIO * exp:
            continue
        actual += act
        expected += exp
        days += 1
    if days < RECENT_MIN_DAYS or expected <= 0:
        return 1.0, days
    return min(RECENT_LIMITS[1], max(RECENT_LIMITS[0], actual / expected)), days


def _weather_from(raw: dict[str, Any]) -> Weather:
    """Open-Meteo hourly answer -> Weather keyed by the end of the hour (UTC).

    With several weather models the answer has one series per model
    (``shortwave_radiation_dwd_icon_seamless``...); their average is used.
    """
    hourly = raw.get("hourly") or {}
    times = []
    for stamp in hourly.get("time") or []:
        times.append(dt_util.parse_datetime(f"{stamp}:00+00:00" if len(stamp) == 16 else stamp))

    def series(name: str, clamp: bool = True) -> dict[datetime, float]:
        # Open-Meteo radiation is the mean of the *preceding* hour: the label is
        # the end of the hour (verified against a year of real production).
        columns = [v for k, v in hourly.items() if k == name or k.startswith(f"{name}_")]
        out: dict[datetime, float] = {}
        for i, t in enumerate(times):
            if t is None:
                continue
            values = [float(col[i]) for col in columns if i < len(col) and col[i] is not None]
            if values:
                mean = sum(values) / len(values)
                out[t] = max(0.0, mean) if clamp else mean
        return out

    return Weather(
        ghi=series("shortwave_radiation"),
        dni=series("direct_normal_irradiance"),
        dhi=series("diffuse_radiation"),
        temp=series("temperature_2m", clamp=False),
        wind=series("wind_speed_10m"),
    )

DEFAULT_KWP = 3.0


def default_factor(kwp: float | None) -> float:
    """Wh per Wh/m² before any calibration: peak power times a typical ratio."""
    return (kwp or DEFAULT_KWP) * PERFORMANCE_RATIO


class SolarForecast:
    """Expected production of the linked solar panels, hour by hour."""

    def __init__(self, hass: HomeAssistant, entry_id: str, power_entity: str, kwp: float | None) -> None:
        self.hass = hass
        self.power_entity = power_entity
        self.kwp = kwp
        self.data = ForecastData()
        self._store: Store[dict] = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}.solar_forecast")
        self._learned: dict[str, Any] = {}
        self._learned_at: datetime | None = None
        self._loaded = False

    # ------------------------------------------------------------------ public
    async def async_update(self, *_: Any) -> None:
        try:
            await self._async_update()
        except Exception as err:  # noqa: BLE001 - a forecast must never break charging
            self.data.error = str(err)
            _LOGGER.info("Solar forecast not available: %s", err)

    def hourly_kw(self) -> dict[datetime, float]:
        """Hour start (UTC) -> expected mean kW in that hour."""
        return {end - timedelta(hours=1): wh / 1000 for end, wh in self.data.hourly.items()}

    # ---------------------------------------------------------------- internal
    async def _async_update(self) -> None:
        if not self._loaded:
            stored = await self._store.async_load() or {}
            if stored.get("model") == MODEL and stored.get("entity") == self.power_entity:
                self._learned = stored.get("surface") or {}
                at = stored.get("learned_at")
                self._learned_at = dt_util.parse_datetime(at) if at else None
            self._loaded = True
        lat, lon = self.hass.config.latitude, self.hass.config.longitude
        if lat is None or lon is None:
            return
        weather = await self._async_weather(lat, lon)
        sun = {end: sun_position(end - timedelta(minutes=30), lat, lon) for end in weather.ghi}
        now = dt_util.utcnow()
        if self._learned_at is None or now - self._learned_at > RELEARN_EVERY:
            history = await self._async_history_weather(lat, lon, weather)
            history_sun = await self.hass.async_add_executor_job(
                lambda: {end: sun_position(end - timedelta(minutes=30), lat, lon) for end in history.ghi}
            )
            await self._async_learn(history, history_sun, lat, lon)
        production_today = await self._async_today_kwh()
        self._compute(weather, sun, lat, lon, production_today)
        self.data.error = None

    async def _async_get(self, url: str, params: dict[str, str], timeout: float) -> Weather:
        session = async_get_clientsession(self.hass)
        last: Exception | None = None
        for models in (",".join(WEATHER_MODELS), None):
            query = dict(params, models=models) if models else params
            try:
                async with session.get(url, params=query, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    resp.raise_for_status()
                    weather = _weather_from(await resp.json(content_type=None))
                if weather.ghi:
                    return weather
            except Exception as err:  # noqa: BLE001 - try the default model
                last = err
        raise last or RuntimeError("no weather data")

    async def _async_weather(self, lat: float, lon: float) -> Weather:
        return await self._async_get(
            OPEN_METEO_URL,
            {"latitude": f"{lat:.3f}", "longitude": f"{lon:.3f}", "hourly": HOURLY,
             "past_days": str(PAST_DAYS), "forecast_days": str(FORECAST_DAYS), "timezone": "UTC"},
            20,
        )

    async def _async_history_weather(self, lat: float, lon: float, recent: Weather) -> Weather:
        today = dt_util.now().date()
        params = {
            "latitude": f"{lat:.3f}", "longitude": f"{lon:.3f}",
            "start_date": (today - timedelta(days=LEARN_DAYS)).isoformat(),
            "end_date": (today - timedelta(days=1)).isoformat(),
            "hourly": HOURLY, "timezone": "UTC",
        }
        merged = Weather(ghi={}, dni={}, dhi={}, temp={}, wind={})
        for url in (HISTORICAL_URL, ARCHIVE_URL):
            try:
                merged = await self._async_get(url, params, 90)
                break
            except Exception as err:  # noqa: BLE001 - next source, or the recent days only
                _LOGGER.info("Open-Meteo history not available: %s", err)
        now = dt_util.utcnow()
        for name in ("ghi", "dni", "dhi", "temp", "wind"):
            target, source = getattr(merged, name), getattr(recent, name)
            for t, v in source.items():
                if t <= now and t not in target:
                    target[t] = v
        return merged

    def _unit_scale(self) -> float:
        state = self.hass.states.get(self.power_entity)
        unit = str(state.attributes.get("unit_of_measurement", "W")) if state else "W"
        return 1000.0 if unit.lower() == "kw" else 1.0

    async def _async_stats(self, start: datetime, end: datetime) -> dict[datetime, float]:
        """Hour end (UTC) -> Wh produced, from the long-term statistics (mean W per hour)."""
        try:
            from homeassistant.components.recorder import get_instance
            from homeassistant.components.recorder.statistics import (
                statistics_during_period,
            )
        except ImportError:
            return {}
        if "recorder" not in self.hass.config.components:
            return {}
        stats = await get_instance(self.hass).async_add_executor_job(
            statistics_during_period, self.hass, start, end, {self.power_entity}, "hour", None, {"mean"}
        )
        scale = self._unit_scale()

        def to_dt(value: Any) -> datetime:
            if isinstance(value, (int, float)):
                return dt_util.utc_from_timestamp(value)
            return dt_util.as_utc(value)

        return {
            to_dt(r["start"]) + timedelta(hours=1): max(0.0, float(r["mean"]) * scale)
            for r in stats.get(self.power_entity, [])
            if r.get("mean") is not None
        }

    async def _async_today_kwh(self) -> float | None:
        start = dt_util.as_utc(dt_util.start_of_local_day())
        rows = await self._async_stats(start, dt_util.utcnow())
        return sum(rows.values()) / 1000 if rows else None

    async def _async_learn(self, weather: Weather, sun: dict[datetime, tuple[float, float]], lat: float, lon: float) -> None:
        end = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)
        production = await self._async_stats(end - timedelta(days=LEARN_DAYS), end)
        previous = self._learned or {}
        entry: dict[str, Any] = {}
        fitted = await self.hass.async_add_executor_job(fit_orientation, production, weather, lat, lon, sun) if production else None
        if fitted:
            entry.update(tilt=fitted[0], azimuth=fitted[1], orientation="learned", fit_error=round(fitted[2], 3))
        elif previous.get("orientation") == "learned":
            entry.update({k: previous[k] for k in ("tilt", "azimuth", "orientation", "fit_error") if k in previous})
        else:
            entry.update(tilt=DEFAULT_TILT, azimuth=DEFAULT_AZIMUTH, orientation="default")
        plane = plane_series(weather, lat, lon, entry["tilt"], entry["azimuth"], sun)
        result = await self.hass.async_add_executor_job(learn_factor_and_shade, production, plane, sun) if production else None
        if result:
            factor, days, shade = result
            recent = recent_ratio(production, plane, sun, factor, shade)
            entry.update(factor=round(factor * recent[0], 4), year_factor=round(factor, 4),
                         recent_ratio=round(recent[0], 3), recent_days=recent[1],
                         calibration_days=days, shade=shade)
        elif previous.get("calibration_days"):
            entry.update(factor=previous["factor"], calibration_days=previous["calibration_days"], shade=previous.get("shade") or {})
        else:
            entry.update(factor=round(default_factor(self.kwp), 4), calibration_days=0, shade={})
        self._learned = entry
        self._learned_at = dt_util.utcnow()
        await self._store.async_save({"surface": entry, "learned_at": self._learned_at.isoformat(),
                                      "model": MODEL, "entity": self.power_entity})

    def _compute(self, weather: Weather, sun: dict[datetime, tuple[float, float]], lat: float, lon: float,
                 produced: float | None) -> None:
        info = self._learned or {"tilt": DEFAULT_TILT, "azimuth": DEFAULT_AZIMUTH, "orientation": "default",
                                 "factor": default_factor(self.kwp), "calibration_days": 0}
        shade = info.get("shade") or {}
        plane = plane_series(weather, lat, lon, info["tilt"], info["azimuth"], sun)
        hourly: dict[datetime, float] = {}
        for moment, value in plane.items():
            corr = shade.get(shade_cell(*sun[moment]), 1.0) if value else 1.0
            hourly[moment] = value * info["factor"] * corr
        now = dt_util.utcnow()
        start = dt_util.as_utc(dt_util.start_of_local_day())

        def day_kwh(offset: int) -> float:
            begin = start + timedelta(days=offset)
            return round(sum(v for t, v in hourly.items() if begin < t <= begin + timedelta(days=1)) / 1000, 2)

        so_far = 0.0
        for moment, value in hourly.items():
            if start < moment <= now:
                so_far += value
            elif moment - timedelta(hours=1) < now < moment and moment > start:
                so_far += value * ((now - (moment - timedelta(hours=1))) / timedelta(hours=1))
        # Today so far tells how the weather really turned out; the next hours follow that.
        if produced is not None and so_far >= 300:
            ratio = min(1.6, max(0.5, produced * 1000 / so_far))
            weight = min(1.0, so_far / 1500) * 0.7
            end_today = start + timedelta(days=1)
            for moment in list(hourly):
                if now < moment <= end_today:
                    ahead = max(0.0, (moment - timedelta(minutes=30) - now) / timedelta(hours=1))
                    hourly[moment] *= 1 + (ratio - 1) * weight * math.exp(-ahead / INTRADAY_HOURS)
        self.data = ForecastData(
            hourly={t: round(v, 1) for t, v in sorted(hourly.items())},
            today=day_kwh(0), tomorrow=day_kwh(1), day_after=day_kwh(2),
            so_far=round(so_far / 1000, 2),
            calibration={k: v for k, v in info.items() if k != "shade"} | {"shade_cells": len(shade)},
            updated=now,
        )


def hourly_from_attribute(raw: Any) -> dict[datetime, float]:
    """Hour start (UTC) -> kW from an `hourly` attribute ([[hour end ISO, Wh], ...]), e.g. Enphase Envoy Local."""
    out: dict[datetime, float] = {}
    if not isinstance(raw, list):
        return out
    for item in raw:
        try:
            end = dt_util.parse_datetime(str(item[0]))
            wh = float(item[1])
        except (TypeError, ValueError, IndexError):
            continue
        if end is not None:
            out[dt_util.as_utc(end) - timedelta(hours=1)] = max(0.0, wh) / 1000
    return out
