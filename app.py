import streamlit as st
import json
import os
from datetime import datetime, timedelta, time
import calendar
import pandas as pd
import random
from typing import Dict, List, Optional, Tuple
import hashlib

# Configuration
DATA_FOLDER = "shift_data"
USERS_FILE = os.path.join(DATA_FOLDER, "users.json")
SHIFTS_FILE = os.path.join(DATA_FOLDER, "shifts.json")

# Shift types and times
SHIFT_TYPES = {
    "morning": {"start": "06:00", "end": "14:00", "weekday": True},
    "late": {"start": "14:00", "end": "22:00", "weekday": True},
    "night": {"start": "22:00", "end": "06:00", "weekday": True},
    "weekend_morning": {"start": "06:00", "end": "18:00", "weekday": False},
    "weekend_night": {"start": "18:00", "end": "06:00", "weekday": False}
}

SHIFT_COMPATIBILITY = {
    "morning": ["weekend_morning"],
    "late": ["weekend_night"],
    "night": ["weekend_night"],
    "weekend_morning": ["morning"],
    "weekend_night": ["late", "night"]
}

# Utility functions
def ensure_data_folder():
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    ensure_data_folder()
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    ensure_data_folder()
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def load_shifts():
    ensure_data_folder()
    if os.path.exists(SHIFTS_FILE):
        with open(SHIFTS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_shifts(shifts):
    ensure_data_folder()
    with open(SHIFTS_FILE, 'w') as f:
        json.dump(shifts, f, indent=2)

def initialize_default_users():
    users = load_users()
    if not users:
        # Create head admin
        users["head_admin"] = {
            "username": "head_admin",
            "password": hash_password("admin123"),
            "role": "head_admin",
            "name": "Head Administrator",
            "email": "head@company.com",
            "primary_shift": "morning",
            "secondary_shift": "weekend_morning",
            "hourly_rate": 30.0
        }
        
        # Create 5 admins
        for i in range(1, 6):
            username = f"admin{i}"
            users[username] = {
                "username": username,
                "password": hash_password("admin123"),
                "role": "admin",
                "name": f"Admin {i}",
                "email": f"admin{i}@company.com",
                "primary_shift": list(SHIFT_TYPES.keys())[i % len(SHIFT_TYPES)],
                "secondary_shift": SHIFT_COMPATIBILITY[list(SHIFT_TYPES.keys())[i % len(SHIFT_TYPES)]][0],
                "hourly_rate": 25.0
            }
        
        # Create 25 employees
        for i in range(1, 26):
            username = f"emp{i}"
            users[username] = {
                "username": username,
                "password": hash_password("emp123"),
                "role": "employee",
                "name": f"Employee {i}",
                "email": f"emp{i}@company.com",
                "primary_shift": list(SHIFT_TYPES.keys())[i % len(SHIFT_TYPES)],
                "secondary_shift": SHIFT_COMPATIBILITY[list(SHIFT_TYPES.keys())[i % len(SHIFT_TYPES)]][0] if SHIFT_COMPATIBILITY[list(SHIFT_TYPES.keys())[i % len(SHIFT_TYPES)]] else "morning",
                "hourly_rate": 20.0
            }
        
        save_users(users)
    return users

def authenticate(username, password):
    users = load_users()
    if username in users and users[username]["password"] == hash_password(password):
        return users[username]
    return None

def get_shift_duration(start_time_str, end_time_str):
    start = datetime.strptime(start_time_str, "%H:%M")
    end = datetime.strptime(end_time_str, "%H:%M")
    
    if end < start:  # Night shift crossing midnight
        end += timedelta(days=1)
    
    duration = end - start
    return duration.total_seconds() / 3600

def calculate_pay(shift_data, hourly_rate):
    # Pay is calculated for approved shifts or manual payroll entries
    if shift_data.get("approved"):
        if shift_data.get("shift_type") == "manual_payroll" and "manual_amount" in shift_data:
            return shift_data["manual_amount"]
        else:
            start_time = shift_data.get("actual_start", shift_data["planned_start"])
            end_time = shift_data.get("actual_end", shift_data["planned_end"])
            hours = get_shift_duration(start_time, end_time)
            return hours * hourly_rate
    return 0

def calculate_payroll_for_user(username: str, hourly_rate: float, start_date_str: str, end_date_str: str) -> Tuple[float, float, List[Dict]]:
    """
    Calculates total hours and pay for a specific user within a date range based on approved shifts.
    Returns total_hours, total_pay, and a list of detailed shift data.
    """
    shifts = load_shifts()
    total_pay = 0.0
    total_hours = 0.0
    detailed_shifts = []

    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

    for shift_id, shift in shifts.items():
        shift_date = datetime.strptime(shift['date'], '%Y-%m-%d').date()
        
        # Check if the shift is assigned to the user, is approved, and falls within the date range
        if (username in shift.get('assigned_employees', []) and 
            shift.get('approved') and 
            start_date <= shift_date <= end_date):

            pay = calculate_pay(shift, hourly_rate)
            
            if shift.get("shift_type") == "manual_payroll":
                # For manual entries, hours are conceptually 0, actual pay is the manual amount
                hours = 0.0
                description = shift.get("description", "Manual Adjustment")
                detailed_shifts.append({
                    "Date": shift['date'],
                    "Shift Type": "Manual Entry",
                    "Planned Start": "N/A",
                    "Planned End": "N/A",
                    "Actual Start": "N/A",
                    "Actual End": "N/A",
                    "Hours": "N/A",
                    "Pay": f"€{pay:.2f}",
                    "Description": description
                })
            else:
                start_time = shift.get("actual_start", shift["planned_start"])
                end_time = shift.get("actual_end", shift["planned_end"])
                hours = get_shift_duration(start_time, end_time)
                
                detailed_shifts.append({
                    "Date": shift['date'],
                    "Shift Type": shift['shift_type'].replace('_', ' ').title(),
                    "Planned Start": shift['planned_start'],
                    "Planned End": shift['planned_end'],
                    "Actual Start": shift.get('actual_start', 'N/A'),
                    "Actual End": shift.get('actual_end', 'N/A'),
                    "Hours": f"{hours:.1f}",
                    "Pay": f"€{pay:.2f}",
                    "Description": "Regular Shift"
                })
            
            total_pay += pay
            total_hours += hours # Only sum actual hours for regular shifts

    
    return total_hours, total_pay, detailed_shifts

# Function to add dummy shift data for approval and payroll
def add_dummy_shift_data():
    shifts = load_shifts()
    users = load_users()
    employees = [u['username'] for u in users.values() if u['role'] == 'employee']

    if not employees:
        return

    today = datetime.now().date()

    # Always add 10 pending and 10 accepted shifts for approval
    for i in range(10):
        shift_id = f"dummy_pending_{today.strftime('%Y%m%d')}_{i}"
        random_employee = random.choice(employees)
        shift_date = today - timedelta(days=random.randint(0, 10))
        shift_type = random.choice(list(SHIFT_TYPES.keys()))
        start_time = SHIFT_TYPES[shift_type]['start']
        end_time = SHIFT_TYPES[shift_type]['end']
        shifts[shift_id] = {
            "id": shift_id,
            "date": shift_date.strftime('%Y-%m-%d'),
            "shift_type": shift_type,
            "planned_start": start_time,
            "planned_end": end_time,
            "assigned_employees": [random_employee],
            "assigned_admin": f"admin{random.randint(1, 5)}",
            "status": "pending",
            "approved": False,
            "actual_start": None,
            "actual_end": None
        }

    for i in range(10):
        shift_id = f"dummy_accepted_{today.strftime('%Y%m%d')}_{i}"
        random_employee = random.choice(employees)
        shift_date = today - timedelta(days=random.randint(0, 10))
        shift_type = random.choice(list(SHIFT_TYPES.keys()))
        start_time = SHIFT_TYPES[shift_type]['start']
        end_time = SHIFT_TYPES[shift_type]['end']
        shifts[shift_id] = {
            "id": shift_id,
            "date": shift_date.strftime('%Y-%m-%d'),
            "shift_type": shift_type,
            "planned_start": start_time,
            "planned_end": end_time,
            "assigned_employees": [random_employee],
            "assigned_admin": f"admin{random.randint(1, 5)}",
            "status": "accepted",
            "approved": False,
            "actual_start": None,
            "actual_end": None
        }

    save_shifts(shifts)


def generate_yearly_shifts_for_all_employees():
    """Generate 1-7 random shifts per week for each employee for the past year, enforcing 12hr downtime and only primary/secondary shifts."""
    users = load_users()
    employees = [u for u in users.values() if u['role'] == 'employee']
    admins = [u for u in users.values() if u['role'] == 'admin']
    shifts = {}

    today = datetime.now().date()
    start_date = today - timedelta(days=365)

    for emp in employees:
        emp_shift_count = 0
        week_start = start_date
        last_shift_end = None  # Track last shift end datetime

        # Only allow primary and secondary shift types
        allowed_shift_types = [emp['primary_shift']]
        if emp.get('secondary_shift') and emp['secondary_shift'] != 'None':
            allowed_shift_types.append(emp['secondary_shift'])

        while week_start < today:
            num_shifts = random.randint(1, 7)
            days_this_week = random.sample(range(7), num_shifts)
            days_this_week.sort()  # Ensure chronological order

            for d in days_this_week:
                shift_date = week_start + timedelta(days=d)
                if shift_date > today:
                    continue

                # Pick only allowed shift types
                shift_type = random.choice(allowed_shift_types)
                start_time = SHIFT_TYPES[shift_type]['start']
                end_time = SHIFT_TYPES[shift_type]['end']

                # Calculate actual start/end datetimes
                start_dt = datetime.combine(shift_date, datetime.strptime(start_time, "%H:%M").time()) + timedelta(minutes=random.randint(-10, 10))
                end_dt = datetime.combine(shift_date, datetime.strptime(end_time, "%H:%M").time()) + timedelta(minutes=random.randint(-10, 10))
                if end_dt <= start_dt:
                    end_dt += timedelta(days=1)

                # Enforce 12-hour downtime
                if last_shift_end and (start_dt - last_shift_end).total_seconds() < 12 * 3600:
                    continue  # Skip this shift, not enough downtime

                shift_id = f"auto_{emp['username']}_{shift_date.strftime('%Y%m%d')}_{emp_shift_count}"
                shifts[shift_id] = {
                    "id": shift_id,
                    "date": shift_date.strftime('%Y-%m-%d'),
                    "shift_type": shift_type,
                    "planned_start": start_time,
                    "planned_end": end_time,
                    "assigned_employees": [emp['username']],
                    "assigned_admin": random.choice(admins)['username'] if admins else None,
                    "status": "approved",
                    "approved": True,
                    "actual_start": start_dt.strftime("%H:%M"),
                    "actual_end": end_dt.strftime("%H:%M")
                }
                emp_shift_count += 1
                last_shift_end = end_dt

                if emp_shift_count >= 350:
                    break
            week_start += timedelta(days=7)
            if emp_shift_count >= 350:
                break

        # If not enough shifts, fill up to at least 50, still respecting downtime and allowed shifts
        while emp_shift_count < 50:
            random_day = start_date + timedelta(days=random.randint(0, 364))
            shift_type = random.choice(allowed_shift_types)
            start_time = SHIFT_TYPES[shift_type]['start']
            end_time = SHIFT_TYPES[shift_type]['end']
            start_dt = datetime.combine(random_day, datetime.strptime(start_time, "%H:%M").time()) + timedelta(minutes=random.randint(-10, 10))
            end_dt = datetime.combine(random_day, datetime.strptime(end_time, "%H:%M").time()) + timedelta(minutes=random.randint(-10, 10))
            if end_dt <= start_dt:
                end_dt += timedelta(days=1)
            if last_shift_end and (start_dt - last_shift_end).total_seconds() < 12 * 3600:
                continue
            shift_id = f"auto_{emp['username']}_extra_{emp_shift_count}"
            shifts[shift_id] = {
                "id": shift_id,
                "date": random_day.strftime('%Y-%m-%d'),
                "shift_type": shift_type,
                "planned_start": start_time,
                "planned_end": end_time,
                "assigned_employees": [emp['username']],
                "assigned_admin": random.choice(admins)['username'] if admins else None,
                "status": "approved",
                "approved": True,
                "actual_start": start_dt.strftime("%H:%M"),
                "actual_end": end_dt.strftime("%H:%M")
            }
            emp_shift_count += 1
            last_shift_end = end_dt

    save_shifts(shifts)

# Main App
def main():
    st.set_page_config(page_title="Shift Management System", layout="wide")
    
    # Initialize session state
    if "user" not in st.session_state:
        st.session_state.user = None
    
    # Initialize default users
    initialize_default_users()
    # Only generate dummy shifts if there are no shifts yet
    if not load_shifts():
        generate_yearly_shifts_for_all_employees()
    
    if st.session_state.user is None:
        login_page()
    else:
        if st.session_state.user["role"] == "employee":
            employee_dashboard()
        elif st.session_state.user["role"] == "admin":
            admin_dashboard()
        elif st.session_state.user["role"] == "head_admin":
            head_admin_dashboard()

def login_page():
    st.title("🕐 Shift Management System")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login", use_container_width=True):
            user = authenticate(username, password)
            if user:
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Invalid credentials")

              
        
        

def employee_dashboard():
    st.title(f"Welcome, {st.session_state.user['name']}")
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Choose page", [
        "Profile", "Work Calendar", "Timesheet", "My Shifts"
    ])
    
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()
    
    if page == "Profile":
        employee_profile()
    elif page == "Work Calendar":
        employee_calendar()
    elif page == "Timesheet":
        employee_timesheet()
    elif page == "My Shifts":
        employee_shifts()

