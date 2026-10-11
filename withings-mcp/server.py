"""Withings MCP server.

Exposes a Withings account's health data (weight and body composition, blood
pressure, sleep, activity, workouts, ECG, devices) to MCP clients such as
Claude. Talks to the Withings Public Health Data API over OAuth2 and refreshes
tokens automatically.

Configuration (environment variables):
  WITHINGS_CLIENT_ID      Client ID from developer.withings.com (required)
  WITHINGS_CLIENT_SECRET  Client secret from developer.withings.com (required)
  WITHINGS_REDIRECT_URI   Callback URL registered with Withings. Defaults to
                          the static callback page on this GitHub Pages site.
  WITHINGS_TOKEN_FILE     Where to persist tokens. Defaults to
                          ~/.config/withings-mcp/tokens.json

Run as an MCP server (stdio):   python server.py
One-off interactive login:      python server.py auth
"""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from mcp.server.mcpserver import MCPServer

API_HOST = "https://wbsapi.withings.net"
AUTHORIZE_URL = "https://account.withings.com/oauth2_user/authorize2"
TOKEN_URL = f"{API_HOST}/v2/oauth2"
DEFAULT_REDIRECT_URI = "https://mothybond80.github.io/withings-mcp/callback.html"
SCOPES = "user.info,user.metrics,user.activity,user.sleepevents"
DEFAULT_TOKEN_FILE = Path.home() / ".config" / "withings-mcp" / "tokens.json"
MAX_PAGES = 20  # safety cap when following `more`/`offset` pagination
REQUEST_TIMEOUT = 30.0

# ---------------------------------------------------------------------------
# Reference tables
# ---------------------------------------------------------------------------

# Withings measurement type id -> (name, unit)
MEASURE_TYPES: dict[int, tuple[str, str]] = {
    1: ("weight", "kg"),
    4: ("height", "m"),
    5: ("fat_free_mass", "kg"),
    6: ("fat_ratio", "%"),
    8: ("fat_mass", "kg"),
    9: ("diastolic_blood_pressure", "mmHg"),
    10: ("systolic_blood_pressure", "mmHg"),
    11: ("heart_rate", "bpm"),
    12: ("temperature", "°C"),
    54: ("spo2", "%"),
    71: ("body_temperature", "°C"),
    73: ("skin_temperature", "°C"),
    76: ("muscle_mass", "kg"),
    77: ("hydration", "kg"),
    88: ("bone_mass", "kg"),
    91: ("pulse_wave_velocity", "m/s"),
    123: ("vo2_max", "ml/min/kg"),
    130: ("atrial_fibrillation_ecg", "flag"),
    135: ("qrs_interval", "ms"),
    136: ("pr_interval", "ms"),
    137: ("qt_interval", "ms"),
    138: ("corrected_qt_interval", "ms"),
    139: ("atrial_fibrillation_ppg", "flag"),
    155: ("vascular_age", "years"),
    158: ("nerve_health_score_left_foot", "score"),
    159: ("nerve_health_score_right_foot", "score"),
    167: ("nerve_health_score_feet", "score"),
    168: ("extracellular_water", "kg"),
    169: ("intracellular_water", "kg"),
    170: ("visceral_fat", "index"),
    173: ("fat_free_mass_segments", "kg"),
    174: ("fat_mass_segments", "kg"),
    175: ("muscle_mass_segments", "kg"),
    196: ("electrodermal_activity_feet", "µS"),
    197: ("electrodermal_activity_left_foot", "µS"),
    198: ("electrodermal_activity_right_foot", "µS"),
    226: ("basal_metabolic_rate", "kcal"),
    227: ("metabolic_age", "years"),
}
MEASURE_NAME_TO_ID = {name: mid for mid, (name, _unit) in MEASURE_TYPES.items()}

BODY_COMPOSITION_TYPES = [1, 5, 6, 8, 76, 77, 88, 168, 169, 170, 226, 227]
BLOOD_PRESSURE_TYPES = [9, 10, 11]

MEASURE_POSITIONS = {
    0: "right_wrist", 1: "left_wrist", 2: "right_arm", 3: "left_arm",
    4: "right_foot", 5: "left_foot", 6: "between_legs", 7: "whole_body",
    8: "left_part_of_body", 9: "right_part_of_body", 10: "left_leg",
    11: "right_leg", 12: "torso", 13: "left_hand", 14: "right_hand",
}

ATTRIBUTION = {
    0: "device_known_user", 1: "device_ambiguous_user", 2: "manual_entry",
    3: "user_picked", 4: "manual_at_account_creation", 5: "auto_measure",
    7: "user_confirmed", 15: "guided_conditions",
}

SLEEP_STATES = {0: "awake", 1: "light", 2: "deep", 3: "rem", 4: "manual", 5: "unspecified"}

