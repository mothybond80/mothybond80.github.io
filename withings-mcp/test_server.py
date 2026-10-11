"""Offline tests for the Withings MCP server using a fake HTTP transport."""

from __future__ import annotations

import json
import time
from datetime import date
from typing import Any
from urllib.parse import parse_qs

import httpx
import pytest

import server


@pytest.fixture(autouse=True)
def _env(tmp_path, monkeypatch):
    monkeypatch.setenv("WITHINGS_CLIENT_ID", "cid")
    monkeypatch.setenv("WITHINGS_CLIENT_SECRET", "secret")
    monkeypatch.setenv("WITHINGS_TOKEN_FILE", str(tmp_path / "tokens.json"))
    monkeypatch.delenv("WITHINGS_REDIRECT_URI", raising=False)
    server._client = None
    yield
    server._client = None


class FakeWithings:
    """Records requests and serves canned Withings-style responses."""

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.responses: list[dict[str, Any]] = []

    def queue(self, body: dict[str, Any], status: int = 0, error: str | None = None) -> None:
        payload: dict[str, Any] = {"status": status, "body": body}
        if error:
            payload["error"] = error
        self.responses.append(payload)

    def handler(self, request: httpx.Request) -> httpx.Response:
        form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
        self.requests.append({"url": str(request.url), "form": form, "auth": request.headers.get("Authorization")})
        payload = self.responses.pop(0) if self.responses else {"status": 0, "body": {}}
        return httpx.Response(200, json=payload)

    def install(self) -> server.WithingsClient:
        http = httpx.AsyncClient(transport=httpx.MockTransport(self.handler))
        c = server.WithingsClient(http=http)
        server._client = c
        return c


def _seed_tokens(expires_in: int = 3600) -> None:
    server.save_tokens(
        {"access_token": "AT", "refresh_token": "RT", "userid": 42, "scope": server.SCOPES,
         "expires_at": int(time.time()) + expires_in, "obtained_at": int(time.time())}
    )


# -- Pure helpers --------------------------------------------------------------


def test_decode_measure():
    assert server.decode_measure(84500, -3) == 84.5
    assert server.decode_measure(120, 0) == 120
    assert server.decode_measure(1, 1) == 10


def test_hms():
    assert server._hms(0) == "0h00m"
    assert server._hms(27000) == "7h30m"
    assert server._hms(None) is None


def test_date_range_defaults():
    start, end = server._date_range(None, "2026-10-11", 7)
    assert end == date(2026, 10, 11)
    assert start == date(2026, 10, 5)


def test_date_range_rejects_bad_input():
    with pytest.raises(server.WithingsError):
        server._date_range("2026-10-12", "2026-10-11", 7)
    with pytest.raises(server.WithingsError):
        server._date_range("12/10/2026", None, 7)


def test_resolve_types_names_and_ids():
    assert server._resolve_types(["weight", "6", "Bone_Mass"]) == [1, 6, 88]
    assert server._resolve_types(None) is None
    with pytest.raises(server.WithingsError):
        server._resolve_types(["nonsense"])


def test_format_measure_groups_decodes_and_sorts():
    groups = [
        {"date": 1_700_000_000, "attrib": 0, "deviceid": "d1",
         "measures": [{"type": 1, "value": 84500, "unit": -3}, {"type": 6, "value": 2215, "unit": -2}]},
        {"date": 1_700_100_000, "attrib": 2, "deviceid": None,
         "measures": [{"type": 1, "value": 84, "unit": 0}]},
    ]
    out = server.format_measure_groups(groups, "Europe/London")
    assert [g["source"] for g in out] == ["manual_entry", "device_known_user"]
    assert out[1]["measures"]["weight"] == {"value": 84.5, "unit": "kg"}
    assert out[1]["measures"]["fat_ratio"] == {"value": 22.15, "unit": "%"}
    assert out[0]["measured_at"].startswith("2023-11-16")


# -- Auth ------------------------------------------------------------------------


def test_authorize_url_contains_required_params():
    c = server.WithingsClient(http=httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))))
    url, state = c.build_authorize_url()
    assert url.startswith(server.AUTHORIZE_URL)
    assert "response_type=code" in url
    assert "client_id=cid" in url
    assert f"state={state}" in url
    assert "user.metrics" in url
    assert "redirect_uri=https%3A%2F%2Fmothybond80.github.io%2Fwithings-mcp%2Fcallback.html" in url


