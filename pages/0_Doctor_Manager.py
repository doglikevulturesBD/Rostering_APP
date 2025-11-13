import streamlit as st
import pandas as pd

from core.database import (
    init_db,
    create_doctor,
    get_all_doctors,
    update_doctor_hours_and_shifts,
    deactivate_doctor,
)

st.set_page_config(page_title="Doctor Manager", layout="wide")
st.title("👨‍⚕️ Doctor Manager")

# Ensure DB and table exist
init_db()

st.subheader("Add New Doctor")

col1, col2, col3 = st.columns(3)
name = col1.text_input("Name", "")
level = col2.selectbox("Level", ["MO", "Registrar", "Consultant", "Community Service"])
firm = col3.number_input("Firm (optional)", min_value=0, max_value=10, value=0)

col4, col5, col6 = st.columns(3)
contract_hours = col4.number_input("Contract hours / month", min_value=40, max_value=240, value=175)
min_shifts = col5.number_input("Min shifts / month", min_value=0, max_value=30, value=16)
max_shifts = col6.number_input("Max shifts / month", min_value=0, max_value=30, value=18)

if st.button("➕ Add Doctor"):
    if not name.strip():
        st.error("Name cannot be empty.")
    else:
        doc = create_doctor(
            name=name.strip(),
            level=level,
            firm=firm if firm != 0 else None,
            contract_hours=int(contract_hours),
            min_shifts=int(min_shifts),
            max_shifts=int(max_shifts),
        )
        st.success(f"Doctor {doc.name} ({doc.id}) added.")
        st.rerun()

st.subheader("Current Doctors")

doctors = get_all_doctors(active_only=False)

if not doctors:
    st.info("No doctors in the system yet.")
else:
    df = pd.DataFrame(
        [
            {
                "external_id": d.id,
                "name": d.name,
                "level": d.level,
                "firm": d.firm,
                "contract_hours": d.contract_hours_per_month,
                "min_shifts": d.min_shifts_per_month,
                "max_shifts": d.max_shifts_per_month,
            }
            for d in doctors
        ]
    )
    st.dataframe(df, use_container_width=True)

    st.markdown("### Edit Hours / Shifts")

    selected_id = st.selectbox(
        "Select doctor",
        options=df["external_id"],
    )

    if selected_id:
        row = df[df["external_id"] == selected_id].iloc[0]
        e_col1, e_col2, e_col3 = st.columns(3)
        new_hours = e_col1.number_input(
            "Contract hours",
            min_value=40,
            max_value=240,
            value=int(row["contract_hours"]),
        )
        new_min = e_col2.number_input(
            "Min shifts",
            min_value=0,
            max_value=30,
            value=int(row["min_shifts"]),
        )
        new_max = e_col3.number_input(
            "Max shifts",
            min_value=0,
            max_value=30,
            value=int(row["max_shifts"]),
        )

        e_col4, e_col5 = st.columns(2)
        if e_col4.button("💾 Save changes"):
            update_doctor_hours_and_shifts(
                external_id=selected_id,
                contract_hours=int(new_hours),
                min_shifts=int(new_min),
                max_shifts=int(new_max),
            )
            st.success("Doctor updated.")
            st.rerun()

        if e_col5.button("🗑 Deactivate doctor"):
            deactivate_doctor(selected_id)
            st.warning("Doctor deactivated.")
            st.rerun()
