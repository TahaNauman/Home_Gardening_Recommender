# scorer.py
# This is the core of the recommendation system.
# It takes a vegetable, the current weather, and the user's preferences,
# and returns a suitability score from 0 to 100.
#
# Think of it like a judge scoring a contestant on 5 criteria:
#   1. Temperature fit   (40 points) — most important, extremes kill plants
#   2. Humidity fit      (25 points) — affects disease and growth
#   3. Season/month fit  (20 points) — Karachi-specific planting calendar
#   4. Space fit         (10 points) — does the plant suit pots/rooftop/ground
#   5. Water fit         ( 5 points) — does watering need match user's habit

import pandas as pd
from datetime import datetime
from src.utils.config import (
    WEIGHT_TEMP, WEIGHT_HUMIDITY, WEIGHT_SEASON,
    WEIGHT_SPACE, WEIGHT_WATER
)


# ── Helper: Temperature fit ───────────────────────────────────────────────────

def temp_fit(veg: dict, temp_c: float) -> float:
    """
    Returns a score between 0.0 and 1.0 based on how well the current
    temperature matches what this vegetable needs.

    - If temp is inside the vegetable's min–max range:
        Score is 1.0 at the optimal temp, dropping toward 0.5 at the edges.
    - If temp is outside the range:
        Score drops quickly — extreme heat/cold is genuinely harmful.

    Example:
        Tomato: min=18, max=32, optimal=25
        temp=25 → 1.0 (perfect)
        temp=30 → ~0.67 (warm but okay)
        temp=35 → 0.3  (too hot, outside range)
        temp=40 → 0.0  (will not survive)
    """
    min_t = veg['min_temp_c']
    max_t = veg['max_temp_c']
    opt_t = veg['optimal_temp_c']

    if min_t <= temp_c <= max_t:
        # Inside range: how far from optimal?
        # Range is the distance from optimal to the nearest edge
        half_range = max(opt_t - min_t, max_t - opt_t)
        deviation = abs(temp_c - opt_t) / half_range if half_range > 0 else 0
        return round(1.0 - (deviation * 0.5), 3)  # Max penalty is 0.5 inside range
    else:
        # Outside range: penalise proportionally to how far outside we are
        if temp_c < min_t:
            gap = min_t - temp_c
        else:
            gap = temp_c - max_t
        # Every 5°C outside range loses 0.3 points, floored at 0
        return max(0.0, round(0.3 - (gap / 5) * 0.3, 3))


# ── Helper: Humidity fit ──────────────────────────────────────────────────────

def humidity_fit(veg: dict, humidity_pct: float) -> float:
    """
    Returns 0.0–1.0 based on how well current humidity matches the vegetable.

    - Inside min–max humidity range → 1.0 (perfect)
    - Outside the range → score drops, but not as harshly as temperature
      because humidity affects disease risk more gradually.
    """
    min_h = veg['min_humidity_pct']
    max_h = veg['max_humidity_pct']

    if min_h <= humidity_pct <= max_h:
        return 1.0
    else:
        if humidity_pct < min_h:
            gap = min_h - humidity_pct
        else:
            gap = humidity_pct - max_h
        # Every 10% outside range loses 0.2 points
        return max(0.0, round(1.0 - (gap / 10) * 0.2, 3))


# ── Helper: Season/month fit ──────────────────────────────────────────────────

def season_fit(veg: dict, current_month: int) -> float:
    """
    Returns 1.0 if this month is in the vegetable's recommended planting months.
    Returns 0.0 if this month is in the avoid list.
    Returns 0.4 for months in neither list (possible but not ideal).

    The karachi_months column in the CSV contains comma-separated month numbers.
    Example: "11,12,1,2,3" means November through March.
    """
    # Parse the comma-separated month strings into lists of integers
    good_months  = [int(m.strip()) for m in str(veg['karachi_months']).split(',') if m.strip()]
    avoid_months = [int(m.strip()) for m in str(veg["avoid_months"]).split(",") if m.strip() and m.strip() != "nan"]

    if current_month in good_months:
        return 1.0
    elif current_month in avoid_months:
        return 0.0
    else:
        return 0.4  # Transition month — not ideal but not harmful


# ── Helper: Space fit ─────────────────────────────────────────────────────────

def space_fit(veg: dict, space: str) -> float:
    """
    Returns 0.0–1.0 based on whether the vegetable suits the user's space.

    space options: 'pot', 'rooftop', 'ground'

    - 'pot'     → only pot_friendly plants score 1.0
    - 'rooftop' → rooftop_ok plants score 1.0; pot_friendly gets 0.8
    - 'ground'  → all plants work on the ground, just some better than others
    """
    pot_ok   = str(veg['pot_friendly']).strip().lower() in ('true', '1', 'yes')
    roof_ok  = str(veg['rooftop_ok']).strip().lower()  in ('true', '1', 'yes')

    if space == 'pot':
        return 1.0 if pot_ok else 0.2   # Non-pot plants can technically be forced but not ideal
    elif space == 'rooftop':
        if roof_ok:
            return 1.0
        elif pot_ok:
            return 0.8   # Pot-friendly = usually works on rooftop too
        else:
            return 0.3
    elif space == 'ground':
        return 1.0       # Ground works for everything
    else:
        return 0.5       # Unknown space — neutral score


