import streamlit as st
import pandas as pd
import requests
from datetime import datetime, time
import pytz

# --- ⚙️ CONFIGURATION ⚙️ ---
# 1. Paste your published Google Sheet CSV link here
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTK91z-KnxqIUFm2m6_N5yE4LOshbLx76msh8a6NiPANCNtnGGGzLUHA6hkvlumR2_Dv3j4LG0yqSii/pub?output=csv"

# 2. Paste your free football-data.org API token here
FOOTBALL_API_TOKEN = "326ea6a887f842a685ee132585df4688"
# ---------------------------

st.set_page_config(page_title="World Cup Pool Live Dashboard", page_icon="🏆", layout="wide")

# --- 🕒 DAILY AUTOMATED REFRESH LOGIC (5 AM GMT) ---
@st.cache_data(ttl=3600)  # Checks for updates hourly
def get_current_day_string():
    gmt = pytz.timezone('GMT')
    now = datetime.now(gmt)
    if now.time() < time(5, 0):
        return f"{now.date()}-before-5am"
    return f"{now.date()}-after-5am"

@st.cache_data(ttl=1800)  # Cache API tables for 30 minutes to stay within free rate limits
def fetch_api_data(endpoint, cache_key):
    url = f"https://api.football-data.org/v4/competitions/WC/{endpoint}"
    headers = {"X-Auth-Token": FOOTBALL_API_TOKEN}
    try:
        response = requests.get(url, headers=headers)
        return response.json()
    except Exception as e:
        return None

@st.cache_data(ttl=300)
def load_predictions_sheet():
    try:
        return pd.read_csv(GOOGLE_SHEET_CSV_URL)
    except:
        return None

# --- 🚀 MAIN APP ENGINE ---
cache_key = get_current_day_string()
standings_data = fetch_api_data("standings", cache_key)
matches_data = fetch_api_data("matches", cache_key)
df_preds = load_predictions_sheet()

if df_preds is None:
    st.error("📥 Could not load predictions. Verify your Google Sheet is published to web as a CSV.")
else:
    friends = [col for col in df_preds.columns if col not in ["Team", "Status", "Crucial Match"]]
    
    # Extract qualified teams from live data
    qualified_teams = set()
    if standings_data and "standings" in standings_data:
        for group in standings_data["standings"]:
            for idx, row in enumerate(group.get("table", [])):
                team_name = row["team"]["name"]
                # Mathematical qualification check: Top 2 from group stages definitely advance
                if idx < 2 and row.get("playedGames", 0) >= 3:
                    qualified_teams.add(team_name)

    # --- 🏆 SIDEBAR LEADERBOARD ---
    st.sidebar.title("🏅 Standings")
    leaderboard = []
    for friend in friends:
        pts = df_preds[(df_preds[friend] == 1) & (df_preds["Team"].isin(qualified_teams))].shape[0]
        leaderboard.append({"Friend": friend, "Points": pts})
    
    df_leaderboard = pd.DataFrame(leaderboard).sort_values(by="Points", ascending=False)
    for index, row in df_leaderboard.iterrows():
        st.sidebar.metric(label=row["Friend"], value=f"{row['Points']} pts")

    # --- 📋 MAIN UI NAVIGATION TABS ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Friend Leaderboard & Disagreements", 
        "🔮 All Group Predictions", 
        "📈 Live Group Standings", 
        "⚽ Match Fixtures & Results"
    ])

    # --- TAB 1: THE MAIN GAME ---
    with tab1:
        st.header("⚡ Live Standings Summary")
        cols = st.columns(len(friends))
        for i, row in enumerate(df_leaderboard.itertuples()):
            with cols[i % len(friends)]:
                st.subheader(f"{row.Friend}")
                st.write(f"**Score:** {row.Points} points")
                
        st.divider()
        st.header("🎯 Crucial Decider Teams")
        st.caption("Teams where your choices split. These teams will dictate the winner!")
        
        # Pull out rows where predictions aren't unanimous
        diff_mask = df_preds[friends].nunique(axis=1) > 1
        df_diff = df_preds[diff_mask][["Team"] + friends]
        st.dataframe(df_diff.style.background_gradient(subset=friends, cmap="Greens"), use_container_width=True, hide_index=True)

    # --- TAB 2: ALL USER PREDICTIONS ---
    with tab2:
        st.header("🔮 The Master Prediction Sheet")
        st.write("Here is the raw look at what everyone locked in before kickoff (1 = Advance, 0 = Go Home):")
        st.dataframe(df_preds, use_container_width=True, hide_index=True)

    # --- TAB 3: LIVE GROUP STANDINGS ---
    with tab3:
        st.header("📈 Official Group Stage Standings")
        if standings_data and "standings" in standings_data:
            # Loop through all 12 groups dynamically
            for group in standings_data["standings"]:
                st.subheader(f"Region: {group.get('group', 'Group stage')}")
                table_rows = []
                for row in group.get("table", []):
                    table_rows.append({
                        "Pos": row["position"],
                        "Team": row["team"]["name"],
                        "Played": row["playedGames"],
                        "Won": row["won"],
                        "Drawn": row["draw"],
                        "Lost": row["lost"],
                        "Points": row["points"],
                        "GD": row["goalDifference"]
                    })
                st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ Live tournament group rankings are temporarily unavailable or have not started yet.")

    # --- TAB 4: FIXTURES & RESULTS ---
    with tab4:
        st.header("⚽ Match Center")
        if matches_data and "matches" in matches_data:
            match_list = []
            for m in matches_data["matches"]:
                home_team = m["homeTeam"]["name"] if m["homeTeam"]["name"] else "TBD"
                away_team = m["awayTeam"]["name"] if m["awayTeam"]["name"] else "TBD"
                
                # Format scores cleanly
                home_score = m["score"]["fullTime"]["home"]
                away_score = m["score"]["fullTime"]["away"]
                score_str = f"{home_score} - {away_score}" if home_score is not None else "vs"
                
                match_list.append({
                    "Date": m["utcDate"][:10],
                    "Stage": m["stage"],
                    "Home Team": home_team,
                    "Score": score_str,
                    "Away Team": away_team,
                    "Status": m["status"]
                })
            
            df_matches = pd.DataFrame(match_list)
            
            # Sub-split into Finished and Upcoming
            finished_matches = df_matches[df_matches["Status"] == "FINISHED"]
            upcoming_matches = df_matches[df_matches["Status"] != "FINISHED"]
            
            subtab_results, subtab_fixtures = st.columns(2)
            with subtab_results:
                st.subheader("🏁 Past Match Results")
                st.dataframe(finished_matches[["Date", "Home Team", "Score", "Away Team"]], use_container_width=True, hide_index=True)
            with subtab_fixtures:
                st.subheader("📅 Upcoming Fixtures")
                st.dataframe(upcoming_matches[["Date", "Home Team", "Score", "Away Team", "Status"]], use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ Live fixture match schedules could not be loaded directly from the source api.")
