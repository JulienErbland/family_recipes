import streamlit as st
from app.lib.repos import ensure_my_profile


def init_session():
    if "session" not in st.session_state:
        st.session_state.session = None
        st.session_state.user = None
        st.session_state.role = None
        st.session_state.profile_ready = False

    # If logged in and profile not ensured yet
    if st.session_state.session and not st.session_state.profile_ready:
        token = st.session_state.session.access_token
        user_id = st.session_state.session.user.id

        ensure_my_profile(token, user_id)
        st.session_state.profile_ready = True

def is_logged_in() -> bool:
    return st.session_state.get("session") is not None

def logout():
    st.session_state.session = None
    st.session_state.user = None
    st.session_state.role = None