def employee_profile():
    st.header("My Profile")
    user = st.session_state.user
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Personal Information")
        st.write(f"**Name:** {user['name']}")
        st.write(f"**Username:** {user['username']}")
        st.write(f"**Email:** {user['email']}")
        st.write(f"**Role:** {user['role'].title()}")
    
    with col2:
        st.subheader("Work Information")
        st.write(f"**Primary Shift:** {user['primary_shift'].replace('_', ' ').title()}")
        st.write(f"**Secondary Shift:** {user['secondary_shift'].replace('_', ' ').title()}")
        st.write(f"**Hourly Rate:** €{user['hourly_rate']:.2f}")

def employee_calendar():
    st.header("Work Calendar")
    
    view_type = st.selectbox("View", ["Monthly", "Weekly"])
    
    shifts = load_shifts()
    user_shifts = {k: v for k, v in shifts.items() if st.session_state.user['username'] in v.get('assigned_employees', [])}
    
    if view_type == "Monthly":
        show_monthly_calendar(user_shifts)
    else:
        show_weekly_calendar(user_shifts)

def show_monthly_calendar(user_shifts):
    today = datetime.now()
    year = st.selectbox("Year", range(today.year - 1, today.year + 2), index=1)
    month = st.selectbox("Month", range(1, 13), index=today.month - 1)
    
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    
    st.subheader(f"{month_name} {year}")
    
    # Create calendar grid
    cols = st.columns(7)
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    
    for i, day in enumerate(days):
        cols[i].write(f"**{day}**")
    
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].write("")
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                day_shifts = [shift for shift_id, shift in user_shifts.items() if shift['date'] == date_str]
                
                with cols[i]:
                    st.write(f"**{day}**") # Make day number bold
                    for shift in day_shifts:
                        # Logic to display pay only if shift is approved/completed AND in the past
                        shift_datetime_str = f"{shift['date']} {shift.get('actual_end', shift['planned_end'])}"
                        shift_end_datetime = datetime.strptime(shift_datetime_str, '%Y-%m-%d %H:%M')
                        
                        if shift.get("shift_type") == "manual_payroll":
                             st.success(f"💰 Manual Pay (€{shift['manual_amount']:.2f})")
                             with st.expander("Details"):
                                 st.write(f"Description: {shift.get('description', 'N/A')}")
                                 st.write(f"Amount: €{shift['manual_amount']:.2f}")
                        elif shift.get('approved') and shift_end_datetime < datetime.now():
                            # Past and approved: show pay
                            pay = calculate_pay(shift, st.session_state.user['hourly_rate'])
                            st.success(f"✓ {shift['shift_type'].replace('_', ' ').title()} (€{pay:.2f})")
                            with st.expander(f"Details for {shift['shift_type'].replace('_', ' ').title()}"):
                                st.write(f"Planned: {shift['planned_start']} - {shift['planned_end']}")
                                st.write(f"Actual: {shift.get('actual_start', 'N/A')} - {shift.get('actual_end', 'N/A')}")
                                st.write(f"Pay: €{pay:.2f}")
                                hours_worked = get_shift_duration(shift.get('actual_start', shift['planned_start']), shift.get('actual_end', shift['planned_end']))
                                st.write(f"Hours: {hours_worked:.1f}")
                        elif shift.get('status') == 'accepted':
                            st.info(f"• {shift['shift_type'].replace('_', ' ').title()}")
                            with st.expander(f"Details for {shift['shift_type'].replace('_', ' ').title()}"):
                                st.write(f"Planned: {shift['planned_start']} - {shift['planned_end']}")
                                st.write("Status: Accepted (Pending Approval)")
                        elif shift.get('status') == 'pending':
                            st.warning(f"? {shift['shift_type'].replace('_', ' ').title()}")
                            with st.expander(f"Details for {shift['shift_type'].replace('_', ' ').title()}"):
                                st.write(f"Planned: {shift['planned_start']} - {shift['planned_end']}")
                                st.write("Status: Pending Employee Confirmation")
                        else: # declined or cancelled
                            st.error(f"✗ {shift['shift_type'].replace('_', ' ').title()}")
                            with st.expander(f"Details for {shift['shift_type'].replace('_', ' ').title()}"):
                                st.write(f"Planned: {shift['planned_start']} - {shift['planned_end']}")
                                st.write(f"Status: {shift.get('status', 'Declined').title()}") # Default to Declined if status missing