async def test_exchange_code_stores_tokens():
    fake = FakeWithings()
    fake.queue({"userid": 42, "access_token": "AT", "refresh_token": "RT", "expires_in": 10800, "scope": "user.metrics"})
    fake.install()
    result = json.loads(await server.withings_exchange_code("abc"))
    assert result == {"connected": True, "userid": 42, "scope": "user.metrics"}
    form = fake.requests[0]["form"]
    assert form["action"] == "requesttoken"
    assert form["grant_type"] == "authorization_code"
    assert form["code"] == "abc"
    assert form["redirect_uri"] == server.DEFAULT_REDIRECT_URI
    saved = server.load_tokens()
    assert saved["refresh_token"] == "RT"
    assert saved["expires_at"] > time.time() + 10000


async def test_not_connected_error_is_helpful():
    FakeWithings().install()
    result = json.loads(await server.withings_get_devices())
    assert "Not connected" in result["error"]
    assert "withings_get_auth_url" in result["error"]


async def test_expired_token_is_refreshed_before_call():
    _seed_tokens(expires_in=10)  # inside the 60s early-refresh window
    fake = FakeWithings()
    fake.queue({"userid": 42, "access_token": "AT2", "refresh_token": "RT2", "expires_in": 10800})
    fake.queue({"devices": []})
    fake.install()
    await server.withings_get_devices()
    assert fake.requests[0]["form"]["grant_type"] == "refresh_token"
    assert fake.requests[0]["form"]["refresh_token"] == "RT"
    assert fake.requests[1]["auth"] == "Bearer AT2"
    assert server.load_tokens()["refresh_token"] == "RT2"


async def test_auth_failure_triggers_one_refresh_and_retry():
    _seed_tokens()
    fake = FakeWithings()
    fake.queue({}, status=401, error="invalid token")
    fake.queue({"userid": 42, "access_token": "AT3", "refresh_token": "RT3", "expires_in": 10800})
    fake.queue({"devices": [{"type": "Scale", "model": "Body+", "battery": "high", "deviceid": "x"}]})
    fake.install()
    result = json.loads(await server.withings_get_devices())
    assert result["count"] == 1
    assert [r["form"]["action"] for r in fake.requests] == ["getdevice", "requesttoken", "getdevice"]
    assert fake.requests[2]["auth"] == "Bearer AT3"


async def test_rate_limit_is_reported():
    _seed_tokens()
    fake = FakeWithings()
    fake.queue({}, status=601, error="Too Many Requests")
    fake.install()
    result = json.loads(await server.withings_get_goals())
    assert "rate limit" in result["error"]


async def test_revoke_deletes_tokens():
    _seed_tokens()
    result = json.loads(await server.withings_revoke_token())
    assert result == {"disconnected": True, "tokens_deleted": True}
    assert server.load_tokens() is None


# -- Data tools ----------------------------------------------------------------------


async def test_body_measurements_request_and_output():
    _seed_tokens()
    fake = FakeWithings()
    fake.queue(
        {"timezone": "Europe/London", "more": 0, "offset": 0,
         "measuregrps": [{"grpid": 1, "attrib": 0, "date": 1_760_000_000, "deviceid": "d",
                          "measures": [{"type": 1, "value": 83120, "unit": -3},
                                       {"type": 76, "value": 61000, "unit": -3}]}]}
    )
    fake.install()
    result = json.loads(await server.withings_get_body_measurements(start_date="2026-10-01", end_date="2026-10-10"))
    form = fake.requests[0]["form"]
    assert fake.requests[0]["url"].endswith("/measure")
    assert form["action"] == "getmeas"
    assert form["category"] == "1"
    assert "1" in form["meastypes"].split(",") and "76" in form["meastypes"].split(",")
    assert int(form["startdate"]) < int(form["enddate"])
    assert result["count"] == 1
    assert result["measurements"][0]["measures"]["weight"] == {"value": 83.12, "unit": "kg"}
    assert result["measurements"][0]["measures"]["muscle_mass"] == {"value": 61.0, "unit": "kg"}


async def test_body_measurements_follows_pagination():
    _seed_tokens()
    fake = FakeWithings()
    fake.queue({"timezone": "UTC", "more": 1, "offset": 7,
                "measuregrps": [{"date": 2, "attrib": 0, "measures": [{"type": 1, "value": 80, "unit": 0}]}]})
    fake.queue({"timezone": "UTC", "more": 0,
                "measuregrps": [{"date": 1, "attrib": 0, "measures": [{"type": 1, "value": 81, "unit": 0}]}]})
    fake.install()
    result = json.loads(await server.withings_get_body_measurements(types=["weight"]))
    assert result["count"] == 2
    assert fake.requests[1]["form"]["offset"] == "7"


