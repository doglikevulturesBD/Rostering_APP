import streamlit as st
import os
from pathlib import Path

from core.database import DB_PATH

st.set_page_config(page_title="DB Debugger", layout="wide")
st.title("🛠 Database Debugger")

st.write("### Expected Database Path")
st.code(str(DB_PATH))

st.write("### Absolute Path")
st.code(str(DB_PATH.resolve()))

folder_exists = os.path.exists(DB_PATH.parent)
db_exists = os.path.exists(DB_PATH)

st.write("### Does the `data/` folder exist?")
st.write(folder_exists)

st.write("### Does the database file exist?")
st.write(db_exists)

st.write("### Searching for `.db` files in current environment...")
found = []
for root, dirs, files in os.walk(".", topdown=True):
    for f in files:
        if f.endswith(".db"):
            found.append(os.path.join(root, f))

if found:
    st.success("Found the following DB files:")
    st.write(found)
else:
    st.warning("No .db files found in any folder.")

# ---------------------------------------------------------
# DELETE / RESET DATABASE
# ---------------------------------------------------------
st.write("---")
st.write("### ⚠️ Danger Zone — Delete Database")

if st.button("Delete Database (ed_roster.db)"):
    if db_exists:
        os.remove(DB_PATH)
        st.success("Database deleted! Reload the app to recreate it.")
    else:
        st.warning("Database was not found, so nothing was deleted.")