def show_weekly_calendar(user_shifts):
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday()) # Monday of current week
    
    week_offset = st.slider("Week offset", -4, 4, 0) # Allows navigating weeks
    selected_week_start = start_of_week + timedelta(weeks=week_offset)
    
    st.subheader(f"Week of {selected_week_start.strftime('%B %d, %Y')}")
    
    for i in range(7):
        current_date = selected_week_start + timedelta(days=i)
        date_str = current_date.strftime('%Y-%m-%d')
        day_name = current_date.strftime('%A')
        
        st.write(f"**{day_name}, {current_date.strftime('%B %d')}**")
        
        day_shifts = [shift for shift_id, shift in user_shifts.items() if shift['date'] == date_str]
        
        if day_shifts:
            for shift in day_shifts:
                if shift.get("shift_type") == "manual_payroll":
                    with st.expander(f"Manual Pay on {shift['date']}"):
                        st.write(f"Description: {shift.get('description', 'N/A')}")
                        st.success(f"**Amount: €{shift['manual_amount']:.2f}**")
                else:
                    shift_datetime_str = f"{shift['date']} {shift.get('actual_end', shift['planned_end'])}"
                    shift_end_datetime = datetime.strptime(shift_datetime_str, '%Y-%m-%d %H:%M')
                    
                    with st.expander(f"{shift['shift_type'].replace('_', ' ').title()} ({shift['planned_start']} - {shift['planned_end']})"):
                        st.write(f"Planned: {shift['planned_start']} - {shift['planned_end']}")
                        if shift_end_datetime < datetime.now(): # Past shift
                            if shift.get('approved'):
                                pay = calculate_pay(shift, st.session_state.user['hourly_rate'])
                                hours_worked = get_shift_duration(shift.get('actual_start', shift['planned_start']), shift.get('actual_end', shift['planned_end']))
                                st.write(f"Actual: {shift.get('actual_start', 'N/A')} - {shift.get('actual_end', 'N/A')}")
                                st.write(f"Hours: {hours_worked:.1f}")
                                st.success(f"**Pay: €{pay:.2f}**")
                            else:
                                st.warning("Shift Completed, but not yet approved for pay.")
                                st.write(f"Actual: {shift.get('actual_start', 'N/A')} - {shift.get('actual_end', 'N/A')}")
                        else: # Current or Future shift
                            st.info("Pay will be calculated after shift completion and approval.")
                            st.write(f"Status: {shift.get('status', 'Pending').title()}") # Show current status

        else:
            st.info("No shifts")
        
        st.write("---")

