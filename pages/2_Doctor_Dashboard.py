# pages/2_📊_Doctor_Dashboard.py
import streamlit as st
import pandas as pd

from core.analytics import compute_doctor_hours_summary

st.set_page_config(page_title="Doctor Dashboard", layout="wide")
st.title("📊 Doctor Dashboard")

if "roster" not in st.session_state:
    st.warning("No roster found. Please generate one in the Roster Builder page.")
    st.stop()

roster = st.session_state["roster"]

summary = compute_doctor_hours_summary(
    roster.doctors,
    roster.shifts,
    roster.assignments,
)

df = pd.DataFrame(summary)

st.subheader("Doctor Summary")
st.dataframe(df, use_container_width=True)

# Optionally: filter by doctor
doctor_names = {d.id: d.name for d in roster.doctors}
selected = st.selectbox(
    "Select a doctor to inspect",
    options=list(doctor_names.keys()),
    format_func=lambda i: doctor_names[i],
)

st.markdown(f"### Details for {doctor_names[selected]}")
row = df[df["doctor_id"] == selected].iloc[0]
st.write(row.to_dict())