async def test_blood_pressure_summary():
    _seed_tokens()
    fake = FakeWithings()
    fake.queue(
        {"timezone": "UTC", "more": 0,
         "measuregrps": [
             {"date": 10, "attrib": 0, "measures": [{"type": 10, "value": 128, "unit": 0},
                                                     {"type": 9, "value": 82, "unit": 0},
                                                     {"type": 11, "value": 64, "unit": 0}]},
             {"date": 20, "attrib": 0, "measures": [{"type": 10, "value": 122, "unit": 0},
                                                     {"type": 9, "value": 78, "unit": 0}]},
         ]}
    )
    fake.install()
    result = json.loads(await server.withings_get_blood_pressure(days=7))
    assert fake.requests[0]["form"]["meastypes"] == "9,10,11"
    assert result["summary"] == {"readings": 2, "average_systolic_mmHg": 125.0, "average_diastolic_mmHg": 80.0}
    assert result["readings"][0]["systolic_mmHg"] == 122  # newest first
    assert result["readings"][1]["heart_rate_bpm"] == 64


async def test_sleep_summary_formats_night():
    _seed_tokens()
    fake = FakeWithings()
    fake.queue(
        {"more": False, "series": [
            {"date": "2026-10-10", "timezone": "Europe/London", "startdate": 1_760_000_000, "enddate": 1_760_028_800,
             "model": 32,
             "data": {"sleep_score": 81, "total_sleep_time": 26100, "total_timeinbed": 28800,
                      "deepsleepduration": 6000, "lightsleepduration": 14100, "remsleepduration": 6000,
                      "wakeupduration": 2700, "wakeupcount": 2, "hr_average": 52, "hr_min": 45, "hr_max": 70,
                      "rr_average": 14, "sleep_efficiency": 91, "snoringepisodecount": 3}}]}
    )
    fake.install()
    result = json.loads(await server.withings_get_sleep_summary(start_date="2026-10-01", end_date="2026-10-10"))
    form = fake.requests[0]["form"]
    assert fake.requests[0]["url"].endswith("/v2/sleep")
    assert form["action"] == "getsummary"
    assert form["startdateymd"] == "2026-10-01" and form["enddateymd"] == "2026-10-10"
    assert "sleep_score" in form["data_fields"]
    night = result["nights"][0]
    assert night["sleep_score"] == 81
    assert night["total_sleep_time"] == "7h15m"
    assert night["deep"] == "1h40m"
    assert night["heart_rate_bpm"] == {"avg": 52, "min": 45, "max": 70}
    assert night["in_bed_at"].endswith("+01:00")  # BST applied from the series timezone


async def test_sleep_details_builds_timeline():
    _seed_tokens()
    fake = FakeWithings()
    fake.queue(
        {"model": 32, "series": [
            {"startdate": 100, "enddate": 1900, "state": 1, "hr": {"100": 60, "700": 58}},
            {"startdate": 1900, "enddate": 5500, "state": 2, "hr": {"1900": 50}},
            {"startdate": 5500, "enddate": 6100, "state": 0},
        ]}
    )
    fake.install()
    result = json.loads(await server.withings_get_sleep_details("2026-10-11"))
    assert fake.requests[0]["form"]["action"] == "get"
    assert result["segments"] == 3
    assert result["totals"] == {"light": "0h30m", "deep": "1h00m", "awake": "0h10m"}
    assert result["timeline"][0]["heart_rate_avg"] == 59.0
    assert result["timeline"][2]["heart_rate_avg"] is None


async def test_activity_converts_seconds_to_minutes():
    _seed_tokens()
    fake = FakeWithings()
    fake.queue(
        {"more": False, "activities": [
            {"date": "2026-10-10", "steps": 8200, "distance": 6100, "calories": 310.5, "totalcalories": 2400,
             "soft": 3600, "moderate": 1800, "intense": 600, "active": 2400, "hr_average": 70,
             "hr_zone_0": 600, "is_tracker": True},
            {"date": "2026-10-09", "steps": 4000, "soft": 0, "is_tracker": True},
        ]}
    )
    fake.install()
    result = json.loads(await server.withings_get_activity(days=2))
    form = fake.requests[0]["form"]
    assert fake.requests[0]["url"].endswith("/v2/measure")
    assert form["action"] == "getactivity"
    assert "steps" in form["data_fields"]
    assert result["average_steps"] == 6100
    day = result["days"][0]
    assert day["date"] == "2026-10-10"
    assert day["activity_minutes"] == {"soft": 60, "moderate": 30, "intense": 10, "total_active": 40}
    assert day["hr_zone_minutes"]["light"] == 10


