# test_integration.py
# End-to-end test that simulates what the dashboard will do:
#   1. Load the vegetable dataset
#   2. Get weather (mocked)
#   3. Parse it
#   4. Score all vegetables
#   5. Rank them
#   6. Print results like the UI would show them
#
# Run with: python tests/test_integration.py

import sys, os
sys.path.insert(0, '.')

import pandas as pd
from src.weather.parser import parse_current_weather, get_gardening_context
from src.recommender.scorer import score_all_vegetables
from src.recommender.ranker import rank_results
from src.utils.helpers import get_score_label, get_current_month

# ── Mock weather scenarios ────────────────────────────────────────────────────
SCENARIOS = {
    "May — Peak Summer (38°C, humid)": {
        "raw_weather": {
            "main"   : {"temp": 38.0, "feels_like": 42.0, "humidity": 68},
            "weather": [{"description": "haze", "icon": "50d"}],
            "wind"   : {"speed": 2.5}, "rain": {}, "clouds": {"all": 10},
            "name"   : "Karachi"
        },
        "month": 5,
        "prefs": {"space": "rooftop", "sunlight": "full", "watering": "daily"}
    },
    "December — Cool Season (22°C, dry)": {
        "raw_weather": {
            "main"   : {"temp": 22.0, "feels_like": 21.0, "humidity": 65},
            "weather": [{"description": "clear sky", "icon": "01d"}],
            "wind"   : {"speed": 1.5}, "rain": {}, "clouds": {"all": 5},
            "name"   : "Karachi"
        },
        "month": 12,
        "prefs": {"space": "pot", "sunlight": "full", "watering": "alternate"}
    },
    "August — Monsoon (31°C, very humid)": {
        "raw_weather": {
            "main"   : {"temp": 31.0, "feels_like": 35.0, "humidity": 84},
            "weather": [{"description": "moderate rain", "icon": "10d"}],
            "wind"   : {"speed": 4.0}, "rain": {"1h": 6.5}, "clouds": {"all": 85},
            "name"   : "Karachi"
        },
        "month": 8,
        "prefs": {"space": "ground", "sunlight": "partial", "watering": "alternate"}
    }
}

# ── Load dataset ──────────────────────────────────────────────────────────────
def load_data():
    path = "data/vegetables.csv"
    assert os.path.exists(path), f"Missing file: {path} — make sure you're running from the project root"
    df = pd.read_csv(path)
    assert len(df) >= 25, f"Expected at least 25 vegetables, found {len(df)}"
    print(f"  Loaded {len(df)} vegetables from dataset\n")
    return df

# ── Run one scenario ──────────────────────────────────────────────────────────
def run_scenario(name, scenario, df):
    print("=" * 62)
    print(f"  {name}")
    print(f"  Space: {scenario['prefs']['space']} | "
          f"Sun: {scenario['prefs']['sunlight']} | "
          f"Water: {scenario['prefs']['watering']}")
    print("=" * 62)

    # Step 1: Parse weather
    weather = parse_current_weather(scenario['raw_weather'])
    ctx     = get_gardening_context(weather)

    print(f"\n  Weather: {weather['temp_c']}°C | "
          f"{weather['humidity_pct']}% humidity | "
          f"{weather['rain_mm']}mm rain | "
          f"{weather['description']}")
    print(f"  Feel   : {weather['feel_label']}")
    print(f"  Watering advice: {ctx['watering_advice']}")

    if ctx['alerts']:
        for alert in ctx['alerts']:
            print(f"  Alert  : {alert}")

    # Step 2: Score all vegetables
    results = score_all_vegetables(df, weather, scenario['prefs'], scenario['month'])

    # Step 3: Rank them
    ranked = rank_results(results)

    # Step 4: Display top picks
    print(f"\n  ✅ TOP PICKS ({len(ranked['recommended'])} recommended):")
    for v in ranked['recommended'][:6]:
        bar   = "█" * int(v['score'] / 5)
        label = get_score_label(v['score'])
        print(f"     {v['emoji']} {v['name']:<16} {v['score']:>5}/100  {bar}  [{label['label']}]")

    if ranked['borderline']:
        print(f"\n  🟡 BORDERLINE ({len(ranked['borderline'])} vegetables):")
        for v in ranked['borderline'][:3]:
            print(f"     {v['emoji']} {v['name']:<16} {v['score']:>5}/100")

    print(f"\n  🔴 AVOID ({len(ranked['avoid'])} vegetables):")
    for v in ranked['avoid'][:4]:
        print(f"     {v['emoji']} {v['name']:<16} {v['score']:>5}/100")

    # Step 5: Validate score breakdown adds up
    top = ranked['recommended'][0] if ranked['recommended'] else None
    if top:
        bd    = top['breakdown']
        total = sum(bd.values())
        assert abs(total - top['score']) < 0.5, \
            f"Breakdown sum {total} doesn't match score {top['score']}"
        print(f"\n  Score breakdown check passed for {top['emoji']} {top['name']} ✓")

    return ranked

# ── Assertions ────────────────────────────────────────────────────────────────
def validate_results(scenario_name, ranked, month):
    """Check that results make real-world sense for Karachi."""
    recommended_names = [v['name'] for v in ranked['recommended']]
    avoid_names       = [v['name'] for v in ranked['avoid']]

    if month == 5:  # May — only heat crops should score well
        assert 'Okra' in recommended_names, \
            "Okra should be recommended in May — it's the classic Karachi summer crop"
        assert 'Peas' in avoid_names or 'Cauliflower' in avoid_names, \
            "Cool-season crops like Peas/Cauliflower should be avoided in May"

    if month == 12:  # December — cool crops should dominate
        assert 'Tomato' in recommended_names or 'Spinach' in recommended_names, \
            "Tomato or Spinach should be recommended in December"
        assert 'Okra' in avoid_names or 'Bitter Gourd' in avoid_names, \
            "Heat crops like Okra/Bitter Gourd should be avoided in December"

    if month == 8:  # August — monsoon crops only
        assert 'Okra' in recommended_names, \
            "Okra should be recommended in August monsoon season"

    # No score should exceed 100 or go below 0
    for v in ranked['all_sorted']:
        assert 0 <= v['score'] <= 100, \
            f"{v['name']} has invalid score: {v['score']}"

    print(f"  Real-world validation passed ✓")

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("\n" + "━" * 62)
    print("  KARACHI GARDENING ASSISTANT — INTEGRATION TEST")
    print("━" * 62 + "\n")

    print("Loading dataset...")
    df = load_data()

    all_passed = True
    for scenario_name, scenario in SCENARIOS.items():
        try:
            ranked = run_scenario(scenario_name, scenario, df)
            validate_results(scenario_name, ranked, scenario['month'])
            print()
        except AssertionError as e:
            print(f"\n  ❌ FAILED: {e}\n")
            all_passed = False

    print("━" * 62)
    if all_passed:
        print("  ALL INTEGRATION TESTS PASSED ✅")
        print("  The scoring engine, weather parser, and ranker")
        print("  are all working correctly together.")
    else:
        print("  SOME TESTS FAILED ❌ — see above for details")
    print("━" * 62 + "\n")