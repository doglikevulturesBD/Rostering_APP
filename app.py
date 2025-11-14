# app.py

import streamlit as st

st.set_page_config(page_title="Doctor Rostering App", layout="wide")

st.title("🏥 Doctor Rostering App")
st.write(
    """
Use the sidebar to navigate:

- **Doctor Manager**: manage doctors and their contract parameters  
- **Roster Builder**: generate shifts and build rosters (naive or optimised)  
- **Doctor Dashboard**: see who is on duty and review workload  
- **Leave Manager**: capture leave requests (affects optimiser)
"""
)
