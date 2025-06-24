import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io

# --- Configuration ---
CHILDREN = ["Ben", "Matilda"]

# Default TASK_DATA (used if no CSV is uploaded)
DEFAULT_TASK_DATA = [
    # Daily Must Do Tasks
    {"id": "md1", "description": "Make bed", "type": "must_do", "applies_to": ["Ben", "Matilda"], "frequency": "daily", "value": 0},
    {"id": "md2", "description": "Brush teeth", "type": "must_do", "applies_to": ["Ben", "Matilda"], "frequency": "daily", "value": 0},
    {"id": "md3", "description": "Get dressed", "type": "must_do", "applies_to": ["Ben", "Matilda"], "frequency": "daily", "value": 0},
    {"id": "md4", "description": "Do homework", "type": "must_do", "applies_to": ["Ben", "Matilda"], "frequency": "daily", "value": 0},

    # Daily Could Do Tasks (for Pocket Money)
    {"id": "cd1", "description": "Help set table", "type": "could_do", "applies_to": ["Ben", "Matilda"], "frequency": "daily", "value": 0.50},
    {"id": "cd2", "description": "Tidy up toys", "type": "could_do", "applies_to": ["Ben", "Matilda"], "frequency": "daily", "value": 0.50},
    {"id": "cd3", "description": "Read for 20 mins", "type": "could_do", "applies_to": ["Ben", "Matilda"], "frequency": "daily", "value": 0.75},
    {"id": "cd4", "description": "Help prepare dinner", "type": "could_do", "applies_to": ["Ben", "Matilda"], "frequency": "daily", "value": 0.75},

    # Weekly Must Do Tasks
    {"id": "wm1", "description": "Tidy room", "type": "must_do", "applies_to": ["Ben", "Matilda"], "frequency": "weekly", "value": 0},
    {"id": "wm2", "description": "Help with laundry (put away)", "type": "must_do", "applies_to": ["Ben", "Matilda"], "frequency": "weekly", "value": 0},

    # Weekly Could Do Tasks (for Pocket Money)
    {"id": "wc1", "description": "Vacuum living room", "type": "could_do", "applies_to": ["Ben", "Matilda"], "frequency": "weekly", "value": 2.00},
    {"id": "wc2", "description": "Wash dishes (full load)", "type": "could_do", "applies_to": ["Ben", "Matilda"], "frequency": "weekly", "value": 1.50},
    {"id": "wc3", "description": "Help with gardening", "type": "could_do", "applies_to": ["Ben", "Matilda"], "frequency": "weekly", "value": 2.50},
]

# --- CSV Handling Functions ---

def load_tasks_from_csv(uploaded_file):
    """
    Loads task data from an uploaded CSV file and converts it to the expected format.
    Expected CSV columns: id, description, type, applies_to, frequency, value
    'applies_to' should be a comma-separated string (e.g., "Ben,Matilda")
    """
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            required_columns = ["id", "description", "type", "applies_to", "frequency", "value"]

            # Basic validation: check if all required columns are present
            if not all(col in df.columns for col in required_columns):
                st.error(f"CSV must contain the following columns: {', '.join(required_columns)}")
                return None

            tasks = []
            for _, row in df.iterrows():
                # Split 'applies_to' string into a list
                applies_to_list = [c.strip() for c in str(row["applies_to"]).split(',')]
                # Convert value to float, handling potential errors
                try:
                    value = float(row["value"])
                except ValueError:
                    st.warning(f"Invalid 'value' for task ID '{row['id']}'. Setting to 0.")
                    value = 0.0

                tasks.append({
                    "id": str(row["id"]),
                    "description": str(row["description"]),
                    "type": str(row["type"]),
                    "applies_to": applies_to_list,
                    "frequency": str(row["frequency"]),
                    "value": value
                })
            return tasks
        except Exception as e:
            st.error(f"Error reading CSV file: {e}")
            return None
    return None

