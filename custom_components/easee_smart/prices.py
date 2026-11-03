"""Built-in day-ahead (APX / EPEX SPOT) prices for every European bidding zone.

Source: Energy-Charts (Fraunhofer ISE), free and without an account. Quarter-hour
prices for today and, from about 13:00, tomorrow.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .logic import PriceSlot

_LOGGER = logging.getLogger(__name__)

API_URL = "https://api.energy-charts.info/price"

# Bidding zones offered by Energy-Charts (label shown in the UI = code)
BIDDING_ZONES = [
    "NL", "BE", "DE-LU", "AT", "FR", "CH", "DK1", "DK2", "NO1", "NO2", "NO3", "NO4", "NO5",
    "SE1", "SE2", "SE3", "SE4", "FI", "PL", "CZ", "SK", "HU", "SI", "HR", "IT-North",
    "ES", "PT", "EE", "LV", "LT",
]
COUNTRY_ZONE = {
    "NL": "NL", "BE": "BE", "DE": "DE-LU", "LU": "DE-LU", "AT": "AT", "FR": "FR", "CH": "CH",
    "DK": "DK1", "NO": "NO1", "SE": "SE3", "FI": "FI", "PL": "PL", "CZ": "CZ", "SK": "SK",
    "HU": "HU", "SI": "SI", "HR": "HR", "IT": "IT-North", "ES": "ES", "PT": "PT",
    "EE": "EE", "LV": "LV", "LT": "LT",
}
# Sensible starting values; the user can change them. Energy tax is per kWh, excl. VAT.
ZONE_DEFAULTS = {
    "NL": {"energy_tax": 0.0916, "vat": 21.0},
    "BE": {"energy_tax": 0.0, "vat": 6.0},
    "DE-LU": {"energy_tax": 0.0, "vat": 19.0},
    "AT": {"energy_tax": 0.0, "vat": 20.0},
    "FR": {"energy_tax": 0.0, "vat": 20.0},
}


def default_zone(hass: HomeAssistant) -> str:
    return COUNTRY_ZONE.get((hass.config.country or "").upper(), "NL")


def zone_defaults(zone: str) -> dict[str, float]:
    return ZONE_DEFAULTS.get(zone, {"energy_tax": 0.0, "vat": 0.0})


def all_in(market_eur_kwh: float, markup: float, energy_tax: float, vat_pct: float) -> float:
    """Consumer price: (market + supplier markup + energy tax) x (1 + VAT)."""
    return round((market_eur_kwh + markup + energy_tax) * (1 + vat_pct / 100), 5)


def parse_energy_charts(data: dict[str, Any]) -> list[tuple[datetime, float]]:
    """Return [(start_utc, market price in EUR/kWh)]."""
    stamps = data.get("unix_seconds") or []
    prices = data.get("price") or []
    out: list[tuple[datetime, float]] = []
    for ts, price in zip(stamps, prices, strict=False):
        if price is None:
            continue
        out.append((datetime.fromtimestamp(int(ts), tz=UTC), float(price) / 1000))
    return out


def to_slots(points: list[tuple[datetime, float]], markup: float, energy_tax: float, vat_pct: float) -> list[PriceSlot]:
    """Turn market points into consumer-price slots (end = next start)."""
    points = sorted(points)
    if not points:
        return []
    gaps = [b[0] - a[0] for a, b in zip(points, points[1:], strict=False) if b[0] > a[0]]
    step = min(gaps) if gaps else timedelta(hours=1)
    slots = []
    for idx, (start, market) in enumerate(points):
        nxt = points[idx + 1][0] if idx + 1 < len(points) else None
        end = nxt if nxt and nxt - start <= step * 4 else start + step
        slots.append(
            PriceSlot(
                dt_util.as_local(start),
                dt_util.as_local(end),
                all_in(market, markup, energy_tax, vat_pct),
            )
        )
    return slots


class DayAheadPrices:
    """Fetches and caches day-ahead prices for one bidding zone."""

    def __init__(self, hass: HomeAssistant, zone: str) -> None:
        self.hass = hass
        self.zone = zone
        self.points: list[tuple[datetime, float]] = []
        self.last_fetch: datetime | None = None
        self.last_error: str | None = None

    @property
    def has_tomorrow(self) -> bool:
        if not self.points:
            return False
        tomorrow = dt_util.now().date() + timedelta(days=1)
        return any(dt_util.as_local(p[0]).date() == tomorrow for p in self.points)

    def needs_refresh(self, now: datetime) -> bool:
        if self.last_fetch is None:
            return True
        age = (now - self.last_fetch).total_seconds()
        if not self.points:
            return age > 300
        if not self.has_tomorrow and now.hour >= 12:
            return age > 900  # tomorrow's auction result is published around 13:00
        return age > 3 * 3600

    async def async_refresh(self) -> bool:
        today = dt_util.now().date()
        params = {
            "bzn": self.zone,
            "start": (today - timedelta(days=1)).isoformat(),
            "end": (today + timedelta(days=2)).isoformat(),
        }
        session = async_get_clientsession(self.hass)
        self.last_fetch = dt_util.now()
        try:
            async with session.get(API_URL, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            self.last_error = str(err) or type(err).__name__
            _LOGGER.warning("Could not fetch day-ahead prices for %s: %s", self.zone, self.last_error)
            return False
        points = parse_energy_charts(data)
        if points:
            self.points = points
            self.last_error = None
            return True
        self.last_error = "empty response"
        return False
