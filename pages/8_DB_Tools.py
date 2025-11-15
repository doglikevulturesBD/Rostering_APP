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
)

# Temporary fallback until preferences exist
def get_all_preferences():
    return []


st.set_page_config(page_title="Database Tools", layout="wide")
st.title("🛠️ Database Tools & Utilities")

# ----------------------------------------------------------
# SECTION: DB PATH INFO
# ----------------------------------------------------------

st.subheader("📁 Database Path Information")

DB_PATH = Path(DB_PATH)   # Convert to Path object
db_exists = DB_PATH.exists()
folder_exists = DB_PATH.parent.exists()

st.write("**Expected DB Location:**")
st.code(str(DB_PATH))

st.write("**Absolute Location:**")
st.code(str(DB_PATH.resolve()))

col1, col2 = st.columns(2)
col1.metric("Folder exists?", "Yes" if folder_exists else "No")
col2.metric("DB exists?", "Yes" if db_exists else "No")

if not folder_exists:
    st.error("The folder 'data/' does not exist. Please create it in your repo.")

if not db_exists:
    st.warning("Database not found. It will be created when shifts or doctors are added.")


# ----------------------------------------------------------
# SECTION: SCAN FOR ALL .db FILES
# ----------------------------------------------------------

st.subheader("🔍 Scan for Other Database Files")

db_files = list(Path(".").rglob("*.db"))

if db_files:
    st.success("Found database files:")
    for f in db_files:
        st.code(str(f))
else:
    st.info("No *.db files detected.")


# ----------------------------------------------------------
# SECTION: DB INSPECTOR
# ----------------------------------------------------------

st.subheader("📊 Database Inspector")

try:
    doctors = get_all_doctors(active_only=False)
    shifts = load_shifts()
    leave = get_all_leave()
    prefs = get_all_preferences()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Doctors", len(doctors))
    col2.metric("Shifts", len(shifts))
    col3.metric("Leave entries", len(leave))
    col4.metric("Preferences", len(prefs))

    st.write("### Doctors")
    st.dataframe(
        pd.DataFrame([d.__dict__ for d in doctors]),
        use_container_width=True
    )

    st.write("### Shifts")
    st.dataframe(
        pd.DataFrame([s.to_dict() for s in shifts]),
        use_container_width=True
    )

    st.write("### Leave")
    st.dataframe(
        pd.DataFrame([dict(row) for row in leave]),
        use_container_width=True
    )

    st.write("### Preferences")
    st.dataframe(
        pd.DataFrame([dict(row) for row in prefs]),
        use_container_width=True
    )

except Exception as e:
    st.error(f"Error loading data: {e}")


# ----------------------------------------------------------
# SECTION: BACKUP / EXPORT
# ----------------------------------------------------------

st.subheader("💾 Backup / Export")

if db_exists:
    if st.button("Download JSON Backup"):
        backup = {
            "doctors": [d.__dict__ for d in doctors],
            "shifts": [s.to_dict() for s in shifts],
            "leave": [dict(r) for r in leave],
            "preferences": [dict(r) for r in prefs],
        }
        st.download_button(
            "Download File",
            json.dumps(backup, indent=2).encode(),
            file_name="roster_backup.json",
            mime="application/json"
        )


# ----------------------------------------------------------
# SECTION: RESET / DELETE
# ----------------------------------------------------------

st.subheader("🧨 Reset / Delete Database")

colA, colB = st.columns(2)

if colA.button("❌ Delete database file"):
    if db_exists:
        os.remove(DB_PATH)
        st.success("Database deleted. Reload the app.")
    else:
        st.warning("No DB file found.")

if colB.button("🧹 Clear all table data"):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("DELETE FROM doctors")
        cur.execute("DELETE FROM shifts")
        cur.execute("DELETE FROM leave_requests")
        conn.commit()
        conn.close()
        st.success("All data cleared.")
    except Exception as e:
        st.error(f"Error clearing data: {e}")

