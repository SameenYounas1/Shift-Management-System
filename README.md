# Shift-Management-System
# 🚀 Shift Management System

A streamlined, web-based Shift Management System built with **Python** and **Streamlit**, designed to simplify employee shift scheduling, attendance tracking, and payroll calculation.

---

## 📌 Features

### 🔐 Authentication & Roles
- Secure login with hashed passwords
- Three user roles:
  - **Head Admin** (`head_admin`)
  - **Admins** (`admin1` to `admin5`)
  - **Employees** (`emp1` to `emp25`)

---

### 🗓️ Shift Scheduling
- Create & assign shifts (Morning, Evening, Night, Weekend)
- Predefined shift timings with validation
- Auto-detection of weekdays vs weekends
- Smart suggestion engine for shift timing

---

### 🧾 Payroll & Attendance
- Auto-calculation of work hours (even across midnight)
- Payroll for approved shifts only
- Summary view: hours worked, pay earned, shift breakdown

---

### 👥 Employee Dashboard
- Profile view and shift preferences
- Interactive calendar: shows assigned shifts and statuses
  - ✅ Green: Approved
  - 🔵 Blue: Pending approval
  - ❓ Yellow: Awaiting response
  - ❌ Red: Declined or cancelled
- "My Shifts" panel to accept/decline offers

---

### 🧑‍💼 Admin Dashboard
- Create and manage shifts
- Approve or adjust submitted shifts
- Employee directory and (WIP) employee creation module
- Key stats: total shifts, employees, pending actions

---

## 💾 Data Storage & Security
- All data saved locally using structured **JSON files**
- Passwords are securely **hashed** before storage

---

## 🚀 Getting Started

### ✅ Requirements
- Python 3.8+
- Streamlit

### 🔧 Installation
```bash
git clone https://github.com/yourusername/shift-management-system.git
cd shift-management-system
pip install -r requirements.txt
streamlit run app.py
