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
    expected_columns = ['Task', 'Cadence', 'Value']
    try:
        df = pd.read_csv(url)

        # --- NEW VALIDATION STEP ---
        # Check if the loaded data has the columns we expect.
        if not all(col in df.columns for col in expected_columns):
            st.error("The data from the URL doesn't look like the expected CSV file.")
            st.info("It seems you might be using a standard GitHub link instead of the 'Raw' file link. Please check the URL.")
            st.warning(f"The app expects columns: {expected_columns}")
            st.warning(f"The file loaded has columns: {df.columns.tolist()[:5]}...") # Show first 5 columns found
            return None # Return None to indicate failure

        # --- Data Processing ---
        df['Reward'] = df['Value'].apply(lambda x: float(re.sub(r'[£$€,]', '', str(x))) if str(x)[0] in '£$€' else 0.0)
        df['IsMustDo'] = df['Value'].apply(lambda x: 'Must do' in str(x))
        return df

    except Exception as e:
        # This will catch other parsing issues, including the C error.
        st.error(f"Failed to process the CSV file. Error: {e}")
        st.info("Please double-check that the URL points to the 'Raw' version of your CSV file on GitHub.")
        return None


def display_task_list(header, tasks_df):
    """Displays a list of tasks as checkboxes and calculates earnings."""
    st.subheader(header, divider='rainbow')
    
    if tasks_df.empty:
        st.write("No tasks in this category.")
        return 0.0

    earned_value = 0.0
    
    if 'task_states' not in st.session_state:
        st.session_state.task_states = {}

    for _, row in tasks_df.iterrows():
        task_id = f"{header}_{row['Task']}"
        
        if row['IsMustDo']:
            label = f"{row['Task']} (Must do)"
        else:
            label = f"{row['Task']} (£{row['Reward']:.2f})"
        
        is_checked = st.checkbox(
            label, 
            key=task_id,
            value=st.session_state.task_states.get(task_id, False)
        )
        
        st.session_state.task_states[task_id] = is_checked
        if is_checked and not row['IsMustDo']:
            earned_value += row['Reward']
            
    return earned_value


# --- Main Application ---
st.title("🏆 Kids' Task Checklist 🏆")
st.write("Tick the boxes for the tasks you've completed!")

# --- GitHub URL Input ---
# IMPORTANT: Replace this with the RAW URL of your 'tasks.csv' file on GitHub
CSV_URL = 'https://raw.githubusercontent.com/Kim2783/Kidstodolist/main/KIDS_TASKS%20-%20Sheet1.csv'

# --- Load Data ---
tasks_df = load_data(CSV_URL)

# --- App Logic ---
# The app will only proceed if the data is loaded successfully.
if tasks_df is not None and not tasks_df.empty:
    
    daily_tasks = tasks_df[tasks_df['Cadence'].str.lower() == 'daily']
    weekly_tasks = tasks_df[tasks_df['Cadence'].str.lower() == 'weekly']
    monthly_tasks = tasks_df[tasks_df['Cadence'].str.lower() == 'monthly']

    tab1, tab2, tab3 = st.tabs(["🗓️ Daily Tasks", "📅 Weekly Tasks", " M️onthly Tasks"])

    with tab1:
        daily_earnings = display_task_list("Your Daily Tasks", daily_tasks)
    with tab2:
        weekly_earnings = display_task_list("Your Weekly Tasks", weekly_tasks)
    with tab3:
        monthly_earnings = display_task_list("Your Monthly Tasks", monthly_tasks)

    total_earned = daily_earnings + weekly_earnings + monthly_earnings
    total_possible_reward = tasks_df['Reward'].sum()
    
    st.sidebar.header("Summary")
    st.sidebar.metric("💰 Total Earned", f"£{total_earned:.2f}")

    if total_possible_reward > 0:
        st.sidebar.metric("Potential Total", f"£{total_possible_reward:.2f}")
    
    completed_tasks = sum(1 for key, value in st.session_state.task_states.items() if value)
    total_tasks = len(tasks_df)
    
    if total_tasks > 0:
        progress = completed_tasks / total_tasks
        st.sidebar.progress(progress)
        st.sidebar.write(f"{completed_tasks} of {total_tasks} tasks completed.")

    if st.sidebar.button("Reset Checklist"):
        st.session_state.task_states = {}
        st.rerun()

else:
    st.warning("Could not load or validate task data. Please check the URL in the `app.py` file and ensure it's a 'Raw' link.")