def employee_timesheet():
    st.header("Timesheet & Pay")
    
    # Allow user to select a period for the timesheet
    period_options = ["This Week", "This Month", "Last Month", "This Year", "Custom Range"]
    selected_period = st.selectbox("Select Period", period_options)

    today = datetime.now()
    start_date = None
    end_date = None

    if selected_period == "This Week":
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
    elif selected_period == "This Month":
        start_date = today.replace(day=1)
        end_date = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1) # Last day of month
    elif selected_period == "Last Month":
        last_month_end = today.replace(day=1) - timedelta(days=1)
        start_date = last_month_end.replace(day=1)
        end_date = last_month_end
    elif selected_period == "This Year":
        start_date = today.replace(month=1, day=1)
        end_date = today.replace(month=12, day=31)
    elif selected_period == "Custom Range":
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", today.replace(day=1).date())
        with col2:
            end_date = st.date_input("End Date", today.date())
        # Convert date objects back to datetime
        start_date = datetime.combine(start_date, datetime.min.time())
        end_date = datetime.combine(end_date, datetime.max.time())
    
    if start_date and end_date:
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')

        total_hours, total_pay, detailed_shifts = calculate_payroll_for_user(
            st.session_state.user['username'],
            st.session_state.user['hourly_rate'],
            start_date_str,
            end_date_str
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Hours", f"{total_hours:.1f}")
        with col2:
            st.metric("Total Pay", f"€{total_pay:.2f}")
        with col3:
            st.metric("Avg. Hourly Rate", f"€{total_pay/total_hours:.2f}" if total_hours > 0 else "€0.00")
        
        st.subheader(f"Detailed Shifts for {selected_period}")
        if detailed_shifts:
            df = pd.DataFrame(detailed_shifts)
            # Ensure 'Date' column is datetime for sorting
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values(by='Date', ascending=False).reset_index(drop=True)
            # Display only relevant columns for employees
            display_cols = ["Date", "Shift Type", "Planned Start", "Planned End", "Actual Start", "Actual End", "Hours", "Pay", "Description"]
            st.dataframe(df[display_cols], use_container_width=True)
        else:
            st.info("No approved shifts or manual entries found for the selected period.")
    else:
        st.warning("Please select a valid date range for the timesheet.")
        

def employee_shifts():
    st.header("My Shifts")
    
    shifts = load_shifts()
    user_shifts = {k: v for k, v in shifts.items() if st.session_state.user['username'] in v.get('assigned_employees', [])}
    
    # Filter out manual payroll entries as they are not "shifts" to accept/decline
    pending_shifts = {k: v for k, v in user_shifts.items() if v.get('status') == 'pending' and v.get('shift_type') != 'manual_payroll'}
    
    if pending_shifts:
        st.subheader("Pending Shifts - Action Required")
        for shift_id, shift in pending_shifts.items():
            with st.expander(f"{shift['date']} - {shift['shift_type'].replace('_', ' ').title()}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Date:** {shift['date']}")
                    st.write(f"**Time:** {shift['planned_start']} - {shift['planned_end']}")
                    st.write(f"**Type:** {shift['shift_type'].replace('_', ' ').title()}")
                
                with col2:
                    if st.button(f"Accept", key=f"accept_{shift_id}"):
                        shifts[shift_id]['status'] = 'accepted'
                        save_shifts(shifts)
                        st.success("Shift accepted! Awaiting Admin approval for pay.")
                        st.rerun()
                    
                    if st.button(f"Decline", key=f"decline_{shift_id}"):
                        shifts[shift_id]['status'] = 'declined'
                        save_shifts(shifts)
                        st.error("Shift declined!")
                        st.rerun()
    
    # All shifts (excluding manual payroll entries for this view)
    st.subheader("All My Shifts (Excluding Manual Entries)")
    
    shift_display_data = []
    for shift_id, shift in user_shifts.items():
        if shift.get('shift_type') == 'manual_payroll':
            continue # Skip manual entries in this view

        status = shift.get('status', 'pending')
        if shift.get('approved'):
            status = 'approved'
        
        shift_display_data.append({
            "Date": shift['date'],
            "Shift Type": shift['shift_type'].replace('_', ' ').title(),
            "Time": f"{shift['planned_start']} - {shift['planned_end']}",
            "Status": status.title()
        })
    
    if shift_display_data:
        df = pd.DataFrame(shift_display_data)
        # Ensure 'Date' column is datetime for sorting
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values(by='Date', ascending=False).reset_index(drop=True)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No shifts assigned")

def admin_dashboard():
    st.title(f"Admin Dashboard - {st.session_state.user['name']}")
    
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Choose page", [
        "Dashboard", "Manage Shifts", "Approve Shifts", "Employee Management", "Create Employee", "Employee Payroll"
    ])
    
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()
    
    if page == "Dashboard":
        admin_dashboard_overview()
    elif page == "Manage Shifts":
        admin_manage_shifts()
    elif page == "Approve Shifts":
        admin_approve_shifts()
    elif page == "Employee Management":
        admin_employee_management()
    elif page == "Create Employee":
        admin_create_employee()
    elif page == "Employee Payroll":
        admin_employee_payroll()

def admin_dashboard_overview():
    st.header("Dashboard Overview")

    users = load_users()
    shifts = load_shifts()

    # Statistics (Row 1)
    col1, col2, col3, col4 = st.columns(4)

    employees = [u for u in users.values() if u['role'] == 'employee']
    admins = [u for u in users.values() if u['role'] == 'admin']
    
    # Filter out manual payroll entries from total_shifts and pending_approvals for a more accurate count of *actual* shifts
    actual_shifts = {sid: s for sid, s in shifts.items() if s.get('shift_type') != 'manual_payroll'}
    total_shifts = len(actual_shifts)
    pending_approvals = len([s for s in actual_shifts.values() if s.get('status') == 'accepted' and not s.get('approved')])
    active_shifts_today = len([s for s in actual_shifts.values() if s['date'] == datetime.now().strftime('%Y-%m-%d')])

    with col1:
        st.metric("Total Employees", len(employees))
    with col2:
        st.metric("Total Admins", len(admins))
    with col3:
        st.metric("Total Shifts", total_shifts)
    with col4:
        st.metric("Pending Approvals", pending_approvals)

    st.markdown("---") 
    st.subheader("Current Shift Status")
    col_single = st.columns(1) 
    with col_single[0]:
        st.metric("Active Shifts Today", active_shifts_today)