SLEEP_SUMMARY_FIELDS = [
    "nb_rem_episodes", "sleep_efficiency", "sleep_latency", "total_sleep_time",
    "total_timeinbed", "wakeup_latency", "waso", "apnea_hypopnea_index",
    "breathing_disturbances_intensity", "asleepduration", "deepsleepduration",
    "hr_average", "hr_min", "hr_max", "lightsleepduration", "mvt_active_duration",
    "mvt_score_avg", "night_events", "out_of_bed_count", "remsleepduration",
    "rr_average", "rr_min", "rr_max", "sleep_score", "snoring",
    "snoringepisodecount", "wakeupcount", "wakeupduration", "withings_index",
]

ACTIVITY_FIELDS = [
    "steps", "distance", "elevation", "soft", "moderate", "intense", "active",
    "calories", "totalcalories", "hr_average", "hr_min", "hr_max",
    "hr_zone_0", "hr_zone_1", "hr_zone_2", "hr_zone_3",
]

WORKOUT_FIELDS = [
    "calories", "intensity", "manual_distance", "manual_calories", "hr_average",
    "hr_min", "hr_max", "hr_zone_0", "hr_zone_1", "hr_zone_2", "hr_zone_3",
    "pause_duration", "algo_pause_duration", "spo2_average", "steps", "distance",
    "elevation", "pool_laps", "strokes", "pool_length",
]

WORKOUT_CATEGORIES = {
    1: "walk", 2: "run", 3: "hiking", 4: "skating", 5: "bmx", 6: "bicycling",
    7: "swimming", 8: "surfing", 9: "kitesurfing", 10: "windsurfing",
    11: "bodyboard", 12: "tennis", 13: "table_tennis", 14: "squash",
    15: "badminton", 16: "lift_weights", 17: "calisthenics", 18: "elliptical",
    19: "pilates", 20: "basketball", 21: "soccer", 22: "football", 23: "rugby",
    24: "volleyball", 25: "waterpolo", 26: "horse_riding", 27: "golf", 28: "yoga",
    29: "dancing", 30: "boxing", 31: "fencing", 32: "wrestling",
    33: "martial_arts", 34: "skiing", 35: "snowboarding", 36: "other",
    128: "no_activity", 187: "rowing", 188: "zumba", 191: "baseball",
    192: "handball", 193: "hockey", 194: "ice_hockey", 195: "climbing",
    196: "ice_skating", 272: "multi_sport", 306: "indoor_walk",
    307: "indoor_running", 308: "indoor_cycling",
}

AUTH_FAILED_STATUSES = {100, 101, 102, 200, 401}
RATE_LIMIT_STATUSES = {601}


class WithingsError(Exception):
    """Raised for any Withings API or configuration problem."""


# ---------------------------------------------------------------------------
# Config and token storage
# ---------------------------------------------------------------------------


def _client_id() -> str:
    value = os.environ.get("WITHINGS_CLIENT_ID", "").strip()
    if not value:
        raise WithingsError("WITHINGS_CLIENT_ID is not set.")
    return value


def _client_secret() -> str:
    value = os.environ.get("WITHINGS_CLIENT_SECRET", "").strip()
    if not value:
        raise WithingsError("WITHINGS_CLIENT_SECRET is not set.")
    return value


def _redirect_uri() -> str:
    return os.environ.get("WITHINGS_REDIRECT_URI", DEFAULT_REDIRECT_URI).strip()


def _token_file() -> Path:
    return Path(os.environ.get("WITHINGS_TOKEN_FILE", str(DEFAULT_TOKEN_FILE))).expanduser()


def load_tokens() -> dict[str, Any] | None:
    path = _token_file()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise WithingsError(f"Token file {path} is not valid JSON: {exc}") from exc


def save_tokens(tokens: dict[str, Any]) -> None:
    path = _token_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(tokens, indent=2))
    tmp.chmod(0o600)
    tmp.replace(path)


def clear_tokens() -> bool:
    path = _token_file()
    if path.exists():
        path.unlink()
        return True
    return False


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------