async def test_workouts_map_category_and_duration():
    _seed_tokens()
    fake = FakeWithings()
    fake.queue(
        {"more": False, "series": [
            {"id": 9, "category": 2, "timezone": "Europe/London", "date": "2026-10-09",
             "startdate": 1_760_000_000, "enddate": 1_760_002_700,
             "data": {"calories": 420.0, "distance": 5020.0, "hr_average": 150, "hr_zone_2": 1200}}]}
    )
    fake.install()
    result = json.loads(await server.withings_get_workouts())
    assert fake.requests[0]["form"]["action"] == "getworkouts"
    w = result["workouts"][0]
    assert w["type"] == "run"
    assert w["duration"] == "0h45m"
    assert w["distance_m"] == 5020.0
    assert w["hr_zone_minutes"]["intense"] == 20


async def test_ecg_recordings_and_signal():
    _seed_tokens()
    fake = FakeWithings()
    fake.queue({"more": False, "series": [
        {"timestamp": 1_760_000_000, "timezone": "Europe/London", "model": 93, "heart_rate": 61,
         "ecg": {"signalid": 555, "afib": 0}, "bloodpressure": {"systole": 120, "diastole": 80}}]})
    fake.queue({"signal": [1, 2, 3, 4, 5, 6], "sampling_frequency": 300, "wearposition": 1})
    fake.install()
    recs = json.loads(await server.withings_get_ecg_recordings(days=30))
    assert fake.requests[0]["url"].endswith("/v2/heart")
    assert fake.requests[0]["form"]["action"] == "list"
    assert recs["recordings"][0]["classification"] == "normal"
    assert recs["recordings"][0]["blood_pressure"] == {"systolic_mmHg": 120, "diastolic_mmHg": 80}
    sig = json.loads(await server.withings_get_ecg_signal(555))
    assert fake.requests[1]["form"] == {"action": "get", "signalid": "555"}
    assert sig["samples"] == 6
    assert sig["wear_position"] == "left_wrist"
    assert sig["duration_s"] == 0.0  # 6 samples at 300 Hz rounds to 0.0 s


async def test_goals_decode_weight():
    _seed_tokens()
    fake = FakeWithings()
    fake.queue({"goals": {"steps": 10000, "sleep": 28800, "weight": {"value": 80000, "unit": -3}}})
    fake.install()
    result = json.loads(await server.withings_get_goals())
    assert result == {"steps_per_day": 10000, "sleep": "8h00m", "sleep_s": 28800, "weight_kg": 80.0}


async def test_latest_measurements_picks_newest_per_type():
    _seed_tokens()
    fake = FakeWithings()
    fake.queue({"timezone": "UTC", "more": 0, "measuregrps": [
        {"date": 100, "attrib": 0, "measures": [{"type": 1, "value": 80, "unit": 0}, {"type": 54, "value": 97, "unit": 0}]},
        {"date": 200, "attrib": 0, "measures": [{"type": 1, "value": 79, "unit": 0}]},
    ]})
    fake.install()
    result = json.loads(await server.withings_get_latest_measurements())
    assert result["count"] == 2
    assert result["latest"]["weight"]["value"] == 79
    assert result["latest"]["spo2"] == {"value": 97, "unit": "%", "measured_at": "1970-01-01T00:01:40+00:00"}


# -- MCP wiring ----------------------------------------------------------------------


async def test_all_tools_registered_with_schemas():
    tools = await server.mcp.list_tools()
    names = {t.name for t in tools}
    expected = {
        "withings_auth_status", "withings_get_auth_url", "withings_exchange_code", "withings_revoke_token",
        "withings_get_body_measurements", "withings_get_latest_measurements", "withings_get_blood_pressure",
        "withings_get_sleep_summary", "withings_get_sleep_details", "withings_get_activity",
        "withings_get_workouts", "withings_get_ecg_recordings", "withings_get_ecg_signal",
        "withings_get_devices", "withings_get_goals",
    }
    assert expected <= names
    by_name = {t.name: t for t in tools}
    props = by_name["withings_get_body_measurements"].input_schema["properties"]
    assert set(props) == {"start_date", "end_date", "days", "types"}
    assert by_name["withings_exchange_code"].input_schema["required"] == ["code"]