def admin_manage_shifts():
    st.header("Manage Shifts (Admin)")
    st.markdown("---")
    st.subheader("Create New Shift")

    users = load_users()
    employees = {u['username']: u for u in users.values() if u['role'] == 'employee'}
    
    shift_date = st.date_input("Shift Date", datetime.now().date())

    # Multi-select for assigning employees
    all_employee_names = {u['username']: u['name'] for u in employees.values()}
    selected_employees = st.multiselect(
        "Assign Employees",
        options=list(all_employee_names.keys()),
        format_func=lambda x: all_employee_names[x]
    )

    # --- Only allow shift types that are primary or secondary for ALL selected employees ---
    if selected_employees:
        # Get intersection of allowed shift types for all selected employees
        allowed_shift_sets = []
        for emp_username in selected_employees:
            emp = employees[emp_username]
            allowed = {emp['primary_shift']}
            if emp.get('secondary_shift') and emp['secondary_shift'] != 'None':
                allowed.add(emp['secondary_shift'])
            allowed_shift_sets.append(allowed)
        # Only allow shift types that are in ALL selected employees' allowed shifts
        available_shift_types = list(set.union(*allowed_shift_sets))
    else:
        # If no employee selected, show nothing
        available_shift_types = []

    if not available_shift_types:
        st.warning("Select employees to see available shift types (only their primary/secondary shifts are allowed).")
        return

    shift_type = st.selectbox(
        "Shift Type",
        available_shift_types,
        format_func=lambda x: (
            f"{x.replace('_', ' ').title()} (Primary)" if x == employees[selected_employees[0]]['primary_shift']
            else f"{x.replace('_', ' ').title()} (Secondary)"
        ) if len(selected_employees) == 1 else x.replace('_', ' ').title()
    )

    default_start_time_str = SHIFT_TYPES[shift_type]['start']
    default_end_time_str = SHIFT_TYPES[shift_type]['end']

    # Initialize planned_end_time with the default end time
    planned_end_time = default_end_time_str

    col1, col2 = st.columns(2)
    with col1:
        planned_start_time = st.text_input("Planned Start Time (HH:MM)", default_start_time_str)
    with col2:
        # Auto-calculate end time based on entered start time and shift duration
        try:
            # Calculate default duration for the shift type
            default_start = datetime.strptime(default_start_time_str, "%H:%M")
            default_end = datetime.strptime(default_end_time_str, "%H:%M")
            if default_end <= default_start:
                default_end += timedelta(days=1)
            default_duration = default_end - default_start

            user_start = datetime.strptime(planned_start_time, "%H:%M")
            user_end = user_start + default_duration
            planned_end_time = user_end.strftime("%H:%M")
        except Exception:
            planned_end_time = default_end_time_str

        planned_end_time = st.text_input("Planned End Time (HH:MM)", planned_end_time)

    # Basic time format validation
    try:
        datetime.strptime(planned_start_time, "%H:%M")
        datetime.strptime(planned_end_time, "%H:%M")
        time_format_valid = True
    except ValueError:
        st.error("Invalid time format. Please use HH:MM (e.g., 09:00, 14:30).")
        time_format_valid = False

    # Optional: Assign an Admin to this shift
    admins = {u['username']: u for u in users.values() if u['role'] == 'admin'}
    all_admin_names = {u['username']: u['name'] for u in admins.values()}
    selected_admin = st.selectbox(
        "Assign Admin (Optional)",
        options=['None'] + list(all_admin_names.keys()),
        format_func=lambda x: all_admin_names.get(x, x)
    )

    # Option to set status directly for testing/admin purposes
    initial_shift_status = st.selectbox(
        "Initial Shift Status",
        options=["pending", "accepted", "approved"],
        index=1,
        help="Set the initial status of the shift. 'Pending' requires employee acceptance. 'Accepted' means employee accepted, awaiting admin approval. 'Approved' means it's ready for payroll."
    )

    # --- 12-Hour Downtime Check ---
    shifts = load_shifts()
    downtime_violations = []
    planned_start_dt = datetime.combine(shift_date, datetime.strptime(planned_start_time, "%H:%M").time())
    for emp_username in selected_employees:
        emp_shifts = [
            s for s in shifts.values()
            if emp_username in s.get('assigned_employees', []) and s.get('date')
        ]
        # Find the latest shift that ends before the new shift's planned start
        latest_end_dt = None
        for s in emp_shifts:
            shift_end_date = datetime.strptime(s['date'], '%Y-%m-%d')
            end_time = s.get('planned_end', '00:00')
            end_dt = datetime.combine(shift_end_date, datetime.strptime(end_time, "%H:%M").time())
            if end_dt <= datetime.combine(shift_end_date, datetime.strptime(s.get('planned_start', '00:00'), "%H:%M").time()):
                end_dt += timedelta(days=1)
            if end_dt <= planned_start_dt:
                if not latest_end_dt or end_dt > latest_end_dt:
                    latest_end_dt = end_dt
        # Check downtime
        if latest_end_dt:
            hours_diff = (planned_start_dt - latest_end_dt).total_seconds() / 3600
            if hours_diff < 12:
                downtime_violations.append(emp_username)

    if downtime_violations:
        names = ", ".join([all_employee_names[u] for u in downtime_violations])
        st.warning(f"⚠️ The following employees have less than 12 hours downtime before this shift: {names}. Downtime should be at least 12 hours.")

    if st.button("Create Shift") and time_format_valid:
        if not selected_employees:
            st.error("Please assign at least one employee to the shift.")
        elif downtime_violations:
            st.error("Cannot create shift: All assigned employees must have at least 12 hours downtime since their last shift.")
        else:
            shifts = load_shifts()
            new_shift_id = f"shift_{len(shifts) + 1}"

            # Set approval and actual times based on status
            if initial_shift_status == 'approved':
                actual_start_time = planned_start_time
                actual_end_time = planned_end_time
                approved_status = True
            else:
                actual_start_time = None
                actual_end_time = None
                approved_status = False

            new_shift = {
                "id": new_shift_id,
                "date": shift_date.strftime('%Y-%m-%d'),
                "shift_type": shift_type,
                "planned_start": planned_start_time,
                "planned_end": planned_end_time,
                "assigned_employees": selected_employees,
                "assigned_admin": selected_admin if selected_admin != 'None' else None,
                "status": initial_shift_status,
                "approved": approved_status,
                "actual_start": actual_start_time,
                "actual_end": actual_end_time
            }
            shifts[new_shift_id] = new_shift
            save_shifts(shifts)
            st.success("Shift created and assigned!")
            st.rerun() # Refresh to clear form

    st.markdown("---")
    st.subheader("Existing Shifts")
    all_shifts = load_shifts()
    
    shift_display_data = []
    for shift_id, shift in all_shifts.items():
        if shift.get('shift_type') == 'manual_payroll':
            continue # Skip manual entries in this general shift overview

        assigned_emps = ", ".join([users[emp_id]['name'] for emp_id in shift['assigned_employees'] if emp_id in users]) if shift.get('assigned_employees') else "N/A"
        assigned_adm = users[shift['assigned_admin']]['name'] if shift.get('assigned_admin') and shift['assigned_admin'] in users else "N/A"
        
        shift_display_data.append({
            "Shift ID": shift_id,
            "Date": shift['date'],
            "Type": shift['shift_type'].replace('_', ' ').title(),
            "Planned Time": f"{shift['planned_start']} - {shift['planned_end']}",
            "Assigned Employees": assigned_emps,
            "Assigned Admin": assigned_adm,
            "Status": shift.get('status', 'Pending').title(),
            "Approved": "Yes" if shift.get('approved') else "No"
        })
    
    if shift_display_data:
        df_shifts = pd.DataFrame(shift_display_data)
        df_shifts['Date'] = pd.to_datetime(df_shifts['Date'])
        df_shifts = df_shifts.sort_values(by='Date', ascending=False).reset_index(drop=True)
        st.dataframe(df_shifts, use_container_width=True)
    else:
        st.info("No shifts created yet.")


