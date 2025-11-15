# pages/2_Doctor_Dashboard.py

import streamlit as st
import pandas as pd
from datetime import datetime

from core.database import get_all_doctors, load_shifts, load_assignments
from core.optimizer import is_night_shift  # reuse same definition

st.set_page_config(page_title="Doctor Dashboard", layout="wide")
st.title("👨‍⚕️ Doctor Dashboard & Burnout Snapshot")

# --------------------------------------------------------
# Load data
# --------------------------------------------------------
doctors = get_all_doctors(active_only=True)
shifts = load_shifts()
assignments = load_assignments()  # should return list[Assignment] or rows

if not doctors or not shifts or not assignments:
    st.warning("Not enough data to show dashboard. Make sure doctors, shifts, and a roster exist.")
    st.stop()

# Build lookup maps
doctor_by_id = {d.id: d for d in doctors}
shift_by_id = {s.id: s for s in shifts}

# Normalise assignments into a list of dicts:
normalized_assignments = []
for a in assignments:
    # Handle both dataclass-style and dict/Row
    doc_id = getattr(a, "doctor_id", None) or a["doctor_id"]
    shift_id = getattr(a, "shift_id", None) or a["shift_id"]

    if doc_id not in doctor_by_id or shift_id not in shift_by_id:
        continue

    sh = shift_by_id[shift_id]
    doc = doctor_by_id[doc_id]

    normalized_assignments.append(
        {
            "doctor_id": doc_id,
            "doctor_name": doc.name,
            "level": doc.level,
            "shift_id": shift_id,
            "date": sh.start.date(),
            "start": sh.start,
            "end": sh.end,
            "duration_hours": sh.duration_hours,
            "is_night": is_night_shift(sh),
            "is_weekend": sh.is_weekend,
        }
    )

if not normalized_assignments:
    st.warning("No valid assignments found. Please regenerate the roster.")
    st.stop()

assign_df = pd.DataFrame(normalized_assignments)

# --------------------------------------------------------
# SECTION 1: Who is on duty now?
# --------------------------------------------------------
st.subheader("🩺 Who is on duty *right now*?")

now = datetime.now()

on_duty = assign_df[
    (assign_df["start"] <= now) & (assign_df["end"] > now)
].copy()

if on_duty.empty:
    st.info("No one is currently on duty according to the stored roster.")
else:
    display_cols = ["doctor_name", "level", "start", "end", "is_night", "is_weekend"]
    st.dataframe(on_duty[display_cols].sort_values("start"), width="stretch")

# --------------------------------------------------------
# SECTION 2: Per-doctor workload summary
# --------------------------------------------------------
st.subheader("📊 Workload Summary (Shifts, Hours, Nights, Weekends)")

summary = (
    assign_df
    .groupby(["doctor_id", "doctor_name", "level"])
    .agg(
        total_shifts=("shift_id", "count"),
        total_hours=("duration_hours", "sum"),
        night_shifts=("is_night", "sum"),
        weekend_shifts=("is_weekend", "sum"),
    )
    .reset_index()
)

# Burnout Index (simple, v1):
# - Base on hours vs 180h, night_shifts, weekend_shifts
def compute_burnout(row):
    # Contract baseline: 180 hours (adjust later or pull from doctor.contract_hours_per_month)
    hours_score = min(row["total_hours"] / 180.0, 1.5)  # cap overweight a bit
    night_score = row["night_shifts"] / 5.0  # 5+ nights pushes this up
    weekend_score = row["weekend_shifts"] / 6.0  # if lots of weekends, higher

    # Simple weighted sum, scaled to 0–100
    raw = 0.5 * hours_score + 0.3 * night_score + 0.2 * weekend_score
    scaled = max(0.0, min(raw * 100.0 / 1.5, 100.0))  # keep in [0, 100]
    return round(scaled, 1)

summary["burnout_index"] = summary.apply(compute_burnout, axis=1)

# Nicely sorted: highest burnout first
summary = summary.sort_values("burnout_index", ascending=False)

st.dataframe(
    summary[
        [
            "doctor_name",
            "level",
            "total_shifts",
            "total_hours",
            "night_shifts",
            "weekend_shifts",
            "burnout_index",
        ]
    ],
    width="stretch",
)

# --------------------------------------------------------
# SECTION 3: Quick filters for consultants / registrars / MOs
# --------------------------------------------------------
st.subheader("🔎 Filter by level")

levels = ["All"] + sorted(summary["level"].unique().tolist())
selected_level = st.selectbox("Filter by level", options=levels, index=0)

if selected_level != "All":
    filtered = summary[summary["level"] == selected_level]
else:
    filtered = summary

st.dataframe(
    filtered[
        [
            "doctor_name",
            "level",
            "total_shifts",
            "total_hours",
            "night_shifts",
            "weekend_shifts",
            "burnout_index",
        ]
    ],
    width="stretch",
)
