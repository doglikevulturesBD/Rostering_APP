# pages/1_📅_Roster_Builder.py
import streamlit as st
import pandas as pd
from pathlib import Path

from core.data_loader import load_doctors_from_csv, load_shifts_from_csv
from core.solver import generate_naive_roster

st.set_page_config(page_title="Roster Builder", layout="wide")

st.title("📅 Roster Builder")

data_dir = Path("data")

doctor_file = st.text_input("Doctors CSV path", str(data_dir / "doctors_sample.csv"))
shift_file = st.text_input("Shifts CSV path", str(data_dir / "shifts_sample.csv"))

if st.button("Load data"):
    doctors = load_doctors_from_csv(doctor_file)
    shifts = load_shifts_from_csv(shift_file)
    st.session_state["doctors"] = doctors
    st.session_state["shifts"] = shifts
    st.success(f"Loaded {len(doctors)} doctors and {len(shifts)} shifts.")

if "doctors" in st.session_state and "shifts" in st.session_state:
    if st.button("Generate roster"):
        roster = generate_naive_roster(
            st.session_state["doctors"],
            st.session_state["shifts"],
        )
        st.session_state["roster"] = roster
        st.success("Roster generated.")

    if "roster" in st.session_state:
        roster = st.session_state["roster"]
        # show as dataframe
        df = pd.DataFrame(
            [
                {
                    "doctor_id": a.doctor_id,
                    "shift_id": a.shift_id,
                }
                for a in roster.assignments
            ]
        )
        st.subheader("Assignments")
        st.dataframe(df, use_container_width=True)
else:
    st.info("Load doctors and shifts to begin.")

