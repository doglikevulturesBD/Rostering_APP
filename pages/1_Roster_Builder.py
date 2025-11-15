import streamlit as st
import pandas as pd
from datetime import datetime

from core.generate_shifts import generate_shifts_for_month
from core.database import (
    load_shifts,
    save_assignments,
)
from core.optimizer import build_and_solve_roster
from core.workload_analyzer import compute_workload

st.set_page_config(page_title="Roster Builder", layout="wide")
st.title("🗓️ Roster Builder")

# ---------------------------------------------------------
# SECTION: SHIFT GENERATION
# ---------------------------------------------------------

st.header("1️⃣ Generate Monthly Shifts")

col1, col2 = st.columns(2)
year = col1.number_input("Year", min_value=2024, max_value=2050, value=datetime.now().year)
month = col2.number_input("Month", min_value=1, max_value=12, value=datetime.now().month)

if st.button("📅 Generate Shifts for Month"):
    try:
        generate_shifts_for_month(int(year), int(month))
        st.success("Shifts generated and saved to database.")
    except Exception as e:
        st.error(f"Error: {e}")

shifts = load_shifts()

if shifts:
    st.write("### Generated Shifts Preview")
    df_shifts = pd.DataFrame([s.to_dict() for s in shifts])
    st.dataframe(df_shifts, use_container_width=True)
else:
    st.info("No shifts available. Generate above.")

# ---------------------------------------------------------
# SECTION: OPTIMIZER
# ---------------------------------------------------------

st.header("2️⃣ Build & Solve Monthly Roster")

if st.button("⚙️ Run Optimizer"):
    if not shifts:
        st.error("No shifts found. Please generate shifts first.")
    else:
        with st.spinner("Optimizing roster... this may take 10–20 seconds..."):
            result = build_and_solve_roster(shifts)

        if result is None:
            st.error("❌ No feasible solution found.")
        else:
            st.success("Roster successfully optimized!")

            # Store into session
            st.session_state["assignments"] = result

            # Also save to DB (optional)
            try:
                save_assignments(result.assignments)
            except Exception as e:
                st.warning(f"Assignments saved to session only (DB save failed): {e}")

# ---------------------------------------------------------
# SECTION: DISPLAY RESULTS
# ---------------------------------------------------------

st.header("3️⃣ Roster Results")

if "assignments" not in st.session_state:
    st.info("Run the optimizer to view the roster.")
else:
    result = st.session_state["assignments"]

    # Safely extract the assignments list
    assignments = result.assignments

    # If empty (rare), inform user
    if len(assignments) == 0:
        st.warning("Optimizer returned 0 assignments.")
    else:
        st.write("### Final Roster")

        df = pd.DataFrame([
            {
                "doctor": a.doctor_id,
                "shift_id": a.shift_id,
                "date": a.shift_start.date(),
                "start": a.shift_start.time(),
                "end": a.shift_end.time(),
            }
            for a in assignments
        ])

        st.dataframe(df, use_container_width=True)

        # ---------------------------------------------------------
        # SECTION: WORKLOAD ANALYSIS
        # ---------------------------------------------------------
        st.write("### Doctor Workload Summary")

        wl = compute_workload(assignments)

        df_work = pd.DataFrame(wl)
        st.dataframe(df_work, use_container_width=True)

