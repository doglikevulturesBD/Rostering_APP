import streamlit as st
import sqlite3
import json
import os
from pathlib import Path
import pandas as pd

from core.database import (
    DB_PATH,
    get_all_doctors,
    load_shifts,
    get_all_leave,
    get_all_preferences,
)

st.set_page_config(page_title="Database Tools", layout="wide")
st.title("🛠️ Database Tools & Utilities")

# ----------------------------------------------------------
# SECTION: DB PATH INFO
# ----------------------------------------------------------

st.subheader("📁 Database Path Information")

db_folder_exists = os.path.exists(DB_PATH.parent)
db_exists = os.path.exists(DB_PATH)
abs_path = DB_PATH.resolve()

st.write("**Expected DB Location:**")
st.code(str(DB_PATH))

st.write("**Absolute Location:**")
st.code(str(abs_path))

col1, col2 = st.columns(2)
col1.metric("Folder exists?", "Yes" if db_folder_exists else "No")
col2.metric("Database exists?", "Yes" if db_exists else "No")

if not db_folder_exists:
    st.error("The folder 'data/' does not exist. Create it in your repo with a .gitkeep file.")
if not db_exists:
    st.warning("Database not found. It will be created on next app reload.")


# ----------------------------------------------------------
# SECTION: SCAN FOR ALL .db FILES
# ----------------------------------------------------------

st.subheader("🔍 Scan for Other Database Files")

db_files = []
for root, dirs, files in os.walk(".", topdown=True):
    for f in files:
        if f.endswith(".db"):
            db_files.append(os.path.join(root, f))

if db_files:
    st.success("Found the following .db files:")
    for f in db_files:
        st.code(f)
else:
    st.info("No .db files found in the working directory.")


# ----------------------------------------------------------
# SECTION: DB INSPECTOR
# ----------------------------------------------------------

st.subheader("📊 Database Inspector (Table Summaries)")

try:
    doctors = get_all_doctors(active_only=False)
    shifts = load_shifts()
    leave = get_all_leave()
    prefs = get_all_preferences()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Doctors", len(doctors))
    col2.metric("Shifts", len(shifts))
    col3.metric("Leave Entries", len(leave))
    col4.metric("Preferences", len(prefs))

    st.write("### Preview Doctors")
    if doctors:
        st.dataframe(
            pd.DataFrame([d.__dict__ for d in doctors]),
            use_container_width=True,
        )
    else:
        st.info("No doctor data available.")

    st.write("### Preview Shifts")
    if shifts:
        st.dataframe(
            pd.DataFrame([s.to_dict() for s in shifts]),
            use_container_width=True,
        )
    else:
        st.info("No shift data.")

    st.write("### Preview Leave Requests")
    if leave:
        df_leave = pd.DataFrame([dict(row) for row in leave])
        st.dataframe(df_leave, use_container_width=True)
    else:
        st.info("No leave requests.")

    st.write("### Preview Preferences")
    if prefs:
        df_pref = pd.DataFrame([dict(row) for row in prefs])
        st.dataframe(df_pref, use_container_width=True)
    else:
        st.info("No preference entries.")

except Exception as e:
    st.error(f"Error reading database: {e}")


# ----------------------------------------------------------
# SECTION: DB BACKUP / EXPORT
# ----------------------------------------------------------

st.subheader("💾 Backup / Export Database")

if db_exists:
    if st.button("Download Full Backup (JSON)", type="primary"):
        backup = {
            "doctors": [d.__dict__ for d in doctors],
            "shifts": [s.to_dict() for s in shifts],
            "leave": [dict(r) for r in leave],
            "preferences": [dict(r) for r in prefs],
        }
        backup_bytes = json.dumps(backup, indent=2).encode("utf-8")
        st.download_button(
            "Download Backup File",
            backup_bytes,
            file_name="roster_backup.json",
            mime="application/json",
        )
else:
    st.info("Database does not exist. Create shifts/doctors to generate it.")


# ----------------------------------------------------------
# SECTION: DB RESET / DELETE
# ----------------------------------------------------------

st.subheader("🧨 Reset / Delete Database")

colA, colB = st.columns(2)

if colA.button("❌ Delete Database File"):
    if db_exists:
        os.remove(DB_PATH)
        st.success("Database deleted successfully. Reload the app to recreate it.")
    else:
        st.warning("Database file not found.")

if colB.button("🧹 Clear All Data (but keep DB structure)"):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("DELETE FROM doctors")
        cur.execute("DELETE FROM shifts")
        cur.execute("DELETE FROM leave_requests")
        cur.execute("DELETE FROM doctor_preferences")
        conn.commit()
        conn.close()
        st.success("All table data cleared. Structure preserved.")
    except Exception as e:
        st.error(f"Error clearing data: {e}")
