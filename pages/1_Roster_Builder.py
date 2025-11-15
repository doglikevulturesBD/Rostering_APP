import streamlit as st
import pandas as pd
from datetime import datetime

from core.generate_shifts import generate_shifts_for_month
from core.database import (
    load_shifts,
    get_all_doctors,
    save_assignments,
)
from core.optimizer import build_and_solve_roster
from core.workload_analyzer import compute_workload

st.set_page_config(page_title="Roster Builder", layout="wide")
st.title("📅 Roster Builder")

# ---------------------------------------------------------
# 1) Generate monthly shifts
# ---------------------------------------------------------

st.header("1️⃣ Generate Monthly Shifts")

col1, col2 = st.columns(2)
year = col1.number_input(
    "Year", min_value=2024, max_value=2100, value=datetime.now().year
)
month = col2.number_input(
    "Month (1–12)", min_value=1, max_value=12, value=datetime.now().month
)

if st.button("🛠 Generate Shifts for This Month", type="primary"):
    try:
        generate_shifts_for_month(int(year), int(month))
        st.success("Shifts successfully generated and saved to the database.")
        st.rerun()
    except Exception as e:
        st.error(f"Error generating shifts: {e}")

# ---------------------------------------------------------
# 2) Show shifts & doctors
# ---------------------------------------------------------

st.header("2️⃣ Current Shifts & Doctors")

shifts = load_shifts()
doctors = get_all_doctors(active_only=True)

col_shifts, col_docs = st.columns(2)

with col_shifts:
    st.subheader("Shifts")
    if not shifts:
        st.info("No shifts found. Generate for a month above.")
    else:
        df_shifts = pd.DataFrame([s.to_dict() for s in shifts])
        st.dataframe(df_shifts, use_container_width=True)

with col_docs:
    st.subheader("Doctors")
    if not doctors:
        st.warning("No active doctors found. Add doctors in the Doctor Manager page.")
    else:
        df_docs = pd.DataFrame(
            [
                {
                    "id": d.id,
                    "name": d.name,
                    "level": d.level,
                    "firm": d.firm,
                    "contract_hours": d.contract_hours_per_month,
                    "min_shifts": d.min_shifts_per_month,
                    "max_shifts": d.max_shifts_per_month,
                    "active": d.active,
                }
                for d in doctors
            ]
        )
        st.dataframe(df_docs, use_container_width=True)

# If we don't have both, stop here
if not shifts or not doctors:
    st.stop()

# ---------------------------------------------------------
# 3) Run optimiser
# ---------------------------------------------------------

st.header("3️⃣ Optimise Roster")

if st.button("🤖 Run Optimiser", type="primary"):
    try:
        with st.spinner("Solving roster (PuLP)..."):
            result = build_and_solve_roster(doctors, shifts)

        if result is None or len(result.assignments) == 0:
            st.error("❌ No feasible solution found by the optimiser.")
        else:
            st.success("✅ Optimised roster generated!")

            # Save to session
            st.session_state["assignment_result"] = result

            # Persist to DB (optional but recommended)
            try:
                save_assignments(result.assignments)
            except Exception as e:
                st.warning(f"Assignments not saved to DB (session-only): {e}")

    except Exception as e:
        st.error(f"Error running optimiser: {e}")

# ---------------------------------------------------------
# 4) Display roster & workload
# ---------------------------------------------------------

st.header("4️⃣ Roster & Workload Summary")

if "assignment_result" not in st.session_state:
    st.info("Run the optimiser to generate a roster.")
else:
    result = st.session_state["assignment_result"]
    assignments = result.assignments

    if not assignments:
        st.warning("Optimiser returned an empty assignment list.")
    else:
        # ---- Roster table
        st.subheader("📋 Final Roster")

        df_assign = pd.DataFrame(
            [
                {
                    "doctor_id": a.doctor_id,
                    "shift_id": a.shift_id,
                    "shift_date": a.shift_start.date()
                    if hasattr(a.shift_start, "date")
                    else str(a.shift_start),
                    "start_time": a.shift_start.time()
                    if hasattr(a.shift_start, "time")
                    else "",
                    "end_time": a.shift_end.time()
                    if hasattr(a.shift_end, "time")
                    else "",
                }
                for a in assignments
            ]
        )

        st.dataframe(df_assign, use_container_width=True)

        # Download CSV
        csv_bytes = df_assign.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download Roster CSV",
            data=csv_bytes,
            file_name="roster_output.csv",
            mime="text/csv",
        )

        # ---- Workload summary
        st.subheader("🔥 Workload & Burnout Preview")

        try:
            workload = compute_workload(doctors, shifts, assignments)
            df_work = pd.DataFrame([w.to_dict() for w in workload])
            st.dataframe(df_work, use_container_width=True)
        except Exception as e:
            st.warning(f"Could not compute workload summary: {e}")


