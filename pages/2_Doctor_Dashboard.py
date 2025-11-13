# pages/2_Doctor_Dashboard.py

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import altair as alt

from core.workload_analyzer import analyze_workload

st.set_page_config(page_title="Doctor Dashboard", layout="wide")
st.title("📊 Doctor Dashboard")

# Get roster from session
roster = st.session_state.get("roster", None)

if roster is None:
    st.info("No roster found. Please generate a roster on the 'Roster Builder' page first.")
    st.stop()

# -------------------------------------
# Common data / lookups
# -------------------------------------
workload = analyze_workload(roster.doctors, roster.shifts, roster.assignments)
shift_map = {s.id: s for s in roster.shifts}
doctor_name_map = {d.id: d.name for d in roster.doctors}
now = datetime.now()

# -------------------------------------
# Section 1: Workload Overview Table
# -------------------------------------
st.subheader("1️⃣ Workload Overview")

rows = []
for doc in roster.doctors:
    w = workload[doc.id]
    rows.append(
        {
            "Doctor": doc.name,
            "Level": doc.level,
            "Shifts": w.total_shifts,
            "Hours": round(w.total_hours, 1),
            "Night Shifts": w.night_shifts,
            "Weekend Shifts": w.weekend_shifts,
            "Consec Days": w.consecutive_days,
            "Consec Nights": w.consecutive_nights,
            "Burnout Score": w.burnout_score,
            "Rest Violations": w.rest_violations,
        }
    )

df_workload = pd.DataFrame(rows)
st.dataframe(df_workload, use_container_width=True)

# -------------------------------------
# Section 2: Burnout Bars
# -------------------------------------
st.subheader("2️⃣ Burnout Index by Doctor")

if not df_workload.empty:
    burnout_df = df_workload[["Doctor", "Burnout Score"]].sort_values(
        "Burnout Score", ascending=False
    )

    chart = (
        alt.Chart(burnout_df)
        .mark_bar()
        .encode(
            x=alt.X("Burnout Score:Q", title="Burnout Score (0–100)"),
            y=alt.Y("Doctor:N", sort="-x", title=""),
            tooltip=["Doctor", "Burnout Score"],
        )
        .properties(height=300)
    )

    st.altair_chart(chart, use_container_width=True)
else:
    st.info("No workload data available.")

# -------------------------------------
# Section 3: 24-hour Coverage Timeline
# -------------------------------------
st.subheader("3️⃣ Next 24 Hours – Coverage Timeline")

next_24h = now + timedelta(hours=24)
timeline_rows = []

for a in roster.assignments:
    shift = shift_map.get(a.shift_id)
    if not shift:
        continue

    # keep shifts that overlap [now, now + 24h]
    latest_start = max(shift.start, now)
    earliest_end = min(shift.end, next_24h)

    if latest_start < earliest_end:
        timeline_rows.append(
            {
                "Doctor": doctor_name_map.get(a.doctor_id, a.doctor_id),
                "Shift Name": shift.name,
                "Start": shift.start,
                "End": shift.end,
                "Is Night": "Night" if shift.is_night else "Day",
                "Is Weekend": "Weekend" if shift.is_weekend else "Weekday",
            }
        )

if not timeline_rows:
    st.info("No scheduled coverage in the next 24 hours.")
else:
    df_timeline = pd.DataFrame(timeline_rows)

    st.write("Shift list for the next 24 hours:")
    st.dataframe(df_timeline, use_container_width=True)

    # Gantt-style chart using Altair
    timeline_chart = (
        alt.Chart(df_timeline)
        .mark_bar()
        .encode(
            y=alt.Y("Doctor:N", title="Doctor"),
            x=alt.X("Start:T", title="Time"),
            x2="End:T",
            color=alt.Color("Is Night:N", title="Shift Type"),
            tooltip=["Doctor", "Shift Name", "Start", "End", "Is Night", "Is Weekend"],
        )
        .properties(height=300)
    )

    st.altair_chart(timeline_chart, use_container_width=True)

# -------------------------------------
# Section 4: Who is on Duty Now?
# -------------------------------------
st.subheader("4️⃣ Who is on Duty Now?")

on_now_rows = []
for a in roster.assignments:
    s = shift_map.get(a.shift_id)
    if s and s.start <= now <= s.end:
        on_now_rows.append(
            {
                "Doctor": doctor_name_map.get(a.doctor_id, a.doctor_id),
                "Shift ID": s.id,
                "Shift Name": s.name,
                "Start": s.start,
                "End": s.end,
                "Type": "Night" if s.is_night else "Day",
                "Day Type": "Weekend" if s.is_weekend else "Weekday",
            }
        )

if not on_now_rows:
    st.info("No doctors currently on duty (based on system time).")
else:
    df_on_now = pd.DataFrame(on_now_rows)
    st.dataframe(df_on_now, use_container_width=True)

# -------------------------------------
# Section 5: Tomorrow's On-Call List
# -------------------------------------
st.subheader("5️⃣ Tomorrow's On-Call List")

tomorrow = (now + timedelta(days=1)).date()
tomorrow_rows = []

for a in roster.assignments:
    s = shift_map.get(a.shift_id)
    if not s:
        continue

    if s.start.date() == tomorrow:
        tomorrow_rows.append(
            {
                "Doctor": doctor_name_map.get(a.doctor_id, a.doctor_id),
                "Shift ID": s.id,
                "Shift Name": s.name,
                "Start": s.start,
                "End": s.end,
                "Type": "Night" if s.is_night else "Day",
                "Day Type": "Weekend" if s.is_weekend else "Weekday",
            }
        )

if not tomorrow_rows:
    st.info("No shifts found for tomorrow in the current roster.")
else:
    df_tomorrow = pd.DataFrame(tomorrow_rows)
    st.dataframe(df_tomorrow.sort_values("Start"), use_container_width=True)

# -------------------------------------
# Section 6: Weekly Workload / Burnout Trend
# -------------------------------------
st.subheader("6️⃣ Weekly Workload Trend (All Doctors Combined)")

# Simple approach: for each of the next 7 days,
# compute a "load index" = sum of shift intensities overlapping that day.
trend_rows = []
for day_offset in range(7):
    date_obj = (now + timedelta(days=day_offset)).date()

    load_index = 0
    for a in roster.assignments:
        s = shift_map.get(a.shift_id)
        if not s:
            continue

        if s.start.date() == date_obj:
            load_index += s.intensity

    trend_rows.append(
        {
            "Date": date_obj,
            "Load Index": load_index,
        }
    )

df_trend = pd.DataFrame(trend_rows)

if df_trend["Load Index"].sum() == 0:
    st.info("No workload scheduled over the next 7 days in this roster.")
else:
    line_chart = (
        alt.Chart(df_trend)
        .mark_line(point=True)
        .encode(
            x=alt.X("Date:T", title="Date"),
            y=alt.Y("Load Index:Q", title="Total Shift Intensity (All Doctors)"),
            tooltip=["Date", "Load Index"],
        )
        .properties(height=300)
    )

    st.altair_chart(line_chart, use_container_width=True)
    st.dataframe(df_trend, use_container_width=True)

