# pages/3_🧠_Burnout_Monitor.py
import streamlit as st
import pandas as pd

from core.burnout.burnout_index import compute_burnout_scores

st.set_page_config(page_title="Burnout Monitor", layout="wide")
st.title("🧠 Burnout Monitor")

if "roster" not in st.session_state:
    st.warning("No roster found. Please generate one in the Roster Builder page.")
    st.stop()

roster = st.session_state["roster"]

scores = compute_burnout_scores(
    roster.doctors,
    roster.shifts,
    roster.assignments,
)

rows = []
id_to_name = {d.id: d.name for d in roster.doctors}

for doc_id, info in scores.items():
    row = {
        "doctor_id": doc_id,
        "name": id_to_name.get(doc_id, doc_id),
        "burnout_score": info["score"],
        "risk_level": info["label"],
        **info["details"],
    }
    rows.append(row)

df = pd.DataFrame(rows)

st.subheader("Burnout Index by Doctor")

# colour code risk
def highlight_risk(row):
    color = ""
    if row["risk_level"] == "low":
        color = "background-color: #d4edda"
    elif row["risk_level"] == "medium":
        color = "background-color: #fff3cd"
    else:
        color = "background-color: #f8d7da"
    return [color] * len(row)

st.dataframe(df.style.apply(highlight_risk, axis=1), use_container_width=True)

# optional: show currently on shift (very simple placeholder)
st.markdown("### Doctors likely currently on duty (simplified)")
st.write("You can later add real-time filtering by current time here.")