# ── Helper: Water fit ─────────────────────────────────────────────────────────

def water_fit(veg: dict, watering: str) -> float:
    """
    Returns 0.0–1.0 based on how well the vegetable's water needs match
    the user's watering habits.

    Vegetable water_need:  'high', 'medium', 'low'
    User watering:         'daily', 'alternate', 'weekly'

    Mapping used:
        daily     ≈ high water supply
        alternate ≈ medium water supply
        weekly    ≈ low water supply
    """
    need_map = {'high': 3, 'medium': 2, 'low': 1}
    pref_map = {'daily': 3, 'alternate': 2, 'weekly': 1}

    veg_need  = need_map.get(str(veg['water_need']).strip().lower(), 2)
    user_pref = pref_map.get(str(watering).strip().lower(), 2)

    diff = abs(veg_need - user_pref)

    if diff == 0:
        return 1.0    # Perfect match
    elif diff == 1:
        return 0.6    # One step off — manageable
    else:
        return 0.2    # Two steps off — plant will struggle


# ── Main scoring function ─────────────────────────────────────────────────────

def score_vegetable(veg: dict, weather: dict, user_prefs: dict, current_month: int = None) -> dict:
    """
    Calculates the overall suitability score for one vegetable.

    Parameters:
        veg          : one row from vegetables.csv as a dictionary
        weather      : dict with keys: temp_c, humidity_pct, rain_mm
        user_prefs   : dict with keys: space ('pot'/'rooftop'/'ground'),
                                       sunlight ('full'/'partial'/'shade'),
                                       watering ('daily'/'alternate'/'weekly')
        current_month: int 1–12 (defaults to today's month if not given)

    Returns a dictionary with:
        - name, emoji, score (0–100)
        - breakdown of each sub-score
        - difficulty, days_to_harvest, notes
    """
    if current_month is None:
        current_month = datetime.now().month

    # Calculate each component (all return 0.0–1.0)
    t_fit  = temp_fit(veg, weather['temp_c'])
    h_fit  = humidity_fit(veg, weather['humidity_pct'])
    s_fit  = season_fit(veg, current_month)
    sp_fit = space_fit(veg, user_prefs.get('space', 'ground'))
    w_fit  = water_fit(veg, user_prefs.get('watering', 'alternate'))

    # Weighted total — multiplied by 100 to give a 0–100 score
    total = (
        t_fit  * WEIGHT_TEMP     +
        h_fit  * WEIGHT_HUMIDITY +
        s_fit  * WEIGHT_SEASON   +
        sp_fit * WEIGHT_SPACE    +
        w_fit  * WEIGHT_WATER
    ) * 100

    return {
        'name'           : veg['name'],
        'name_urdu'      : veg['name_urdu'],
        'emoji'          : veg['emoji'],
        'score'          : round(total, 1),
        'breakdown'      : {
            'temperature' : round(t_fit  * WEIGHT_TEMP     * 100, 1),
            'humidity'    : round(h_fit  * WEIGHT_HUMIDITY * 100, 1),
            'season'      : round(s_fit  * WEIGHT_SEASON   * 100, 1),
            'space'       : round(sp_fit * WEIGHT_SPACE    * 100, 1),
            'water'       : round(w_fit  * WEIGHT_WATER    * 100, 1),
        },
        'difficulty'     : veg['difficulty'],
        'days_to_harvest': veg['days_to_harvest'],
        'water_need'     : veg['water_need'],
        'sunlight'       : veg['sunlight'],
        'pot_friendly'   : veg['pot_friendly'],
        'notes'          : veg['notes'],
    }


# ── Score entire dataset ──────────────────────────────────────────────────────

def score_all_vegetables(veg_df: pd.DataFrame, weather: dict, user_prefs: dict, current_month: int = None) -> list:
    """
    Runs score_vegetable() on every row in the vegetables DataFrame.
    Returns a list of result dictionaries, unsorted.

    Usage:
        import pandas as pd
        from src.recommender.scorer import score_all_vegetables

        df = pd.read_csv('data/vegetables.csv')
        weather = {'temp_c': 34, 'humidity_pct': 72, 'rain_mm': 0}
        prefs   = {'space': 'pot', 'sunlight': 'partial', 'watering': 'daily'}
        results = score_all_vegetables(df, weather, prefs)
    """
    if current_month is None:
        current_month = datetime.now().month

    results = []
    for _, row in veg_df.iterrows():
        result = score_vegetable(row.to_dict(), weather, user_prefs, current_month)
        results.append(result)

    return results