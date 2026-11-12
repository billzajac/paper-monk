"""Pasadena, CA weather, 12-hour trajectory, Air Quality (AQI/UV), and Moon Phase fetcher."""

from __future__ import annotations

import json
import math
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone as dt_timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def c_to_f(celsius: float) -> float:
    return celsius * 9.0 / 5.0 + 32.0


def compute_moon_phase(epoch_ts: float | None = None) -> tuple[str, int, float]:
    """Return (phase_name, illumination_percent, cycle_0_to_1) using synodic lunar period."""
    ts = epoch_ts if epoch_ts is not None else time.time()
    # Known New Moon reference: 2000-01-06 18:14 UTC (epoch 947182440)
    synodic_days = 29.530588853
    days_since = (ts - 947182440.0) / 86400.0
    cycle = (days_since % synodic_days) / synodic_days  # 0.0 = New, 0.5 = Full
    illum = int(round((1.0 - math.cos(2.0 * math.pi * cycle)) * 50.0))

    if cycle < 0.03 or cycle >= 0.97:
        name = "New Moon"
    elif cycle < 0.22:
        name = "Waxing Crescent"
    elif cycle < 0.28:
        name = "First Quarter"
    elif cycle < 0.47:
        name = "Waxing Gibbous"
    elif cycle < 0.53:
        name = "Full Moon"
    elif cycle < 0.72:
        name = "Waning Gibbous"
    elif cycle < 0.78:
        name = "Last Quarter"
    else:
        name = "Waning Crescent"
    return name, illum, round(cycle, 4)


def aqi_label(aqi: int | None) -> str:
    if aqi is None:
        return "—"
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Fair"
    if aqi <= 150:
        return "Mod"
    return "Poor"


@dataclass
class HourlyPoint:
    label: str
    temp_c: int
    temp_f: int


@dataclass
class DailyForecast:
    date_iso: str
    day_label: str
    icon_key: str
    condition: str
    high_c: int
    high_f: int
    low_c: int
    low_f: int


@dataclass
class WeatherData:
    location_name: str
    temp_c: int
    temp_f: int
    temp_c_exact: float
    temp_f_exact: float
    feels_c: int
    feels_f: int
    high_c: int
    high_f: int
    low_c: int
    low_f: int
    humidity: int
    wind_kmh: int
    wind_mph: int
    condition: str
    icon_key: str
    is_day: bool
    sunrise: str
    sunset: str
    us_aqi: int | None = None
    aqi_status: str = "Good"
    uv_index: float = 0.0
    moon_name: str = "Waxing Crescent"
    moon_illum: int = 12
    moon_cycle: float = 0.1
    hourly: list[HourlyPoint] = field(default_factory=list)
    forecast: list[DailyForecast] = field(default_factory=list)
    fetched_at_epoch: float = 0.0
    stale: bool = False


WMO_MAP: dict[int, tuple[str, str, str]] = {
    0: ("Clear Sky", "sun", "moon_stars"),
    1: ("Mostly Clear", "sun", "moon_stars"),
    2: ("Partly Cloudy", "partly_cloudy", "cloud_night"),
    3: ("Overcast", "cloudy", "cloudy"),
    45: ("Soft Fog", "fog", "fog"),
    48: ("Rime Fog", "fog", "fog"),
    51: ("Light Drizzle", "drizzle", "drizzle"),
    53: ("Drizzle", "drizzle", "drizzle"),
    55: ("Dense Drizzle", "rain", "rain"),
    56: ("Freezing Drizzle", "rain", "rain"),
    57: ("Freezing Drizzle", "rain", "rain"),
    61: ("Light Rain", "rain", "rain"),
    63: ("Steady Rain", "rain", "rain"),
    65: ("Heavy Rain", "rain", "rain"),
    66: ("Freezing Rain", "rain", "rain"),
    67: ("Freezing Rain", "rain", "rain"),
    71: ("Light Snow", "snow", "snow"),
    73: ("Snowfall", "snow", "snow"),
    75: ("Heavy Snow", "snow", "snow"),
    77: ("Snow Grains", "snow", "snow"),
    80: ("Rain Showers", "rain", "rain"),
    81: ("Rain Showers", "rain", "rain"),
    82: ("Heavy Showers", "storm", "storm"),
    85: ("Snow Showers", "snow", "snow"),
    86: ("Snow Showers", "snow", "snow"),
    95: ("Thunderstorm", "storm", "storm"),
    96: ("Storm & Hail", "storm", "storm"),
    99: ("Thunderstorm", "storm", "storm"),
}


