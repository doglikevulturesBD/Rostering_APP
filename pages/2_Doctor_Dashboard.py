# pages/2_Doctor_Dashboard.py

import streamlit as st
import pandas as pd
from datetime import datetime

from core.database import get_all_doctors, load_shifts
from core.workload_analyzer import analyze_workload
from core.models import Assignment, Roster

st.set_page_config(page_title="Doctor Dashboard", layout="wide")
st.title("📊 Doctor Dashboard")

doctors = get_all_doctors(active_only=True)
shifts = load_shifts()

if "roster" in st.session_state and st.session_state["roster"]:
    roster: Roster = st.session_state["roster"]
else:
    # No roster in session → empty fallback
    roster = Roster(doctors=doctors, shifts=shifts, assignments=[])

st.subheader("Who is on duty right now?")

now = datetime.now()
on_duty = []
shift_by_id = {s.id: s for s in roster.shifts}
for a in roster.assignments:
    sh = shift_by_id.get(a.shift_id)
    if sh and sh.start <= now <= sh.end:
        doc = next((d for d in roster.doctors if d.id == a.doctor_id), None)
        if doc:
            on_duty.append({"Doctor": doc.name, "Shift ID": sh.id, "Start": sh.start, "End": sh.end})

if on_duty:
    st.dataframe(pd.DataFrame(on_duty), width="stretch")
else:
    st.info("No doctors currently on duty according to the active roster.")

st.subheader("Doctor Workload Overview")

if roster.assignments:
    workload = analyze_workload(roster.doctors, roster.shifts, roster.assignments)
    rows = []
    for doc in roster.doctors:
        w = workload[doc.id]
        rows.append(
            {
                "Doctor": doc.name,
                "Shifts": w.total_shifts,
                "Hours": round(w.total_hours, 1),
                "Night Shifts": w.night_shifts,
                "Weekend Shifts": w.weekend_shifts,
                "Burnout Score": round(w.burnout_score, 1),
            }
        )
    st.dataframe(pd.DataFrame(rows), width="stretch")
else:
    st.info("No roster assignments to summarise yet.")
