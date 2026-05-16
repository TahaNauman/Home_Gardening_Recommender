# fetcher.py
# Responsible for ONE thing: getting raw weather data from OpenWeatherMap.
#
# Key design decisions:
#   1. Caching — Streamlit reruns your entire script on every button click.
#      Without a cache, you'd burn through your API rate limit in minutes.
#      We save the last fetch to a JSON file and reuse it for 30 minutes.
#
#   2. Separation — this file only FETCHES. Cleaning and interpreting
#      the data happens in parser.py. Keeps each file small and testable.

import os
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
from src.utils.config import (
    OWM_API_KEY,
    CITY_NAME,
    WEATHER_CACHE_PATH,
    WEATHER_CACHE_MINUTES
)


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _load_cache() -> dict | None:
    """
    Reads the cache file. Returns the cached data if it's still fresh,
    or None if the cache is missing or expired.
    """
    cache_file = Path(WEATHER_CACHE_PATH)

    if not cache_file.exists():
        return None  # No cache yet — first run

    try:
        cached = json.loads(cache_file.read_text())
        fetched_at = datetime.fromisoformat(cached['fetched_at'])
        age = datetime.now() - fetched_at

        if age < timedelta(minutes=WEATHER_CACHE_MINUTES):
            print(f"[Weather] Using cached data ({int(age.total_seconds() / 60)}m old)")
            return cached['data']
        else:
            print(f"[Weather] Cache expired ({int(age.total_seconds() / 60)}m old) — fetching fresh data")
            return None

    except (json.JSONDecodeError, KeyError, ValueError):
        # Cache file is corrupted — ignore it and fetch fresh
        return None


def save_cache(data: dict) -> None:
    """Saves fresh weather data to the cache file with a timestamp."""
    cache_file = Path(WEATHER_CACHE_PATH)
    cache_file.parent.mkdir(parents=True, exist_ok=True)  # Make sure data/ folder exists

    payload = {
        'fetched_at': datetime.now().isoformat(),
        'data': data
    }
    cache_file.write_text(json.dumps(payload, indent=2))
    print("[Weather] Fresh data saved to cache")


# ── Current weather ───────────────────────────────────────────────────────────

def fetch_current_weather() -> dict:
    """
    Fetches the current weather for Karachi from OpenWeatherMap.
    Returns the raw API response as a Python dictionary.

    Uses cache if data is less than WEATHER_CACHE_MINUTES old.
    Raises an exception if the API call fails.

    Raw response contains nested data — parser.py will clean this up.
    """
    # Try cache first
    cached = _load_cache()
    if cached:
        return cached

    # Validate API key exists
    if not OWM_API_KEY:
        raise ValueError(
            "OWM_API_KEY is not set. "
            "Copy .env.example to .env and add your OpenWeatherMap API key. "
            "Get a free key at https://openweathermap.org/api"
        )

    # Make the API call
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q"     : CITY_NAME,
        "appid" : OWM_API_KEY,
        "units" : "metric",   # Always metric — we want Celsius
        "lang"  : "en"
    }

    print(f"[Weather] Fetching live data for {CITY_NAME}...")

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # Raises an error for 4xx/5xx responses
    except requests.exceptions.ConnectionError:
        raise ConnectionError("No internet connection. Check your network and try again.")
    except requests.exceptions.Timeout:
        raise TimeoutError("Weather API timed out. Try again in a moment.")
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            raise PermissionError("Invalid API key. Check your OWM_API_KEY in the .env file.")
        elif response.status_code == 404:
            raise ValueError(f"City '{CITY_NAME}' not found by the weather API.")
        else:
            raise RuntimeError(f"Weather API error: {e}")

    raw_data = response.json()
    save_cache(raw_data)

    return raw_data


# ── 5-day forecast ────────────────────────────────────────────────────────────

def fetch_forecast() -> dict:
    """
    Fetches a 5-day / 3-hour forecast for Karachi.
    Returns the raw API response. Used later for showing upcoming planting windows.

    Note: This is NOT cached separately — call sparingly.
    """
    if not OWM_API_KEY:
        raise ValueError("OWM_API_KEY is not set.")

    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {
        "q"     : CITY_NAME,
        "appid" : OWM_API_KEY,
        "units" : "metric",
        "cnt"   : 40   # 40 x 3hr slots = 5 days
    }

    print(f"[Weather] Fetching 5-day forecast for {CITY_NAME}...")

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    return response.json()