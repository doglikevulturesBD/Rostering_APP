import streamlit as st
import pandas as pd
import os

from core.data_loader import load_doctors_from_csv, load_shifts_from_csv
from core.solver import generate_naive_roster
from core.generate_shifts import generate_shifts_for_month


st.set_page_config(page_title="Roster Builder", layout="wide")
st.title("📅 Roster Builder")

# Initialize state
if "doctors" not in st.session_state:
    st.session_state["doctors"] = None
if "shifts" not in st.session_state:
    st.session_state["shifts"] = None
if "roster" not in st.session_state:
    st.session_state["roster"] = None


# 🔧 Helper to ensure shift file exists
def ensure_shift_file(path):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        st.warning("Shift file missing or empty. Generating shifts for Jan 2025...")
        generate_shifts_for_month(2025, 1, path)
        st.success("Shift file generated successfully!")


# ---------------------------------
# 1. Load Data Files
# ---------------------------------
st.subheader("Load Data Files")

doctor_file = st.text_input("Doctors CSV", "data/doctors_sample.csv")
shift_file = st.text_input("Shifts CSV", "data/shifts_sample.csv")

if st.button("Load Doctors & Shifts"):
    try:
        ensure_shift_file(shift_file)

        doctors = load_doctors_from_csv(doctor_file)
        shifts = load_shifts_from_csv(shift_file)

        st.session_state["doctors"] = doctors
        st.session_state["shifts"] = shifts
        st.success(f"Loaded {len(doctors)} doctors and {len(shifts)} shifts.")

    except Exception as e:
        st.error(f"❌ Error loading data: {e}")


# ---------------------------------
# 2. Generate Roster
# ---------------------------------
if st.session_state["doctors"] and st.session_state["shifts"]:
    st.subheader("Generate Roster")

    if st.button("Generate Roster Now"):
        roster = generate_naive_roster(
            st.session_state["doctors"],
            st.session_state["shifts"]
        )
        st.session_state["roster"] = roster
        st.success("Roster generated successfully!")


# ---------------------------------
# 3. Display Roster
# ---------------------------------
if st.session_state["roster"]:
    roster = st.session_state["roster"]

    df = pd.DataFrame([
        {"doctor_id": a.doctor_id, "shift_id": a.shift_id}
        for a in roster.assignments
    ])

    st.subheader("Roster Assignments")
    st.dataframe(df, use_container_width=True)

    st.download_button(
        "⬇ Download Roster CSV",
        df.to_csv(index=False).encode("utf-8"),
        "roster_output.csv",
        "text/csv"
    )
