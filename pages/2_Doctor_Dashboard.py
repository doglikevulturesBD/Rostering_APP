# pages/2_Doctor_Dashboard.py

import streamlit as st
import pandas as pd
from datetime import datetime

from core.workload_analyzer import analyze_workload

st.set_page_config(page_title="Doctor Dashboard", layout="wide")
st.title("📊 Doctor Dashboard")

# Get roster from session
roster = st.session_state.get("roster", None)

if roster is None:
    st.info("No roster found. Please generate a roster on the 'Roster Builder' page first.")
    st.stop()

# -------------------------------------
# Workload Table
# -------------------------------------
st.subheader("Workload Overview")

workload = analyze_workload(roster.doctors, roster.shifts, roster.assignments)

rows = []
for doc in roster.doctors:
    w = workload[doc.id]
    rows.append(
        {
            "Doctor": doc.name,
            "Level": doc.level,
            "Shifts": w.total_shifts,
            "Hours": round(w.total_hours, 1),
            "Night Shifts": w.night_shifts,
            "Weekend Shifts": w.weekend_shifts,
            "Consec Days": w.consecutive_days,
            "Consec Nights": w.consecutive_nights,
            "Burnout Score": w.burnout_score,
            "Rest Violations": w.rest_violations,
        }
    )

df = pd.DataFrame(rows)
st.dataframe(df, use_container_width=True)

# -------------------------------------
# Who is on shift NOW?
# -------------------------------------
st.subheader("Who is on Duty Now?")

now = datetime.now()

# Build lookup
shift_map = {s.id: s for s in roster.shifts}
doctor_name_map = {d.id: d.name for d in roster.doctors}

on_now = []
for a in roster.assignments:
    s = shift_map.get(a.shift_id)
    if s and s.start <= now <= s.end:
        on_now.append(
            {
                "Doctor": doctor_name_map.get(a.doctor_id, a.doctor_id),
                "Shift ID": s.id,
                "Shift Name": s.name,
                "Start": s.start,
                "End": s.end,
            }
        )

if not on_now:
    st.info("No doctors currently on duty (based on system time).")
else:
    df_on = pd.DataFrame(on_now)
    st.dataframe(df_on, use_container_width=True)
