# app.py
import streamlit as st

st.set_page_config(
    page_title="Doctor Rostering & Burnout Monitor",
    layout="wide",
)

st.title("🩺 Doctor Rostering Platform")

st.markdown(
    """
Welcome to the **Doctor Rostering & Burnout Monitoring** app.

Use the pages in the sidebar to:

1. **📅 Roster Builder** – load doctors & shifts and generate a roster  
2. **📊 Doctor Dashboard** – see per-doctor hours, shifts, and summaries  
3. **🧠 Burnout Monitor** – view fatigue/burnout risk index in real time  
"""
)