class WithingsClient:
    """Minimal async client for the Withings Public API with token refresh."""

    def __init__(self, http: httpx.AsyncClient | None = None) -> None:
        self._http = http or httpx.AsyncClient(timeout=REQUEST_TIMEOUT)
        self._lock = asyncio.Lock()

    async def aclose(self) -> None:
        await self._http.aclose()

    # -- OAuth ---------------------------------------------------------------

    def build_authorize_url(self, state: str | None = None) -> tuple[str, str]:
        state = state or secrets.token_urlsafe(16)
        params = {
            "response_type": "code",
            "client_id": _client_id(),
            "state": state,
            "scope": SCOPES,
            "redirect_uri": _redirect_uri(),
        }
        url = str(httpx.URL(AUTHORIZE_URL, params=params))
        return url, state

    async def exchange_code(self, code: str) -> dict[str, Any]:
        body = await self._token_request(
            {
                "action": "requesttoken",
                "grant_type": "authorization_code",
                "client_id": _client_id(),
                "client_secret": _client_secret(),
                "code": code.strip(),
                "redirect_uri": _redirect_uri(),
            }
        )
        return self._store_token_body(body)

    async def refresh(self, refresh_token: str) -> dict[str, Any]:
        body = await self._token_request(
            {
                "action": "requesttoken",
                "grant_type": "refresh_token",
                "client_id": _client_id(),
                "client_secret": _client_secret(),
                "refresh_token": refresh_token,
            }
        )
        return self._store_token_body(body)

    async def _token_request(self, data: dict[str, str]) -> dict[str, Any]:
        resp = await self._http.post(TOKEN_URL, data=data)
        return _unwrap(resp, context="token request")

    @staticmethod
    def _store_token_body(body: dict[str, Any]) -> dict[str, Any]:
        expires_in = int(body.get("expires_in", 10800))
        tokens = {
            "access_token": body["access_token"],
            "refresh_token": body["refresh_token"],
            "userid": body.get("userid"),
            "scope": body.get("scope"),
            "expires_at": int(time.time()) + expires_in,
            "obtained_at": int(time.time()),
        }
        save_tokens(tokens)
        return tokens

    async def _access_token(self) -> str:
        async with self._lock:
            tokens = load_tokens()
            if not tokens:
                raise WithingsError(
                    "Not connected to Withings. Call withings_get_auth_url, open the link, "
                    "approve access, then pass the returned code to withings_exchange_code."
                )
            # Refresh a minute early to avoid racing the expiry.
            if int(tokens.get("expires_at", 0)) - 60 <= time.time():
                tokens = await self.refresh(tokens["refresh_token"])
            return tokens["access_token"]

    # -- Data API -----------------------------------------------------------

    async def call(self, path: str, data: dict[str, Any], *, retry_auth: bool = True) -> dict[str, Any]:
        token = await self._access_token()
        payload = {k: v for k, v in data.items() if v is not None}
        resp = await self._http.post(
            f"{API_HOST}/{path}",
            data=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        try:
            return _unwrap(resp, context=f"{path} {data.get('action')}")
        except WithingsAuthError:
            if not retry_auth:
                raise
            # Token may have been revoked server-side or expired early; force refresh once.
            tokens = load_tokens()
            if not tokens:
                raise
            await self.refresh(tokens["refresh_token"])
            return await self.call(path, data, retry_auth=False)

    async def call_paged(self, path: str, data: dict[str, Any], list_key: str) -> list[dict[str, Any]]:
        """Follow Withings `more`/`offset` pagination and concatenate `list_key`."""
        items: list[dict[str, Any]] = []
        offset: int | None = None
        for _ in range(MAX_PAGES):
            body = await self.call(path, {**data, "offset": offset})
            items.extend(body.get(list_key) or [])
            if not body.get("more"):
                break
            offset = body.get("offset")
            if offset is None:
                break
        return items


class WithingsAuthError(WithingsError):
    """Access token rejected."""


def _unwrap(resp: httpx.Response, *, context: str) -> dict[str, Any]:
    if resp.status_code >= 500:
        raise WithingsError(f"Withings returned HTTP {resp.status_code} for {context}.")
    try:
        payload = resp.json()
    except ValueError as exc:
        raise WithingsError(f"Non-JSON response from Withings for {context}: {resp.text[:200]}") from exc
    status = payload.get("status", -1)
    if status == 0:
        return payload.get("body") or {}
    error = payload.get("error", "unknown error")
    if status in AUTH_FAILED_STATUSES:
        raise WithingsAuthError(f"Withings rejected the credentials for {context} (status {status}): {error}")
    if status in RATE_LIMIT_STATUSES:
        raise WithingsError(f"Withings rate limit hit (status {status}): {error}. Wait a minute and retry.")
    raise WithingsError(f"Withings error for {context} (status {status}): {error}")


# ---------------------------------------------------------------------------
# Helpers: dates, decoding, formatting
# ---------------------------------------------------------------------------


def _parse_date(value: str | None, *, default: date) -> date:
    if not value:
        return default
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise WithingsError(f"Date '{value}' must be YYYY-MM-DD.") from exc


def _date_range(start_date: str | None, end_date: str | None, days: int) -> tuple[date, date]:
    end = _parse_date(end_date, default=date.today())
    start = _parse_date(start_date, default=end - timedelta(days=max(days, 1) - 1))
    if start > end:
        raise WithingsError(f"start_date {start} is after end_date {end}.")
    return start, end


def _epoch_bounds(start: date, end: date) -> tuple[int, int]:
    """Epoch seconds covering [start 00:00, end 24:00) in local time."""
    start_dt = datetime.combine(start, datetime.min.time()).astimezone()
    end_dt = datetime.combine(end + timedelta(days=1), datetime.min.time()).astimezone()
    return int(start_dt.timestamp()), int(end_dt.timestamp())


def _tz(name: str | None) -> timezone | ZoneInfo:
    if not name:
        return timezone.utc
    try:
        return ZoneInfo(name)
    except Exception:  # noqa: BLE001 - unknown zone names fall back to UTC
        return timezone.utc


def _iso(ts: int | None, tz: timezone | ZoneInfo) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(int(ts), tz=tz).isoformat(timespec="seconds")


def decode_measure(value: int, unit: int) -> float:
    """Withings encodes values as value * 10^unit."""
    return round(value * (10 ** unit), 4)


def _hms(seconds: int | None) -> str | None:
    if seconds is None:
        return None
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, _ = divmod(rem, 60)
    return f"{h}h{m:02d}m"


def _resolve_types(types: list[str] | None) -> list[int] | None:
    if not types:
        return None
    ids: list[int] = []
    for t in types:
        t = str(t).strip().lower()
        if t.isdigit():
            ids.append(int(t))
        elif t in MEASURE_NAME_TO_ID:
            ids.append(MEASURE_NAME_TO_ID[t])
        else:
            known = ", ".join(sorted(MEASURE_NAME_TO_ID))
            raise WithingsError(f"Unknown measurement type '{t}'. Known: {known}")
    return ids


def format_measure_groups(groups: list[dict[str, Any]], tz_name: str | None) -> list[dict[str, Any]]:
    tz = _tz(tz_name)
    out: list[dict[str, Any]] = []
    for grp in groups:
        measures: dict[str, Any] = {}
        for m in grp.get("measures", []):
            name, unit = MEASURE_TYPES.get(m["type"], (f"type_{m['type']}", "?"))
            entry: dict[str, Any] = {"value": decode_measure(m["value"], m["unit"]), "unit": unit}
            if m.get("position") is not None:
                entry["position"] = MEASURE_POSITIONS.get(m["position"], m["position"])
            measures[name] = entry
        out.append(
            {
                "measured_at": _iso(grp.get("date"), tz),
                "source": ATTRIBUTION.get(grp.get("attrib"), grp.get("attrib")),
                "device_id": grp.get("deviceid"),
                "measures": measures,
            }
        )
    out.sort(key=lambda g: g["measured_at"] or "", reverse=True)
    return out


def _dumps(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# MCP server and tools
# ---------------------------------------------------------------------------

mcp = MCPServer(
    "withings",
    instructions=(
        "Read-only access to a Withings account: weight and body composition, blood "
        "pressure, sleep, daily activity, workouts, ECG recordings and devices. Dates "
        "are YYYY-MM-DD. If a tool reports that the account is not connected, call "
        "withings_get_auth_url and then withings_exchange_code with the returned code."
    ),
)

_client: WithingsClient | None = None


def client() -> WithingsClient:
    global _client
    if _client is None:
        _client = WithingsClient()
    return _client


def _tool_error(exc: Exception) -> str:
    return _dumps({"error": str(exc)})


# -- Auth tools --------------------------------------------------------------


@mcp.tool()
async def withings_auth_status() -> str:
    """Report whether the server is connected to a Withings account and when the access token expires."""
    try:
        tokens = load_tokens()
        if not tokens:
            return _dumps({"connected": False, "next_step": "Call withings_get_auth_url."})
        return _dumps(
            {
                "connected": True,
                "userid": tokens.get("userid"),
                "scope": tokens.get("scope"),
                "access_token_expires_at": datetime.fromtimestamp(tokens["expires_at"], tz=timezone.utc).isoformat(),
                "token_file": str(_token_file()),
                "redirect_uri": _redirect_uri(),
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _tool_error(exc)


@mcp.tool()
async def withings_get_auth_url() -> str:
    """Start connecting a Withings account. Returns a URL for the user to open and approve access.

    After approving, Withings redirects to the callback page, which shows an authorization
    code. Pass that code to withings_exchange_code within 30 seconds.
    """
    try:
        url, state = client().build_authorize_url()
        return _dumps(
            {
                "authorize_url": url,
                "state": state,
                "instructions": (
                    "Open the URL, sign in to Withings and approve access. The callback page "
                    "will display a code. Call withings_exchange_code with that code promptly; "
                    "Withings codes expire after about 30 seconds."
                ),
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _tool_error(exc)


@mcp.tool()
async def withings_exchange_code(code: str) -> str:
    """Finish connecting a Withings account by exchanging the authorization code for tokens.

    Args:
        code: The authorization code shown on the callback page after approving access.
    """
    try:
        tokens = await client().exchange_code(code)
        return _dumps({"connected": True, "userid": tokens.get("userid"), "scope": tokens.get("scope")})
    except Exception as exc:  # noqa: BLE001
        return _tool_error(exc)


@mcp.tool()
async def withings_revoke_token() -> str:
    """Disconnect this server from the Withings account by deleting the stored tokens.

    To fully revoke the app's access, also remove it under Settings > Connected apps in the
    Withings app or at account.withings.com.
    """
    try:
        removed = clear_tokens()
        return _dumps({"disconnected": True, "tokens_deleted": removed})
    except Exception as exc:  # noqa: BLE001
        return _tool_error(exc)


# -- Measurements -------------------------------------------------------------


@mcp.tool()
async def withings_get_body_measurements(
    start_date: str | None = None,
    end_date: str | None = None,
    days: int = 30,
    types: list[str] | None = None,
) -> str:
    """Get body measurements (weight, fat ratio, muscle mass, bone mass, hydration, etc.) from Withings scales.

    Returns one entry per weigh-in, newest first, with decoded values and units.

    Args:
        start_date: First day to include, YYYY-MM-DD. Defaults to `days` before end_date.
        end_date: Last day to include, YYYY-MM-DD. Defaults to today.
        days: Window length when start_date is omitted (default 30).
        types: Optional list of measurement names or Withings type ids to restrict to, e.g.
            ["weight", "fat_ratio"]. Defaults to the full body-composition set.
    """
    try:
        start, end = _date_range(start_date, end_date, days)
        s, e = _epoch_bounds(start, end)
        type_ids = _resolve_types(types) or BODY_COMPOSITION_TYPES
        body = await client().call(
            "measure",
            {"action": "getmeas", "meastypes": ",".join(map(str, type_ids)), "category": 1,
             "startdate": s, "enddate": e},
        )
        groups = body.get("measuregrps", [])
        # Follow pagination if needed.
        offset = body.get("offset")
        pages = 1
        while body.get("more") and offset is not None and pages < MAX_PAGES:
            body = await client().call(
                "measure",
                {"action": "getmeas", "meastypes": ",".join(map(str, type_ids)), "category": 1,
                 "startdate": s, "enddate": e, "offset": offset},
            )
            groups.extend(body.get("measuregrps", []))
            offset = body.get("offset")
            pages += 1
        return _dumps(
            {
                "start_date": str(start),
                "end_date": str(end),
                "timezone": body.get("timezone"),
                "count": len(groups),
                "measurements": format_measure_groups(groups, body.get("timezone")),
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _tool_error(exc)


@mcp.tool()
async def withings_get_latest_measurements() -> str:
    """Get the most recent reading of every measurement type Withings has for the account.

    Covers weight, body composition, blood pressure, heart rate, SpO2, temperature, pulse wave
    velocity, vascular age, VO2 max and ECG intervals where devices provide them.
    """
    try:
        # Last 2 years is enough to find the latest of each type for an active account.
        end = date.today()
        start = end - timedelta(days=730)
        s, e = _epoch_bounds(start, end)
        groups = await client().call_paged(
            "measure", {"action": "getmeas", "category": 1, "startdate": s, "enddate": e}, "measuregrps"
        )
        latest: dict[str, dict[str, Any]] = {}
        for grp in sorted(groups, key=lambda g: g.get("date", 0), reverse=True):
            for m in grp.get("measures", []):
                name, unit = MEASURE_TYPES.get(m["type"], (f"type_{m['type']}", "?"))
                if name not in latest:
                    latest[name] = {
                        "value": decode_measure(m["value"], m["unit"]),
                        "unit": unit,
                        "measured_at": _iso(grp.get("date"), timezone.utc),
                    }
        return _dumps({"count": len(latest), "latest": latest})
    except Exception as exc:  # noqa: BLE001
        return _tool_error(exc)


@mcp.tool()
async def withings_get_blood_pressure(
    start_date: str | None = None,
    end_date: str | None = None,
    days: int = 30,
) -> str:
    """Get blood pressure readings (systolic, diastolic, heart rate) from a Withings BPM, newest first.

    Args:
        start_date: First day to include, YYYY-MM-DD. Defaults to `days` before end_date.
        end_date: Last day to include, YYYY-MM-DD. Defaults to today.
        days: Window length when start_date is omitted (default 30).
    """
    try:
        start, end = _date_range(start_date, end_date, days)
        s, e = _epoch_bounds(start, end)
        groups = await client().call_paged(
            "measure",
            {"action": "getmeas", "meastypes": ",".join(map(str, BLOOD_PRESSURE_TYPES)), "category": 1,
             "startdate": s, "enddate": e},
            "measuregrps",
        )
        readings = []
        for g in format_measure_groups(groups, None):
            m = g["measures"]
            sysv = m.get("systolic_blood_pressure", {}).get("value")
            diav = m.get("diastolic_blood_pressure", {}).get("value")
            if sysv is None and diav is None:
                continue
            readings.append(
                {
                    "measured_at": g["measured_at"],
                    "systolic_mmHg": sysv,
                    "diastolic_mmHg": diav,
                    "heart_rate_bpm": m.get("heart_rate", {}).get("value"),
                    "source": g["source"],
                }
            )
        summary = None
        if readings:
            sys_vals = [r["systolic_mmHg"] for r in readings if r["systolic_mmHg"] is not None]
            dia_vals = [r["diastolic_mmHg"] for r in readings if r["diastolic_mmHg"] is not None]
            summary = {
                "readings": len(readings),
                "average_systolic_mmHg": round(sum(sys_vals) / len(sys_vals), 1) if sys_vals else None,
                "average_diastolic_mmHg": round(sum(dia_vals) / len(dia_vals), 1) if dia_vals else None,
            }
        return _dumps({"start_date": str(start), "end_date": str(end), "summary": summary, "readings": readings})
    except Exception as exc:  # noqa: BLE001
        return _tool_error(exc)


# -- Sleep ----------------------------------------------------------------------


@mcp.tool()
async def withings_get_sleep_summary(
    start_date: str | None = None,
    end_date: str | None = None,
    days: int = 14,
) -> str:
    """Get nightly sleep summaries: sleep score, durations by stage, heart and breathing rate, wake-ups, snoring.

    One entry per night, newest first. Durations are in seconds with a readable h/m alongside.

    Args:
        start_date: First night to include, YYYY-MM-DD. Defaults to `days` before end_date.
        end_date: Last night to include, YYYY-MM-DD. Defaults to today.
        days: Window length when start_date is omitted (default 14).
    """
    try:
        start, end = _date_range(start_date, end_date, days)
        series = await client().call_paged(
            "v2/sleep",
            {"action": "getsummary", "startdateymd": str(start), "enddateymd": str(end),
             "data_fields": ",".join(SLEEP_SUMMARY_FIELDS)},
            "series",
        )
        nights = []
        for s in sorted(series, key=lambda x: x.get("date", ""), reverse=True):
            tz = _tz(s.get("timezone"))
            d = s.get("data", {})
            nights.append(
                {
                    "date": s.get("date"),
                    "in_bed_at": _iso(s.get("startdate"), tz),
                    "out_of_bed_at": _iso(s.get("enddate"), tz),
                    "sleep_score": d.get("sleep_score"),
                    "total_sleep_time": _hms(d.get("total_sleep_time")),
                    "total_sleep_time_s": d.get("total_sleep_time"),
                    "time_in_bed": _hms(d.get("total_timeinbed")),
                    "deep": _hms(d.get("deepsleepduration")),
                    "light": _hms(d.get("lightsleepduration")),
                    "rem": _hms(d.get("remsleepduration")),
                    "awake_in_bed": _hms(d.get("wakeupduration")),
                    "sleep_efficiency_pct": d.get("sleep_efficiency"),
                    "time_to_fall_asleep": _hms(d.get("sleep_latency")),
                    "time_to_get_up": _hms(d.get("wakeup_latency")),
                    "wake_up_count": d.get("wakeupcount"),
                    "out_of_bed_count": d.get("out_of_bed_count"),
                    "heart_rate_bpm": {"avg": d.get("hr_average"), "min": d.get("hr_min"), "max": d.get("hr_max")},
                    "breathing_rate": {"avg": d.get("rr_average"), "min": d.get("rr_min"), "max": d.get("rr_max")},
                    "snoring_s": d.get("snoring"),
                    "snoring_episodes": d.get("snoringepisodecount"),
                    "breathing_disturbances_intensity": d.get("breathing_disturbances_intensity"),
                    "apnea_hypopnea_index": d.get("apnea_hypopnea_index"),
                    "device_model": s.get("model"),
                }
            )
        return _dumps({"start_date": str(start), "end_date": str(end), "count": len(nights), "nights": nights})
    except Exception as exc:  # noqa: BLE001
        return _tool_error(exc)


@mcp.tool()
async def withings_get_sleep_details(night: str | None = None) -> str:
    """Get the stage-by-stage timeline for one night (awake, light, deep, REM) with heart rate and breathing per segment.

    Args:
        night: The night to fetch as the morning date, YYYY-MM-DD (e.g. sleep ending on the morning
            of 2026-10-11). Defaults to last night. Looks from 18:00 the evening before to 14:00.
    """
    try:
        morning = _parse_date(night, default=date.today())
        start_dt = datetime.combine(morning - timedelta(days=1), datetime.min.time()).astimezone() + timedelta(hours=18)
        end_dt = datetime.combine(morning, datetime.min.time()).astimezone() + timedelta(hours=14)
        body = await client().call(
            "v2/sleep",
            {"action": "get", "startdate": int(start_dt.timestamp()), "enddate": int(end_dt.timestamp()),
             "data_fields": "hr,rr,snoring,sdnn_1,mvt_score"},
        )
        series = body.get("series", [])
        segments = []
        totals: dict[str, int] = {}
        for seg in sorted(series, key=lambda x: x.get("startdate", 0)):
            state = SLEEP_STATES.get(seg.get("state"), str(seg.get("state")))
            dur = int(seg.get("enddate", 0)) - int(seg.get("startdate", 0))
            totals[state] = totals.get(state, 0) + dur

            def _avg(d: dict[str, Any] | None) -> float | None:
                if not d:
                    return None
                vals = [v for v in d.values() if isinstance(v, (int, float))]
                return round(sum(vals) / len(vals), 1) if vals else None

            segments.append(
                {
                    "start": _iso(seg.get("startdate"), timezone.utc),
                    "end": _iso(seg.get("enddate"), timezone.utc),
                    "duration": _hms(dur),
                    "state": state,
                    "heart_rate_avg": _avg(seg.get("hr")),
                    "breathing_rate_avg": _avg(seg.get("rr")),
                    "hrv_sdnn_avg": _avg(seg.get("sdnn_1")),
                    "snoring_avg": _avg(seg.get("snoring")),
                }
            )
        return _dumps(
            {
                "night_ending": str(morning),
                "segments": len(segments),
                "totals": {k: _hms(v) for k, v in totals.items()},
                "device_model": body.get("model"),
                "timeline": segments,
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _tool_error(exc)


# -- Activity and workouts ---------------------------------------------------------


@mcp.tool()
async def withings_get_activity(
    start_date: str | None = None,
    end_date: str | None = None,
    days: int = 14,
) -> str:
    """Get daily activity summaries: steps, distance, calories, active minutes by intensity, heart rate zones.

    Args:
        start_date: First day to include, YYYY-MM-DD. Defaults to `days` before end_date.
        end_date: Last day to include, YYYY-MM-DD. Defaults to today.
        days: Window length when start_date is omitted (default 14).
    """
    try:
        start, end = _date_range(start_date, end_date, days)
        acts = await client().call_paged(
            "v2/measure",
            {"action": "getactivity", "startdateymd": str(start), "enddateymd": str(end),
             "data_fields": ",".join(ACTIVITY_FIELDS)},
            "activities",
        )
        days_out = []
        for a in sorted(acts, key=lambda x: x.get("date", ""), reverse=True):
            days_out.append(
                {
                    "date": a.get("date"),
                    "steps": a.get("steps"),
                    "distance_m": a.get("distance"),
                    "elevation_m": a.get("elevation"),
                    "active_calories_kcal": a.get("calories"),
                    "total_calories_kcal": a.get("totalcalories"),
                    "activity_minutes": {
                        "soft": round((a.get("soft") or 0) / 60),
                        "moderate": round((a.get("moderate") or 0) / 60),
                        "intense": round((a.get("intense") or 0) / 60),
                        "total_active": round((a.get("active") or 0) / 60),
                    },
                    "heart_rate_bpm": {"avg": a.get("hr_average"), "min": a.get("hr_min"), "max": a.get("hr_max")},
                    "hr_zone_minutes": {
                        "light": round((a.get("hr_zone_0") or 0) / 60),
                        "moderate": round((a.get("hr_zone_1") or 0) / 60),
                        "intense": round((a.get("hr_zone_2") or 0) / 60),
                        "maximal": round((a.get("hr_zone_3") or 0) / 60),
                    },
                    "from_tracker": a.get("is_tracker"),
                }
            )
        total_steps = sum(d["steps"] or 0 for d in days_out)
        return _dumps(
            {
                "start_date": str(start),
                "end_date": str(end),
                "count": len(days_out),
                "average_steps": round(total_steps / len(days_out)) if days_out else None,
                "days": days_out,
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _tool_error(exc)


@mcp.tool()
async def withings_get_workouts(
    start_date: str | None = None,
    end_date: str | None = None,
    days: int = 30,
) -> str:
    """Get recorded workouts (runs, walks, cycling, swims, etc.) with duration, calories, distance and heart rate.

    Args:
        start_date: First day to include, YYYY-MM-DD. Defaults to `days` before end_date.
        end_date: Last day to include, YYYY-MM-DD. Defaults to today.
        days: Window length when start_date is omitted (default 30).
    """
    try:
        start, end = _date_range(start_date, end_date, days)
        series = await client().call_paged(
            "v2/measure",
            {"action": "getworkouts", "startdateymd": str(start), "enddateymd": str(end),
             "data_fields": ",".join(WORKOUT_FIELDS)},
            "series",
        )
        workouts = []
        for w in sorted(series, key=lambda x: x.get("startdate", 0), reverse=True):
            tz = _tz(w.get("timezone"))
            d = w.get("data", {})
            dur = int(w.get("enddate", 0)) - int(w.get("startdate", 0))
            workouts.append(
                {
                    "id": w.get("id"),
                    "type": WORKOUT_CATEGORIES.get(w.get("category"), f"category_{w.get('category')}"),
                    "date": w.get("date"),
                    "start": _iso(w.get("startdate"), tz),
                    "end": _iso(w.get("enddate"), tz),
                    "duration": _hms(dur),
                    "duration_s": dur,
                    "calories_kcal": d.get("calories"),
                    "distance_m": d.get("distance"),
                    "steps": d.get("steps"),
                    "elevation_m": d.get("elevation"),
                    "heart_rate_bpm": {"avg": d.get("hr_average"), "min": d.get("hr_min"), "max": d.get("hr_max")},
                    "hr_zone_minutes": {
                        "light": round((d.get("hr_zone_0") or 0) / 60),
                        "moderate": round((d.get("hr_zone_1") or 0) / 60),
                        "intense": round((d.get("hr_zone_2") or 0) / 60),
                        "maximal": round((d.get("hr_zone_3") or 0) / 60),
                    },
                    "spo2_average": d.get("spo2_average"),
                    "pool_laps": d.get("pool_laps"),
                    "intensity": d.get("intensity"),
                }
            )
        return _dumps({"start_date": str(start), "end_date": str(end), "count": len(workouts), "workouts": workouts})
    except Exception as exc:  # noqa: BLE001
        return _tool_error(exc)


# -- Heart / ECG --------------------------------------------------------------------


@mcp.tool()
async def withings_get_ecg_recordings(
    start_date: str | None = None,
    end_date: str | None = None,
    days: int = 90,
) -> str:
    """List ECG recordings taken with a ScanWatch or BPM Core, with heart rate, AFib classification and any blood pressure taken alongside.

    Args:
        start_date: First day to include, YYYY-MM-DD. Defaults to `days` before end_date.
        end_date: Last day to include, YYYY-MM-DD. Defaults to today.
        days: Window length when start_date is omitted (default 90).
    """
    try:
        start, end = _date_range(start_date, end_date, days)
        s, e = _epoch_bounds(start, end)
        series = await client().call_paged("v2/heart", {"action": "list", "startdate": s, "enddate": e}, "series")
        afib = {0: "normal", 1: "atrial_fibrillation", 2: "inconclusive"}
        recs = []
        for r in sorted(series, key=lambda x: x.get("timestamp", 0), reverse=True):
            tz = _tz(r.get("timezone"))
            ecg = r.get("ecg") or {}
            bp = r.get("bloodpressure") or {}
            recs.append(
                {
                    "recorded_at": _iso(r.get("timestamp"), tz),
                    "signal_id": ecg.get("signalid"),
                    "classification": afib.get(ecg.get("afib"), ecg.get("afib")),
                    "heart_rate_bpm": r.get("heart_rate"),
                    "blood_pressure": {"systolic_mmHg": bp.get("systole"), "diastolic_mmHg": bp.get("diastole")} if bp else None,
                    "device_model": r.get("model"),
                }
            )
        return _dumps({"start_date": str(start), "end_date": str(end), "count": len(recs), "recordings": recs})
    except Exception as exc:  # noqa: BLE001
        return _tool_error(exc)


@mcp.tool()
async def withings_get_ecg_signal(signal_id: int) -> str:
    """Get the raw ECG waveform (microvolt samples) and sampling frequency for one recording.

    Args:
        signal_id: The signal_id from withings_get_ecg_recordings.
    """
    try:
        body = await client().call("v2/heart", {"action": "get", "signalid": int(signal_id)})
        signal = body.get("signal") or []
        return _dumps(
            {
                "signal_id": signal_id,
                "sampling_frequency_hz": body.get("sampling_frequency"),
                "wear_position": MEASURE_POSITIONS.get(body.get("wearposition"), body.get("wearposition")),
                "samples": len(signal),
                "duration_s": round(len(signal) / body["sampling_frequency"], 1) if body.get("sampling_frequency") else None,
                "signal_microvolts": signal,
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _tool_error(exc)


# -- Account -----------------------------------------------------------------------


@mcp.tool()
async def withings_get_devices() -> str:
    """List the Withings devices linked to the account with type, model, battery level and last sync."""
    try:
        body = await client().call("v2/user", {"action": "getdevice"})
        devices = []
        for d in body.get("devices", []):
            devices.append(
                {
                    "type": d.get("type"),
                    "model": d.get("model"),
                    "battery": d.get("battery"),
                    "first_session": _iso(d.get("first_session_date"), timezone.utc),
                    "last_session": _iso(d.get("last_session_date"), timezone.utc),
                    "device_id": d.get("deviceid"),
                }
            )
        return _dumps({"count": len(devices), "devices": devices})
    except Exception as exc:  # noqa: BLE001
        return _tool_error(exc)


@mcp.tool()
async def withings_get_goals() -> str:
    """Get the user's goals set in the Withings app: daily steps, sleep duration and target weight."""
    try:
        body = await client().call("v2/user", {"action": "getgoals"})
        g = body.get("goals", {})
        weight = g.get("weight") or {}
        return _dumps(
            {
                "steps_per_day": g.get("steps"),
                "sleep": _hms(g.get("sleep")),
                "sleep_s": g.get("sleep"),
                "weight_kg": decode_measure(weight["value"], weight["unit"]) if weight.get("value") is not None else None,
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _tool_error(exc)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


async def _interactive_auth() -> None:
    c = WithingsClient()
    try:
        url, _state = c.build_authorize_url()
        print("1. Open this URL in a browser and approve access:\n")
        print(f"   {url}\n")
        print("2. Withings will redirect to the callback page, which shows a code.")
        code = input("3. Paste the code here (within 30 seconds): ").strip()
        tokens = await c.exchange_code(code)
        print(f"\nConnected. User id {tokens.get('userid')}. Tokens saved to {_token_file()}")
    finally:
        await c.aclose()


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "auth":
        asyncio.run(_interactive_auth())
        return
    mcp.run("stdio")


if __name__ == "__main__":
    main()
