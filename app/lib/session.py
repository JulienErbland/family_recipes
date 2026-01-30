import streamlit as st

def init_session():
    st.session_state.setdefault("session", None)   # Supabase session object
    st.session_state.setdefault("user", None)      # Supabase user object
    st.session_state.setdefault("role", None)      # 'reader' or 'editor'

def is_logged_in() -> bool:
    return st.session_state.get("session") is not None

def logout():
    st.session_state.session = None
    st.session_state.user = None
    st.session_state.role = None
