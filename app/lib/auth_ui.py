import streamlit as st
from app.lib.session import init_session, logout
from app.lib.supabase_client import get_supabase
from supabase_auth.errors import AuthApiError

def auth_sidebar():
    init_session()
    sb = get_supabase()

    st.sidebar.header("Account")

    if st.session_state.session:
        email = st.session_state.user.email if st.session_state.user else "Unknown"
        st.sidebar.success(f"Logged in as: {email}")
        if st.sidebar.button("Log out"):
            logout()
            st.rerun()
        return

    tab_login, tab_signup = st.sidebar.tabs(["Login", "Sign up"])

    with tab_login:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pw")
        if st.button("Login"):
            try:
                res = sb.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.session = res.session
                st.session_state.user = res.user
                st.rerun()
            except AuthApiError as e:
                msg = str(e)
                if "Email not confirmed" in msg:
                    st.error("Email not confirmed. Confirm it in Supabase Auth settings or disable email confirmation for dev.")
                else:
                    st.error(f"Login failed: {msg}")
