"""Send the charge plan to Victron VRM, so Dynamic ESS can plan the home battery around the car.

VRM keeps an hourly consumption forecast per installation (total, EV charger, heat pump). Its
"adjust consumption" endpoint lets you overrule single hours. We overrule the EV part with what the
plan will charge and set the total to (forecast without EV) + planned EV. Hours we overruled earlier
that are no longer in the plan are given back to VRM (value -1).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import VRM_API, VRM_HORIZON_H, VRM_MIN_PUSH_S, VRM_REFRESH_S

_LOGGER = logging.getLogger(__name__)

KEY_TOTAL = "vrm_consumption_fc"
KEY_EV = "vrm_consum_evcs_fc"
ADJ_TOTAL = "vrm_consumption_fc_adj"
ADJ_EV = "vrm_consum_evcs_fc_adj"
RESET = -1

STATUS_OFF = "off"
STATUS_WAITING = "waiting"
STATUS_OK = "ok"
STATUS_AUTH = "auth_error"
STATUS_ERROR = "error"


class VrmError(Exception):
    """VRM could not be reached or answered with an error."""


class VrmAuthError(VrmError):
    """The token is wrong or has no access to this installation."""


def hour_ts(when: datetime) -> int:
    return int(when.timestamp()) // 3600 * 3600


def first_hour(now: datetime) -> int:
    """VRM refuses the running hour ("values in the past"): start at the next whole hour."""
    return hour_ts(now) + 3600


def hourly_ev_wh(rows: list[dict[str, Any]], now: datetime) -> dict[int, int]:
    """Charge schedule rows (kWh from grid and sun per price slot) → Wh per whole hour."""
    first = first_hour(now)
    out: dict[int, float] = {}
    for row in rows:
        start = dt_util.parse_datetime(str(row.get("start")))
        if start is None:
            continue
        h = hour_ts(start)
        if h < first or h >= first + VRM_HORIZON_H * 3600:
            continue
        kwh = float(row.get("grid") or 0.0) + float(row.get("sun") or 0.0)
        out[h] = out.get(h, 0.0) + kwh * 1000
    return {h: int(round(v)) for h, v in out.items() if v >= 1}


def parse_series(records: dict[str, Any], key: str) -> dict[int, float]:
    """[[ms, value], ...] → {hour (s): value}."""
    out: dict[int, float] = {}
    for item in records.get(key) or []:
        try:
            ts, value = item[0], item[1]
        except (TypeError, IndexError, KeyError):
            continue
        if value is None:
            continue
        ts = int(ts)
        if ts > 10_000_000_000:  # milliseconds
            ts //= 1000
        out[ts // 3600 * 3600] = float(value)
    return out


def to_wh(total: dict[int, float], ev: dict[int, float]) -> tuple[dict[int, float], dict[int, float]]:
    """VRM gives these in Wh; should it ever give kWh (a house never uses < 50 Wh an hour), convert."""
    values = [v for v in total.values() if v > 0]
    if values and max(values) < 50:
        return {k: v * 1000 for k, v in total.items()}, {k: v * 1000 for k, v in ev.items()}
    return total, ev


def build_adjustment(
    ev_wh: dict[int, int],
    zero_hours: set[int],
    total_fc: dict[int, float],
    ev_fc: dict[int, float],
    sent: dict[int, tuple[int, int]],
    first_hour: int,
) -> tuple[dict[str, list[dict[str, int]]], dict[int, tuple[int, int]]]:
    """Work out what to send. Returns the payload and the new {hour: (total, ev)} we have overruled.

    ``zero_hours``: hours where the car is plugged in but the plan does not charge (EV = 0 there).
    The base (forecast without EV) is taken from VRM; if VRM already returns our own earlier total
    for an hour, our own earlier numbers give the base, so repeated pushes never stack up.
    """
    total_adj: list[dict[str, int]] = []
    ev_adj: list[dict[str, int]] = []
    new_sent: dict[int, tuple[int, int]] = {}
    for h in sorted(set(ev_wh) | zero_hours):
        if h < first_hour:
            continue
        ev = int(ev_wh.get(h, 0))
        prev = sent.get(h)
        if prev is not None and h in total_fc and abs(total_fc[h] - prev[0]) <= 1:
            base = prev[0] - prev[1]
        elif h in total_fc:
            base = total_fc[h] - ev_fc.get(h, 0.0)
        elif prev is not None:
            base = prev[0] - prev[1]
        else:
            base = None
        ev_adj.append({"timestamp": h, "value": ev})
        if base is not None:
            total = int(round(max(0.0, base) + ev))
            total_adj.append({"timestamp": h, "value": total})
            new_sent[h] = (total, ev)
        else:
            new_sent[h] = (ev, ev)
    for h in sorted(sent):
        if h >= first_hour and h not in new_sent:
            total_adj.append({"timestamp": h, "value": RESET})
            ev_adj.append({"timestamp": h, "value": RESET})
    payload: dict[str, list[dict[str, int]]] = {}
    if total_adj:
        payload[ADJ_TOTAL] = total_adj
    if ev_adj:
        payload[ADJ_EV] = ev_adj
    return payload, new_sent


class VrmClient:
    """Tiny client for the VRM API with a personal access token."""

    def __init__(self, hass: HomeAssistant, token: str) -> None:
        self.hass = hass
        self.token = token.strip()

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        session = async_get_clientsession(self.hass)
        headers = {"X-Authorization": f"Token {self.token}", "Content-Type": "application/json"}
        try:
            async with session.request(
                method, f"{VRM_API}{path}", headers=headers, timeout=aiohttp.ClientTimeout(total=30), **kwargs
            ) as resp:
                if resp.status in (401, 403):
                    raise VrmAuthError(f"HTTP {resp.status}")
                if resp.status >= 400:
                    raise VrmError(f"HTTP {resp.status}: {(await resp.text())[:200]}")
                data = await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise VrmError(str(err)) from err
        if isinstance(data, dict) and data.get("success") is False:
            raise VrmError(str(data.get("errors") or data.get("error_code") or "failed"))
        return data if isinstance(data, dict) else {}

    async def async_installations(self) -> list[dict[str, Any]]:
        me = await self._request("GET", "/users/me")
        user_id = (me.get("user") or {}).get("id")
        if not user_id:
            raise VrmError("no user id")
        data = await self._request("GET", f"/users/{user_id}/installations")
        return [r for r in data.get("records") or [] if isinstance(r, dict) and r.get("idSite")]

    async def async_forecast(self, site: int, start: int, end: int) -> tuple[dict[int, float], dict[int, float]]:
        data = await self._request(
            "GET", f"/installations/{site}/stats",
            params={"type": "forecast", "interval": "hours", "start": start, "end": end},
        )
        records = data.get("records") or {}
        if not isinstance(records, dict):
            records = {}
        return to_wh(parse_series(records, KEY_TOTAL), parse_series(records, KEY_EV))

    async def async_adjust(self, site: int, payload: dict[str, Any]) -> None:
        await self._request("POST", f"/installations/{site}/adjust-consumption", json=payload)


class VrmPlanSync:
    """Keeps the EV forecast in VRM in line with the charge plan."""

    def __init__(self, hass: HomeAssistant, token: str, site: int) -> None:
        self.client = VrmClient(hass, token)
        self.site = int(site)
        self.status = STATUS_WAITING
        self.error: str | None = None
        self.last_push: datetime | None = None
        self.sent: dict[int, tuple[int, int]] = {}
        self._last_wish: tuple | None = None
        self._busy = False
        self._auth_failed_at: datetime | None = None

    def attributes(self) -> dict[str, Any]:
        hours = {
            dt_util.as_local(dt_util.utc_from_timestamp(h)).strftime("%a %H:00"): round(ev / 1000, 2)
            for h, (_t, ev) in sorted(self.sent.items())
            if ev > 0
        }
        return {
            "installation": self.site,
            "last_push": self.last_push.isoformat() if self.last_push else None,
            "planned_kwh": round(sum(ev for _t, ev in self.sent.values()) / 1000, 2),
            "hours": hours,
            "error": self.error,
        }

    async def async_sync(self, ev_wh: dict[int, int], zero_hours: set[int], now: datetime) -> bool:
        """Push when the wish changed (max. every 5 min) or once an hour. True when something was sent."""
        if self._busy:
            return False
        wish = (tuple(sorted(ev_wh.items())), tuple(sorted(zero_hours)))
        since = (now - self.last_push).total_seconds() if self.last_push else None
        if self.status == STATUS_AUTH and self._auth_failed_at and (now - self._auth_failed_at).total_seconds() < 3600:
            return False
        if since is not None:
            if wish == self._last_wish and since < VRM_REFRESH_S:
                return False
            if since < VRM_MIN_PUSH_S:
                return False
        if not ev_wh and not zero_hours and not self.sent:
            self._last_wish = wish
            return False
        self._busy = True
        try:
            first = first_hour(now)
            hours = set(ev_wh) | zero_hours | set(self.sent)
            end = max(hours) + 3600 if hours else first + 3600
            total_fc, ev_fc = await self.client.async_forecast(self.site, first, end)
            payload, new_sent = build_adjustment(ev_wh, zero_hours, total_fc, ev_fc, self.sent, first)
            if payload:
                await self.client.async_adjust(self.site, payload)
            self.sent = new_sent
            self._last_wish = wish
            self.last_push = now
            self.status, self.error = STATUS_OK, None
            _LOGGER.debug("VRM plan sent: %s", payload)
            return True
        except VrmAuthError as err:
            self.status, self.error, self._auth_failed_at = STATUS_AUTH, str(err), now
            self.last_push = now
            _LOGGER.warning("Victron VRM refused the access token (%s); check it in the Easee Smart options", err)
        except VrmError as err:
            self.status, self.error = STATUS_ERROR, str(err)
            self.last_push = now
            _LOGGER.warning("Could not send the charge plan to Victron VRM: %s", err)
        finally:
            self._busy = False
        return False

    async def async_clear(self, now: datetime) -> None:
        """Give every hour we overruled back to VRM (on unload / when switched off)."""
        first = first_hour(now)
        hours = [h for h in self.sent if h >= first]
        if not hours:
            return
        payload = {
            ADJ_TOTAL: [{"timestamp": h, "value": RESET} for h in sorted(hours)],
            ADJ_EV: [{"timestamp": h, "value": RESET} for h in sorted(hours)],
        }
        try:
            await self.client.async_adjust(self.site, payload)
            self.sent = {}
        except VrmError as err:
            _LOGGER.debug("VRM reset failed: %s", err)
