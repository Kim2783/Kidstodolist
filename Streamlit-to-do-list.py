import streamlit as st
import pandas as pd
import re
import requests
from streamlit_lottie import st_lottie

# --- Page Configuration ---
st.set_page_config(
    page_title="Kids' Task Checklist",
    page_icon="🎉",
    layout="wide"
)

# --- Custom Styling (CSS) ---
# This makes the app look fancier!
st.markdown("""
<style>
    /* Main app background */
    .stApp {
        background: linear-gradient(to right, #f0f2f6, #e6e9f0);
    }

    /* Style for the containers */
    [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] {
        border: 2px solid #90a4ae;
        border-radius: 10px;
        padding: 15px;
        background-color: #ffffff;
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.1);
    }
    
    /* Title style */
    .st-emotion-cache-10trblm {
        color: #263238;
        font-family: 'Comic Sans MS', cursive, sans-serif;
    }

    /* Sidebar style */
    [data-testid="stSidebar"] {
        background-color: #eceff1;
    }

</style>
""", unsafe_allow_html=True)


# --- Lottie Animation Loader ---
@st.cache_data
def load_lottie_url(url: str):
    """Loads a Lottie animation from a URL."""
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

# --- Data Loading ---
@st.cache_data
def load_data(url):
    """Loads task data from a raw GitHub URL."""
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

# --- Main App ---

# --- Header with Animation ---
lottie_animation_url = "https://lottie.host/8cd98287-73c3-455b-8640-57c9a1a329d1/j34S4Yn0N8.json"
lottie_anim = load_lottie_url(lottie_animation_url)

col1, col2 = st.columns([1, 4])
with col1:
    if lottie_anim:
        st_lottie(lottie_anim, speed=1, height=150, key="initial")
with col2:
    st.title("🏆 Kids' Awesome Task Checklist 🏆")
    st.write("Let's get things done and have some fun!")

# --- Session State Initialization ---
if 'task_states' not in st.session_state:
    st.session_state.task_states = {}
if 'last_completed_task' not in st.session_state:
    st.session_state.last_completed_task = None


def display_task_list(tasks_df):
    """Displays tasks and detects when a new task is completed."""
    earned_value = 0.0
    
    if tasks_df.empty:
        st.write("No tasks in this category today!")
        return 0.0

    for _, row in tasks_df.iterrows():
        task_id = f"{row['Cadence']}_{row['Task']}"
        is_currently_checked = st.session_state.task_states.get(task_id, False)

        if row['IsMustDo']:
            label = f"**{row['Task']}** (Must do)"
        else:
            label = f"**{row['Task']}** (£{row['Reward']:.2f})"
        
        is_now_checked = st.checkbox(
            label,
            value=is_currently_checked,
            key=f"cb_{task_id}" # Use a different key for the widget
        )

        # THE SURPRISE LOGIC: Detect if a checkbox was just ticked
        if is_now_checked and not is_currently_checked:
            # Check if it's a paid task to trigger the surprise
            if not row['IsMustDo']:
                st.session_state.last_completed_task = row['Task'] # Store the name of the task
        
        st.session_state.task_states[task_id] = is_now_checked
        
        if is_now_checked and not row['IsMustDo']:
            earned_value += row['Reward']
            
    return earned_value


# --- Load Data and Display Lists ---
# Paste your RAW GitHub URL here
CSV_URL = 'https://raw.githubusercontent.com/Kim2783/Kidstodolist/main/KIDS_TASKS%20-%20Sheet1.csv'
tasks_df = load_data(CSV_URL)

if tasks_df is not None and not tasks_df.empty:
    
    daily_tasks = tasks_df[tasks_df['Cadence'].str.lower() == 'daily']
    weekly_tasks = tasks_df[tasks_df['Cadence'].str.lower() == 'weekly']
    monthly_tasks = tasks_df[tasks_df['Cadence'].str.lower() == 'monthly']

    # --- Create columns for a cleaner layout ---
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

    # --- Surprise Trigger ---
    # Check if a paid task was just completed on this run
    if st.session_state.last_completed_task:
        task_name = st.session_state.last_completed_task
        st.toast(f"🎉 Great job finishing '{task_name}'! 🎉", icon="🥳")
        st.balloons()
        st.session_state.last_completed_task = None # Reset so it doesn't fire again

    # --- Sidebar Summary ---
    total_earned = daily_earnings + weekly_earnings + monthly_earnings
    total_possible_reward = tasks_df['Reward'].sum()
    
    st.sidebar.header("Summary")
    st.sidebar.metric("💰 Total Earned", f"£{total_earned:.2f}")

    if total_possible_reward > 0:
        st.sidebar.metric("Potential Total", f"£{total_possible_reward:.2f}")
    
    completed_tasks = sum(1 for value in st.session_state.task_states.values() if value)
    total_tasks = len(tasks_df)
    
    if total_tasks > 0:
        progress = completed_tasks / total_tasks
        st.sidebar.progress(progress)
        st.sidebar.write(f"**{completed_tasks}** of **{total_tasks}** tasks completed.")

    if st.sidebar.button("Reset All Tasks"):
        st.session_state.task_states = {}
        st.rerun()

else:
    st.warning("Could not load task data. Please check the URL in the `app.py` file.")
