# test_weather_parser.py
# Tests the parser using a FAKE API response — no API key needed.
# This is called "mocking" — we simulate what the real API would return.
#
# Run with:  python3 -m pytest tests/ -v
# Or simply: python3 tests/test_weather_parser.py

import sys
sys.path.insert(0, '.')

from src.weather.parser import parse_current_weather, get_gardening_context, parse_forecast

# ── Fake OWM API response (same structure as the real thing) ──────────────────
MOCK_CURRENT = {
    "main": {
        "temp"       : 34.2,
        "feels_like" : 38.5,
        "humidity"   : 72,
        "pressure"   : 1005
    },
    "weather": [{"description": "haze", "icon": "50d"}],
    "wind"   : {"speed": 3.2},
    "rain"   : {},           # No rain
    "clouds" : {"all": 20},
    "name"   : "Karachi",
    "dt"     : 1716800000
}

MOCK_CURRENT_RAINY = {
    "main"   : {"temp": 31.0, "feels_like": 34.0, "humidity": 85},
    "weather": [{"description": "moderate rain", "icon": "10d"}],
    "wind"   : {"speed": 4.5},
    "rain"   : {"1h": 8.2},  # Heavy rain
    "clouds" : {"all": 90},
    "name"   : "Karachi",
    "dt"     : 1716800000
}

MOCK_FORECAST = {
    "list": [
        {"dt_txt": "2025-05-16 06:00:00", "main": {"temp": 30, "humidity": 65}, "rain": {}},
        {"dt_txt": "2025-05-16 09:00:00", "main": {"temp": 34, "humidity": 68}, "rain": {}},
        {"dt_txt": "2025-05-16 12:00:00", "main": {"temp": 38, "humidity": 70}, "rain": {}},
        {"dt_txt": "2025-05-17 06:00:00", "main": {"temp": 32, "humidity": 72}, "rain": {"3h": 2.5}},
        {"dt_txt": "2025-05-17 12:00:00", "main": {"temp": 35, "humidity": 74}, "rain": {}},
    ]
}


def test_parse_current_weather():
    result = parse_current_weather(MOCK_CURRENT)

    assert result['temp_c']        == 34.2,   f"Expected 34.2, got {result['temp_c']}"
    assert result['humidity_pct']  == 72,     f"Expected 72, got {result['humidity_pct']}"
    assert result['rain_mm']       == 0,      f"Expected 0 rain, got {result['rain_mm']}"
    assert result['wind_kmh']      == 11.5,   f"Expected 11.5 km/h, got {result['wind_kmh']}"
    assert result['description']   == 'Haze', f"Expected 'Haze', got {result['description']}"
    assert result['feel_label']    == 'Hot',  f"Expected 'Hot', got {result['feel_label']}"
    assert 'fetched_at' in result

    print("  PASS — parse_current_weather (clear day)")


def test_parse_rainy_weather():
    result = parse_current_weather(MOCK_CURRENT_RAINY)

    assert result['rain_mm']    == 8.2,            f"Expected 8.2mm rain, got {result['rain_mm']}"
    assert result['description'] == 'Moderate Rain', f"Got {result['description']}"

    print("  PASS — parse_current_weather (rainy day)")


def test_gardening_context_extreme_heat():
    parsed = parse_current_weather({'main': {'temp': 41, 'feels_like': 44, 'humidity': 50},
                                    'weather': [{'description': 'clear', 'icon': '01d'}],
                                    'wind': {}, 'rain': {}, 'clouds': {'all': 0}, 'name': 'Karachi'})
    ctx = get_gardening_context(parsed)

    assert len(ctx['alerts']) > 0, "Should have a heat warning"
    assert any('Extreme heat' in a for a in ctx['alerts']), f"Got alerts: {ctx['alerts']}"
    assert 'twice' in ctx['watering_advice'], f"Should suggest twice daily watering, got: {ctx['watering_advice']}"

    print("  PASS — gardening_context extreme heat alerts")


def test_gardening_context_rain():
    parsed = parse_current_weather(MOCK_CURRENT_RAINY)
    ctx    = get_gardening_context(parsed)

    assert 'Skip watering' in ctx['watering_advice'], f"Got: {ctx['watering_advice']}"
    assert len(ctx['tips']) > 0, "Should have tips for rainy day"

    print("  PASS — gardening_context rainy day tips")


def test_parse_forecast():
    result = parse_forecast(MOCK_FORECAST)

    assert len(result) == 2, f"Expected 2 days, got {len(result)}"

    day1 = result[0]
    assert day1['avg_temp_c'] == 34.0, f"Expected 34.0, got {day1['avg_temp_c']}"
    assert day1['rain_mm']    == 0,    f"Expected 0mm rain, got {day1['rain_mm']}"

    day2 = result[1]
    assert day2['rain_mm']    == 2.5,  f"Expected 2.5mm, got {day2['rain_mm']}"

    print("  PASS — parse_forecast daily grouping")


if __name__ == '__main__':
    print("\nRunning weather parser tests...\n")
    test_parse_current_weather()
    test_parse_rainy_weather()
    test_gardening_context_extreme_heat()
    test_gardening_context_rain()
    test_parse_forecast()
    print("\nAll tests passed!")