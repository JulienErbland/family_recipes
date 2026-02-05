import streamlit as st

from app.lib.session import init_session, is_logged_in
from app.lib.auth_ui import auth_sidebar
from app.lib.repos import get_my_role
from app.lib.ui import load_css
from app.lib.brand import sidebar_brand

import os
from app.lib.repos import set_my_role

from app.lib.ui import set_page_background, set_full_page_background


st.set_page_config(page_title="La cuisine de la Madre", page_icon="🍋", layout="wide")

#set_page_background("app/static/bg_home.png", "bg-home")
#st.markdown("<div class='bg-home'>", unsafe_allow_html=True)

set_full_page_background("app/static/bg_home.png")

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
        Le carnet de recettes de la Tribue Erbland (et plus)
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


EDITOR_CODE = st.secrets.get("EDITOR_INVITE_CODE", os.getenv("EDITOR_INVITE_CODE", ""))


# Show editor upgrade UI only for non-editors
if st.session_state.role != "editor":
    with st.expander("🔑 Become an editor"):
        st.write("If you have the family editor code, enter it to unlock recipe editing.")
        code = st.text_input("Editor code", type="password", key="home_editor_code")

        if st.button("Upgrade to editor", use_container_width=True, key="home_upgrade_btn"):
            if not EDITOR_CODE:
                st.error("Editor code is not configured on the server (missing EDITOR_INVITE_CODE).")
                st.stop()

            if code.strip() != EDITOR_CODE:
                st.error("Wrong code.")
                st.stop()

            user_id = st.session_state.session.user.id
            token = st.session_state.session.access_token

            set_my_role(token, user_id, "editor")

            # Update local state immediately
            st.session_state.role = "editor"
            st.success("Upgraded to editor ✅")
            st.rerun()


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

#st.markdown("</div>", unsafe_allow_html=True)