# pages/3_Leave_Manager.py

import streamlit as st
import pandas as pd
from datetime import datetime

from core.database import (
    init_db,
    get_all_doctors,
    create_leave,
    get_all_leave,
    delete_leave,
)

st.set_page_config(page_title="Leave Manager", layout="wide")
st.title("🏖 Leave Manager")

init_db()

doctors = get_all_doctors(active_only=True)
if not doctors:
    st.error("No doctors found. Add doctors before managing leave.")
else:
    st.subheader("Add Leave Request")

    doc_map = {f"{d.name} ({d.id})": d.id for d in doctors}
    label = st.selectbox("Doctor", list(doc_map.keys()))
    doc_id = doc_map[label]

    c1, c2 = st.columns(2)
    start_date = c1.date_input("Start date", datetime.today())
    end_date = c2.date_input("End date", datetime.today())

    leave_type = st.selectbox("Type", ["Annual", "Sick", "Study", "Other"])
    reason = st.text_input("Reason (optional)", "")

    if st.button("➕ Add Leave"):
        if end_date < start_date:
            st.error("End date cannot be before start date.")
        else:
            create_leave(
                doctor_external_id=doc_id,
                start_date=datetime.combine(start_date, datetime.min.time()),
                end_date=datetime.combine(end_date, datetime.min.time()),
                leave_type=leave_type,
                reason=reason,
            )
            st.success("Leave added.")
            st.rerun()

    st.subheader("Existing Leave Entries")
    leave_rows = get_all_leave()
    if not leave_rows:
        st.info("No leave requests recorded.")
    else:
        df_leave = pd.DataFrame(
            [
                {
                    "id": r["id"],
                    "doctor_id": r["doctor_external_id"],
                    "start_date": r["start_date"],
                    "end_date": r["end_date"],
                    "type": r["leave_type"],
                    "reason": r["reason"],
                }
                for r in leave_rows
            ]
        )
        st.dataframe(df_leave, width="stretch")

        delete_id = st.selectbox("Select leave ID to delete", df_leave["id"])
        if st.button("🗑 Delete selected leave"):
            delete_leave(int(delete_id))
            st.warning("Leave entry deleted.")
            st.rerun()

