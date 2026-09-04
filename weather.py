"""Tiny wttr.in client for the Tbilisi weather widget on the client list page.

Renders as native themed HTML (via list.html) rather than embedding wttr.in's
PNG output, since that image is a fixed low pixel size (blurry on high-DPI
screens) baked with ANSI terminal colors that can't follow the site's
light/dark theme. Fetching the JSON and rendering our own markup fixes both,
and also lets a failed/offline fetch simply omit the widget instead of
showing a broken-image icon.
"""
import json
import time
import urllib.error
import urllib.request
from threading import Lock
from typing import Optional

LOCATION = "Tbilisi"
WTTR_URL = f"https://wttr.in/{LOCATION}?format=j1&lang=ru"
REQUEST_TIMEOUT_SECONDS = 4
CACHE_TTL_SECONDS = 1800  # 30 minutes -- plenty fresh for a "today" widget.

# Rough grouping of WWO/wttr.in weatherCode values to a representative emoji.
_ICONS_BY_CODE = {
    "113": "☀️",
    "116": "⛅", "119": "☁️", "122": "☁️",
    "143": "🌫️", "248": "🌫️", "260": "🌫️",
    "176": "🌦️", "263": "🌦️", "266": "🌦️", "293": "🌦️", "296": "🌦️",
    "353": "🌦️",
    "299": "🌧️", "302": "🌧️", "305": "🌧️", "308": "🌧️", "356": "🌧️", "359": "🌧️",
    "179": "🌨️", "182": "🌨️", "185": "🌨️", "281": "🌨️", "284": "🌨️",
    "311": "🌨️", "314": "🌨️", "317": "🌨️", "350": "🌨️", "362": "🌨️", "365": "🌨️",
    "227": "❄️", "230": "❄️", "320": "❄️", "323": "❄️", "326": "❄️", "329": "❄️",
    "332": "❄️", "335": "❄️", "338": "❄️", "368": "❄️", "371": "❄️", "374": "❄️", "377": "❄️",
    "200": "⛈️", "386": "⛈️", "389": "⛈️", "392": "⛈️", "395": "⛈️",
}
_DEFAULT_ICON = "🌡️"

_lock = Lock()
_cache = {"data": None, "fetched_at": 0.0}


def _icon_for_code(code: Optional[str]) -> str:
    return _ICONS_BY_CODE.get(code, _DEFAULT_ICON)


def _parse(payload: dict) -> dict:
    current = payload["current_condition"][0]
    today = payload["weather"][0]
    desc = current.get("lang_ru") or current.get("weatherDesc") or [{"value": ""}]

    return {
        "temp_c": current["temp_C"],
        "feels_like_c": current["FeelsLikeC"],
        "description": desc[0]["value"].strip(),
        "icon": _icon_for_code(current.get("weatherCode")),
        "wind_kmph": current["windspeedKmph"],
        "humidity": current["humidity"],
        "max_temp_c": today["maxtempC"],
        "min_temp_c": today["mintempC"],
    }


def _fetch_fresh() -> Optional[dict]:
    try:
        req = urllib.request.Request(WTTR_URL, headers={"User-Agent": "curl/8.0"})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return _parse(payload)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError, IndexError):
        # No internet, wttr.in unreachable/slow, or an unexpected response shape --
        # any of these should just result in the widget being omitted, not a 500.
        return None


def get_tbilisi_weather() -> Optional[dict]:
    """Returns a small dict of today's Tbilisi conditions, or None if unavailable
    (no internet, wttr.in down, timeout, etc.) -- callers should omit the widget
    entirely in that case rather than showing a broken/empty widget."""
    with _lock:
        cached = _cache["data"]
        if cached is not None and (time.time() - _cache["fetched_at"]) < CACHE_TTL_SECONDS:
            return cached

    fresh = _fetch_fresh()

    with _lock:
        if fresh is not None:
            _cache["data"] = fresh
            _cache["fetched_at"] = time.time()
            return fresh
        # Fetch failed: serve a still-cached value if we have one (better than
        # nothing), otherwise stay None so the widget is omitted.
        return _cache["data"]
