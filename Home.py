import streamlit as st

from app.lib.session import init_session, is_logged_in
from app.lib.auth_ui import auth_sidebar
from app.lib.repos import get_my_role
from app.lib.ui import load_css
from app.lib.brand import sidebar_brand

st.set_page_config(page_title="La cuisine de la Madre", page_icon="🍋", layout="wide")

init_session()
load_css()
sidebar_brand()

# Sidebar auth
auth_sidebar()

# =========================
# HERO
# =========================
st.markdown(
    """
    <div class="hero">
      <h1 style="margin:0">🍋 La cuisine de la Madre</h1>
      <p style="margin:8px 0 0; color:rgba(0,0,0,.65); font-size: 1.02rem">
        Un carnet de recettes simple, beau, et partagé en famille.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")

# If not logged in, show CTA and stop
if not is_logged_in():
    st.info("Log in using the sidebar to start.")
    c1, c2 = st.columns([1, 1])

    with c1:
        st.markdown(
            "<div class='card'><h3>✨ Browse</h3><p>Explore recipes by season and ingredients.</p></div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            "<div class='card'><h3>🔐 Create an account</h3><p>Sign up in the sidebar to join the family cookbook.</p></div>",
            unsafe_allow_html=True,
        )

    st.stop()

# =========================
# Logged-in content
# =========================
token = st.session_state.session.access_token

if "role" not in st.session_state or st.session_state.role is None:
    st.session_state.role = get_my_role(token)

role = st.session_state.role or "reader"
is_editor = (role == "editor")

st.write("")
st.markdown(
    f"<span class='badge'>Authenticated ✅</span>"
    f"<span class='badge'>Role: {role}</span>",
    unsafe_allow_html=True,
)

st.write("")

# =========================
# Feature cards
# =========================
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(
        "<div class='card'><h3>📚 Browse</h3>"
        "<p>Filter by season, creator, and ingredients — then open full details.</p></div>",
        unsafe_allow_html=True,
    )

with c2:
    if is_editor:
        st.markdown(
            "<div class='card'><h3>✍️ Add Recipe</h3>"
            "<p>Create a new recipe and link ingredients cleanly.</p></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='card'><h3>✍️ Add Recipe</h3>"
            "<p>You need the <b>editor</b> role to create/edit recipes.</p></div>",
            unsafe_allow_html=True,
        )

with c3:
    st.markdown(
        "<div class='card'><h3>👤 My Space</h3>"
        "<p>See your recipes and manage them (edit / delete if editor).</p></div>",
        unsafe_allow_html=True,
    )

st.write("")
st.caption("Use the pages in the left navigation to browse recipes and manage your space.")
