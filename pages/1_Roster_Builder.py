import streamlit as st
import pandas as pd
from datetime import datetime

from core.generate_shifts import generate_shifts_for_month
from core.database import (
    load_shifts,
    get_all_doctors,
)
from core.optimizer import build_and_solve_roster  # your OR-Tools solver
from core.workload_analyzer import compute_workload


st.set_page_config(page_title="Roster Builder", layout="wide")
st.title("📅 Roster Builder")


# =========================================================
# 1) INPUT: SELECT MONTH + YEAR
# =========================================================

st.subheader("📆 Generate Monthly Shifts")

col1, col2 = st.columns(2)
year = col1.number_input("Year", min_value=2020, max_value=2100, value=datetime.now().year)
month = col2.number_input("Month (1–12)", min_value=1, max_value=12, value=datetime.now().month)

generate_btn = st.button("🛠 Generate Shifts for This Month", type="primary")

if generate_btn:
    try:
        generate_shifts_for_month(int(year), int(month))
        st.success("Shifts successfully generated!")
        st.rerun()
    except Exception as e:
        st.error(f"Error generating shifts: {e}")


# =========================================================
# 2) DISPLAY SHIFTS
# =========================================================

st.subheader("🗂 Generated Shifts")

shifts = load_shifts()

if not shifts:
    st.info("No shifts found. Please generate shifts first.")
    st.stop()

shift_df = pd.DataFrame([s.to_dict() for s in shifts])
st.dataframe(shift_df, width="stretch")


# =========================================================
# 3) GET DOCTORS
# =========================================================

st.subheader("👨‍⚕️ Doctors Available for Scheduling")

doctors = get_all_doctors(active_only=True)

if not doctors:
    st.warning("No active doctors found. Add doctors first.")
    st.stop()

docs_df = pd.DataFrame([d.__dict__ for d in doctors])
st.dataframe(docs_df, width="stretch")


# =========================================================
# 4) RUN OPTIMISER
# =========================================================

st.subheader("🤖 Generate Optimised Roster (OR-Tools)")

if st.button("Run Optimiser", type="primary"):
    try:
        assignments = build_and_solve_roster(doctors, shifts)

        if assignments is None or len(assignments) == 0:
            st.error("❗ No feasible solution found.")
            st.stop()

        st.session_state["assignments"] = assignments
        st.success("Optimised roster generated successfully!")

    except Exception as e:
        st.error(f"Error running optimiser: {e}")


# =========================================================
# 5) SHOW ASSIGNMENTS
# =========================================================

if "assignments" in st.session_state:
    st.subheader("📋 Final Roster Assignments")

    roster = st.session_state["assignments"]

    df = pd.DataFrame(
        {
            "doctor": [a.doctor_id for a in roster.assignments],
            "shift_id": [a.shift_id for a in roster.assignments],
            "start": [a.shift_start for a in roster.assignments],
            "end": [a.shift_end for a in roster.assignments],
        }
    )

    st.dataframe(df, width="stretch")

    # --------------------------------------------------------
    # DOWNLOAD CSV
    # --------------------------------------------------------
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Download Roster CSV",
        data=csv,
        file_name="roster_output.csv",
        mime="text/csv",
    )


# =========================================================
# 6) WORKLOAD ANALYSIS (Burnout Index Preview)
# =========================================================

if "assignments" in st.session_state:
    st.subheader("🔥 Workload & Burnout Preview")

    workload_summary = compute_workload(
        doctors=doctors,
        shifts=shifts,
        assignments=st.session_state["assignments"].assignments,
    )

    workload_df = pd.DataFrame([w.to_dict() for w in workload_summary])
    st.dataframe(workload_df, width="stretch")

