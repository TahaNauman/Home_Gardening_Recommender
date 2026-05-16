# helpers.py
# Small utility functions used across the project.
# Nothing domain-specific here — just handy tools.

def get_score_label(score: float) -> dict:
    """
    Takes a numeric score (0-100) and returns a display label,
    emoji, and colour for use in the Streamlit UI.

    Example:
        get_score_label(85) → {"label": "Excellent", "emoji": "🟢", "color": "green"}
    """
    if score >= 80:
        return {"label": "Excellent",  "emoji": "🟢", "color": "green",  "advice": "Plant now!"}
    elif score >= 60:
        return {"label": "Good",       "emoji": "🟡", "color": "orange", "advice": "Suitable with some care."}
    elif score >= 40:
        return {"label": "Marginal",   "emoji": "🟠", "color": "orange", "advice": "Possible but challenging."}
    else:
        return {"label": "Avoid",      "emoji": "🔴", "color": "red",    "advice": "Not recommended this season."}


def get_current_month() -> int:
    """Returns the current month as an integer (1 = January, 12 = December)."""
    from datetime import datetime
    return datetime.now().month


def celsius_to_feel(temp_c: float) -> str:
    """Converts a temperature to a human-friendly description for Karachi gardeners."""
    if temp_c < 15:
        return "Cold"
    elif temp_c < 25:
        return "Cool & Pleasant"
    elif temp_c < 33:
        return "Warm"
    elif temp_c < 40:
        return "Hot"
    else:
        return "Extreme Heat"
