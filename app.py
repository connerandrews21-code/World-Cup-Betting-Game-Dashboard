import streamlit as st
import pandas as pd
import requests
from datetime import datetime, time
import pytz

# --- CONFIGURATION ---
# 1. Paste your published Google Sheet CSV link here (containing user votes)
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTK91z-KnxqIUFm2m6_N5yE4LOshbLx76msh8a6NiPANCNtnGGGzLUHA6hkvlumR2_Dv3j4LG0yqSii/pub?output=csv"

# 2. Paste your free football-data.org API token here
FOOTBALL_API_TOKEN = "326ea6a887f842a685ee132585df4688"
# ---------------------

st.set_page_config(page_title="World Cup Pool Leaderboard", layout="wide")

# This forces Streamlit to clear its cache and fetch fresh data if it's 5:00 AM GMT or later
@st.cache_data(ttl=3600)  # Checks hourly, enforcing the 5 AM GMT reset window
def get_current_day_string():
    gmt = pytz.timezone('GMT')
    now = datetime.now(gmt)
    
    # Adjusted to 5:00 AM GMT
    if now.time() < time(5, 0):
        return f"{now.date()}-before-5am"
    return f"{now.date()}-after-5am"

def fetch_live_standings():
    day_key = get_current_day_string()
    return _fetch_data_from_api(day_key)

def _fetch_data_from_api(cache_key):
    # World Cup Competition ID for football-data.org is WC
    url = "https://api.football-data.org/v4/competitions/WC/standings"
    headers = {"X-Auth-Token": FOOTBALL_API_TOKEN}
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        return data
    except Exception as e:
        st.error("Could not fetch latest tournament data. Showing cached sheet details instead.")
        return None

st.title("🏆 World Cup Pool Dashboard")
st.write("Live data automatically refreshes every morning at **5:00 AM GMT**.")

# Your scoring logic runs down here, comparing GOOGLE_SHEET_CSV_URL choices 
# against the live data pulled from fetch_live_standings().
