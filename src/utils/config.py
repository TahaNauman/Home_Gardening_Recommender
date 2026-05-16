# config.py
# Central place for all settings and constants.
# If you need to change a threshold or weight, you change it HERE — not scattered across files.

import os
from dotenv import load_dotenv

# This reads your .env file and makes the keys available via os.getenv()
load_dotenv()

# ── API ──────────────────────────────────────────────────────────────────────
OWM_API_KEY = os.getenv("OWM_API_KEY")          # OpenWeatherMap key
CITY_NAME   = "Karachi,PK"                       # City query string for the API

# ── Caching ──────────────────────────────────────────────────────────────────
WEATHER_CACHE_PATH    = "data/.weather_cache.json"
WEATHER_CACHE_MINUTES = 30  # How long before we fetch fresh weather data

# ── Scoring weights (must sum to 1.0) ────────────────────────────────────────
# These control how much each factor influences the final vegetable score.
# Temperature matters most because extreme heat/cold outright kills plants.
WEIGHT_TEMP     = 0.40
WEIGHT_HUMIDITY = 0.25
WEIGHT_SEASON   = 0.20
WEIGHT_SPACE    = 0.10
WEIGHT_WATER    = 0.05

# ── Score bands ───────────────────────────────────────────────────────────────
# These define the label shown on each vegetable card.
SCORE_EXCELLENT = 80   # Green  — plant now
SCORE_GOOD      = 60   # Yellow — suitable with care
SCORE_MARGINAL  = 40   # Orange — possible but challenging
# Below 40    → Red   — avoid this season

# ── Data paths ───────────────────────────────────────────────────────────────
VEG_DATA_PATH     = "data/vegetables.csv"
SEASONS_DATA_PATH = "data/karachi_seasons.csv"
