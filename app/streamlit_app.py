# streamlit_app.py
# The main dashboard for the Karachi Gardening Assistant.
# Run with: streamlit run app/streamlit_app.py
#
# Layout:
#   Sidebar  — user inputs (space, sunlight, watering)
#   Main     — weather card, top picks, avoid list, score chart

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from src.weather.parser import parse_current_weather, get_gardening_context
from src.recommender.scorer import score_all_vegetables
from src.recommender.ranker import rank_results
from src.utils.helpers import get_score_label, get_current_month

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Karachi Garden Guide",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main background and base text colour */
    .stApp { background-color: #f8faf5; color: #1a1a1a; }
    .stMarkdown, .stMarkdown p, .stMarkdown li,
    .stMarkdown span, .element-container { color: #1a1a1a; }
    h1, h2, h3, h4 { color: #1a3a1a !important; }

    /* Sidebar — light text on dark green */
    [data-testid="stSidebar"] { background-color: #1a3a1a; }
    [data-testid="stSidebar"] * { color: #e8f5e8 !important; }
    [data-testid="stSidebar"] label { color: #a8d5a8 !important; }
    /* Dropdown popup — force white background, dark text */
    [data-baseweb="popover"] { background-color: #ffffff !important; }
    [data-baseweb="popover"] * { color: #1a1a1a !important; background-color: transparent !important; }
    [data-baseweb="menu"] { background-color: #ffffff !important; }
    [data-baseweb="menu"] li { color: #1a1a1a !important; background-color: #ffffff !important; }
    [data-baseweb="menu"] li:hover { background-color: #e8f5e8 !important; color: #1a3a1a !important; }
    [data-baseweb="select"] div { color: #1a1a1a !important; }
    ul[role="listbox"] { background-color: #ffffff !important; }
    ul[role="listbox"] li { color: #1a1a1a !important; }
    ul[role="listbox"] li:hover { background-color: #e8f5e8 !important; }
    /* Expander header */
    details summary p { color: #1a3a1a !important; font-weight: 600; }

    /* Vegetable cards */
    .veg-card {
        background: white;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        border-left: 5px solid #2d7a2d;
        box-shadow: 0 2px 8px rgba(0,0,0,0.07);
    }
    .veg-card.avoid {
        border-left-color: #c0392b;
    }
    .veg-card.borderline {
        border-left-color: #e67e22;
    }

    /* Score badge */
    .score-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.85em;
    }
    .badge-excellent { background: #d4edda; color: #155724; }
    .badge-good      { background: #fff3cd; color: #856404; }
    .badge-marginal  { background: #ffe5d0; color: #7d3c0a; }
    .badge-avoid     { background: #f8d7da; color: #721c24; }

    /* Weather card */
    .weather-card {
        background: linear-gradient(135deg, #1a3a1a, #2d7a2d);
        border-radius: 14px;
        padding: 20px 24px;
        color: white;
        margin-bottom: 20px;
    }
    .weather-temp { font-size: 3em; font-weight: bold; color: white; }
    .weather-label { font-size: 1em; color: #b8e0b8; }

    /* Section headers */
    .section-header {
        font-size: 1.2em;
        font-weight: 700;
        color: #1a3a1a;
        padding: 8px 0 4px 0;
        border-bottom: 2px solid #2d7a2d;
        margin-bottom: 12px;
    }

    /* Alert box */
    .alert-box {
        background: #fff8e1;
        border-left: 4px solid #f39c12;
        border-radius: 6px;
        padding: 10px 14px;
        margin-bottom: 8px;
        color: #7d5a00;
        font-size: 0.9em;
    }
    .tip-box {
        background: #e8f5e9;
        border-left: 4px solid #2d7a2d;
        border-radius: 6px;
        padding: 10px 14px;
        margin-bottom: 8px;
        color: #1a3a1a;
        font-size: 0.9em;
    }

    /* Difficulty pill */
    .pill {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.75em;
        font-weight: 600;
        margin-left: 6px;
    }
    .pill-easy   { background: #d4edda; color: #155724; }
    .pill-medium { background: #fff3cd; color: #856404; }
    .pill-hard   { background: #f8d7da; color: #721c24; }

    /* Hide streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ── Mock weather (used until API key is added) ────────────────────────────────
def get_mock_weather(month: int) -> dict:
    """Returns realistic mock weather based on the current month."""
    monthly = {
        1:  {"temp": 20, "humidity": 68, "rain": 0,   "description": "Clear Sky",    "icon": "01d"},
        2:  {"temp": 22, "humidity": 65, "rain": 0,   "description": "Clear Sky",    "icon": "01d"},
        3:  {"temp": 28, "humidity": 65, "rain": 0,   "description": "Partly Cloudy","icon": "02d"},
        4:  {"temp": 32, "humidity": 68, "rain": 0,   "description": "Haze",         "icon": "50d"},
        5:  {"temp": 36, "humidity": 68, "rain": 0,   "description": "Haze",         "icon": "50d"},
        6:  {"temp": 36, "humidity": 72, "rain": 0,   "description": "Hot & Hazy",   "icon": "50d"},
        7:  {"temp": 33, "humidity": 80, "rain": 4,   "description": "Light Rain",   "icon": "10d"},
        8:  {"temp": 31, "humidity": 84, "rain": 7,   "description": "Moderate Rain","icon": "10d"},
        9:  {"temp": 31, "humidity": 78, "rain": 2,   "description": "Partly Cloudy","icon": "02d"},
        10: {"temp": 30, "humidity": 68, "rain": 0,   "description": "Partly Cloudy","icon": "02d"},
        11: {"temp": 24, "humidity": 62, "rain": 0,   "description": "Clear Sky",    "icon": "01d"},
        12: {"temp": 20, "humidity": 65, "rain": 0,   "description": "Clear Sky",    "icon": "01d"},
    }
    m = monthly[month]
    return {
        "main"   : {"temp": m["temp"], "feels_like": m["temp"] + 2, "humidity": m["humidity"]},
        "weather": [{"description": m["description"], "icon": m["icon"]}],
        "wind"   : {"speed": 2.0},
        "rain"   : {"1h": m["rain"]} if m["rain"] > 0 else {},
        "clouds" : {"all": 20},
        "name"   : "Karachi"
    }


# ── Load dataset (cached so it only reads CSV once) ───────────────────────────
@st.cache_data
def load_vegetables():
    path = os.path.join(os.path.dirname(__file__), '..', 'data', 'vegetables.csv')
    return pd.read_csv(path)


# ── Render one vegetable card ─────────────────────────────────────────────────
def render_veg_card(veg: dict, card_type: str = "recommend"):
    label    = get_score_label(veg['score'])
    badge_cls = {
        "Excellent": "badge-excellent",
        "Good"     : "badge-good",
        "Marginal" : "badge-marginal",
        "Avoid"    : "badge-avoid"
    }.get(label['label'], "badge-good")

    pill_cls = f"pill-{veg['difficulty']}"
    card_cls = {"recommend": "", "borderline": "borderline", "avoid": "avoid"}.get(card_type, "")

    bd = veg['breakdown']

    st.markdown(f"""
    <div class="veg-card {card_cls}">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <span style="font-size:1.6em">{veg['emoji']}</span>
                <strong style="font-size:1.05em; margin-left:8px;">{veg['name']}</strong>
                <span style="color:#888; margin-left:6px; font-size:0.85em">{veg['name_urdu']}</span>
                <span class="pill {pill_cls}">{veg['difficulty']}</span>
            </div>
            <div>
                <span class="score-badge {badge_cls}">{veg['score']}/100</span>
            </div>
        </div>
        <div style="margin-top:10px; display:flex; gap:16px; flex-wrap:wrap; font-size:0.82em; color:#555;">
            <span>🌡️ <b>Temp</b> {bd['temperature']}/40</span>
            <span>💧 <b>Humidity</b> {bd['humidity']}/25</span>
            <span>📅 <b>Season</b> {bd['season']}/20</span>
            <span>🪴 <b>Space</b> {bd['space']}/10</span>
            <span>🚿 <b>Water</b> {bd['water']}/5</span>
        </div>
        <div style="margin-top:8px; font-size:0.85em; color:#444;">
            ⏱️ {veg['days_to_harvest']} days to harvest &nbsp;|&nbsp;
            💧 {veg['water_need']} water &nbsp;|&nbsp;
            ☀️ {veg['sunlight']} sun
        </div>
        <div style="margin-top:6px; font-size:0.82em; color:#666; font-style:italic;">
            💡 {veg['notes']}
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Score bar chart ───────────────────────────────────────────────────────────
def render_score_chart(all_sorted: list):
    names  = [f"{v['emoji']} {v['name']}" for v in all_sorted]
    scores = [v['score'] for v in all_sorted]
    colors = [
        "#2d7a2d" if s >= 80 else
        "#f39c12" if s >= 60 else
        "#e67e22" if s >= 40 else
        "#c0392b"
        for s in scores
    ]

    fig = go.Figure(go.Bar(
        x=scores, y=names,
        orientation='h',
        marker_color=colors,
        text=[f"{s}/100" for s in scores],
        textposition='inside',
        insidetextanchor='end',
        textfont=dict(color='#ffffff', size=12, family='Arial', weight='bold'),
        hovertemplate='<b>%{y}</b><br>Score: %{x}/100<extra></extra>'
    ))

    fig.update_layout(
        title=dict(text="All Vegetables — Suitability Scores", font=dict(color="#1a3a1a", size=15)),
        xaxis=dict(
            range=[0, 108],
            title=dict(text="Score (0–100)", font=dict(color="#333333", size=12)),
            tickfont=dict(color="#333333", size=11),
            fixedrange=True,
            showgrid=True,
            gridcolor="#e0e0e0",
        ),
        yaxis=dict(
            autorange="reversed",
            tickfont=dict(color="#1a1a1a", size=12),
            tickcolor="#1a1a1a",
        ),
        height=max(500, len(names) * 28),
        margin=dict(l=160, r=20, t=50, b=40),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#f8faf5",
        font=dict(size=12, color="#1a1a1a"),
    )

    st.plotly_chart(fig, width='stretch')


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN APP
# ══════════════════════════════════════════════════════════════════════════════

def main():
    df           = load_vegetables()
    current_month = get_current_month()

    # ── SIDEBAR ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## 🌱 Karachi Garden Guide")
        st.markdown("*Smart vegetable recommendations for your home garden*")
        st.markdown("---")

        st.markdown("### 🏡 Your Garden")
        space = st.selectbox(
            "Gardening space",
            options=["pot", "rooftop", "ground"],
            format_func=lambda x: {"pot": "🪴 Pots", "rooftop": "🏠 Rooftop", "ground": "🌍 Ground"}[x]
        )

        sunlight = st.selectbox(
            "Sunlight availability",
            options=["full", "partial", "shade"],
            format_func=lambda x: {"full": "☀️ Full sun (6+ hrs)", "partial": "⛅ Partial (3–6 hrs)", "shade": "🌥️ Shade (<3 hrs)"}[x]
        )

        watering = st.selectbox(
            "Watering frequency",
            options=["daily", "alternate", "weekly"],
            format_func=lambda x: {"daily": "💧 Every day", "alternate": "💧 Every other day", "weekly": "💧 Once a week"}[x]
        )

        st.markdown("---")

        # Month override for testing different seasons
        st.markdown("### 🗓️ Test Different Months")
        use_override = st.checkbox("Override current month", value=False)
        if use_override:
            month_names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
            selected_month = st.selectbox("Select month", options=list(range(1,13)),
                                          format_func=lambda x: month_names[x-1])
        else:
            selected_month = current_month

        st.markdown("---")
        st.markdown("### 📍 Location")
        st.markdown("📌 **Karachi, Pakistan**")
        st.markdown(f"🗓️ Month: **{datetime.now().strftime('%B')}**")
        st.markdown("🌐 Weather: **Mock data** *(add API key for live)*")

        st.markdown("---")
        st.markdown("<small>Built for Karachi home gardeners 🇵🇰</small>", unsafe_allow_html=True)

    # ── FETCH & PARSE WEATHER ─────────────────────────────────────────────────
    raw_weather = get_mock_weather(selected_month)
    weather     = parse_current_weather(raw_weather)
    ctx         = get_gardening_context(weather)

    # ── SCORE & RANK ──────────────────────────────────────────────────────────
    user_prefs = {"space": space, "sunlight": sunlight, "watering": watering}
    results    = score_all_vegetables(df, weather, user_prefs, selected_month)
    ranked     = rank_results(results)

    # ── MAIN PANEL ────────────────────────────────────────────────────────────
    st.markdown("# 🌱 Karachi Gardening Assistant")

    # Weather card
    month_name = datetime(2025, selected_month, 1).strftime('%B')
    st.markdown(f"""
    <div class="weather-card">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
            <div>
                <div class="weather-label">📍 Karachi, Pakistan &nbsp;·&nbsp; {month_name}</div>
                <div class="weather-temp">{weather['temp_c']}°C</div>
                <div class="weather-label">{weather['description']} &nbsp;·&nbsp; Feels like {weather['feels_like_c']}°C &nbsp;·&nbsp; {weather['feel_label']}</div>
            </div>
            <div style="text-align:right;">
                <div class="weather-label">💧 Humidity: <b style="color:white">{weather['humidity_pct']}%</b></div>
                <div class="weather-label">🌧️ Rain: <b style="color:white">{weather['rain_mm']} mm</b></div>
                <div class="weather-label">💨 Wind: <b style="color:white">{weather['wind_kmh']} km/h</b></div>
                <div style="margin-top:8px; background:rgba(255,255,255,0.15); border-radius:8px; padding:6px 12px;">
                    🚿 <b style="color:white">{ctx['watering_advice']}</b>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Alerts and tips
    if ctx['alerts'] or ctx['tips']:
        for alert in ctx['alerts']:
            st.markdown(f'<div class="alert-box">⚠️ {alert}</div>', unsafe_allow_html=True)
        for tip in ctx['tips']:
            st.markdown(f'<div class="tip-box">💡 {tip}</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Two column layout: results + chart ────────────────────────────────────
    col1, col2 = st.columns([1.1, 0.9])

    with col1:
        # Recommended
        st.markdown(f'<div class="section-header">✅ Plant Now — {len(ranked["recommended"])} vegetables recommended</div>', unsafe_allow_html=True)
        if ranked['recommended']:
            for veg in ranked['recommended'][:6]:
                render_veg_card(veg, "recommend")
            if len(ranked['recommended']) > 6:
                with st.expander(f"Show {len(ranked['recommended']) - 6} more recommended vegetables"):
                    for veg in ranked['recommended'][6:]:
                        render_veg_card(veg, "recommend")
        else:
            st.info("No vegetables strongly recommended for these conditions.")

        # Borderline
        if ranked['borderline']:
            st.markdown('<div class="section-header">🟡 Possible with care</div>', unsafe_allow_html=True)
            with st.expander(f"Show {len(ranked['borderline'])} borderline vegetables"):
                for veg in ranked['borderline']:
                    render_veg_card(veg, "borderline")

        # Avoid
        st.markdown(f'<div class="section-header">🔴 Avoid This Season — {len(ranked["avoid"])} vegetables</div>', unsafe_allow_html=True)
        if ranked['avoid']:
            for veg in ranked['avoid'][:3]:
                render_veg_card(veg, "avoid")
            if len(ranked['avoid']) > 3:
                with st.expander(f"Show {len(ranked['avoid']) - 3} more vegetables to avoid"):
                    for veg in ranked['avoid'][3:]:
                        render_veg_card(veg, "avoid")

    with col2:
        st.markdown('<div class="section-header">📊 Suitability Chart</div>', unsafe_allow_html=True)
        render_score_chart(ranked['all_sorted'])

        # Score legend
        st.markdown("""
        <div style="background:white; border-radius:10px; padding:14px; margin-top:12px; font-size:0.85em;">
            <b>Score legend</b><br><br>
            <span style="color:#2d7a2d">🟢 80–100</span> &nbsp; Excellent — plant now<br>
            <span style="color:#f39c12">🟡 60–79</span> &nbsp;&nbsp; Good — suitable with care<br>
            <span style="color:#e67e22">🟠 40–59</span> &nbsp;&nbsp; Marginal — possible but challenging<br>
            <span style="color:#c0392b">🔴 0–39</span> &nbsp;&nbsp;&nbsp; Avoid — not this season<br><br>
            <b>Score formula</b><br><br>
            🌡️ Temperature &nbsp; 40%<br>
            💧 Humidity &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 25%<br>
            📅 Season &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 20%<br>
            🪴 Space &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 10%<br>
            🚿 Watering &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 5%
        </div>
        """, unsafe_allow_html=True)


if __name__ == '__main__':
    main()