def decode_wmo(code: int, is_day: bool = True) -> tuple[str, str]:
    label, day_icon, night_icon = WMO_MAP.get(code, ("Fair", "partly_cloudy", "cloud_night"))
    return label, (day_icon if is_day else night_icon)


def _format_iso_clock(iso_str: str, use_24h: bool = False) -> str:
    try:
        dt = datetime.fromisoformat(iso_str)
        if use_24h:
            return dt.strftime("%H:%M")
        return dt.strftime("%-I:%M %p")
    except Exception:
        return iso_str[-5:]


def _format_iso_hour_short(iso_str: str, use_24h: bool = False) -> str:
    try:
        dt = datetime.fromisoformat(iso_str)
        if use_24h:
            return dt.strftime("%H:00")
        return dt.strftime("%-I %p")
    except Exception:
        return iso_str[-5:]


def fetch_weather(
    latitude: float = 34.1478,
    longitude: float = -118.1445,
    timezone: str = "America/Los_Angeles",
    location_name: str = "Pasadena, California",
    cache_path: Path | None = None,
    refresh_minutes: int = 15,
    use_24h: bool = False,
) -> WeatherData:
    """Fetch Pasadena weather + 12h curve + AQI/UV from Open-Meteo with local disk caching."""
    now = time.time()
    moon_name, moon_illum, moon_cycle = compute_moon_phase(now)

    if cache_path and cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            age = now - float(cached.get("fetched_at_epoch", 0))
            if age < refresh_minutes * 60 and cached.get("hourly"):
                w = _dict_to_weather(cached, stale=False)
                w.moon_name, w.moon_illum, w.moon_cycle = moon_name, moon_illum, moon_cycle
                return w
        except Exception:
            pass

    params = {
        "latitude": f"{latitude:.4f}",
        "longitude": f"{longitude:.4f}",
        "current": ",".join(
            [
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "is_day",
                "weather_code",
                "wind_speed_10m",
            ]
        ),
        "hourly": "temperature_2m",
        "daily": ",".join(
            [
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "sunrise",
                "sunset",
            ]
        ),
        "timezone": timezone,
        "forecast_days": "5",
    }
    url = f"https://api.open-meteo.com/v1/forecast?{urlencode(params)}"

    aq_params = {
        "latitude": f"{latitude:.4f}",
        "longitude": f"{longitude:.4f}",
        "current": "us_aqi,uv_index",
        "timezone": timezone,
    }
    aq_url = f"https://air-quality-api.open-meteo.com/v1/air-quality?{urlencode(aq_params)}"

    try:
        req = Request(url, headers={"User-Agent": "KindleZenDashboard/2.0"})
        with urlopen(req, timeout=10) as resp:
            payload: dict[str, Any] = json.loads(resp.read().decode("utf-8"))

        us_aqi_val: int | None = None
        uv_val: float = 0.0
        try:
            aq_req = Request(aq_url, headers={"User-Agent": "KindleZenDashboard/2.0"})
            with urlopen(aq_req, timeout=6) as aq_resp:
                aq_data = json.loads(aq_resp.read().decode("utf-8")).get("current", {})
                if aq_data.get("us_aqi") is not None:
                    us_aqi_val = int(round(float(aq_data["us_aqi"])))
                if aq_data.get("uv_index") is not None:
                    uv_val = round(float(aq_data["uv_index"]), 1)
        except Exception:
            pass

        cur = payload["current"]
        daily = payload["daily"]
        hourly_block = payload.get("hourly", {})

        temp_c_val = float(cur["temperature_2m"])
        feels_c_val = float(cur["apparent_temperature"])
        is_day = bool(int(cur.get("is_day", 1)))
        wmo = int(cur.get("weather_code", 0))
        condition, icon_key = decode_wmo(wmo, is_day=is_day)

        wind_kmh_val = float(cur.get("wind_speed_10m", 0.0))
        wind_mph_val = wind_kmh_val * 0.621371

        high_c_0 = float(daily["temperature_2m_max"][0])
        low_c_0 = float(daily["temperature_2m_min"][0])
        sunrise_str = _format_iso_clock(daily["sunrise"][0], use_24h=use_24h)
        sunset_str = _format_iso_clock(daily["sunset"][0], use_24h=use_24h)

        # Build 5 checkpoints across next 12 hours (NOW, +3h, +6h, +9h, +12h)
        hourly_points: list[HourlyPoint] = []
        h_times: list[str] = hourly_block.get("time", [])
        h_temps: list[float] = hourly_block.get("temperature_2m", [])
        cur_hour_prefix = str(cur.get("time", ""))[:13]
        start_idx = 0
        for i, ht in enumerate(h_times):
            if ht.startswith(cur_hour_prefix):
                start_idx = i
                break

        for step_num, step in enumerate((0, 3, 6, 9, 12)):
            idx = start_idx + step
            if idx < len(h_times) and idx < len(h_temps):
                tc = temp_c_val if step_num == 0 else float(h_temps[idx])
                lbl = "NOW" if step_num == 0 else _format_iso_hour_short(h_times[idx], use_24h=use_24h)
                hourly_points.append(
                    HourlyPoint(
                        label=lbl,
                        temp_c=round(tc),
                        temp_f=round(c_to_f(tc)),
                    )
                )

        forecast_items: list[DailyForecast] = []
        dates = daily["time"]
        indices = [1, 2, 3, 4] if len(dates) >= 5 else list(range(min(4, len(dates))))
        for idx in indices:
            d_iso = dates[idx]
            dt_day = datetime.fromisoformat(d_iso)
            day_label = dt_day.strftime("%a").upper()
            d_wmo = int(daily["weather_code"][idx])
            d_cond, d_icon = decode_wmo(d_wmo, is_day=True)
            hc = float(daily["temperature_2m_max"][idx])
            lc = float(daily["temperature_2m_min"][idx])
            forecast_items.append(
                DailyForecast(
                    date_iso=d_iso,
                    day_label=day_label,
                    icon_key=d_icon,
                    condition=d_cond,
                    high_c=round(hc),
                    high_f=round(c_to_f(hc)),
                    low_c=round(lc),
                    low_f=round(c_to_f(lc)),
                )
            )

        data = WeatherData(
            location_name=location_name,
            temp_c=round(temp_c_val),
            temp_f=round(c_to_f(temp_c_val)),
            temp_c_exact=round(temp_c_val, 1),
            temp_f_exact=round(c_to_f(temp_c_val), 1),
            feels_c=round(feels_c_val),
            feels_f=round(c_to_f(feels_c_val)),
            high_c=round(high_c_0),
            high_f=round(c_to_f(high_c_0)),
            low_c=round(low_c_0),
            low_f=round(c_to_f(low_c_0)),
            humidity=int(round(float(cur.get("relative_humidity_2m", 0)))),
            wind_kmh=round(wind_kmh_val),
            wind_mph=round(wind_mph_val),
            condition=condition,
            icon_key=icon_key,
            is_day=is_day,
            sunrise=sunrise_str,
            sunset=sunset_str,
            us_aqi=us_aqi_val,
            aqi_status=aqi_label(us_aqi_val),
            uv_index=uv_val,
            moon_name=moon_name,
            moon_illum=moon_illum,
            moon_cycle=moon_cycle,
            hourly=hourly_points,
            forecast=forecast_items,
            fetched_at_epoch=now,
            stale=False,
        )

        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(asdict(data), indent=2), encoding="utf-8")

        return data
    except Exception:
        if cache_path and cache_path.exists():
            try:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
                w = _dict_to_weather(cached, stale=True)
                w.moon_name, w.moon_illum, w.moon_cycle = moon_name, moon_illum, moon_cycle
                return w
            except Exception:
                pass
        return WeatherData(
            location_name=location_name,
            temp_c=22,
            temp_f=72,
            temp_c_exact=22.0,
            temp_f_exact=71.6,
            feels_c=22,
            feels_f=72,
            high_c=25,
            high_f=77,
            low_c=12,
            low_f=54,
            humidity=40,
            wind_kmh=8,
            wind_mph=5,
            condition="Offline · Cached",
            icon_key="partly_cloudy",
            is_day=True,
            sunrise="6:25 AM",
            sunset="4:55 PM",
            us_aqi=35,
            aqi_status="Good",
            uv_index=2.0,
            moon_name=moon_name,
            moon_illum=moon_illum,
            moon_cycle=moon_cycle,
            hourly=[],
            forecast=[],
            fetched_at_epoch=now,
            stale=True,
        )


def _dict_to_weather(raw: dict[str, Any], stale: bool) -> WeatherData:
    fc = [DailyForecast(**item) for item in raw.get("forecast", [])]
    hr = [HourlyPoint(**item) for item in raw.get("hourly", [])]
    copy = dict(raw)
    copy["forecast"] = fc
    copy["hourly"] = hr
    copy["stale"] = stale
    return WeatherData(**copy)
