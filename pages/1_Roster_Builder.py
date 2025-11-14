import streamlit as st
import pandas as pd

from core.generate_shifts import generate_shifts_for_month
from core.database import load_shifts, get_all_doctors, get_all_leave
from core.solver import generate_naive_roster
from core.optimizer import generate_optimized_roster
from core.workload_analyzer import analyze_workload

st.set_page_config(page_title="Roster Builder", layout="wide")
st.title("📅 Roster Builder")

for key in ["shifts", "roster"]:
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

    st.success(f"Generated {len(shifts)} shifts")

    try:
        st.dataframe(pd.read_csv(csv_path).head(), width="stretch")
    except:
        st.info("Shifts saved, but CSV preview unavailable.")


# ------------------------------------------------------------
# 2. Load Doctors
# ------------------------------------------------------------
st.subheader("2. Load Doctors")

doctors = get_all_doctors(active_only=True)
if not doctors:
    st.error("No active doctors found. Add doctors first.")
else:
    st.success(f"{len(doctors)} doctors loaded.")
    df_doctors = pd.DataFrame([
        {
            "ID": d.id,
            "Name": d.name,
            "Level": d.level,
            "Firm": d.firm,
            "Min Shifts": d.min_shifts_per_month,
            "Max Shifts": d.max_shifts_per_month,
        }
        for d in doctors
    ])
    st.dataframe(df_doctors, width="stretch")


# ------------------------------------------------------------
# 3. Choose Mode
# ------------------------------------------------------------
st.subheader("3. Generate Roster")

mode = st.radio(
    "Choose Mode",
    ["Naive assignment", "Optimised (PuLP)"],
    index=1,
)

shifts = st.session_state["shifts"]

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
                    rest_hours_required=11,   # UPDATED: was 18
                )

            st.session_state["roster"] = roster
            st.success(f"Roster generated: {mode}")

        except Exception as e:
            st.error(f"Optimizer error: {e}")
else:
    st.info("Generate shifts and load doctors first.")


# ------------------------------------------------------------
# 4. Display Assignments
# ------------------------------------------------------------
if st.session_state["roster"]:
    roster = st.session_state["roster"]

    st.subheader("4. Roster Assignments")

    df_assign = pd.DataFrame([
        {"Doctor": a.doctor_id, "Shift": a.shift_id}
        for a in roster.assignments
    ])

    st.dataframe(df_assign, width="stretch")

    st.download_button(
        "⬇ Download CSV",
        df_assign.to_csv(index=False).encode("utf-8"),
        "roster_output.csv",
        "text/csv",
    )

    # --------------------------------------------------------
    # 5. Workload / Burnout Summary
    # --------------------------------------------------------
    st.subheader("5. Workload & Burnout Summary")

    workload = analyze_workload(
        roster.doctors,
        roster.shifts,
        roster.assignments,
    )

    rows = []
    for doc in roster.doctors:
        w = workload[doc.id]
        rows.append({
            "Doctor": doc.name,
            "Shifts": w.total_shifts,
            "Hours": round(w.total_hours, 1),
            "Night shifts": w.night_shifts,
            "Weekend shifts": w.weekend_shifts,
            "Consec Days": w.consecutive_days,
            "Consec Nights": w.consecutive_nights,
            "Rest Violations": w.rest_violations,
            "Burnout Score": round(w.burnout_score, 1),
        })

    df_work = pd.DataFrame(rows)
    st.dataframe(df_work, width="stretch")
