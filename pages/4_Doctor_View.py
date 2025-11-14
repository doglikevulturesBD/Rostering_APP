# pages/4_Doctor_View.py

import streamlit as st
import pandas as pd
from datetime import timedelta

import plotly.graph_objects as go

from core.database import get_all_doctors, load_shifts, load_assignments
from core.workload_analyzer import analyze_workload

st.set_page_config(page_title="Doctor Dashboard", layout="wide")
st.title("🧑‍⚕️ Doctor Dashboard")

# Load data
doctors = get_all_doctors(active_only=True)
shifts = load_shifts()
assignments = load_assignments()

if not doctors or not shifts or not assignments:
    st.warning("Please generate roster first.")
    st.stop()

workload = analyze_workload(doctors, shifts, assignments)

# Select doctor
doc_ids = [d.id for d in doctors]
name_map = {d.id: d.name for d in doctors}
doc_id = st.selectbox("Select Your Name", options=doc_ids, format_func=lambda i: name_map[i])

doc = next(d for d in doctors if d.id == doc_id)
summary = workload[doc_id]

# -------------------------------------------------------
# Burnout Gauge
# -------------------------------------------------------
st.subheader("Burnout Index")

fig = go.Figure(go.Indicator(
    mode="gauge+number",
    value=summary.burnout_score,
    gauge={
        "axis": {"range": [0, 100]},
        "bar": {"color": "black"},
        "steps": [
            {"range": [0, 25], "color": "green"},
            {"range": [25, 50], "color": "yellowgreen"},
            {"range": [50, 75], "color": "orange"},
            {"range": [75, 100], "color": "red"},
        ],
    },
    title={"text": f"Burnout Score for {doc.name}"}
))

st.plotly_chart(fig, use_container_width=True)

# -------------------------------------------------------
# Personal Stats
# -------------------------------------------------------
st.subheader("Monthly Statistics")

stats_df = pd.DataFrame(
    {
        "Metric": [
            "Total Hours",
            "Total Shifts",
            "Night Shifts",
            "Weekend Shifts",
            "Consecutive Days",
            "Consecutive Nights",
            "Rest Violations",
        ],
        "Value": [
            summary.total_hours,
            summary.total_shifts,
            summary.night_shifts,
            summary.weekend_shifts,
            summary.consecutive_days,
            summary.consecutive_nights,
            summary.rest_violations,
        ],
    }
)

st.dataframe(stats_df, width="stretch")

# -------------------------------------------------------
# Upcoming Shifts Table
# -------------------------------------------------------
st.subheader("Upcoming Shifts (Next 7 Days)")

today = min(s.start for s in shifts).date()  # fallback for static months
future = today + timedelta(days=7)

doc_assignments = [
    s for s in shifts
    if any(a.doctor_id == doc_id and a.shift_id == s.id for a in assignments)
]

upcoming = [
    s for s in doc_assignments
    if today <= s.start.date() <= future
]

if upcoming:
    df_up = pd.DataFrame([
        {
            "Date": s.start.date().isoformat(),
            "Start": s.start.strftime("%H:%M"),
            "End": s.end.strftime("%H:%M"),
            "Hours": s.duration_hours,
            "Type": "Night" if s.start.hour >= 21 else ("Weekend" if s.is_weekend else "Day"),
        }
        for s in sorted(upcoming, key=lambda x: x.start)
    ])
    st.dataframe(df_up, width="stretch")
else:
    st.info("No upcoming shifts in the next 7 days.")

# -------------------------------------------------------
# Alerts
# -------------------------------------------------------
st.subheader("⚠️ Alerts / Recommendations")

alerts = []

if summary.burnout_score > 75:
    alerts.append("High burnout risk — consider rest days or reduced night load.")

if summary.consecutive_nights >= 2:
    alerts.append("Consecutive nights ≥2 — monitor fatigue.")

if summary.consecutive_days >= 5:
    alerts.append("High consecutive day load.")

if summary.rest_violations > 0:
    alerts.append(f"{summary.rest_violations} rest violations detected (<11 hours).")

if not alerts:
    st.success("No alerts — workload balanced.")
else:
    for a in alerts:
        st.warning(a)
