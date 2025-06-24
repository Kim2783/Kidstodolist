import streamlit as st
import pandas as pd
import re

# --- Page Configuration ---
st.set_page_config(
    page_title="Kids' Task Checklist",
    page_icon="✅",
    layout="centered"
)

# --- Data Loading ---
# This function caches the data to avoid reloading on every interaction.
@st.cache_data
def load_data(url):
    """Loads task data from a raw GitHub URL."""
    try:
        df = pd.read_csv(url)
        # Clean up the 'Value' column to handle currency and text
        df['Reward'] = df['Value'].apply(lambda x: float(re.sub(r'[£$€,]', '', str(x))) if str(x)[0] in '£$€' else 0.0)
        df['IsMustDo'] = df['Value'].apply(lambda x: 'Must do' in str(x))
        return df
    except Exception as e:
        st.error(f"Error loading data from URL: {e}")
        st.info("Please make sure the GitHub raw URL is correct and the CSV file is accessible.")
        return pd.DataFrame(columns=['Task', 'Cadence', 'Value', 'Reward', 'IsMustDo'])


def display_task_list(header, tasks_df):
    """Displays a list of tasks as checkboxes and calculates earnings."""
    st.subheader(header, divider='rainbow')
    
    if tasks_df.empty:
        st.write("No tasks in this category.")
        return 0.0

    earned_value = 0.0
    
    # Initialize session state for tasks if not already present
    if 'task_states' not in st.session_state:
        st.session_state.task_states = {}

    for _, row in tasks_df.iterrows():
        task_id = f"{header}_{row['Task']}" # Unique key for each checkbox
        
        # Format the label to show task and value
        if row['IsMustDo']:
            label = f"{row['Task']} (Must do)"
        else:
            label = f"{row['Task']} (£{row['Reward']:.2f})"
        
        # Create a checkbox and use session state to hold its value
        is_checked = st.checkbox(
            label, 
            key=task_id,
            value=st.session_state.task_states.get(task_id, False)
        )
        
        # Update session state and calculate earnings
        st.session_state.task_states[task_id] = is_checked
        if is_checked and not row['IsMustDo']:
            earned_value += row['Reward']
            
    return earned_value


# --- Main Application ---

# --- GitHub URL Input ---
# IMPORTANT: Replace this with the raw URL of your 'tasks.csv' file on GitHub
# See instructions below on how to get this URL.
CSV_URL = 'https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPOSITORY/main/tasks.csv'

# --- App Title ---
st.title("🏆 Kids' Task Checklist 🏆")
st.write("Tick the boxes for the tasks you've completed!")

# --- Load Data ---
tasks_df = load_data(CSV_URL)

if not tasks_df.empty:
    
    # --- Filter data by cadence ---
    daily_tasks = tasks_df[tasks_df['Cadence'].str.lower() == 'daily']
    weekly_tasks = tasks_df[tasks_df['Cadence'].str.lower() == 'weekly']
    monthly_tasks = tasks_df[tasks_df['Cadence'].str.lower() == 'monthly']

    # --- Create tabs for each cadence ---
    tab1, tab2, tab3 = st.tabs(["🗓️ Daily Tasks", "📅 Weekly Tasks", " M️onthly Tasks"])

    with tab1:
        daily_earnings = display_task_list("Your Daily Tasks", daily_tasks)
    
    with tab2:
        weekly_earnings = display_task_list("Your Weekly Tasks", weekly_tasks)

    with tab3:
        monthly_earnings = display_task_list("Your Monthly Tasks", monthly_tasks)

    # --- Summary & Earnings Calculation ---
    total_earned = daily_earnings + weekly_earnings + monthly_earnings
    total_possible_reward = tasks_df['Reward'].sum()
    
    st.sidebar.header("Summary")
    st.sidebar.metric("💰 Total Earned", f"£{total_earned:.2f}")

    if total_possible_reward > 0:
        st.sidebar.metric("Potential Total", f"£{total_possible_reward:.2f}")
    
    # Progress Bar
    completed_tasks = sum(st.session_state.task_states.values())
    total_tasks = len(tasks_df)
    
    if total_tasks > 0:
        progress = completed_tasks / total_tasks
        st.sidebar.progress(progress)
        st.sidebar.write(f"{completed_tasks} of {total_tasks} tasks completed.")

    # Add a reset button to clear all checkboxes
    if st.sidebar.button("Reset Checklist"):
        st.session_state.task_states = {}
        st.rerun()

else:
    st.warning("Could not load task data. Please check the URL in the `app.py` file.")
