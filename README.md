# 🌱 Karachi Gardening Assistant

A weather-aware vegetable planting recommendation system built specifically for Karachi's climate.

## What it does
- Fetches live weather data for Karachi
- Scores vegetables based on current temperature, humidity, season, your gardening space, and watering habits
- Recommends which vegetables to plant now and which to avoid

## Project structure
```
karachi-garden-assistant/
├── data/               # Vegetable dataset and seasonal data (CSV files)
├── src/
│   ├── weather/        # Fetch and parse live weather data
│   ├── recommender/    # Scoring engine and ranking logic
│   ├── ml/             # Machine learning pipeline (Phase 4)
│   └── utils/          # Shared config and helper functions
├── app/                # Streamlit dashboard
├── notebooks/          # Jupyter notebooks for exploration
└── tests/              # Unit tests
```

## Setup

### 1. Clone and install dependencies
```bash
pip install -r requirements.txt
```

### 2. Add your API key
```bash
cp .env.example .env
# Open .env and paste your OpenWeatherMap key
```
Get a free key at https://openweathermap.org/api

### 3. Run the app
```bash
streamlit run app/streamlit_app.py
```

## Development phases
- **Phase 1** ✅ Project structure + vegetable dataset
- **Phase 2** — Weather API integration
- **Phase 3** — Streamlit dashboard
- **Phase 4** — ML-based scoring
- **Phase 5** — User profiles, reminders, AI chatbot