def admin_approve_shifts():
    st.header("Approve Shifts (Admin)")

    # Only add dummy data if there are less than 10 pending/accepted shifts
    shifts = load_shifts()
    pending_or_accepted = [
        s for s in shifts.values()
        if s.get('status') in ['pending', 'accepted'] and s.get('shift_type') != 'manual_payroll'
    ]
    if len(pending_or_accepted) < 10:
        add_dummy_shift_data()
    shifts = load_shifts()

    users = load_users()

    # Filter for shifts that are accepted or pending by employees but not yet approved by admin
    # AND are not manual payroll entries
    pending_approval_shifts = {
        sid: s for sid, s in shifts.items() 
        if s.get('status') in ['accepted', 'pending'] and not s.get('approved') and s.get('shift_type') != 'manual_payroll'
    }

    if not pending_approval_shifts:
        st.info("No shifts pending approval.")
        return

    st.write("Review and approve employee shifts for payroll.")

    for shift_id, shift in pending_approval_shifts.items():
        assigned_emps_names = [users[emp_id]['name'] for emp_id in shift.get('assigned_employees', []) if emp_id in users]
        
        with st.expander(f"Shift on {shift['date']} - {shift['shift_type'].replace('_', ' ').title()} for {', '.join(assigned_emps_names)}"):
            st.write(f"**Planned Time:** {shift['planned_start']} - {shift['planned_end']}")
            st.write(f"**Assigned Employees:** {', '.join(assigned_emps_names)}")
            st.write(f"**Current Status:** {shift.get('status', 'pending').title()}")

            approval_type = st.radio(
                f"Approval Type for {shift_id}",
                ["Full Approval", "Partial Approval"],
                key=f"approval_type_{shift_id}"
            )

            actual_start_time = shift['planned_start']
            actual_end_time = shift['planned_end']

            if approval_type == "Partial Approval":
                col1, col2 = st.columns(2)
                with col1:
                    actual_start_time = st.text_input(
                        "Actual Start Time (HH:MM)",
                        shift['planned_start'],
                        key=f"actual_start_{shift_id}"
                    )
                with col2:
                    actual_end_time = st.text_input(
                        "Actual End Time (HH:MM)",
                        shift['planned_end'],
                        key=f"actual_end_{shift_id}"
                    )
                
                # Basic validation for actual times
                try:
                    datetime.strptime(actual_start_time, "%H:%M")
                    datetime.strptime(actual_end_time, "%H:%M")
                    time_valid = True
                except ValueError:
                    st.error("Invalid time format for actual times. Please use HH:MM.")
                    time_valid = False
            else:
                time_valid = True # No time input needed for full approval

            if st.button(f"Approve Shift {shift_id}", key=f"approve_{shift_id}"):
                if time_valid:
                    shifts[shift_id]['approved'] = True
                    shifts[shift_id]['actual_start'] = actual_start_time
                    shifts[shift_id]['actual_end'] = actual_end_time
                    shifts[shift_id]['status'] = 'approved' # Update status to approved
                    save_shifts(shifts)
                    st.success(f"Shift {shift_id} approved with actual times: {actual_start_time} - {actual_end_time}")
                    st.rerun()
                else:
                    st.error("Cannot approve due to invalid time format.")


def admin_employee_management():
    st.header("Employee Management (Admin)")
    st.info("This section will allow admins to view detailed information about employees. Creation is handled under 'Create Employee'.")
    
    users = load_users()
    employees = {u['username']: u for u in users.values() if u['role'] == 'employee'}

    if not employees:
        st.info("No employees found.")
        return
    
    st.subheader("All Employees")
    
    employee_data = []
    for username, user_data in employees.items():
        employee_data.append({
            "Username": username,
            "Name": user_data.get('name', 'N/A'),
            "Email": user_data.get('email', 'N/A'),
            "Primary Shift": user_data.get('primary_shift', 'N/A').replace('_', ' ').title(),
            "Hourly Rate": f"€{user_data.get('hourly_rate', 0.0):.2f}"
        })
    
    if employee_data:
        df = pd.DataFrame(employee_data)
        st.dataframe(df, use_container_width=True)


def admin_create_employee():
    st.header("Create New Employee Account")
    
    users = load_users()

    with st.form("create_employee_form"):
        new_username = st.text_input("Username", help="Must be unique")
        new_password = st.text_input("Password", type="password")
        new_name = st.text_input("Full Name")
        new_email = st.text_input("Email")
        
        # Select primary shift
        primary_shift_options = list(SHIFT_TYPES.keys())
        new_primary_shift = st.selectbox(
            "Primary Shift Type", 
            primary_shift_options,
            format_func=lambda x: x)
        # Define secondary_shift_options based on selected primary shift
        secondary_shift_options = SHIFT_COMPATIBILITY.get(new_primary_shift, [])
        if secondary_shift_options:
            new_secondary_shift = st.selectbox(
                "Secondary Shift Type (Optional)", 
                ['None'] + secondary_shift_options,
                format_func=lambda x: x.replace('_', ' ').title()
            )
        else:
            new_secondary_shift = 'None'
            st.info("No compatible secondary shifts for the selected primary shift.")
            
        new_hourly_rate = st.number_input("Hourly Rate (€)", min_value=0.0, value=20.0, step=0.5)

        submitted = st.form_submit_button("Create Employee")

        if submitted:
            if not new_username or not new_password or not new_name or not new_email:
                st.error("Please fill in all required fields (Username, Password, Full Name, Email).")
            elif new_username in users:
                st.error(f"Username '{new_username}' already exists. Please choose a different one.")
            else:
                users[new_username] = {
                    "username": new_username,
                    "password": hash_password(new_password),
                    "role": "employee",
                    "name": new_name,
                    "email": new_email,
                    "primary_shift": new_primary_shift,
                    "secondary_shift": new_secondary_shift if new_secondary_shift != 'None' else None,
                    "hourly_rate": new_hourly_rate
                }
                save_users(users)
                st.success(f"Employee '{new_name}' created successfully!")
                st.rerun() # Refresh to clear form fields


