import streamlit as st
import pandas as pd

from core.generate_shifts import generate_shifts_for_month
from core.database import load_shifts, get_all_doctors
from core.solver import generate_naive_roster

st.set_page_config(page_title="Roster Builder", layout="wide")
st.title("📅 Roster Builder")

# Ensure session keys exist
for key in ["shifts", "roster"]:
    if key not in st.session_state:
        st.session_state[key] = None

# -----------------------------
# Generate Shifts
# -----------------------------
st.subheader("1. Generate Shifts")

col1, col2 = st.columns(2)
year = col1.number_input("Year", 2024, 2035, value=2025)
month = col2.number_input("Month", 1, 12, value=1)

if st.button("Generate Shifts"):
    output = "data/generated_shifts.csv"
    generate_shifts_for_month(int(year), int(month), output)

    shifts = load_shifts()
    st.session_state["shifts"] = shifts

    st.success(f"Generated & saved {len(shifts)} shifts.")
    st.write(pd.read_csv(output).head())

# -----------------------------
# Load Doctors
# -----------------------------
st.subheader("2. Load Doctors")

doctors = get_all_doctors(active_only=True)

if not doctors:
    st.error("No doctors in DB. Add them in the Doctor Manager.")
else:
    st.success(f"{len(doctors)} doctors loaded.")
    df = pd.DataFrame(
        [{"id": d.id, "name": d.name, "level": d.level} for d in doctors]
    )
    st.dataframe(df, use_container_width=True)

# -----------------------------
# Generate Roster
# -----------------------------
st.subheader("3. Generate Roster")

if st.session_state["shifts"] and doctors:
    if st.button("Generate Roster"):
        roster = generate_naive_roster(doctors, st.session_state["shifts"])
        st.session_state["roster"] = roster
        st.success("Roster generated!")
else:
    st.info("Generate shifts and ensure doctors exist first.")

# -----------------------------
# Display Assignments
# -----------------------------
if st.session_state["roster"]:
    assignments = st.session_state["roster"].assignments
    df_assign = pd.DataFrame(
        [{"doctor": a.doctor_id, "shift": a.shift_id} for a in assignments]
    )

    st.subheader("Roster Assignments")
    st.dataframe(df_assign, use_container_width=True)

    st.download_button(
        "Download CSV",
        df_assign.to_csv(index=False).encode("utf-8"),
        file_name="roster_output.csv",
    )
