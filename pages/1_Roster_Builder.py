import streamlit as st
import pandas as pd

from core.generate_shifts import generate_shifts_for_month
from core.data_loader import load_doctors_from_csv  # we keep for now
from core.solver import generate_naive_roster

st.set_page_config(page_title="Roster Builder", layout="wide")
st.title("📅 Roster Builder")

# Session state
for key in ["doctors", "shifts", "roster"]:
    if key not in st.session_state:
        st.session_state[key] = None

# -------------------------------
# STEP 1 — User selects month/year
# -------------------------------
st.subheader("Generate Shifts for Month")

col1, col2 = st.columns(2)
year = col1.number_input("Year", min_value=2024, max_value=2030, value=2025)
month = col2.number_input("Month", min_value=1, max_value=12, value=1)

if st.button("Generate Shifts"):
    output = "data/generated_shifts.csv"
    generate_shifts_for_month(int(year), int(month), output)
    st.session_state["shifts"] = pd.read_csv(output)
    st.success(f"Generated {len(st.session_state['shifts'])} shifts!")

# --------------------------------------
# STEP 2 — Load doctor CSV (temporary)
# --------------------------------------
st.subheader("Load Doctors (Temporary CSV)")

doctor_file = st.text_input("Doctor CSV", "data/doctors_sample.csv")

if st.button("Load Doctors"):
    try:
        doctors = load_doctors_from_csv(doctor_file)
        st.session_state["doctors"] = doctors
        st.success(f"Loaded {len(doctors)} doctors.")
    except Exception as e:
        st.error(f"Error loading doctors: {e}")

# ---------------------------------------
# STEP 3 — Generate roster
# ---------------------------------------
if st.session_state["doctors"] is not None and st.session_state["shifts"] is not None:

    if st.button("Generate Roster"):
        shifts = st.session_state["shifts"]
        doctors = st.session_state["doctors"]

        roster = generate_naive_roster(doctors, shifts)
        st.session_state["roster"] = roster
        st.success("Roster generated!")

# ---------------------------------------
# STEP 4 — Display roster
# ---------------------------------------
if st.session_state["roster"]:

    roster = st.session_state["roster"]

    df = pd.DataFrame([
        {"doctor_id": a.doctor_id, "shift_id": a.shift_id}
        for a in roster.assignments
    ])

    st.subheader("Roster Assignments")
    st.dataframe(df, use_container_width=True)

    st.download_button(
        "Download Roster CSV",
        df.to_csv(index=False).encode("utf-8"),
        "roster_output.csv",
        "text/csv"
    )