# --- Session State Initialization and Reset Logic ---

def get_current_week_number():
    """Returns the ISO week number for the current date (Monday is the first day of the week)."""
    return datetime.now().isocalendar()[1]

def initialize_session_state(tasks_data_source):
    """
    Initializes or updates session state based on the current date/week.
    This simulates daily and weekly resets for tasks and pocket money.
    It now takes the active TASK_DATA as an argument.
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    current_week = get_current_week_number()

    # Determine which task data to use for initialization
    current_tasks = tasks_data_source

    # Reset daily tasks and related money if a new day has started
    if "last_daily_reset" not in st.session_state or st.session_state["last_daily_reset"] != today_str:
        st.session_state["last_daily_reset"] = today_str
        # Initialize daily task status for all children as not completed
        st.session_state["daily_task_status"] = {
            child: {task["id"]: False for task in current_tasks if task["frequency"] == "daily" and child in task["applies_to"]}
            for child in CHILDREN
        }
        # Recalculate total money including weekly for all children
        for child in CHILDREN:
            calculate_pocket_money_for_child(child, current_tasks)

    # Reset weekly tasks and related money if a new ISO week has started
    if "last_weekly_reset" not in st.session_state or st.session_state["last_weekly_reset"] != current_week:
        st.session_state["last_weekly_reset"] = current_week
        # Initialize weekly task status for all children as not completed
        st.session_state["weekly_task_status"] = {
            child: {task["id"]: False for task in current_tasks if task["frequency"] == "weekly" and child in task["applies_to"]}
            for child in CHILDREN
        }
        # Recalculate total money including daily for all children
        for child in CHILDREN:
            calculate_pocket_money_for_child(child, current_tasks)

    # Initialize total pocket money if not already set (for the very first run)
    if "current_pocket_money" not in st.session_state:
        st.session_state["current_pocket_money"] = {child: 0.0 for child in CHILDREN}
        # Calculate initial total pocket money based on current state (should be 0 on fresh start)
        for child in CHILDREN:
            calculate_pocket_money_for_child(child, current_tasks)


# --- Functions to manage tasks and money ---

def calculate_pocket_money_for_child(child_name, tasks_data_source):
    """
    Calculates the total pocket money earned by a specific child
    based on their currently completed 'could do' tasks.
    It now takes the active TASK_DATA as an argument.
    """
    total_earned = 0.0
    for task in tasks_data_source: # Iterate through the master list of tasks
        if child_name in task["applies_to"] and task["type"] == "could_do":
            if task["frequency"] == "daily":
                # Check if the daily task is marked as completed for the child
                if st.session_state["daily_task_status"][child_name].get(task["id"], False):
                    total_earned += task["value"]
            elif task["frequency"] == "weekly":
                # Check if the weekly task is marked as completed for the child
                if st.session_state["weekly_task_status"][child_name].get(task["id"], False):
                    total_earned += task["value"]
    # Update the total earned in session state for the specific child
    st.session_state["current_pocket_money"][child_name] = total_earned

def update_task_status_callback(child_name, task_id, frequency, task_type, tasks_data_source):
    """
    Callback function executed when a task checkbox is toggled.
    It reads the new state of the checkbox from session_state and updates
    the task completion status, then recalculates pocket money.
    It now takes the active TASK_DATA as an argument.
    """
    # Streamlit automatically updates the widget's value in session_state under its key.
    # We reconstruct the key here to access the *new* state of the checkbox.
    checkbox_key = f"{frequency}_{task_type}_{child_name}_{task_id}"
    is_completed = st.session_state[checkbox_key]

    # Update the completion status in the appropriate daily/weekly status dictionary
    if frequency == "daily":
        st.session_state["daily_task_status"][child_name][task_id] = is_completed
    elif frequency == "weekly":
        st.session_state["weekly_task_status"][child_name][task_id] = is_completed

    # Recalculate pocket money for the child after the status change
    calculate_pocket_money_for_child(child_name, tasks_data_source)


# --- Streamlit UI ---

# Set basic page configuration
st.set_page_config(layout="centered", page_title="Kids Task Tracker")

st.title("🏡 Family Task Tracker")
st.markdown("Here's a list of tasks for Ben and Matilda to help out at home. "
            "Some are 'must do' tasks, and others are 'could do' tasks that earn pocket money!")

# --- CSV Upload Section ---
st.sidebar.header("Upload Task List (CSV)")
st.sidebar.markdown("Upload a CSV file to customize the task list. Ensure it has columns: `id, description, type, applies_to, frequency, value`.")
st.sidebar.markdown("For `applies_to`, use comma-separated names (e.g., 'Ben,Matilda').")

uploaded_file = st.sidebar.file_uploader("Choose a CSV file", type="csv")

if uploaded_file is not None:
    # Load tasks from the uploaded CSV
    loaded_tasks = load_tasks_from_csv(uploaded_file)
    if loaded_tasks:
        st.session_state["TASK_DATA"] = loaded_tasks
        st.sidebar.success("Task list loaded from CSV!")
        # Re-initialize session state with the new task data, forcing a reset
        st.session_state.pop("last_daily_reset", None)
        st.session_state.pop("last_weekly_reset", None)
        st.session_state.pop("current_pocket_money", None)
        initialize_session_state(st.session_state["TASK_DATA"])
    else:
        st.session_state["TASK_DATA"] = DEFAULT_TASK_DATA # Fallback to default if CSV loading fails
        st.sidebar.error("Failed to load tasks from CSV. Using default tasks.")
        initialize_session_state(st.session_state["TASK_DATA"]) # Re-initialize with default
else:
    # Use default tasks if no file is uploaded or if the file uploader is empty
    if "TASK_DATA" not in st.session_state:
        st.session_state["TASK_DATA"] = DEFAULT_TASK_DATA
    initialize_session_state(st.session_state["TASK_DATA"]) # Initialize with current (default or previously loaded)

# The active TASK_DATA for the rest of the app will always be from session_state
CURRENT_ACTIVE_TASK_DATA = st.session_state["TASK_DATA"]


# Create tabs for each child to organize their task lists
tab_titles = [f"{child}'s Tasks" for child in CHILDREN]
tabs = st.tabs(tab_titles)

# Iterate through each child to render their respective task lists in their tab
for i, child_name in enumerate(CHILDREN):
    with tabs[i]:
        st.header(f"{child_name}'s Daily Tasks (Today: {st.session_state['last_daily_reset']})")

        # Section for Daily Must Do Tasks
        st.subheader("Daily Must Do Tasks")
        # Filter tasks relevant to the current child and type
        daily_must_dos = [t for t in CURRENT_ACTIVE_TASK_DATA if t["frequency"] == "daily" and t["type"] == "must_do" and child_name in t["applies_to"]]
        if daily_must_dos:
            for task in daily_must_dos:
                checkbox_key = f"daily_must_do_{child_name}_{task['id']}" # Unique key for each checkbox
                st.checkbox(
                    f"{task['description']}",
                    value=st.session_state["daily_task_status"][child_name].get(task["id"], False),
                    key=checkbox_key,
                    on_change=update_task_status_callback,
                    args=(child_name, task["id"], "daily", task["type"], CURRENT_ACTIVE_TASK_DATA)
                )
        else:
            st.info("No daily 'must do' tasks assigned yet!")

        # Section for Daily Could Do Tasks
        st.subheader("Daily Could Do Tasks (for Pocket Money)")
        daily_could_dos = [t for t in CURRENT_ACTIVE_TASK_DATA if t["frequency"] == "daily" and t["type"] == "could_do" and child_name in t["applies_to"]]
        if daily_could_dos:
            for task in daily_could_dos:
                checkbox_key = f"daily_could_do_{child_name}_{task['id']}"
                st.checkbox(
                    f"{task['description']} (+\${task['value']:.2f})", # Display pocket money value
                    value=st.session_state["daily_task_status"][child_name].get(task["id"], False),
                    key=checkbox_key,
                    on_change=update_task_status_callback,
                    args=(child_name, task["id"], "daily", task["type"], CURRENT_ACTIVE_TASK_DATA)
                )
        else:
            st.info("No daily 'could do' tasks assigned yet!")

        st.header(f"{child_name}'s Weekly Tasks (Week: {st.session_state['last_weekly_reset']})")

        # Section for Weekly Must Do Tasks
        st.subheader("Weekly Must Do Tasks")
        weekly_must_dos = [t for t in CURRENT_ACTIVE_TASK_DATA if t["frequency"] == "weekly" and t["type"] == "must_do" and child_name in t["applies_to"]]
        if weekly_must_dos:
            for task in weekly_must_dos:
                checkbox_key = f"weekly_must_do_{child_name}_{task['id']}"
                st.checkbox(
                    f"{task['description']}",
                    value=st.session_state["weekly_task_status"][child_name].get(task["id"], False),
                    key=checkbox_key,
                    on_change=update_task_status_callback,
                    args=(child_name, task["id"], "weekly", task["type"], CURRENT_ACTIVE_TASK_DATA)
                )
        else:
            st.info("No weekly 'must do' tasks assigned yet!")

        # Section for Weekly Could Do Tasks
        st.subheader("Weekly Could Do Tasks (for Pocket Money)")
        weekly_could_dos = [t for t in CURRENT_ACTIVE_TASK_DATA if t["frequency"] == "weekly" and t["type"] == "could_do" and child_name in t["applies_to"]]
        if weekly_could_dos:
            for task in weekly_could_dos:
                checkbox_key = f"weekly_could_do_{child_name}_{task['id']}"
                st.checkbox(
                    f"{task['description']} (+\${task['value']:.2f})",
                    value=st.session_state["weekly_task_status"][child_name].get(task["id"], False),
                    key=checkbox_key,
                    on_change=update_task_status_callback,
                    args=(child_name, task["id"], "weekly", task["type"], CURRENT_ACTIVE_TASK_DATA)
                )
        else:
            st.info("No weekly 'could do' tasks assigned yet!")

        st.markdown("---")
        # Display the total pocket money earned by the child
        st.metric(label=f"Total Pocket Money Earned by {child_name}", value=f"${st.session_state['current_pocket_money'][child_name]:.2f}")

# --- Sidebar for Admin Controls and Notes ---
st.sidebar.header("Admin Controls (Simulated)")
st.sidebar.warning("Note: This app uses in-memory storage. Data will reset if the page is refreshed, if a new session starts, or when the simulated reset buttons are used.")
st.sidebar.info("Daily tasks reset automatically each new day. Weekly tasks reset automatically with a new ISO week (Monday as start of week).")

# Button to manually simulate a daily reset
if st.sidebar.button("Simulate Daily Reset"):
    # Clear the tag to force a reset on next run
    st.session_state.pop("last_daily_reset", None)
    # Re-initialize to apply reset logic with the current active task data
    initialize_session_state(CURRENT_ACTIVE_TASK_DATA)
    st.experimental_rerun() # Rerun the app to reflect changes
    st.sidebar.success("Daily tasks reset simulated!")

# Button to manually simulate a weekly reset
if st.sidebar.button("Simulate Weekly Reset"):
    # Clear the tag to force a reset on next run
    st.session_state.pop("last_weekly_reset", None)
    # Re-initialize to apply reset logic with the current active task data
    initialize_session_state(CURRENT_ACTIVE_TASK_DATA)
    st.experimental_rerun() # Rerun the app to reflect changes
    st.sidebar.success("Weekly tasks reset simulated!")

