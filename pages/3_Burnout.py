# pages/3_Burnout_Overview.py

import streamlit as st
import pandas as pd

from core.workload_analyzer import analyze_workload

st.set_page_config(page_title="Burnout Overview", layout="wide")
st.title("🔥 Burnout Overview")

roster = st.session_state.get("roster", None)

if roster is None:
    st.info("No roster available. Please generate a roster first.")
    st.stop()

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
            "Consec Nights": w.consecutive_nights,
            "Intensity Sum": w.intensity_sum,
            "Burnout Score": w.burnout_score,
            "Rest Violations": w.rest_violations,
        }
    )

df = pd.DataFrame(rows)
df = df.sort_values("Burnout Score", ascending=False)

st.subheader("Doctors Sorted by Burnout Score")
st.dataframe(df, use_container_width=True)

# Highlight high risk
st.subheader("High-Risk Doctors (Burnout Score ≥ 70)")

high_risk = df[df["Burnout Score"] >= 70.0]

if high_risk.empty:
    st.write("✅ No doctors currently flagged as high burnout risk.")
else:
    st.write("⚠️ The following doctors are at high burnout risk:")
    st.dataframe(high_risk, use_container_width=True)
