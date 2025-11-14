# pages/1_Roster_Builder.py

import streamlit as st
import pandas as pd

from core.generate_shifts import generate_shifts_for_month
from core.database import load_shifts, get_all_doctors, get_all_leave
from core.solver import generate_naive_roster
from core.optimizer import generate_optimized_roster
from core.workload_analyzer import analyze_workload
from core.feasibility import analyze_feasibility

st.set_page_config(page_title="Roster Builder", layout="wide")
st.title("📅 Roster Builder")

for key in ["shifts", "roster", "feasibility"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ------------------------------------------------------------
# 1. Generate Shifts
# ------------------------------------------------------------
st.subheader("1. Generate Shifts")

c1, c2 = st.columns(2)
year = c1.number_input("Year", 2024, 2035, value=2025)
month = c2.number_input("Month", 1, 12, value=1)

if st.button("Generate Shifts"):
    csv_path = "data/generated_shifts.csv"
    generate_shifts_for_month(int(year), int(month), csv_path)
    shifts = load_shifts()
    st.session_state["shifts"] = shifts
    st.session_state["feasibility"] = None
    st.success(f"Generated {len(shifts)} shifts.")
    try:
        st.dataframe(pd.read_csv(csv_path).head(), width="stretch")
    except Exception:
        st.info("Shifts saved to DB. CSV preview unavailable.")

# ------------------------------------------------------------
# 2. Load Doctors
# ------------------------------------------------------------
st.subheader("2. Load Doctors")

doctors = get_all_doctors(active_only=True)
if not doctors:
    st.error("No active doctors found. Add doctors on Doctor Manager page.")
else:
    st.success(f"{len(doctors)} doctors loaded.")
    df_docs = pd.DataFrame(
        [
            {
                "ID": d.id,
                "Name": d.name,
                "Level": d.level,
                "Firm": d.firm,
                "Min Shifts": d.min_shifts_per_month,
                "Max Shifts": d.max_shifts_per_month,
                "Contract Hours": d.contract_hours_per_month,
            }
            for d in doctors
        ]
    )
    st.dataframe(df_docs, width="stretch")

# ------------------------------------------------------------
# 3. Feasibility Analysis
# ------------------------------------------------------------
st.subheader("3. Feasibility Analysis")

shifts = st.session_state["shifts"]

if shifts and doctors:
    if st.button("Run Feasibility Analysis"):
        leave_rows = get_all_leave()
        feas = analyze_feasibility(doctors, shifts, leave_rows=leave_rows)
        st.session_state["feasibility"] = feas

    feas = st.session_state["feasibility"]
    if feas:
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("Min demand", feas["total_min_demand"])
        col_b.metric("Max demand", feas["total_max_demand"])
        col_c.metric("Min capacity", feas["total_min_capacity"])
        col_d.metric("Max capacity", feas["total_max_capacity"])

        st.metric("Night-shift demand", feas["night_shift_demand"])
        st.metric("Weekend-shift demand", feas["weekend_shift_demand"])

        if feas["warnings"]:
            st.markdown("**Warnings / Notes:**")
            for w in feas["warnings"]:
                st.write(f"- {w}")

        if not feas["feasible"]:
            st.warning(
                "Feasibility analysis detected potential problems. "
                "You can still attempt optimisation, but it may fail."
            )
else:
    st.info("Generate shifts and ensure doctors exist before running feasibility.")

# ------------------------------------------------------------
# 4. Generate roster
# ------------------------------------------------------------
st.subheader("4. Generate Roster")

mode = st.radio(
    "Mode",
    ["Naive assignment", "Optimised (PuLP with fairness)"],
    index=1,
)

if shifts and doctors:
    if st.button("Generate Roster"):
        try:
            if mode == "Naive assignment":
                roster = generate_naive_roster(doctors, shifts)
            else:
                leave_rows = get_all_leave()
                roster = generate_optimized_roster(
                    doctors,
                    shifts,
                    leave_rows=leave_rows,
                    rest_hours_required=11.0,  # can tweak later
                )
            st.session_state["roster"] = roster
            st.success(f"Roster generated using: {mode}")
        except Exception as e:
            st.error(f"Error generating roster: {e}")
else:
    st.info("Generate shifts and ensure doctors exist before generating a roster.")

# ------------------------------------------------------------
# 5. Display assignments & workload
# ------------------------------------------------------------
if st.session_state["roster"]:
    roster = st.session_state["roster"]

    st.subheader("5. Roster Assignments")
    df_assign = pd.DataFrame(
        [{"Doctor": a.doctor_id, "Shift": a.shift_id} for a in roster.assignments]
    )
    st.dataframe(df_assign, width="stretch")
    st.download_button(
        "⬇ Download roster CSV",
        df_assign.to_csv(index=False).encode("utf-8"),
        "roster_output.csv",
        "text/csv",
    )

    st.subheader("6. Workload & Burnout Summary")
    workload = analyze_workload(roster.doctors, roster.shifts, roster.assignments)

    rows = []
    for doc in roster.doctors:
        w = workload[doc.id]
        rows.append(
            {
                "Doctor": doc.name,
                "Shifts": w.total_shifts,
                "Hours": round(w.total_hours, 1),
                "Night Shifts": w.night_shifts,
                "Weekend Shifts": w.weekend_shifts,
                "Consec Days": w.consecutive_days,
                "Consec Nights": w.consecutive_nights,
                "Rest Violations": w.rest_violations,
                "Burnout Score": round(w.burnout_score, 1),
            }
        )
    st.dataframe(pd.DataFrame(rows), width="stretch")
