# parser.py
# Responsible for ONE thing: taking the messy raw OpenWeatherMap JSON
# and converting it into a clean, simple dictionary that the rest of
# the app can use without knowing anything about the API structure.
#
# Why separate from fetcher.py?
# If we ever switch from OpenWeatherMap to another API (Visual Crossing,
# WeatherAPI, etc.), we only change THIS file. Everything else stays the same.

from src.utils.helpers import celsius_to_feel
from src.utils.config import CITY_NAME


# ── Current weather parser ────────────────────────────────────────────────────

def parse_current_weather(raw: dict) -> dict:
    """
    Converts the raw OpenWeatherMap /weather response into a clean dict.

    Input (raw OWM response has this structure):
    {
        "main": {"temp": 34.2, "feels_like": 38.1, "humidity": 72, ...},
        "weather": [{"description": "haze", "icon": "50d"}],
        "wind": {"speed": 3.2},
        "rain": {"1h": 0.5},   ← only present if it's raining
        "clouds": {"all": 20},
        "dt": 1716800000,       ← Unix timestamp
        "name": "Karachi"
    }

    Output (clean, flat dict used by scorer.py and the Streamlit UI):
    {
        "temp_c"        : 34.2,
        "feels_like_c"  : 38.1,
        "humidity_pct"  : 72,
        "rain_mm"       : 0.5,
        "wind_kmh"      : 11.5,
        "cloud_pct"     : 20,
        "description"   : "Haze",
        "feel_label"    : "Hot",
        "icon_code"     : "50d",
        "city"          : "Karachi",
        "fetched_at"    : "2025-05-16 14:30"
    }
    """
    from datetime import datetime

    main    = raw.get('main', {})
    weather = raw.get('weather', [{}])[0]   # OWM returns a list — we take the first
    wind    = raw.get('wind', {})
    rain    = raw.get('rain', {})
    clouds  = raw.get('clouds', {})

    temp_c = main.get('temp', 0)

    return {
        # Core values used by the scoring engine
        'temp_c'       : round(temp_c, 1),
        'humidity_pct' : main.get('humidity', 0),
        'rain_mm'      : rain.get('1h', 0),           # Rain in last hour (mm)

        # Extra values used by the Streamlit UI
        'feels_like_c' : round(main.get('feels_like', temp_c), 1),
        'wind_kmh'     : round(wind.get('speed', 0) * 3.6, 1),  # m/s → km/h
        'cloud_pct'    : clouds.get('all', 0),
        'description'  : weather.get('description', 'Unknown').title(),
        'feel_label'   : celsius_to_feel(temp_c),
        'icon_code'    : weather.get('icon', '01d'),
        'icon_url'     : f"https://openweathermap.org/img/wn/{weather.get('icon', '01d')}@2x.png",
        'city'         : raw.get('name', CITY_NAME),
        'fetched_at'   : datetime.now().strftime('%Y-%m-%d %H:%M'),
    }


# ── Gardening context ─────────────────────────────────────────────────────────

def get_gardening_context(parsed: dict) -> dict:
    """
    Takes the clean parsed weather and adds gardening-specific commentary.
    This is the layer that translates weather numbers into plain English
    advice for beginner gardeners.

    Returns extra keys to add to the weather card in the UI.
    """
    temp    = parsed['temp_c']
    humid   = parsed['humidity_pct']
    rain    = parsed['rain_mm']

    alerts  = []   # Warning messages to show the user
    tips    = []   # Actionable gardening tips

    # ── Temperature alerts ──────────────────────────────────────────────────
    if temp >= 40:
        alerts.append("🔥 Extreme heat warning — most plants need shade cloth and extra water today")
    elif temp >= 35:
        alerts.append("☀️ Very hot — water your plants in the early morning or after sunset, not midday")
    elif temp <= 12:
        alerts.append("🧊 Unusually cold for Karachi — cover sensitive seedlings overnight")

    # ── Humidity alerts ─────────────────────────────────────────────────────
    if humid >= 85:
        alerts.append("💧 Very high humidity — watch for fungal disease (white powder on leaves)")
        tips.append("Avoid overhead watering today. Water at the base of the plant only.")
    elif humid <= 30:
        alerts.append("🏜️ Very dry air — increase watering frequency today")

    # ── Rain tips ────────────────────────────────────────────────────────────
    if rain > 5:
        tips.append("It has rained recently — skip watering today to avoid root rot.")
    elif rain > 0:
        tips.append("Light rain detected — reduce watering by half today.")

    # ── General seasonal tip ─────────────────────────────────────────────────
    if 25 <= temp <= 32 and 50 <= humid <= 75:
        tips.append("Great growing conditions right now — ideal for most Karachi vegetables.")

    return {
        'alerts' : alerts,
        'tips'   : tips,
        'watering_advice': _watering_advice(temp, rain),
    }


def _watering_advice(temp_c: float, rain_mm: float) -> str:
    """Returns a one-line watering recommendation based on today's conditions."""
    if rain_mm > 5:
        return "Skip watering — recent rainfall is sufficient."
    elif rain_mm > 0:
        return "Water lightly — recent rain has helped."
    elif temp_c >= 38:
        return "Water twice today — morning and evening."
    elif temp_c >= 32:
        return "Water in the morning before 8am."
    else:
        return "Normal watering schedule today."


# ── Forecast parser ───────────────────────────────────────────────────────────

def parse_forecast(raw: dict) -> list:
    """
    Parses the 5-day forecast into a list of daily summaries.
    Groups the 3-hour slots by day and averages the values.

    Returns a list of dicts, one per day:
    [
        {"date": "Mon 20 May", "avg_temp_c": 35, "humidity_pct": 68, "rain_mm": 0},
        ...
    ]
    """
    from collections import defaultdict
    from datetime import datetime

    daily = defaultdict(lambda: {'temps': [], 'humidities': [], 'rain': 0})

    for slot in raw.get('list', []):
        date_str = slot['dt_txt'][:10]   # "2025-05-16 12:00:00" → "2025-05-16"
        daily[date_str]['temps'].append(slot['main']['temp'])
        daily[date_str]['humidities'].append(slot['main']['humidity'])
        daily[date_str]['rain'] += slot.get('rain', {}).get('3h', 0)

    result = []
    for date_str, values in sorted(daily.items()):
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        result.append({
            'date'         : dt.strftime('%a %d %b'),
            'avg_temp_c'   : round(sum(values['temps']) / len(values['temps']), 1),
            'max_temp_c'   : round(max(values['temps']), 1),
            'min_temp_c'   : round(min(values['temps']), 1),
            'humidity_pct' : round(sum(values['humidities']) / len(values['humidities']), 1),
            'rain_mm'      : round(values['rain'], 1),
            'feel_label'   : celsius_to_feel(sum(values['temps']) / len(values['temps']))
        })

    return result