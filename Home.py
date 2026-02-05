import streamlit as st
from app.lib.session import init_session, is_logged_in
from app.lib.auth_ui import auth_sidebar
from app.lib.repos import get_my_role
from app.lib.ui import load_css

st.set_page_config(page_title="Les recettes de la Madre", page_icon="🍋", layout="wide")

init_session()
#load_css()

# Sidebar auth
auth_sidebar()
st.write("DEBUG: after auth_sidebar")
st.sidebar.write("DEBUG: sidebar is alive")

st.title("Home page")

if not is_logged_in():
    st.info("Log in using the sidebar to start.")
    st.stop()

token = st.session_state.session.access_token

# Make sure role key exists
if "role" not in st.session_state or st.session_state.role is None:
    st.session_state.role = get_my_role(token)

st.success("Authenticated ✅")
st.write(f"Your role: **{st.session_state.role}**")
st.write("Use the pages in the left navigation to browse recipes and (if editor) add/manage data.")

st.write("")
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(
        "<div class='card'><h3>📚 Browse</h3><p>Filter by season, creator, and ingredients — then open full details.</p></div>",
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        "<div class='card'><h3>✍️ Add Recipe</h3><p>Create a new recipe (editors) and link ingredients cleanly.</p></div>",
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        "<div class='card'><h3>👤 My Space</h3><p>See only your recipes and manage them (edit / delete).</p></div>",
        unsafe_allow_html=True,
    )