def admin_employee_payroll():
    st.header("Employee Payroll (Admin)")

    users = load_users()
    employees = {u['username']: u for u in users.values() if u['role'] == 'employee'}
    admins = {u['username']: u for u in users.values() if u['role'] == 'admin'}

    # --- DUMMY PAYROLL GENERATION SECTION ---
    shifts = load_shifts()
    today = datetime.now().date()
    # Generate dummy payrolls for last 6 months and last year
    for user_dict in list(employees.values()) + list(admins.values()):
        username = user_dict['username']
        # Last 6 months
        for i in range(6):
            month_date = (today.replace(day=1) - timedelta(days=1)).replace(day=1) - timedelta(days=30*i)
            period_label = f"Last {i+1} Month"
            dummy_id = f"dummy_payroll_{period_label.replace(' ', '_').lower()}_{username}"
            if dummy_id not in shifts:
                shifts[dummy_id] = {
                    "id": dummy_id,
                    "date": month_date.strftime('%Y-%m-%d'),
                    "shift_type": "manual_payroll",
                    "planned_start": "00:00",
                    "planned_end": "00:00",
                    "assigned_employees": [username],
                    "assigned_admin": st.session_state.user['username'],
                    "status": "approved",
                    "approved": True,
                    "actual_start": "00:00",
                    "actual_end": "00:00",
                    "manual_amount": round(random.uniform(500, 2000), 2),
                    "description": f"Dummy Payroll {period_label} ({month_date.strftime('%B %Y')})"
                }
        # Last year
        year_date = today.replace(year=today.year - 1, day=1, month=1)
        period_label = "Last Year"
        dummy_id = f"dummy_payroll_last_year_{username}"
        if dummy_id not in shifts:
            shifts[dummy_id] = {
                "id": dummy_id,
                "date": year_date.strftime('%Y-%m-%d'),
                "shift_type": "manual_payroll",
                "planned_start": "00:00",
                "planned_end": "00:00",
                "assigned_employees": [username],
                "assigned_admin": st.session_state.user['username'],
                "status": "approved",
                "approved": True,
                "actual_start": "00:00",
                "actual_end": "00:00",
                "manual_amount": round(random.uniform(8000, 25000), 2),
                "description": f"Dummy Payroll Last Year ({year_date.strftime('%Y')})"
            }
    save_shifts(shifts)
    # --- END DUMMY PAYROLL GENERATION SECTION ---

    if not employees and not admins:
        st.info("No employees or admins to calculate payroll for.")
        return

    st.subheader("Calculate Payroll for Employees/Admins")
    
    all_user_options = {**employees, **admins}
    selected_user_username = st.selectbox(
        "Select Employee/Admin",
        options=['All Users'] + list(all_user_options.keys()),
        format_func=lambda x: all_user_options[x]['name'] if x != 'All Users' else x
    )

    col1, col2 = st.columns(2)
    with col1:
        payroll_start_date = st.date_input("Payroll Start Date", datetime.now().replace(day=1).date())
    with col2:
        payroll_end_date = st.date_input("Payroll End Date", datetime.now().date())
    
    if st.button("Calculate Payroll"):
        payroll_start_date_str = payroll_start_date.strftime('%Y-%m-%d')
        payroll_end_date_str = payroll_end_date.strftime('%Y-%m-%d')

        all_payroll_data = []

        if selected_user_username == 'All Users':
            for username, user_data in all_user_options.items():
                hourly_rate = user_data.get('hourly_rate', 0.0)
                total_hours, total_pay, detailed_shifts = calculate_payroll_for_user(
                    username, hourly_rate, payroll_start_date_str, payroll_end_date_str
                )
                if total_hours > 0 or total_pay > 0:
                    all_payroll_data.append({
                        "Name": user_data['name'],
                        "Role": user_data['role'].title(),
                        "Total Hours": f"{total_hours:.1f}",
                        "Total Pay": f"€{total_pay:.2f}",
                        "Details": detailed_shifts
                    })
        else:
            user_data = all_user_options[selected_user_username]
            hourly_rate = user_data.get('hourly_rate', 0.0)
            total_hours, total_pay, detailed_shifts = calculate_payroll_for_user(
                selected_user_username, hourly_rate, payroll_start_date_str, payroll_end_date_str
            )
            if total_hours > 0 or total_pay > 0:
                all_payroll_data.append({
                    "Name": user_data['name'],
                    "Role": user_data['role'].title(),
                    "Total Hours": f"{total_hours:.1f}",
                    "Total Pay": f"€{total_pay:.2f}",
                    "Details": detailed_shifts
                })
        
        if all_payroll_data:
            st.subheader("Payroll Summary")
            summary_data = [{k: v for k, v in item.items() if k != "Details"} for item in all_payroll_data]
            df_summary = pd.DataFrame(summary_data)
            st.dataframe(df_summary, use_container_width=True)

            st.subheader("Detailed Payroll Information")
            for entry in all_payroll_data:
                with st.expander(f"Details for {entry['Name']} ({entry['Role']})"):
                    if entry['Details']:
                        df_details = pd.DataFrame(entry['Details'])
                        df_details['Date'] = pd.to_datetime(df_details['Date'])
                        df_details = df_details.sort_values(by='Date', ascending=False).reset_index(drop=True)
                        st.dataframe(df_details, use_container_width=True)
                    else:
                        st.info("No approved shifts or manual entries for this user in the selected period.")
        else:
            st.info("No payroll data found for the selected criteria.")

    # --- NEW: COLUMN SHOWING ALL PAYROLLS (DUMMY + MANUAL) ---
    st.markdown("---")
    st.subheader("All Payroll Entries (Dummy & Manual, Last 6 Months & Year)")
    all_payroll_entries = []
    for shift in shifts.values():
        if shift.get("shift_type") == "manual_payroll":
            user = shift['assigned_employees'][0] if shift.get('assigned_employees') else "N/A"
            user_name = users[user]['name'] if user in users else user
            user_role = users[user]['role'].title() if user in users else "N/A"
            all_payroll_entries.append({
                "Date": shift['date'],
                "Name": user_name,
                "Role": user_role,
                "Amount": f"€{shift.get('manual_amount', 0):.2f}",
                "Description": shift.get('description', ''),
                "Entry ID": shift.get('id', '')
            })
    if all_payroll_entries:
        df_all_payrolls = pd.DataFrame(all_payroll_entries)
        df_all_payrolls['Date'] = pd.to_datetime(df_all_payrolls['Date'])
        df_all_payrolls = df_all_payrolls.sort_values(by='Date', ascending=False).reset_index(drop=True)
        st.dataframe(df_all_payrolls, use_container_width=True)
    else:
        st.info("No payroll entries found.")

    st.markdown("---")
    st.subheader("Manually Add Payroll Entry")
    def manual_add_payroll_entry():
        """Allows admins to manually add payroll entries for an employee or admin."""
        users = load_users()
        employees_and_admins = {u['username']: u for u in users.values() if u['role'] in ['employee', 'admin']}

        if not employees_and_admins:
            st.warning("No employees or admins available to add manual payroll for.")
            return

        with st.form("manual_payroll_form"):
            st.write("Enter details for a manual payroll entry.")
            
            selected_user = st.selectbox(
                "Select Employee/Admin",
                options=list(employees_and_admins.keys()),
                format_func=lambda x: employees_and_admins[x]['name'],
                key="manual_payroll_employee"
            )

            entry_date = st.date_input("Date of Entry", datetime.now().date(), key="manual_payroll_date")
            description = st.text_input("Description (e.g., Bonus, Expense Reimbursement, Adjustment)", key="manual_payroll_description")
            amount = st.number_input("Amount (€)", min_value=0.0, format="%.2f", key="manual_payroll_amount")
            
            payroll_submitted = st.form_submit_button("Add Manual Payroll Entry")

            if payroll_submitted:
                if not selected_user or not description or amount is None:
                    st.error("Please fill in all fields for the manual payroll entry.")
                elif amount == 0.0:
                    st.warning("Please enter an amount greater than zero for the manual payroll entry.")
                else:
                    shifts = load_shifts()
                    
                    manual_entry_id = f"manual_payroll_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}"
                    
                    shifts[manual_entry_id] = {
                        "id": manual_entry_id,
                        "date": entry_date.strftime('%Y-%m-%d'),
                        "shift_type": "manual_payroll", 
                        "planned_start": "00:00",
                        "planned_end": "00:00", 
                        "assigned_employees": [selected_user],
                        "assigned_admin": st.session_state.user['username'],
                        "status": "approved", # Manual entries are directly "approved" for payroll
                        "approved": True,
                        "actual_start": "00:00",
                        "actual_end": "00:00",
                        "manual_amount": amount, 
                        "description": description
                    }
                    save_shifts(shifts)
                    st.success(f"Manual payroll entry of €{amount:.2f} for {employees_and_admins[selected_user]['name']} added successfully!")
                    st.rerun()
    manual_add_payroll_entry()

def head_admin_dashboard():
    st.title(f"Head Administrator Dashboard - {st.session_state.user['name']}")
    
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Choose page", [
        "Dashboard", "Manage Users", "Manage Shifts", "Approve Shifts", "Employee Payroll"
    ])
    
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

    if page == "Dashboard":
        admin_dashboard_overview() # Head admin can also see general overview
    elif page == "Manage Users":
        head_admin_manage_users()
    elif page == "Manage Shifts":
        admin_manage_shifts() # Head admin has access to admin shift management
    elif page == "Approve Shifts":
        admin_approve_shifts() # Head admin has access to admin shift approval
    elif page == "Employee Payroll":
        admin_employee_payroll() # Head admin has access to employee payroll

