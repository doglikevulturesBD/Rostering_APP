import streamlit as st
import pandas as pd
from core.data_loader import load_doctors_from_csv, load_shifts_from_csv
from core.solver import generate_naive_roster

st.set_page_config(page_title="Roster Builder", layout="wide")
st.title("📅 Roster Builder")

# --- Load Doctors and Shifts ---
st.subheader("Load Data")

default_doctor_path = "data/doctors_sample.csv"
default_shift_path = "data/shifts_sample.csv"

doctor_file = st.text_input("Doctors CSV", default_doctor_path)
shift_file = st.text_input("Shifts CSV", default_shift_path)

if st.button("Load Doctors & Shifts"):
    try:
        doctors = load_doctors_from_csv(doctor_file)
        shifts = load_shifts_from_csv(shift_file)
        st.session_state["doctors"] = doctors
        st.session_state["shifts"] = shifts
        st.success(f"Loaded {len(doctors)} doctors and {len(shifts)} shifts.")
    except Exception as e:
        st.error(f"Error loading data: {e}")

# --- Generate Roster ---
if "doctors" in st.session_state and "shifts" in st.session_state:
    st.subheader("Generate Roster")

    if st.button("Generate"):
        roster = generate_naive_roster(
            st.session_state["doctors"],
            st.session_state["shifts"]
        )
        st.session_state["roster"] = roster
        st.success("Roster generated successfully!")

# --- Display Roster ---
if "roster" in st.session_state:
    roster = st.session_state["roster"]

    df = pd.DataFrame(
        {
            "doctor": [a.doctor_id for a in roster.assignments],
            "shift": [a.shift_id for a in roster.assignments],
        }
    )

    st.subheader("Assignments")
    st.dataframe(df, use_container_width=True)

    if st.button("Download Roster CSV"):
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download File", csv, "roster_output.csv", "text/csv")
