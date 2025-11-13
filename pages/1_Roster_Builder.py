import streamlit as st
import pandas as pd

from core.generate_shifts import generate_shifts_for_month
from core.database import get_all_doctors
from core.solver import generate_naive_roster

st.set_page_config(page_title="Roster Builder", layout="wide")
st.title("📅 Roster Builder")

# Initialise session
for key in ["shifts", "roster"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ---------------------------------
# STEP 1 — Generate Shifts
# ---------------------------------
st.subheader("Generate Shifts for the Month")

col1, col2 = st.columns(2)
year = col1.number_input("Year", 2024, 2035, value=2025)
month = col2.number_input("Month", 1, 12, value=1)

if st.button("Generate Shifts"):
    output = "data/generated_shifts.csv"
    generate_shifts_for_month(int(year), int(month), output)

    df_shifts = pd.read_csv(output)
    st.session_state["shifts"] = df_shifts

    st.success(f"Generated {len(df_shifts)} shifts for {year}-{month:02d}.")
    st.dataframe(df_shifts.head(), use_container_width=True)

# ---------------------------------
# STEP 2 — Load Doctors from DB
# ---------------------------------
st.subheader("Load Doctors (from Database)")

doctors = get_all_doctors(active_only=True)

if not doctors:
    st.error("No doctors found. Add doctors in the Doctor Manager first.")
else:
    st.success(f"Loaded {len(doctors)} doctors from the database.")

    df_doctors = pd.DataFrame(
        {
            "id": [d.id for d in doctors],
            "name": [d.name for d in doctors],
            "level": [d.level for d in doctors],
            "firm": [d.firm for d in doctors],
            "contract_hours": [d.contract_hours_per_month for d in doctors],
            "min_shifts": [d.min_shifts_per_month for d in doctors],
            "max_shifts": [d.max_shifts_per_month for d in doctors],
        }
    )

    st.dataframe(df_doctors, use_container_width=True)

# ---------------------------------
# STEP 3 — Generate Roster
# ---------------------------------
if st.session_state["shifts"] is not None and doctors:
    st.subheader("Generate Roster")

    if st.button("Generate Roster"):
        df_shifts = st.session_state["shifts"]

        # Convert dataframe rows to simple objects the solver expects
        shifts_list = df_shifts.to_dict(orient="records")

        roster = generate_naive_roster(doctors, shifts_list)
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
        "text/csv"
    )