def head_admin_manage_users():
    st.header("Manage Users (Head Admin)")
    users = load_users()

    st.subheader("All System Users")
    user_data = []
    for username, user_info in users.items():
        user_data.append({
            "Username": username,
            "Name": user_info.get('name', 'N/A'),
            "Email": user_info.get('email', 'N/A'),
            "Role": user_info.get('role', 'N/A').replace('_', ' ').title(),
            "Primary Shift": user_info.get('primary_shift', 'N/A').replace('_', ' ').title(),
            "Hourly Rate": f"€{user_info.get('hourly_rate', 0.0):.2f}" if user_info.get('role') != 'head_admin' else 'N/A'
        })
    
    if user_data:
        df_users = pd.DataFrame(user_data)
        st.dataframe(df_users, use_container_width=True)

    st.markdown("---")
    st.subheader("Add New User")

    with st.form("add_user_form"):
        new_username = st.text_input("New Username", help="Must be unique")
        new_password = st.text_input("New Password", type="password")
        new_name = st.text_input("Full Name")
        new_email = st.text_input("Email")
        
        # Select primary shift
        primary_shift_options = list(SHIFT_TYPES.keys())
        new_primary_shift = st.selectbox(
            "Primary Shift Type", 
            primary_shift_options,
            format_func=lambda x: x.replace('_', ' ').title()
        )
        
        # Select secondary shift based on primary shift compatibility
        secondary_shift_options = SHIFT_COMPATIBILITY.get(new_primary_shift, [])
        if secondary_shift_options:
            new_secondary_shift = st.selectbox(
                "Secondary Shift Type (Optional)", 
                ['None'] + secondary_shift_options,
                format_func=lambda x: x.replace('_', ' ').title()
            )
        else:
            new_secondary_shift = 'None'
            st.info("No compatible secondary shifts for the selected primary shift.")
            
        new_hourly_rate = st.number_input("Hourly Rate (€)", min_value=0.0, value=20.0, step=0.5)
        new_role = st.selectbox("Role", ["admin", "employee"], key="new_user_role", format_func=lambda x: x.title())


        if st.form_submit_button("Add User"):
            if not new_username or not new_password or not new_name or not new_email:
                st.error("Please fill in all required fields.")
            elif new_username in users:
                st.error(f"Username '{new_username}' already exists.")
            else:
                users[new_username] = {
                    "username": new_username,
                    "password": hash_password(new_password),
                    "role": new_role,
                    "name": new_name,
                    "email": new_email,
                }
                if new_role != "head_admin": # Head admin doesn't need shift or rate
                    users[new_username]["primary_shift"] = new_primary_shift
                    users[new_username]["secondary_shift"] = new_secondary_shift if new_secondary_shift != 'None' else None
                    users[new_username]["hourly_rate"] = new_hourly_rate

                save_users(users)
                st.success(f"User '{new_name}' with role '{new_role.title()}' added successfully!")
                st.rerun()

    st.markdown("---")
    st.subheader("Update User")
    
    # Dropdown to select user to update, excluding head_admin from being modified here
    update_username = st.selectbox(
        "Select User to Update", 
        [''] + [u for u in users if users[u]['role'] != 'head_admin'], 
        key="update_user_select"
    )

    if update_username and update_username != '':
        user_to_update = users[update_username]
        st.write(f"Editing user: **{user_to_update['name']}** ({user_to_update['role'].title()})")
        
        with st.form(f"update_user_form_{update_username}"):
            updated_name = st.text_input("Full Name", value=user_to_update.get('name', ''), key=f"update_name_{update_username}")
            updated_email = st.text_input("Email", value=user_to_update.get('email', ''), key=f"update_email_{update_username}")
            
            # Role cannot be changed for head_admin
            updated_role = st.selectbox(
                "Role", 
                ["admin", "employee"], 
                index=["admin", "employee"].index(user_to_update['role']), 
                key=f"update_role_{update_username}", 
                disabled=(user_to_update['role'] == 'head_admin') # Disable role change for head_admin
            )

            updated_primary_shift = None
            updated_secondary_shift = None
            updated_hourly_rate = None

            if updated_role != "head_admin":
                primary_shift_options = list(SHIFT_TYPES.keys())
                current_primary_shift_index = primary_shift_options.index(user_to_update.get('primary_shift', primary_shift_options[0]))
                updated_primary_shift = st.selectbox(
                    "Primary Shift Type", 
                    primary_shift_options,
                    index=current_primary_shift_index,
                    key=f"update_primary_shift_{update_username}",
                    format_func=lambda x: x.replace('_', ' ').title()
                )
                
                secondary_shift_options = SHIFT_COMPATIBILITY.get(updated_primary_shift, [])
                current_secondary_shift = user_to_update.get('secondary_shift')
                if current_secondary_shift in secondary_shift_options:
                    current_secondary_shift_index = secondary_shift_options.index(current_secondary_shift) + 1 # +1 for 'None'
                else:
                    current_secondary_shift_index = 0 # 'None'
                
                if secondary_shift_options:
                    updated_secondary_shift = st.selectbox(
                        "Secondary Shift Type (Optional)", 
                        ['None'] + secondary_shift_options,
                        index=current_secondary_shift_index,
                        key=f"update_secondary_shift_{update_username}",
                        format_func=lambda x: x.replace('_', ' ').title()
                    )
                else:
                    updated_secondary_shift = 'None'
                    st.info(f"No compatible secondary shifts for the selected primary shift for {user_to_update['name']}.")

                updated_hourly_rate = st.number_input(
                    "Hourly Rate (€)", 
                    min_value=0.0, 
                    value=user_to_update.get('hourly_rate', 0.0), 
                    step=0.5, 
                    key=f"update_hourly_rate_{update_username}"
                )

            if st.form_submit_button("Update User"):
                users[update_username]['name'] = updated_name
                users[update_username]['email'] = updated_email
                users[update_username]['role'] = updated_role # Role change handled only if not head_admin

                if updated_role != "head_admin":
                    users[update_username]['primary_shift'] = updated_primary_shift
                    users[update_username]['secondary_shift'] = updated_secondary_shift if updated_secondary_shift != 'None' else None
                    users[update_username]['hourly_rate'] = updated_hourly_rate

                save_users(users)
                st.success(f"User '{updated_name}' updated successfully!")
                st.rerun()
    
    st.markdown("---")
    st.subheader("Delete User")
    delete_username = st.selectbox(
        "Select User to Delete", 
        [''] + [u for u in users if users[u]['role'] not in ['head_admin']], # Cannot delete head admin
        key="delete_user_select"
    )
    if delete_username and delete_username != '':
        st.warning(f"Are you sure you want to delete user: **{users[delete_username]['name']}**?")
        if st.button(f"Confirm Delete {users[delete_username]['name']}", key=f"confirm_delete_{delete_username}"):
            del users[delete_username]
            save_users(users)
            st.success(f"User '{delete_username}' deleted successfully.")
            st.rerun()

if __name__ == "__main__":
    main()