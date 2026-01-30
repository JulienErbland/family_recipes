import streamlit as st
from app.lib.session import init_session, is_logged_in
from app.lib.auth_ui import auth_sidebar
from app.lib.repos import get_my_role

st.set_page_config(page_title="Family Recipes (Test)", page_icon="🍲", layout="centered")

init_session()
auth_sidebar()

st.title("🍲 Family Recipes — DB Test Frontend")

if not is_logged_in():
    st.info("Log in using the sidebar to start testing the database.")
    st.stop()

token = st.session_state.session.access_token

# Load role once per session
if st.session_state.role is None:
    st.session_state.role = get_my_role(token)

st.success("Authenticated ✅")
st.write(f"Your role: **{st.session_state.role}**")
st.write("Use the pages in the sidebar to browse recipes and (if editor) add data.")

