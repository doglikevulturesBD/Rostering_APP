# pages/1_Roster_Builder.py

import streamlit as st
import pandas as pd

from core.generate_shifts import generate_shifts_for_month
from core.database import load_shifts, get_all_doctors
from core.solver import generate_naive_roster
from core.workload_analyzer import analyze_workload

st.set_page_config(page_title="Roster Builder", layout="wide")
st.title("📅 Roster Builder")

# Ensure session keys exist
for key in ["shifts", "roster"]:
    if key not in st.session_state:
        st.session_state[key] = None

# -----------------------------
# 1. Generate Shifts
# -----------------------------
st.subheader("1. Generate Shifts")

col1, col2 = st.columns(2)
year = col1.number_input("Year", 2024, 2035, value=2025)
month = col2.number_input("Month", 1, 12, value=1)

if st.button("Generate Shifts"):
    output = "data/generated_shifts.csv"
    generate_shifts_for_month(int(year), int(month), output)

    # Load from DB to ensure DB & UI aligned
    shifts = load_shifts()
    st.session_state["shifts"] = shifts

    st.success(f"Generated & saved {len(shifts)} shifts.")
    st.write("Preview of CSV:")
    st.dataframe(pd.read_csv(output).head(), use_container_width=True)

# -----------------------------
# 2. Load Doctors
# -----------------------------
st.subheader("2. Load Doctors")

doctors = get_all_doctors(active_only=True)

if not doctors:
    st.error("No doctors in DB. Please add them on the Doctor Manager page.")
else:
    st.success(f"{len(doctors)} doctors loaded.")
    df_docs = pd.DataFrame(
        [
            {
                "ID": d.id,
                "Name": d.name,
                "Level": d.level,
                "Firm": d.firm,
                "Contract Hours": d.contract_hours_per_month,
                "Min Shifts": d.min_shifts_per_month,
                "Max Shifts": d.max_shifts_per_month,
            }
            for d in doctors
        ]
    )
    st.dataframe(df_docs, use_container_width=True)

# -----------------------------
# 3. Generate Roster
# -----------------------------
st.subheader("3. Generate Roster")

if st.session_state["shifts"] and doctors:
    if st.button("Generate Roster"):
        roster = generate_naive_roster(doctors, st.session_state["shifts"])
        st.session_state["roster"] = roster
        st.success("Roster generated!")
else:
    st.info("You need shifts and doctors before generating a roster.")

# -----------------------------
# 4. Display Assignments
# -----------------------------
if st.session_state["roster"]:
    roster = st.session_state["roster"]

    st.subheader("Roster Assignments")

    df_assign = pd.DataFrame(
        [
            {"Doctor ID": a.doctor_id, "Shift ID": a.shift_id}
            for a in roster.assignments
        ]
    )

    st.dataframe(df_assign, use_container_width=True)

    st.download_button(
        "⬇ Download Roster CSV",
        df_assign.to_csv(index=False).encode("utf-8"),
        file_name="roster_output.csv",
        mime="text/csv",
    )

    # -----------------------------
    # 5. Workload + Burnout Summary
    # -----------------------------
    st.subheader("Doctor Workload & Burnout Summary")

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
                "Burnout Score": w.burnout_score,
            }
        )

    df_work = pd.DataFrame(rows)
    st.dataframe(df_work, use_container_width=True)

    # -----------------------------
    # 6. Warnings / Violations
    # -----------------------------
    st.subheader("Warnings & Rest Violations")

    for doc in roster.doctors:
        w = workload[doc.id]
        if w.rule_flags:
            with st.expander(f"{doc.name} — {len(w.rule_flags)} issues"):
                for flag in w.rule_flags:
                    st.write(f"⚠️ {flag}")
        else:
            st.write(f"✅ {doc.name} — No issues found")
