import streamlit as st
import pandas as pd
import re
import requests
import json
import os
from datetime import datetime
from streamlit_lottie import st_lottie

# --- Page Configuration ---
st.set_page_config(
    page_title="Kids' Task Checklist",
    page_icon="💜",
    layout="wide"
)

# --- Custom Styling (CSS) ---
# This section has been updated with a new purple color scheme!
st.markdown("""
<style>
    /* Main app background with a soft purple gradient */
    .stApp {
        background: linear-gradient(to right, #e6e6fa, #d8bfd8);
    }

    /* Style for the task containers with purple borders */
    [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] {
        border: 2px solid #9370db; /* Medium Purple */
        border-radius: 10px;
        padding: 15px;
        background-color: #faf8ff; /* Ghost White - a very light lilac */
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.1);
    }
    
    /* Title style with a deep purple color */
    .st-emotion-cache-10trblm {
        color: #483d8b; /* Dark Slate Blue */
        font-family: 'Comic Sans MS', cursive, sans-serif;
    }

    /* Sidebar style with a complementary light purple */
    [data-testid="stSidebar"] {
        background-color: #dcd0ff; /* Light purple */
    }

</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_lottie_url(url: str):
    r = requests.get(url)
    if r.status_code != 200: return None
    return r.json()

# --- State Management ---
STATE_FILE = "state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        task_states = state.get("task_states", {})
        last_update_str = state.get("last_update")
        if last_update_str:
            last_update_date = datetime.fromisoformat(last_update_str)
            now = datetime.now()
            if now.date() > last_update_date.date():
                for task_id in list(task_states.keys()):
                    if task_id.startswith('Daily_'): task_states[task_id] = False
            last_update_week = last_update_date.isocalendar()[1]
            now_week = now.isocalendar()[1]
            if now_week != last_update_week:
                 for task_id in list(task_states.keys()):
                    if task_id.startswith('Weekly_'): task_states[task_id] = False
            if now.month != last_update_date.month or now.year != last_update_date.year:
                for task_id in list(task_states.keys()):
                    if task_id.startswith('Monthly_'): task_states[task_id] = False
        return task_states
    return {}

def save_state(task_states):
    state = { "last_update": datetime.now().isoformat(), "task_states": task_states }
    with open(STATE_FILE, 'w') as f: json.dump(state, f, indent=4)

# --- Data Loading ---
@st.cache_data
def load_data(url):
    expected_columns = ['Task', 'Cadence', 'Value']
    try:
        df = pd.read_csv(url)
        if not all(col in df.columns for col in expected_columns):
            st.error("CSV file is not in the expected format.")
            return None
        df['Reward'] = df['Value'].apply(lambda x: float(re.sub(r'[£$€,]', '', str(x))) if str(x)[0] in '£$€' else 0.0)
        df['IsMustDo'] = df['Value'].apply(lambda x: 'Must do' in str(x))
        return df
    except Exception as e:
        st.error(f"Failed to process the CSV file. Error: {e}")
        return None

# --- Session State Initialization ---
if 'initialized' not in st.session_state:
    st.session_state.task_states = load_state()
    st.session_state.last_paid_task_surprise = None
    st.session_state.last_daily_task_surprise = None
    st.session_state.initialized = True

# --- Main App ---
lottie_anim = load_lottie_url("https://lottie.host/8cd98287-73c3-455b-8640-57c9a1a329d1/j34S4Yn0N8.json")
col1, col2 = st.columns([1, 4])
with col1:
    if lottie_anim: st_lottie(lottie_anim, speed=1, height=150, key="initial")
with col2:
    st.title("🏆 Kids' Awesome Task Checklist 🏆")
    st.write("Let's get things done and have some fun!")

def display_task_list(tasks_df):
    earned_value = 0.0
    if tasks_df.empty: return 0.0

    for _, row in tasks_df.iterrows():
        task_id = f"{row['Cadence']}_{row['Task']}"
        is_currently_checked = st.session_state.task_states.get(task_id, False)
        if row['IsMustDo']: label = f"**{row['Task']}** (Must do)"
        else: label = f"**{row['Task']}** (£{row['Reward']:.2f})"
        is_now_checked = st.checkbox(label, value=is_currently_checked, key=f"cb_{task_id}")
        if is_now_checked != is_currently_checked:
            st.session_state.task_states[task_id] = is_now_checked
            if is_now_checked:
                if not row['IsMustDo']: st.session_state.last_paid_task_surprise = row['Task']
                elif row['IsMustDo'] and row['Cadence'].lower() == 'daily': st.session_state.last_daily_task_surprise = row['Task']
            save_state(st.session_state.task_states)
            st.rerun()
        if is_now_checked and not row['IsMustDo']:
            earned_value += row['Reward']
    return earned_value

CSV_URL = 'https://raw.githubusercontent.com/Kim2783/Kidstodolist/main/KIDS_TASKS%20-%20Sheet1.csv'
tasks_df = load_data(CSV_URL)

if tasks_df is not None:
    daily_tasks = tasks_df[tasks_df['Cadence'].str.lower() == 'daily']
    weekly_tasks = tasks_df[tasks_df['Cadence'].str.lower() == 'weekly']
    monthly_tasks = tasks_df[tasks_df['Cadence'].str.lower() == 'monthly']

    col_daily, col_weekly, col_monthly = st.columns(3)
    with col_daily:
        with st.container(border=True):
            st.header("🗓️ Daily Tasks")
            daily_earnings = display_task_list(daily_tasks)
    with col_weekly:
        with st.container(border=True):
            st.header("📅 Weekly Tasks")
            weekly_earnings = display_task_list(weekly_tasks)
    with col_monthly:
        with st.container(border=True):
            st.header("Ⓜ️ Monthly Tasks")
            monthly_earnings = display_task_list(monthly_tasks)

    if st.session_state.last_paid_task_surprise:
        st.toast(f"🎉 Awesome! You've earned money for '{st.session_state.last_paid_task_surprise}'! 🎉", icon="🥳")
        st.balloons()
        st.session_state.last_paid_task_surprise = None
    if st.session_state.last_daily_task_surprise:
        st.toast(f"👍 Great job on your daily goal: '{st.session_state.last_daily_task_surprise}'! 👍", icon="✅")
        st.session_state.last_daily_task_surprise = None

    total_earned = daily_earnings + weekly_earnings + monthly_earnings
    total_possible_reward = tasks_df['Reward'].sum()
    st.sidebar.header("Summary")
    st.sidebar.metric("💰 Total Earned", f"£{total_earned:.2f}")
    if total_possible_reward > 0: st.sidebar.metric("Potential Total", f"£{total_possible_reward:.2f}")
    
    completed_tasks = sum(1 for value in st.session_state.task_states.values() if value)
    total_tasks = len(tasks_df)
    if total_tasks > 0:
        st.sidebar.progress(completed_tasks / total_tasks)
        st.sidebar.write(f"**{completed_tasks}** of **{total_tasks}** tasks completed.")

    if st.sidebar.button("💥 Reset All Tasks Now 💥"):
        st.session_state.task_states = {}
        save_state({})
        st.rerun()
