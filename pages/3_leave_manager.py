import streamlit as st
import pandas as pd
from datetime import date

from core.database import (
    get_all_doctors,
    create_leave_request,
    get_all_leave,
    delete_leave,
)

st.set_page_config(page_title="Leave Manager", layout="wide")
st.title("🏥 Leave Manager")

st.subheader("Add New Leave Request")

doctors = get_all_doctors(active_only=True)
doctor_map = {d.name: d.id for d in doctors}

col1, col2 = st.columns(2)
doctor_name = col1.selectbox("Doctor", list(doctor_map.keys()))
leave_type = col2.selectbox("Type of Leave", ["Annual", "Sick"])

col3, col4 = st.columns(2)
start = col3.date_input("Start Date", value=date.today())
end = col4.date_input("End Date", value=date.today())

reason = st.text_area("Reason (optional)")

if st.button("➕ Submit Leave Request"):
    create_leave_request(
        doctor_id=doctor_map[doctor_name],
        leave_type=leave_type.lower(),
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        reason=reason,
    )
    st.success("Leave recorded successfully!")
    st.rerun()

# ----------------------------
# View Existing Leave
# ----------------------------
st.subheader("Leave Records")

leave_rows = get_all_leave()

if not leave_rows:
    st.info("No leave entries yet.")
else:
    df = pd.DataFrame(leave_rows)
    st.dataframe(df, use_container_width=True)

    delete_id = st.number_input("Delete Leave Entry (ID)", min_value=1, step=1)

    if st.button("🗑 Delete Leave"):
        delete_leave(delete_id)
        st.warning("Leave entry removed.")
        st.rerun()
