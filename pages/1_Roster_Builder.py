import streamlit as st
import pandas as pd

from core.generate_shifts import generate_shifts_for_month
from core.database import get_all_doctors
from core.models import Shift
from core.solver import generate_naive_roster

st.set_page_config(page_title="Roster Builder", layout="wide")
st.title("📅 Roster Builder")

# Initialise session state
for key in ["shifts", "roster"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ---------------------------------
# STEP 1 — Generate Shifts
# ---------------------------------
st.subheader("1. Generate Shifts for the Month")

col1, col2 = st.columns(2)
year = col1.number_input("Year", min_value=2024, max_value=2035, value=2025)
month = col2.number_input("Month", min_value=1, max_value=12, value=1)

if st.button("Generate Shifts Now"):
    output = "data/generated_shifts.csv"
    generate_shifts_for_month(int(year), int(month), output)

    df_shifts = pd.read_csv(output)
    # Convert to Shift dataclasses and store in session
    shift_rows = df_shifts.to_dict(orient="records")
    shifts = [Shift.from_dict(r) for r in shift_rows]
    st.session_state["shifts"] = shifts

    st.success(f"Generated {len(shifts)} shifts for {year}-{month:02d}.")
    st.write("Preview of generated shifts:")
    st.dataframe(df_shifts.head(), use_container_width=True)

# ---------------------------------
# STEP 2 — Load Doctors from DB
# ---------------------------------
st.subheader("2. Load Doctors from Database")

doctors = get_all_doctors(active_only=True)

if not doctors:
    st.error("No doctors found in the database. Please add doctors in the Doctor Manager page.")
else:
    st.success(f"{len(doctors)} active doctors loaded from the database.")
    df_doctors = pd.DataFrame(
        [
            {
                "id": d.id,
                "name": d.name,
                "level": d.level,
                "firm": d.firm,
                "contract_hours": d.contract_hours_per_month,
                "min_shifts": d.min_shifts_per_month,
                "max_shifts": d.max_shifts_per_month,
            }
            for d in doctors
        ]
    )
    st.dataframe(df_doctors, use_container_width=True)

# ---------------------------------
# STEP 3 — Generate Roster
# ---------------------------------
st.subheader("3. Generate Roster")

if st.session_state["shifts"] is None:
    st.info("Generate shifts first.")
elif not doctors:
    st.info("Add doctors in the Doctor Manager first.")
else:
    if st.button("Generate Roster"):
        roster = generate_naive_roster(doctors, st.session_state["shifts"])
        st.session_state["roster"] = roster
        st.success("Roster generated successfully!")

# ---------------------------------
# STEP 4 — Display Roster
# ---------------------------------
if st.session_state["roster"]:
    roster = st.session_state["roster"]

    df_assign = pd.DataFrame(
        [
            {"doctor_id": a.doctor_id, "shift_id": a.shift_id}
            for a in roster.assignments
        ]
    )

    st.subheader("Roster Assignments")
    st.dataframe(df_assign, use_container_width=True)

    st.download_button(
        "⬇ Download Roster CSV",
        df_assign.to_csv(index=False).encode("utf-8"),
        "roster_output.csv",
        "text/csv",
    )

